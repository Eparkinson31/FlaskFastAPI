"""
Archivist Configuration

Loads and validates config.yaml, provides typed access to settings.
"""

from dataclasses import dataclass, field
from pathlib import Path

#pip install pyyaml
import yaml


@dataclass
class ModelRoute:
    model: str
    host: str


@dataclass
class LLMConfig:
    mode: str = "auto"
    max_iterations: int = 10
    temperature: float = 0.1
    context_length: int = 32768


@dataclass
class Config:
    vault_path: Path = field(default_factory=lambda: Path("./vault"))
    outputs_path: Path = field(default_factory=lambda: Path("./vault/outputs"))
    host: str = "127.0.0.1"
    port: int = 8420
    ws_port: int = 8421
    llm: LLMConfig = field(default_factory=LLMConfig)

    # Raw config for model routing
    _raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def load(cls, path: str | Path = "config/config.yaml") -> "Config":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")

        with open(path) as f:
            raw = yaml.safe_load(f)

        app = raw.get("app", {})
        server = raw.get("server", {})
        llm_raw = raw.get("llm", {})

        return cls(
            vault_path=Path(app.get("vault_path", "./vault")),
            outputs_path=Path(app.get("outputs_path", "./vault/outputs")),
            host=server.get("host", "127.0.0.1"),
            port=server.get("port", 8420),
            ws_port=server.get("ws_port", 8421),
            llm=LLMConfig(
                mode=llm_raw.get("mode", "auto"),
                max_iterations=llm_raw.get("max_iterations", 10),
                temperature=llm_raw.get("temperature", 0.1),
                context_length=llm_raw.get("context_length", 32768),
            ),
            _raw=raw,
        )

    def resolve_model_route(self, task_type: str = "default") -> ModelRoute:
        """Resolve which model and host to use for a given task type."""
        models = self._raw.get("models", {})
        routing = models.get("routing", {})

        # Get the route string (e.g., "local.quick" or "remote.heavy")
        route_str = routing.get(task_type, routing.get("default", "local.default"))
        tier, level = route_str.split(".")

        tier_config = models.get(tier, {})
        model = tier_config.get(level, "qwen3:8b")
        host = tier_config.get("host", "http://localhost:11434")

        # If remote is requested but disabled/unreachable, fall back to local
        if tier == "remote" and not models.get("remote", {}).get("enabled", False):
            local = models.get("local", {})
            model = local.get("default", "qwen3:8b")
            host = local.get("host", "http://localhost:11434")

        return ModelRoute(model=model, host=host)

    @property
    def schema_path(self) -> Path:
        return self.vault_path / "schema.md"

    @property
    def index_path(self) -> Path:
        return self.vault_path / "index.md"

    @property
    def log_path(self) -> Path:
        return self.vault_path / "log.md"

    @property
    def wiki_path(self) -> Path:
        return self.vault_path / "wiki"

    @property
    def raw_path(self) -> Path:
        return self.vault_path / "raw"
