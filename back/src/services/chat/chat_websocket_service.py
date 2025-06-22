"""
Servicio para manejar la lógica de negocio de WebSocket
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.repositories.chat_repository import ChatRepository
from src.repositories.user_repository import UserRepository
from src.models.domain import Chat, Message, User
from src.core.exceptions import NotFoundException, ForbiddenException, DatabaseException

logger = logging.getLogger(__name__)

class ChatWebSocketService:
    """Servicio para gestionar lógica de negocio de chat WebSocket"""
    
    def __init__(self):
        self.chat_repository = ChatRepository()
        self.user_repository = UserRepository()
        
    def verify_chat_access(self, chat_id: int, user_id: int) -> bool:
        """
        Verifica si un usuario tiene acceso a un chat
        
        Args:
            chat_id: ID del chat
            user_id: ID del usuario
            
        Returns:
            bool: True si tiene acceso, False en caso contrario
        """
        try:
            # Verificar que el chat existe y pertenece al usuario
            chat = self.chat_repository.get_chat_by_id(chat_id, user_id)
            return chat is not None
        except NotFoundException:
            # Chat no existe o no pertenece al usuario
            return False
        except Exception as e:
            logger.error(f"Error verificando acceso al chat {chat_id} para usuario {user_id}: {str(e)}")
            return False
        
    def handle_connection_event(
        self, 
        chat_id: int, 
        user_id: int, 
        event_type: str, 
        metadata: Dict[str, Any]
    ) -> None:
        """
        Registra eventos de conexión/desconexión
        
        Args:
            chat_id: ID del chat
            user_id: ID del usuario
            event_type: Tipo de evento (connect/disconnect)
            metadata: Datos adicionales del evento
        """
        try:
            # Por ahora solo hacemos logging, pero aquí se podría implementar
            # el guardado en una tabla websocket_events para auditoría
            logger.info(
                f"WebSocket {event_type} - Chat: {chat_id}, Usuario: {user_id}, "
                f"IP: {metadata.get('ip_address', 'unknown')}, "
                f"Timestamp: {datetime.utcnow().isoformat()}"
            )
            
            # Futuro: Implementar guardado en base de datos
            # websocket_event = {
            #     "chat_id": chat_id,
            #     "user_id": user_id,
            #     "event_type": event_type,
            #     "ip_address": metadata.get('ip_address'),
            #     "user_agent": metadata.get('user_agent'),
            #     "timestamp": datetime.utcnow()
            # }
            # self.websocket_event_repository.create(websocket_event)
            
        except Exception as e:
            logger.error(f"Error registrando evento WebSocket: {str(e)}")
        
    def save_message(
        self,
        chat_id: int,
        question: str,
        answer: str,
        user_id: int,
        processing_time: float
    ) -> int:
        """
        Guarda un mensaje en la base de datos
        
        Args:
            chat_id: ID del chat
            question: Pregunta del usuario
            answer: Respuesta generada
            user_id: ID del usuario
            processing_time: Tiempo de procesamiento
            
        Returns:
            int: ID del mensaje guardado
        """
        try:
            # Verificar que el usuario tiene acceso al chat
            if not self.verify_chat_access(chat_id, user_id):
                raise ForbiddenException(f"Usuario {user_id} no tiene acceso al chat {chat_id}")
                
            # Crear el mensaje usando el repositorio
            from src.repositories.message_repository import MessageRepository
            message_repository = MessageRepository()
            
            message = message_repository.create_message(
                chat_id=chat_id,
                question=question,
                answer=answer
            )
            
            logger.info(
                f"Mensaje guardado - ID: {message.id}, Chat: {chat_id}, "
                f"Usuario: {user_id}, Tiempo procesamiento: {processing_time:.2f}s"
            )
            
            # Opcional: Guardar metadata adicional como processing_time
            # Esto requeriría agregar campos adicionales a la tabla messages
            
            return message.id
            
        except ForbiddenException:
            raise
        except Exception as e:
            logger.error(f"Error guardando mensaje: {str(e)}")
            raise Exception(f"Error al guardar mensaje: {str(e)}")
        
    def process_message(
        self,
        chat_id: int,
        user_id: int,
        content: str,
        document_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje sin streaming
        
        Args:
            chat_id: ID del chat
            user_id: ID del usuario
            content: Contenido del mensaje
            document_ids: IDs de documentos a usar
            
        Returns:
            Dict con la respuesta procesada
        """
        try:
            # Verificar que el usuario tiene acceso al chat
            if not self.verify_chat_access(chat_id, user_id):
                raise ForbiddenException(f"Usuario {user_id} no tiene acceso al chat {chat_id}")
                
            # Usar ChatService para procesar el mensaje
            from src.services.chat_service import ChatService
            from src.models.schemas.chat import MessageCreate
            
            chat_service = ChatService()
            
            # Crear objeto MessageCreate
            message_data = MessageCreate(
                question=content,
                document_ids=document_ids if document_ids else None,
                n_results=5  # Valor por defecto
            )
            
            # Procesar mensaje usando el servicio de chat
            # Esto incluye corrección ortográfica, detección de contexto, RAG, etc.
            start_time = datetime.utcnow()
            message_response = chat_service.create_message(
                chat_id=chat_id,
                message_data=message_data,
                user_id=user_id
            )
            end_time = datetime.utcnow()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # Construir respuesta
            return {
                "message_id": message_response.id,
                "question": message_response.question,
                "answer": message_response.answer,
                "processing_time": processing_time,
                "timestamp": message_response.created_at.isoformat() if message_response.created_at else datetime.utcnow().isoformat(),
                "document_ids": document_ids if document_ids else []
            }
            
        except ForbiddenException:
            raise
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            raise Exception(f"Error al procesar mensaje: {str(e)}")
