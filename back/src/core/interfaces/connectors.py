"""
Interfaces para conectores externos
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional

class IAIConnector(ABC):
    """Interfaz para conectores de IA"""
    
    @abstractmethod
    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        model: Optional[str] = None
    ) -> str:
        """Genera una respuesta de chat"""
        pass
    
    @abstractmethod
    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Genera una respuesta en streaming"""
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Cuenta los tokens en un texto"""
        pass


class IVectorDBConnector(ABC):
    """Interfaz para conectores de base de datos vectorial"""
    
    @abstractmethod
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        collection_name: str = "documents"
    ) -> None:
        """Añade documentos a la base de datos vectorial"""
        pass
    
    @abstractmethod
    def search_relevant_chunks(
        self,
        query: str,
        n_results: int = 5,
        document_ids: Optional[List[int]] = None,
        collection_name: str = "documents"
    ) -> List[Dict[str, Any]]:
        """Busca chunks relevantes"""
        pass
    
    @abstractmethod
    def delete_document_chunks(
        self,
        document_id: int,
        collection_name: str = "documents"
    ) -> int:
        """Elimina chunks de un documento"""
        pass
    
    @abstractmethod
    def get_collection_stats(self, collection_name: str = "documents") -> Dict[str, Any]:
        """Obtiene estadísticas de la colección"""
        pass


class IDocumentProcessor(ABC):
    """Interfaz para procesadores de documentos"""
    
    @abstractmethod
    def extract_text(self, file_path: str, content_type: str) -> str:
        """Extrae texto de un archivo"""
        pass
    
    @abstractmethod
    def split_into_chunks(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """Divide el texto en chunks"""
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extrae metadata de un archivo"""
        pass
