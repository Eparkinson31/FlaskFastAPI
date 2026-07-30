"""
Archivist Server

FastAPI application that serves the agent loop via REST API.
Run with: python -m src.main
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import Config
from search import WikiSearch
from agent import run_agent_loop, AgentResponse
from handlers import ActionRegistry

# --- Logging ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("archivist")

# --- Global State ---

config: Config = None
search: WikiSearch = None
registry: ActionRegistry = None
schema_content: str = ""


# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    global config, search, registry, schema_content

    logger.info("Starting Archivist server...")

    # Load config
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        logger.error(f"Config not found at {config_path}")
        sys.exit(1)

    config = Config.load(config_path)
    logger.info(f"Vault path: {config.vault_path.resolve()}")

    # Ensure vault directories exist
    config.wiki_path.mkdir(parents=True, exist_ok=True)
    config.raw_path.mkdir(parents=True, exist_ok=True)
    config.outputs_path.mkdir(parents=True, exist_ok=True)

    # Load schema
    if config.schema_path.exists():
        schema_content = config.schema_path.read_text(encoding="utf-8")
        logger.info("Schema loaded")
    else:
        schema_content = "No schema file found. Maintain wiki pages with clear structure."
        logger.warning("No schema.md found in vault")

    # Initialise search index
    search = WikiSearch(
        db_path=config._raw.get("search", {}).get("db_path", "./archivist-index.db"),
        wiki_path=config.wiki_path,
    )
    if config._raw.get("search", {}).get("rebuild_on_startup", True):
        search.rebuild()

    # Initialise action registry
    registry = ActionRegistry(config=config, search=search)
    logger.info(f"Registered {len(registry.handlers)} actions")

    # Check Ollama connectivity
    try:
        import ollama
        route = config.resolve_model_route("default")
        client = ollama.AsyncClient(host=route.host)
        models = await client.list()
        model_names = [m.model for m in models.models] if hasattr(models, 'models') else []
        logger.info(f"Ollama connected. Available models: {model_names[:5]}")
    except Exception as e:
        logger.warning(f"Could not connect to Ollama: {e}")
        logger.warning("Server will start but chat will fail until Ollama is available")

    logger.info(f"Archivist ready on http://{config.host}:{config.port}")
    yield

    # Shutdown
    if search:
        search.close()
    logger.info("Archivist shut down")


# --- App ---

app = FastAPI(
    title="Archivist",
    description="Personal wiki assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Electron app connects from file:// or localhost
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---

class ChatRequest(BaseModel):
    message: str
    task_type: str = "default"
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    text: str
    actions_taken: list[dict] = []
    model_used: str = ""
    mode_used: str = ""
    iterations: int = 0


class WikiPageResponse(BaseModel):
    path: str
    content: str
    exists: bool


class SearchResult(BaseModel):
    path: str
    title: str
    snippet: str


# --- Endpoints ---

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "vault": str(config.vault_path.resolve()),
        "pages_indexed": len(search.list_pages()) if search else 0,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the agent and get a response."""
    logger.info(f"Chat request: {request.message[:80]}...")

    # Load current wiki index
    wiki_index = ""
    if config.index_path.exists():
        wiki_index = config.index_path.read_text(encoding="utf-8")

    # Run the agent loop
    result: AgentResponse = await run_agent_loop(
        user_message=request.message,
        config=config,
        action_handlers=registry.handlers,
        action_descriptions=registry.descriptions,
        schema=schema_content,
        wiki_index=wiki_index,
        task_type=request.task_type,
    )

    return ChatResponse(
        text=result.text,
        actions_taken=result.actions_taken,
        model_used=result.model_used,
        mode_used=result.mode_used,
        iterations=result.iterations,
    )


@app.get("/wiki/{path:path}", response_model=WikiPageResponse)
async def get_wiki_page(path: str):
    """Read a wiki page."""
    full_path = config.vault_path / path
    if full_path.exists() and full_path.is_file():
        return WikiPageResponse(
            path=path,
            content=full_path.read_text(encoding="utf-8"),
            exists=True,
        )
    return WikiPageResponse(path=path, content="", exists=False)


@app.get("/search")
async def search_wiki(q: str, limit: int = 5):
    """Search wiki pages."""
    results = search.search(q, limit=limit)
    return {"query": q, "results": results}


@app.get("/wiki")
async def list_wiki_pages(directory: str | None = None, type: str | None = None):
    """List wiki pages."""
    results = search.list_pages(directory=directory, page_type=type)
    return {"pages": results}


@app.get("/outputs")
async def list_outputs():
    """List generated output files."""
    outputs = []
    for f in config.outputs_path.rglob("*"):
        if f.is_file() and f.name != ".gitkeep":
            outputs.append({
                "path": str(f.relative_to(config.outputs_path)),
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })
    return {"outputs": sorted(outputs, key=lambda x: x["modified"], reverse=True)}


# --- CLI Entry Point ---
"""==
def cli():
   # Command-line entry point.
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=config.host if config else "127.0.0.1",
        port=config.port if config else 8420,
        reload=True,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=8420,
        reload=True,
    ) 
"""