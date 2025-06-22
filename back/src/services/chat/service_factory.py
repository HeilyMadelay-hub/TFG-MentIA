"""
Factory para crear servicios y dependencias
"""
from typing import Optional
import logging

from src.core.interfaces.connectors import IAIConnector, IVectorDBConnector
from src.utils.ai_connector import OpenAIConnector
from src.utils.chromadb_connector import ChromaDBConnector
from src.services.chat.spelling_correction_service import SpellingCorrectionService
from src.services.chat.context_detection_service import ContextDetectionService
from src.services.chat.message_enrichment_service import MessageEnrichmentService
from src.services.chat.ai_response_service import AIResponseService
from src.services.chat.chat_config import ChatServiceConfig

logger = logging.getLogger(__name__)

class ServiceFactory:
    """Factory para crear instancias de servicios"""
    
    _instances = {}
    
    @classmethod
    def get_ai_connector(cls, provider: str = "openai") -> IAIConnector:
        """
        Obtiene una instancia de conector de IA
        
        Args:
            provider: Proveedor de IA (openai, anthropic, etc.)
            
        Returns:
            IAIConnector: Instancia del conector
        """
        key = f"ai_connector_{provider}"
        
        if key not in cls._instances:
            if provider == "openai":
                cls._instances[key] = OpenAIConnector()
            else:
                raise ValueError(f"Proveedor de IA no soportado: {provider}")
            
            logger.info(f"Creada instancia de {provider} AI connector")
        
        return cls._instances[key]
    
    @classmethod
    def get_vector_db_connector(cls, provider: str = "chromadb") -> IVectorDBConnector:
        """
        Obtiene una instancia de conector de base de datos vectorial
        
        Args:
            provider: Proveedor de BD vectorial (chromadb, pinecone, etc.)
            
        Returns:
            IVectorDBConnector: Instancia del conector
        """
        key = f"vector_db_{provider}"
        
        if key not in cls._instances:
            if provider == "chromadb":
                cls._instances[key] = ChromaDBConnector()
            else:
                raise ValueError(f"Proveedor de BD vectorial no soportado: {provider}")
            
            logger.info(f"Creada instancia de {provider} vector DB connector")
        
        return cls._instances[key]
    
    @classmethod
    def get_spelling_service(cls) -> SpellingCorrectionService:
        """Obtiene instancia del servicio de corrección ortográfica"""
        if "spelling_service" not in cls._instances:
            cls._instances["spelling_service"] = SpellingCorrectionService()
            logger.info("Creada instancia de SpellingCorrectionService")
        
        return cls._instances["spelling_service"]
    
    @classmethod
    def get_context_service(cls) -> ContextDetectionService:
        """Obtiene instancia del servicio de detección de contexto"""
        if "context_service" not in cls._instances:
            cls._instances["context_service"] = ContextDetectionService()
            logger.info("Creada instancia de ContextDetectionService")
        
        return cls._instances["context_service"]
    
    @classmethod
    def get_enrichment_service(cls) -> MessageEnrichmentService:
        """Obtiene instancia del servicio de enriquecimiento"""
        if "enrichment_service" not in cls._instances:
            cls._instances["enrichment_service"] = MessageEnrichmentService()
            logger.info("Creada instancia de MessageEnrichmentService")
        
        return cls._instances["enrichment_service"]
    
    @classmethod
    def get_ai_response_service(cls, ai_provider: str = "openai") -> AIResponseService:
        """Obtiene instancia del servicio de respuestas de IA"""
        key = f"ai_response_service_{ai_provider}"
        
        if key not in cls._instances:
            ai_connector = cls.get_ai_connector(ai_provider)
            cls._instances[key] = AIResponseService(ai_connector)
            logger.info(f"Creada instancia de AIResponseService con {ai_provider}")
        
        return cls._instances[key]
    
    @classmethod
    def get_chat_config(cls) -> ChatServiceConfig:
        """Obtiene la configuración del chat"""
        if "chat_config" not in cls._instances:
            config = ChatServiceConfig.from_env()
            config.validate()
            cls._instances["chat_config"] = config
            logger.info("Cargada configuración de ChatService")
        
        return cls._instances["chat_config"]
    
    @classmethod
    def reset(cls):
        """Resetea todas las instancias (útil para testing)"""
        cls._instances.clear()
        logger.info("Factory reseteado - todas las instancias eliminadas")
    
    def create_spelling_service(self) -> SpellingCorrectionService:
        """Crea instancia del servicio de corrección ortográfica"""
        return self.get_spelling_service()
    
    def create_context_service(self) -> ContextDetectionService:
        """Crea instancia del servicio de detección de contexto"""
        return self.get_context_service()
    
    def create_enrichment_service(self) -> MessageEnrichmentService:
        """Crea instancia del servicio de enriquecimiento"""
        return self.get_enrichment_service()
    
    def create_ai_service(self, ai_provider: str = "openai") -> AIResponseService:
        """Crea instancia del servicio de respuestas de IA"""
        return self.get_ai_response_service(ai_provider)
