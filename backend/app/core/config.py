"""Application configuration.

The project keeps environment-specific values in ``backend/.env`` and exposes
them through this settings object. This version uses only the Python standard
library so the V0.1 project can run before dependencies are installed.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent
ENV_FILE = BACKEND_DIR / ".env"


def _load_env_file(path: Path = ENV_FILE) -> Dict[str, str]:
    """Load simple KEY=VALUE pairs from a .env file."""

    values: Dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value

    return values


def _get_str(env: Dict[str, str], key: str, default: str = "") -> str:
    return env.get(key, default)


def _get_int(env: Dict[str, str], key: str, default: int) -> int:
    value = env.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_list(env: Dict[str, str], key: str, default: List[str]) -> List[str]:
    value = env.get(key)
    if not value:
        return default

    text = value.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]

    return [
        item.strip().strip('"').strip("'")
        for item in text.split(",")
        if item.strip()
    ]


def _resolve_backend_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from ``backend/.env``."""

    # LLM
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model_id: str = "gpt-4o-mini"
    llm_timeout: int = 60

    # Embedding
    embed_model_type: str = "openai"
    embed_model_name: str = "text-embedding-3-small"
    embed_api_key: str = ""
    embed_base_url: str = ""

    # Search providers
    tavily_api_key: str = ""
    serpapi_api_key: str = ""

    # Qdrant vector store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "learning_course_materials"
    qdrant_vector_size: int = 1536
    qdrant_distance: str = "Cosine"
    qdrant_timeout: int = 30

    # Neo4j knowledge graph, reserved for later versions.
    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    neo4j_max_connection_lifetime: int = 3600
    neo4j_max_connection_pool_size: int = 50
    neo4j_connection_timeout: int = 30

    # API server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:5173"])
    log_level: str = "INFO"

    # V0.1 course RAG settings
    course_materials_dir: str = "data/course_materials"
    rag_index_dir: str = "data/vector_store"
    rag_top_k: int = 5
    chunk_size: int = 800
    chunk_overlap: int = 120

    # Optional third-party tools, reserved for later versions.
    unsplash_access_key: str = ""
    unsplash_secret_key: str = ""
    amap_api_key: str = ""

    @property
    def course_materials_path(self) -> Path:
        """Absolute path to course materials."""

        return _resolve_backend_path(self.course_materials_dir)

    @property
    def rag_index_path(self) -> Path:
        """Absolute path to the local RAG index directory."""

        return _resolve_backend_path(self.rag_index_dir)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    env = _load_env_file()
    return Settings(
        llm_api_key=_get_str(env, "LLM_API_KEY"),
        llm_base_url=_get_str(env, "LLM_BASE_URL"),
        llm_model_id=_get_str(env, "LLM_MODEL_ID", "gpt-4o-mini"),
        llm_timeout=_get_int(env, "LLM_TIMEOUT", 60),
        embed_model_type=_get_str(env, "EMBED_MODEL_TYPE", "openai"),
        embed_model_name=_get_str(env, "EMBED_MODEL_NAME", "text-embedding-3-small"),
        embed_api_key=_get_str(env, "EMBED_API_KEY"),
        embed_base_url=_get_str(env, "EMBED_BASE_URL"),
        tavily_api_key=_get_str(env, "TAVILY_API_KEY"),
        serpapi_api_key=_get_str(env, "SERPAPI_API_KEY"),
        qdrant_url=_get_str(env, "QDRANT_URL", "http://localhost:6333"),
        qdrant_api_key=_get_str(env, "QDRANT_API_KEY"),
        qdrant_collection=_get_str(env, "QDRANT_COLLECTION", "learning_course_materials"),
        qdrant_vector_size=_get_int(env, "QDRANT_VECTOR_SIZE", 1536),
        qdrant_distance=_get_str(env, "QDRANT_DISTANCE", "Cosine"),
        qdrant_timeout=_get_int(env, "QDRANT_TIMEOUT", 30),
        neo4j_uri=_get_str(env, "NEO4J_URI"),
        neo4j_username=_get_str(env, "NEO4J_USERNAME"),
        neo4j_password=_get_str(env, "NEO4J_PASSWORD"),
        neo4j_database=_get_str(env, "NEO4J_DATABASE", "neo4j"),
        neo4j_max_connection_lifetime=_get_int(env, "NEO4J_MAX_CONNECTION_LIFETIME", 3600),
        neo4j_max_connection_pool_size=_get_int(env, "NEO4J_MAX_CONNECTION_POOL_SIZE", 50),
        neo4j_connection_timeout=_get_int(env, "NEO4J_CONNECTION_TIMEOUT", 30),
        host=_get_str(env, "HOST", "0.0.0.0"),
        port=_get_int(env, "PORT", 8000),
        cors_origins=_get_list(env, "CORS_ORIGINS", ["http://localhost:5173"]),
        log_level=_get_str(env, "LOG_LEVEL", "INFO"),
        course_materials_dir=_get_str(env, "COURSE_MATERIALS_DIR", "data/course_materials"),
        rag_index_dir=_get_str(env, "RAG_INDEX_DIR", "data/vector_store"),
        rag_top_k=_get_int(env, "RAG_TOP_K", 5),
        chunk_size=_get_int(env, "CHUNK_SIZE", 800),
        chunk_overlap=_get_int(env, "CHUNK_OVERLAP", 120),
        unsplash_access_key=_get_str(env, "UNSPLASH_ACCESS_KEY"),
        unsplash_secret_key=_get_str(env, "UNSPLASH_SECRET_KEY"),
        amap_api_key=_get_str(env, "AMAP_API_KEY"),
    )
