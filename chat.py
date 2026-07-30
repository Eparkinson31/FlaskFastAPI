"""
Archivist Terminal Chat

Quick way to test the agent loop without the full server.
Run with: python -m src.chat

This connects directly to Ollama — no FastAPI server needed.
"""

import asyncio
import sys
from pathlib import Path

from config import Config
from search import WikiSearch
from agent import run_agent_loop
from handlers import ActionRegistry


async def main():
    print("=" * 50)
    print("  ARCHIVIST — Terminal Chat")
    print("=" * 50)
    print()

    # Load config
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        print(f"Error: {config_path} not found. Run from the project root.")
        sys.exit(1)

    config = Config.load(config_path)
    print(f"Vault: {config.vault_path.resolve()}")

    # Load schema
    schema = ""
    if config.schema_path.exists():
        schema = config.schema_path.read_text(encoding="utf-8")
        print("Schema: loaded")

    # Init search
    search = WikiSearch(
        db_path=config._raw.get("search", {}).get("db_path", "./archivist-index.db"),
        wiki_path=config.wiki_path,
    )
    search.rebuild()
    pages = search.list_pages()
    print(f"Wiki pages indexed: {len(pages)}")

    # Init actions
    registry = ActionRegistry(config=config, search=search)
    print(f"Actions available: {len(registry.handlers)}")

    # Detect model
    route = config.resolve_model_route("default")
    print(f"Model: {route.model} @ {route.host}")
    print()
    print("Type your message. 'quit' to exit.")
    print("-" * 50)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        # Load fresh index each time (it may have changed)
        wiki_index = ""
        if config.index_path.exists():
            wiki_index = config.index_path.read_text(encoding="utf-8")

        print("\n[thinking...]")

        try:
            result = await run_agent_loop(
                user_message=user_input,
                config=config,
                action_handlers=registry.handlers,
                action_descriptions=registry.descriptions,
                schema=schema,
                wiki_index=wiki_index,
            )

            # Show actions taken
            if result.actions_taken:
                print(f"\n[{result.mode_used} mode | {result.iterations} iterations]")
                for a in result.actions_taken:
                    print(f"  → {a['action']}({', '.join(f'{k}={repr(v)[:40]}' for k,v in a['params'].items())})")

            print(f"\nArchivist: {result.text}")

        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()

    search.close()
    print("\nGoodbye.")


if __name__ == "__main__":
    asyncio.run(main())
