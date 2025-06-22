"""
Configuración para el servicio de chat
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ChatServiceConfig:
    """Configuración para ChatService"""
    
    # Configuración de IA
    default_temperature: float = 0.7
    default_max_tokens: int = 1000
    default_ai_model: Optional[str] = None
    
    # Configuración de chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Configuración de búsqueda
    default_search_results: int = 5
    max_search_results: int = 20
    
    # Configuración de historial
    max_history_messages: int = 10
    
    # Configuración de límites
    max_message_length: int = 10000
    max_documents_per_query: int = 10
    
    # Configuración de timeouts
    ai_timeout_seconds: int = 30
    search_timeout_seconds: int = 10
    
    # Configuración de caché
    enable_response_cache: bool = True
    cache_ttl_seconds: int = 3600
    
    @classmethod
    def from_env(cls) -> 'ChatServiceConfig':
        """Crea configuración desde variables de entorno"""
        return cls(
            default_temperature=float(os.getenv('CHAT_DEFAULT_TEMPERATURE', '0.7')),
            default_max_tokens=int(os.getenv('CHAT_DEFAULT_MAX_TOKENS', '1000')),
            default_ai_model=os.getenv('CHAT_DEFAULT_AI_MODEL'),
            chunk_size=int(os.getenv('CHAT_CHUNK_SIZE', '1000')),
            chunk_overlap=int(os.getenv('CHAT_CHUNK_OVERLAP', '200')),
            default_search_results=int(os.getenv('CHAT_DEFAULT_SEARCH_RESULTS', '5')),
            max_search_results=int(os.getenv('CHAT_MAX_SEARCH_RESULTS', '20')),
            max_history_messages=int(os.getenv('CHAT_MAX_HISTORY_MESSAGES', '10')),
            max_message_length=int(os.getenv('CHAT_MAX_MESSAGE_LENGTH', '10000')),
            max_documents_per_query=int(os.getenv('CHAT_MAX_DOCUMENTS_PER_QUERY', '10')),
            ai_timeout_seconds=int(os.getenv('CHAT_AI_TIMEOUT_SECONDS', '30')),
            search_timeout_seconds=int(os.getenv('CHAT_SEARCH_TIMEOUT_SECONDS', '10')),
            enable_response_cache=os.getenv('CHAT_ENABLE_RESPONSE_CACHE', 'true').lower() == 'true',
            cache_ttl_seconds=int(os.getenv('CHAT_CACHE_TTL_SECONDS', '3600'))
        )
    
    def validate(self) -> None:
        """Valida la configuración"""
        if self.default_temperature < 0 or self.default_temperature > 2:
            raise ValueError("La temperatura debe estar entre 0 y 2")
        
        if self.default_max_tokens < 1:
            raise ValueError("max_tokens debe ser mayor que 0")
        
        if self.chunk_size < 100:
            raise ValueError("chunk_size debe ser al menos 100")
        
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap debe ser menor que chunk_size")
        
        if self.max_history_messages < 0:
            raise ValueError("max_history_messages debe ser 0 o mayor")
