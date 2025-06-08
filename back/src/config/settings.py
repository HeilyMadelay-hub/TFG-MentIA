"""
Configuración temporal para solucionar el problema de DATABASE_URL
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict

class Settings(BaseSettings):
    """
    Configuraciones principales de la aplicación - Versión simplificada
    """
    # Información general
    APP_NAME: str = "ChatBotMadSL"
    APP_VERSION: str = "1.0.0"
    APP_ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Servidor
    HOST: str = "127.0.0.1"
    PORT: int = 2690
    
    # Base de datos - usando Field para mayor flexibilidad
    SUPABASE_URL: str = Field(default="", env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(default="", env="SUPABASE_KEY")
    SUPABASE_SERVICE_KEY: str = Field(default="", env="SUPABASE_SERVICE_KEY")
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_TELEMETRY_ENABLED: bool = False
    CHROMA_SERVER_TIMEOUT: int = 300
    
    # Documentos
    MAX_DOCUMENT_SIZE: int = 30
    DOCUMENT_PROCESSING_TIMEOUT: int = 180
    
    # Docker
    DOCKER_ENV: bool = False
    
    # Gemini
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    
    # Seguridad
    SECRET_KEY: str = Field(default="clave-secreta-temporal", env="SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 57600
    
    # Configuración RAG
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 100
    RAG_MAX_TOKENS: int = 1500
    RAG_NUM_RESULTS: int = 5
    
    # Email SMTP Configuration
    SMTP_HOST: Optional[str] = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    FROM_EMAIL: Optional[str] = Field(default=None, env="FROM_EMAIL")
    
    # Frontend URL para links en emails
    FRONTEND_URL: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    
    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.SECRET_KEY
    
    @property
    def JWT_EXPIRES_MINUTES(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignorar campos extras en lugar de permitirlos
        env_nested_delimiter="__"
    )

# Cargar variables de entorno manualmente si es necesario
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

# Instancia global
settings = Settings()

def get_settings() -> Settings:
    return settings
