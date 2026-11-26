import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    
    # AI Provider routing: auto, gemini, groq, local
    AI_PROVIDER: str = "auto"

    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # Groq AI
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    
    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "fortivoice_crm"
    
    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    
    # RAG Settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    MAX_RETRIEVAL_RESULTS: int = 4

    def __init__(self, **values):
        super().__init__(**values)
        # If GEMINI_API_KEY is not set or empty, check environment variables (GEMINI_API_KEY and GOOGLE_API_KEY)
        if not self.GEMINI_API_KEY:
            self.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        # If GROQ_API_KEY is not set or empty, check environment variables
        if not self.GROQ_API_KEY:
            self.GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or ""
        # If AI_PROVIDER is in env, respect it
        if "AI_PROVIDER" in os.environ and os.environ["AI_PROVIDER"]:
            self.AI_PROVIDER = os.environ["AI_PROVIDER"].lower()

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = (
            ".env",
            "backend/.env",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", ".env")
        )
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()
