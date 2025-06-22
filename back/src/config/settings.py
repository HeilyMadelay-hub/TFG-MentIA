"""
Configuración de la aplicación con todas las variables centralizadas.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from loguru import logger

class Settings(BaseSettings):
    """
    Configuraciones principales de la aplicación - Versión mejorada
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
    CHROMA_HOST: str = Field(default="localhost", env="CHROMA_HOST")
    CHROMA_PORT: int = Field(default=8050, env="CHROMA_PORT")
    CHROMA_TELEMETRY_ENABLED: bool = False
    CHROMA_SERVER_TIMEOUT: int = 300
    
    # Documentos - Límites claros y optimización
    MAX_DOCUMENT_SIZE_MB: int = Field(default=100, env="MAX_DOCUMENT_SIZE_MB")  # Tamaño máximo en MB
    MAX_DOCUMENT_SIZE_BYTES: int = Field(default=104857600, env="MAX_DOCUMENT_SIZE_BYTES")  # 100MB en bytes
    DOCUMENT_PROCESSING_TIMEOUT: int = 180
    
    # Límites específicos por tipo de archivo
    MAX_PDF_SIZE_MB: int = Field(default=50, env="MAX_PDF_SIZE_MB")  # PDFs hasta 50MB
    MAX_TEXT_SIZE_MB: int = Field(default=10, env="MAX_TEXT_SIZE_MB")  # Archivos de texto hasta 10MB
    MAX_EXCEL_SIZE_MB: int = Field(default=25, env="MAX_EXCEL_SIZE_MB")  # Excel hasta 25MB
    
    # Streaming configuration
    STREAMING_CHUNK_SIZE: int = Field(default=1048576, env="STREAMING_CHUNK_SIZE")  # 1MB chunks
    PDF_PROCESSING_CHUNK_SIZE: int = Field(default=5242880, env="PDF_PROCESSING_CHUNK_SIZE")  # 5MB para PDFs
    
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
    
    # Refresh Token Configuration
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, env="REFRESH_TOKEN_EXPIRE_DAYS")  # 30 días por defecto
    REFRESH_TOKEN_ROTATE: bool = Field(default=True, env="REFRESH_TOKEN_ROTATE")  # Rotar tokens en cada refresh
    REFRESH_TOKEN_BLACKLIST_ENABLED: bool = Field(default=True, env="REFRESH_TOKEN_BLACKLIST_ENABLED")
    
    # Configuración RAG
    RAG_CHUNK_SIZE: int = Field(default=1000, env="RAG_CHUNK_SIZE")
    RAG_CHUNK_OVERLAP: int = Field(default=100, env="RAG_CHUNK_OVERLAP")
    RAG_MAX_TOKENS: int = Field(default=1500, env="RAG_MAX_TOKENS")
    RAG_NUM_RESULTS: int = Field(default=5, env="RAG_NUM_RESULTS")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    LOG_FILE_MAX_SIZE: int = Field(default=10485760, env="LOG_FILE_MAX_SIZE")  # 10MB
    LOG_FILE_BACKUP_COUNT: int = Field(default=5, env="LOG_FILE_BACKUP_COUNT")
    
    # AI/ML Models Configuration
    SENTENCE_TRANSFORMER_MODEL: str = Field(default="all-MiniLM-L6-v2", env="SENTENCE_TRANSFORMER_MODEL")
    DEFAULT_CHUNK_SIZE: int = Field(default=1000, env="DEFAULT_CHUNK_SIZE")
    DEFAULT_CHUNK_OVERLAP: int = Field(default=100, env="DEFAULT_CHUNK_OVERLAP")
    
    # File Processing
    TEXT_PROCESSING_CHUNK_SIZE: int = Field(default=8192, env="TEXT_PROCESSING_CHUNK_SIZE")  # 8KB para texto
    BINARY_PROCESSING_CHUNK_SIZE: int = Field(default=65536, env="BINARY_PROCESSING_CHUNK_SIZE")  # 64KB para binarios
    
    # External Services Timeouts
    EXTERNAL_SERVICE_TIMEOUT: int = Field(default=30, env="EXTERNAL_SERVICE_TIMEOUT")  # 30 segundos
    GEMINI_REQUEST_TIMEOUT: int = Field(default=60, env="GEMINI_REQUEST_TIMEOUT")  # 60 segundos
    CHROMA_OPERATION_TIMEOUT: int = Field(default=35, env="CHROMA_OPERATION_TIMEOUT")  # 35 segundos
    
    # Email SMTP Configuration
    SMTP_HOST: Optional[str] = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    FROM_EMAIL: Optional[str] = Field(default=None, env="FROM_EMAIL")
    
    # Frontend URL para links en emails
    FRONTEND_URL: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    
    # CORS Configuration
    CORS_ORIGINS: str = Field(
        default="http://localhost:53793,http://localhost:3000,http://localhost:8080",
        env="CORS_ORIGINS"
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")  # requests per minute
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # window in seconds
    
    # API Rate Limits por endpoint
    RATE_LIMIT_REGISTER: str = "5/minute"  # 5 registros por minuto
    RATE_LIMIT_LOGIN: str = "10/minute"    # 10 intentos de login por minuto
    RATE_LIMIT_CHAT: str = "30/minute"     # 30 mensajes de chat por minuto
    RATE_LIMIT_UPLOAD: str = "10/minute"   # 10 uploads por minuto
    RATE_LIMIT_DEFAULT: str = "100/minute" # 100 requests por minuto por defecto
    
    # Sentry
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")

    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.SECRET_KEY
    
    @property
    def JWT_EXPIRES_MINUTES(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES
    
    @property
    def get_cors_origins(self) -> list:
        """Convierte la cadena de orígenes CORS en una lista"""
        if self.APP_ENVIRONMENT == "development":
            # En desarrollo, permitir localhost con diferentes puertos
            return [
                "http://localhost:53793",
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:8080",
                "http://localhost:5173",  # Vite default
                "http://127.0.0.1:53793",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8080"
            ]
        else:
            # En producción, usar solo los orígenes especificados
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
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

# Configuración de Loguru
logger.add("logs/app.log", rotation="10 MB", retention="10 days", level="DEBUG")

# Inicializar Sentry si el DSN está configurado
if Settings().SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    import logging

    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Captura logs de nivel INFO y superior
        event_level=logging.ERROR  # Envía eventos de nivel ERROR y superior a Sentry
    )

    sentry_sdk.init(
        dsn=Settings().SENTRY_DSN,
        integrations=[sentry_logging]
    )

# Instancia global
settings = Settings()

def get_settings() -> Settings:
    return settings
