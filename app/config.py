from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://msauser:msapass123@localhost:5432/msa_db"
    
    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # Paths
    DATA_DIR: str = "/app/data/tasks"
    LOG_DIR: str = "/app/logs"
    
    # Limits for safety (prototype)
    MAX_SEQUENCES: int = 5000
    MAX_SEQUENCE_LENGTH: int = 50000  # ~50kb per seq for genes/genomes
    MSA_TIMEOUT_SECONDS: int = 3600 * 6  # 6 hours max per task
    
    # NCBI Entrez (optional, set your email)
    NCBI_EMAIL: str = "biomsa-service@example.com"
    NCBI_API_KEY: str = ""  # optional, increases rate limit
    
    # Demo mode (True = использовать mock данные вместо реальных скачиваний)
    DEMO_MODE: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()