"""
Servicio para enriquecer mensajes con contexto y RAG
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.services.document_service import DocumentService
from src.utils.chromadb_connector import ChromaDBConnector
from src.core.exceptions import ExternalServiceException, DatabaseException

logger = logging.getLogger(__name__)

class MessageEnrichmentService:
    """Servicio para enriquecer mensajes con contexto de documentos y RAG"""
    
    def __init__(self):
        self.document_service = DocumentService()
        self.chromadb = ChromaDBConnector()
    
    async def enrich_with_documents(
        self, 
        message: str, 
        document_ids: List[int],
        user_id: int,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """
        Enriquece un mensaje con contexto de documentos usando RAG.
        
        Args:
            message: Mensaje/pregunta del usuario
            document_ids: IDs de documentos a consultar
            user_id: ID del usuario
            n_results: Número de resultados a obtener
            
        Returns:
            Dict con la respuesta enriquecida y metadata
        """
        try:
            logger.info(f"Enriqueciendo mensaje con {len(document_ids)} documentos")
            
            # Usar el servicio de documentos para obtener respuesta RAG
            rag_result = self.document_service.get_rag_response(
                query=message,
                user_id=user_id,
                n_results=n_results,
                document_ids=document_ids
            )
            
            # Extraer información adicional
            documents_used = rag_result.get("documents", [])
            relevance_scores = []
            
            for doc in documents_used:
                relevance_scores.append({
                    "document_id": doc.get("document_id"),
                    "title": doc.get("title"),
                    "relevance": doc.get("relevance_score", 0.0)
                })
            
            return {
                "response": rag_result["response"],
                "documents_used": len(documents_used),
                "relevance_scores": relevance_scores,
                "enrichment_method": "rag",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error enriqueciendo mensaje con documentos: {str(e)}")
            raise ExternalServiceException(f"Error al procesar documentos: {str(e)}")
    
    async def detect_document_queries(self, message: str) -> bool:
        """
        Detecta si un mensaje es una consulta sobre documentos.
        
        Args:
            message: Mensaje a analizar
            
        Returns:
            bool: True si es una consulta sobre documentos
        """
        message_lower = message.lower().strip()
        
        # Palabras clave que indican consulta sobre documentos
        document_keywords = [
            "documento", "archivo", "pdf", "txt", "texto",
            "resume", "resumir", "resumen", "busca", "buscar", 
            "encuentra", "analiza", "analizar", "información",
            "tramite", "trámite", "contenido", "dice", "explica",
            "habla", "trata", "menciona", "contiene", "sobre"
        ]
        
        # Frases específicas sobre listar documentos
        list_phrases = [
            "qué documentos tengo",
            "que documentos tengo", 
            "mis documentos",
            "listar documentos",
            "mostrar documentos",
            "cuáles son mis documentos",
            "documentos disponibles",
            "qué archivos tengo",
            "documentos subidos"
        ]
        
        # Verificar frases completas primero
        for phrase in list_phrases:
            if phrase in message_lower:
                return True
        
        # Verificar palabras clave
        return any(keyword in message_lower for keyword in document_keywords)
    
    async def build_document_list_response(self, user_id: int) -> str:
        """
        Construye una respuesta formateada con la lista de documentos del usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            str: Respuesta formateada con la lista de documentos
        """
        try:
            # Obtener documentos del usuario
            documents = self.document_service.list_user_documents(user_id, limit=100)
            
            if not documents:
                return (
                    "No tienes documentos subidos aún. \n\n"
                    "Puedes subir documentos desde la sección 'Mis Documentos' "
                    "en el menú principal. Acepto archivos PDF y TXT."
                )
            
            # Agrupar por tipo de contenido
            docs_by_type = {}
            for doc in documents:
                doc_type = doc.content_type or "otro"
                if doc_type not in docs_by_type:
                    docs_by_type[doc_type] = []
                docs_by_type[doc_type].append(doc)
            
            # Construir respuesta formateada
            response_parts = [f"Tienes {len(documents)} documento(s) en tu biblioteca:\n"]
            
            for doc_type, docs in docs_by_type.items():
                type_name = {
                    "application/pdf": "📄 Documentos PDF",
                    "text/plain": "📝 Documentos de texto (TXT)"
                }.get(doc_type, "📎 Otros archivos")
                
                response_parts.append(f"\n{type_name}:")
                for i, doc in enumerate(docs, 1):
                    fecha = doc.created_at.strftime('%d/%m/%Y') if doc.created_at else "Fecha desconocida"
                    size_mb = doc.file_size / (1024 * 1024) if doc.file_size else 0
                    response_parts.append(
                        f"  {i}. **{doc.title}** ({size_mb:.1f} MB) - Subido: {fecha}"
                    )
            
            response_parts.append(
                "\n\n💡 **Tip**: Para hacer preguntas sobre un documento, "
                "selecciónalo con el botón de carpeta en la parte superior del chat."
            )
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error construyendo lista de documentos: {str(e)}")
            raise DatabaseException(f"Error al obtener documentos: {str(e)}")
    
    def extract_document_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Extrae y formatea el contexto de los chunks de documentos.
        
        Args:
            chunks: Lista de chunks con contenido y metadata
            
        Returns:
            str: Contexto formateado
        """
        if not chunks:
            return ""
        
        context_parts = []
        seen_content = set()  # Para evitar duplicados
        
        for chunk in chunks:
            content = chunk.get('content', '').strip()
            if content and content not in seen_content:
                seen_content.add(content)
                
                # Obtener metadata
                metadata = chunk.get('metadata', {})
                doc_title = metadata.get('document_title', 'Documento')
                page_num = metadata.get('page_number')
                
                # Formatear referencia
                if page_num:
                    reference = f"[{doc_title}, página {page_num}]"
                else:
                    reference = f"[{doc_title}]"
                
                context_parts.append(f"{reference}: {content}")
        
        return "\n\n".join(context_parts)
    
    def summarize_document_usage(self, documents_used: List[Dict[str, Any]]) -> str:
        """
        Crea un resumen del uso de documentos en una respuesta.
        
        Args:
            documents_used: Lista de documentos utilizados
            
        Returns:
            str: Resumen formateado
        """
        if not documents_used:
            return ""
        
        unique_docs = {}
        for doc in documents_used:
            doc_id = doc.get('document_id')
            if doc_id not in unique_docs:
                unique_docs[doc_id] = {
                    'title': doc.get('title', f'Documento {doc_id}'),
                    'chunks_used': 0
                }
            unique_docs[doc_id]['chunks_used'] += 1
        
        summary_parts = ["\n📚 **Fuentes consultadas**:"]
        for doc_info in unique_docs.values():
            summary_parts.append(
                f"- {doc_info['title']} ({doc_info['chunks_used']} fragmentos)"
            )
        
        return "\n".join(summary_parts)
    
    async def get_document_metadata(self, document_ids: List[int], user_id: int) -> Dict[int, Dict[str, Any]]:
        """
        Obtiene metadata de múltiples documentos.
        
        Args:
            document_ids: IDs de documentos
            user_id: ID del usuario
            
        Returns:
            Dict con metadata por documento ID
        """
        metadata = {}
        
        for doc_id in document_ids:
            try:
                doc = self.document_service.get_document(doc_id, user_id)
                metadata[doc_id] = {
                    'title': doc.title,
                    'content_type': doc.content_type,
                    'file_size': doc.file_size,
                    'created_at': doc.created_at.isoformat() if doc.created_at else None
                }
            except Exception as e:
                logger.warning(f"No se pudo obtener metadata del documento {doc_id}: {str(e)}")
                metadata[doc_id] = {'title': f'Documento {doc_id}', 'error': str(e)}
        
        return metadata
