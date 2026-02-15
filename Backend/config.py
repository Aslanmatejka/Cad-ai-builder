"""
Configuration Management for Chat-to-CAD Platform
Loads environment variables and provides typed settings
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    ANTHROPIC_API_KEY: str
    
    # AI Configuration
    AI_MODEL_NAME: str = "claude-opus-4-20250514"
    AI_MAX_TOKENS: int = 16384
    AI_TEMPERATURE: float = 0.3
    
    # Server Configuration
    PORT: int = 3001
    HOST: str = "0.0.0.0"
    DEBUG: bool = False
    
    # CAD Engine
    CAD_ENGINE: str = "cadquery"
    
    # Paths
    EXPORTS_DIR: Path = Path(__file__).parent.parent / "exports"
    CAD_DIR: Path = EXPORTS_DIR / "cad"
    
    # MySQL Database Configuration
    DB_HOST: Optional[str] = "localhost"
    DB_PORT: int = 3306
    DB_USER: Optional[str] = "root"
    DB_PASSWORD: Optional[str] = None
    DB_NAME: Optional[str] = "product_builder"
    DB_CONNECTION_LIMIT: int = 10
    
    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env

# Singleton settings instance
settings = Settings()

# Ensure directories exist
settings.CAD_DIR.mkdir(parents=True, exist_ok=True)
