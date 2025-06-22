"""
Servicio para manejar streaming de respuestas AI
"""
import logging
from typing import List, Dict, Any, AsyncGenerator
from src.utils.ai_connector import get_openai_connector
from src.core.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)

class ChatStreamingService:
    """Servicio para gestionar streaming de respuestas AI"""
    
    def __init__(self):
        self.ai_connector = get_openai_connector()
        
    async def stream_ai_response(
        self,
        question: str,
        chat_id: int,
        user_id: int,
        document_ids: List[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Genera respuesta AI en streaming
        
        Args:
            question: Pregunta del usuario
            chat_id: ID del chat
            user_id: ID del usuario
            document_ids: IDs de documentos para contexto
            
        Yields:
            str: Chunks de la respuesta
        """
        try:
            # Implementar búsqueda de contexto en documentos
            context = []
            if document_ids:
                from src.services.document_service import DocumentService
                from src.utils.chromadb_connector import ChromaDBConnector
                
                document_service = DocumentService()
                chromadb = ChromaDBConnector()
                
                # Buscar chunks relevantes en los documentos especificados
                relevant_chunks = chromadb.search_relevant_chunks(
                    query=question,
                    document_ids=document_ids,
                    n_results=5  # Número de chunks más relevantes
                )
                
                # Construir contexto a partir de los chunks encontrados
                for chunk in relevant_chunks:
                    document_id = chunk.get('metadata', {}).get('document_id')
                    content = chunk.get('content', '')
                    
                    # Obtener información del documento
                    try:
                        document = document_service.get_document(document_id, user_id)
                        doc_title = document.title
                    except:
                        doc_title = f"Documento {document_id}"
                    
                    context.append(f"[{doc_title}]: {content}")
                
                logger.info(f"Encontrados {len(context)} chunks relevantes para la pregunta")
            
            # Preparar mensajes para el modelo
            messages = [
                {
                    "role": "system",
                    "content": "Eres un asistente útil que responde basándose en el contexto proporcionado."
                }
            ]
            
            if context:
                messages.append({
                    "role": "system",
                    "content": f"Contexto: {' '.join(context)}"
                })
                
            messages.append({
                "role": "user",
                "content": question
            })
            
            # Generar respuesta en streaming
            async for chunk in self.ai_connector.stream_completion(messages):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error en streaming: {str(e)}")
            yield f"\n[Error generando respuesta: {str(e)}]"
            
    def estimate_tokens(self, text: str) -> int:
        """
        Estima el número de tokens en un texto
        
        Args:
            text: Texto a analizar
            
        Returns:
            int: Número estimado de tokens
        """
        # Estimación simple: ~4 caracteres por token
        return len(text) // 4
