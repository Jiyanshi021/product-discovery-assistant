# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Project basics
    PROJECT_NAME: str = "Product Discovery Assistant"
    API_V1_PREFIX: str = "/api/v1"

    # Database (Neon Postgres)
    DATABASE_URL: str

    # Qdrant (vector DB)
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION: str = "products_collection_minilm"

    # Embedding model
    BGE_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # LLMs
    GROQ_API_KEY: str
    OPENAI_API_KEY: str

    # Neo4j (Knowledge Graph)
    # KG is OFF by default; turn it on later via .env
    NEO4J_ENABLED: bool = True
    NEO4J_URI: str = "neo4j+s://df6ecb3e.databases.neo4j.io"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
