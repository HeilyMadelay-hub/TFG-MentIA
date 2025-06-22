"""
Repositorio para operaciones con mensajes en Supabase.
Maneja el acceso a datos para la entidad Message usando el cliente de Supabase.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from src.models.domain import Message
from src.config.database import get_supabase_client
from src.utils.date_utils import get_safe_timestamp
from src.utils.timezone_utils import get_utc_now, format_for_db
from src.core.exceptions import (
    NotFoundException,
    DatabaseException,
    ValidationException
)


# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageRepository:
    """
    Repositorio para gestionar mensajes en Supabase.
    Implementa operaciones CRUD básicas y consultas específicas.
    """
    
    def __init__(self):
        """Inicializa el repositorio con el cliente de Supabase."""
        self.table_name = "messages"
    
    def get(self, message_id: int) -> Message:
        """
        Obtiene un mensaje por su ID.
        
        Args:
            message_id: ID del mensaje
            
        Returns:
            Message: El mensaje encontrado
            
        Raises:
            NotFoundException: Si el mensaje no existe
        """
        return self.get_message_by_id(message_id)
    
    def create_message(self, chat_id: int, question: str, answer: Optional[str] = None) -> Message:
        """
        Crea un nuevo mensaje en un chat.
        
        Args:
            chat_id: ID del chat al que pertenece el mensaje
            question: Pregunta o mensaje del usuario
            answer: Respuesta opcional (puede ser None y actualizarse después)
            
        Returns:
            Message: El objeto mensaje creado
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Preparar datos para inserción
            message_data = {
                "id_chat": chat_id,
                "question": question,
                "answer": answer,
                "created_at": get_safe_timestamp()  # Usar fecha segura para evitar error de partición
            }
            
            # Insertar en Supabase
            response = supabase.table(self.table_name).insert(message_data).execute()
            
            if response.data and len(response.data) > 0:
                msg_data = response.data[0]
                
                # Convertir a objeto Message
                message = Message(
                    id=msg_data['id'],
                    id_chat=msg_data['id_chat'],
                    question=msg_data['question'],
                    answer=msg_data.get('answer'),
                    created_at=msg_data.get('created_at')
                )
                
                logger.info(f"Mensaje creado en chat {chat_id}")
                return message
            else:
                raise DatabaseException("No se pudo crear el mensaje")
                
        except (DatabaseException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"Error al crear mensaje: {str(e)}")
            raise DatabaseException(f"Error al crear mensaje: {str(e)}")
    
    def get_messages_by_chat(self, chat_id: int, limit: int = 100, skip: int = 0) -> List[Message]:
        """
        Obtiene todos los mensajes de un chat con paginación.
        
        Args:
            chat_id: ID del chat
            limit: Número máximo de mensajes a retornar
            skip: Número de mensajes a saltar (para paginación)
            
        Returns:
            List[Message]: Lista de mensajes del chat
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Consultar mensajes
            response = supabase.table(self.table_name)\
                .select('*')\
                .eq('id_chat', chat_id)\
                .order('created_at', desc=False)\
                .order('id', desc=False)\
                .range(skip, skip + limit - 1)\
                .execute()
            
            messages = []
            if response.data:
                for msg_data in response.data:
                    message = Message(
                        id=msg_data['id'],
                        id_chat=msg_data['id_chat'],
                        question=msg_data['question'],
                        answer=msg_data.get('answer'),
                        created_at=msg_data.get('created_at')
                    )
                    messages.append(message)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error al obtener mensajes del chat {chat_id}: {str(e)}")
            raise DatabaseException(f"Error al obtener mensajes del chat: {str(e)}")
    
    def get_message_by_id(self, message_id: int, chat_id: Optional[int] = None) -> Message:
        """
        Obtiene un mensaje específico por su ID.
        Opcionalmente puede verificar que pertenezca a un chat específico.
        
        Args:
            message_id: ID del mensaje
            chat_id: ID del chat (opcional, para verificación)
            
        Returns:
            Optional[Message]: El mensaje encontrado o None
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Construir query base
            query = supabase.table(self.table_name).select('*').eq('id', message_id)
            
            # Si se especificó chat_id, agregar filtro
            if chat_id is not None:
                query = query.eq('id_chat', chat_id)
            
            # Ejecutar consulta
            response = query.execute()
            
            if response.data and len(response.data) > 0:
                msg_data = response.data[0]
                
                message = Message(
                    id=msg_data['id'],
                    id_chat=msg_data['id_chat'],
                    question=msg_data['question'],
                    answer=msg_data.get('answer'),
                    created_at=msg_data.get('created_at')
                )
                
                return message
            
            # No se encontró el mensaje
            if chat_id is not None:
                raise NotFoundException(f"Mensaje {message_id} no encontrado en el chat {chat_id}")
            else:
                raise NotFoundException("Mensaje", message_id)
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener mensaje {message_id}: {str(e)}")
            raise DatabaseException(f"Error al obtener mensaje: {str(e)}")
    
    def exists(self, message_id: int, chat_id: Optional[int] = None) -> bool:
        """
        Verifica si un mensaje existe.
        
        Args:
            message_id: ID del mensaje
            chat_id: ID del chat (opcional, para verificación)
            
        Returns:
            bool: True si existe, False si no
        """
        try:
            self.get_message_by_id(message_id, chat_id)
            return True
        except NotFoundException:
            return False
    
    def update_message(self, message_id: int, 
                       chat_id: int, 
                       data: Dict[str, Any]) -> Optional[Message]:
        """
        Actualiza un mensaje existente.
        
        Args:
            message_id: ID del mensaje a actualizar
            chat_id: ID del chat al que pertenece el mensaje
            data: Diccionario con los campos a actualizar
            
        Returns:
            Optional[Message]: El mensaje actualizado o None si no existe
        """
        try:
            # Verificar que el mensaje existe
            try:
                message = self.get_message_by_id(message_id, chat_id)
            except NotFoundException:
                logger.warning(f"Mensaje {message_id} no encontrado para actualización")
                return None
            
            supabase = get_supabase_client(use_service_role=True)
            
            # Actualizar en Supabase
            response = supabase.table(self.table_name)\
                .update(data)\
                .eq('id', message_id)\
                .eq('id_chat', chat_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                msg_data = response.data[0]
                
                # Convertir a objeto Message
                message = Message(
                    id=msg_data['id'],
                    id_chat=msg_data['id_chat'],
                    question=msg_data['question'],
                    answer=msg_data.get('answer'),
                    created_at=msg_data.get('created_at')
                )
                
                logger.info(f"Mensaje {message_id} actualizado")
                return message
            
            return None
            
        except NotFoundException:
            return None
        except Exception as e:
            logger.error(f"Error al actualizar mensaje {message_id}: {str(e)}")
            raise DatabaseException(f"Error al actualizar mensaje: {str(e)}")
    
    def delete_message(self, message_id: int, chat_id: Optional[int] = None) -> bool:
        """
        Elimina un mensaje específico.
        
        Args:
            message_id: ID del mensaje a eliminar
            chat_id: ID del chat (opcional, para verificación)
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            # Verificar que el mensaje existe
            try:
                message = self.get_message_by_id(message_id, chat_id)
            except NotFoundException:
                logger.warning(f"Mensaje {message_id} no encontrado para eliminación")
                return False
            
            supabase = get_supabase_client(use_service_role=True)
            
            # Construir query de eliminación
            query = supabase.table(self.table_name).delete().eq('id', message_id)
            
            # Si se especificó chat_id, agregar filtro
            if chat_id is not None:
                query = query.eq('id_chat', chat_id)
            
            # Ejecutar eliminación
            response = query.execute()
            
            success = response.data is not None
            
            if success:
                logger.info(f"Mensaje {message_id} eliminado")
            
            return success
            
        except NotFoundException:
            return False
        except Exception as e:
            logger.error(f"Error al eliminar mensaje {message_id}: {str(e)}")
            raise DatabaseException(f"Error al eliminar mensaje: {str(e)}")
    
    def delete_messages_by_chat(self, chat_id: int) -> int:
        """
        Elimina todos los mensajes de un chat.
        
        Args:
            chat_id: ID del chat
            
        Returns:
            int: Número de mensajes eliminados
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Primero contar los mensajes
            count_response = supabase.table(self.table_name)\
                .select('*', count='exact')\
                .eq('id_chat', chat_id)\
                .execute()
            
            count = count_response.count if hasattr(count_response, 'count') else 0
            
            # Eliminar mensajes
            response = supabase.table(self.table_name)\
                .delete()\
                .eq('id_chat', chat_id)\
                .execute()
            
            if response.data is not None:
                logger.info(f"Eliminados {count} mensajes del chat {chat_id}")
                return count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error al eliminar mensajes del chat {chat_id}: {str(e)}")
            raise DatabaseException(f"Error al eliminar mensajes del chat: {str(e)}")
    
    def search_messages(self, query: str, chat_id: Optional[int] = None, 
                       limit: int = 50) -> List[Message]:
        """
        Busca mensajes que contengan un texto específico.
        
        Args:
            query: Texto a buscar
            chat_id: ID del chat (opcional, para filtrar por chat)
            limit: Número máximo de resultados
            
        Returns:
            List[Message]: Lista de mensajes que coinciden
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Construir query base
            # Nota: Supabase usa `or` de manera diferente, necesitamos hacer consultas separadas
            messages = []
            
            # Buscar en questions
            query_question = supabase.table(self.table_name)\
                .select('*')\
                .ilike('question', f'%{query}%')
            
            if chat_id is not None:
                query_question = query_question.eq('id_chat', chat_id)
            
            response_question = query_question.limit(limit).execute()
            
            # Buscar en answers
            query_answer = supabase.table(self.table_name)\
                .select('*')\
                .ilike('answer', f'%{query}%')
            
            if chat_id is not None:
                query_answer = query_answer.eq('id_chat', chat_id)
            
            response_answer = query_answer.limit(limit).execute()
            
            # Combinar resultados únicos
            seen_ids = set()
            all_results = []
            
            if response_question.data:
                all_results.extend(response_question.data)
            if response_answer.data:
                all_results.extend(response_answer.data)
            
            # Eliminar duplicados y convertir a objetos Message
            for msg_data in all_results:
                if msg_data['id'] not in seen_ids:
                    seen_ids.add(msg_data['id'])
                    message = Message(
                        id=msg_data['id'],
                        id_chat=msg_data['id_chat'],
                        question=msg_data['question'],
                        answer=msg_data.get('answer'),
                        created_at=msg_data.get('created_at')
                    )
                    messages.append(message)
            
            # Ordenar por created_at descendente
            messages.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
            
            # Limitar resultados
            return messages[:limit]
            
        except Exception as e:
            logger.error(f"Error al buscar mensajes con '{query}': {str(e)}")
            raise DatabaseException(f"Error al buscar mensajes: {str(e)}")
    
    def get_message_count_by_chat(self, chat_id: int) -> int:
        """
        Obtiene el número total de mensajes en un chat.
        
        Args:
            chat_id: ID del chat
            
        Returns:
            int: Número total de mensajes
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Contar mensajes
            response = supabase.table(self.table_name)\
                .select('*', count='exact')\
                .eq('id_chat', chat_id)\
                .execute()
            
            count = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0
            
            return count
            
        except Exception as e:
            logger.error(f"Error al contar mensajes del chat {chat_id}: {str(e)}")
            raise DatabaseException(f"Error al contar mensajes del chat: {str(e)}")
    
    # ==================== MÉTODOS ADMINISTRATIVOS ====================
    
    def count_all_messages(self) -> int:
        """
        Cuenta el total de mensajes en el sistema.
        
        Returns:
            int: Número total de mensajes
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Usar count() para obtener el total
            response = supabase.table(self.table_name)\
                .select('*', count='exact')\
                .execute()
            
            return response.count or 0
            
        except Exception as e:
            logger.error(f"Error al contar todos los mensajes: {str(e)}")
            raise DatabaseException(f"Error al contar todos los mensajes: {str(e)}")
