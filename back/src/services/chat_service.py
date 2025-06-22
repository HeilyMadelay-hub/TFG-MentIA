"""
Servicio refactorizado para la gestión de chats y mensajes - VERSION COMPLETA
Implementa la lógica de negocio relacionada con la comunicación entre usuarios y el sistema.
Integra servicios especializados para mejor mantenibilidad y escalabilidad.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from src.models.domain import Chat, Message
from src.repositories.chat_repository import ChatRepository
from src.repositories.message_repository import MessageRepository
from src.models.schemas.chat import ChatCreate, ChatResponse, ChatMessage, MessageCreate
from src.services.document_service import DocumentService
from src.repositories.document_repository import DocumentRepository

# Servicios especializados
from src.services.chat.service_factory import ServiceFactory
from src.services.chat.chat_config import ChatServiceConfig
from src.services.chat.spelling_correction_service import SpellingCorrectionService
from src.services.chat.context_detection_service import ContextDetectionService
from src.services.chat.message_enrichment_service import MessageEnrichmentService
from src.services.chat.ai_response_service import AIResponseService

from src.core.exceptions import (
    NotFoundException,
    DatabaseException,
    ValidationException,
    ForbiddenException,
    ExternalServiceException
)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatService:
    """
    Servicio refactorizado para gestionar la lógica de negocio relacionada con chats y mensajes.
    Utiliza el patrón de composición con servicios especializados para mejor mantenibilidad.
    """
    
    def __init__(self):
        """Inicializa el servicio con sus dependencias y servicios especializados"""
        # Repositorios
        self.chat_repository = ChatRepository()
        self.message_repository = MessageRepository()
        self.document_repo = DocumentRepository()
        self.document_service = DocumentService()
        
        # Configuración
        self.config = ChatServiceConfig()
        
        # Factory para crear servicios especializados
        self.service_factory = ServiceFactory()
        
        # Servicios especializados
        self.spelling_service = self.service_factory.create_spelling_service()
        self.context_service = self.service_factory.create_context_service()
        self.enrichment_service = self.service_factory.create_enrichment_service()
        self.ai_service = self.service_factory.create_ai_service()
        
        logger.info("ChatService inicializado con servicios especializados")
    
    # ==================== MÉTODOS DE CHAT ====================
    
    def create_chat(self, user_id: int, name_chat: str = None) -> ChatResponse:
        """
        Crea un nuevo chat para el usuario usando el repositorio.
        
        Args:
            user_id: ID del usuario
            name_chat: Nombre del chat (opcional)
            
        Returns:
            ChatResponse: Chat creado
        """
        try:
            # Usar nombre por defecto si no se proporciona
            if not name_chat:
                name_chat = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Usar el repositorio en lugar de acceso directo a Supabase
            chat = self.chat_repository.create_chat(
                name_chat=name_chat,
                user_id=user_id
            )
            
            # Convertir a esquema de respuesta
            return self._map_to_chat_response(chat)
            
        except (NotFoundException, DatabaseException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"Error al crear chat: {str(e)}")
            raise DatabaseException(f"Error al crear chat: {str(e)}")
    
    def get_user_chats(self, user_id: int, limit: int = 100, skip: int = 0, 
                      sort_by: str = 'created_at', order: str = 'desc') -> List[ChatResponse]:
        """
        Obtiene todos los chats del usuario.
        
        Args:
            user_id: ID del usuario
            limit: Número máximo de chats a retornar
            skip: Número de chats a saltar (paginación)
            sort_by: Campo por el cual ordenar
            order: Orden (asc o desc)
            
        Returns:
            List[ChatResponse]: Lista de chats del usuario
        """
        try:
            # Obtener chats de la base de datos con ordenamiento
            chats = self.chat_repository.get_chats_by_user(
                user_id=user_id,
                limit=limit,
                skip=skip,
                sort_by=sort_by,
                order=order
            )
            
            # Convertir a esquema de respuesta
            return [self._map_to_chat_response(chat) for chat in chats]
            
        except Exception as e:
            logger.error(f"Error en servicio al obtener chats: {str(e)}")
            raise DatabaseException(f"Error al obtener chats: {str(e)}")
    
    def list_chats(self, user_id: int, limit: int = 100, skip: int = 0, 
                  sort_by: str = 'created_at', order: str = 'desc') -> List[ChatResponse]:
        """Alias para get_user_chats - para mantener compatibilidad"""
        return self.get_user_chats(user_id, limit, skip, sort_by, order)
    
    def get_chat(self, chat_id: int, user_id: int, is_admin: bool = False) -> ChatResponse:
        """
        Obtiene un chat específico por su ID.
        
        Args:
            chat_id: ID del chat
            user_id: ID del usuario propietario
            is_admin: Si el usuario es administrador
            
        Returns:
            ChatResponse: Datos del chat con sus mensajes
        """
        try:
            # Si es administrador, obtener el chat sin verificar pertenencia
            if is_admin:
                chat = self.chat_repository.get_chat_by_id(chat_id)
            else:
                # Si es usuario normal, verificar que el chat le pertenece
                chat = self.chat_repository.get_chat_by_id(chat_id, user_id)
            
            # Obtener mensajes del chat
            messages = self.message_repository.get_messages_by_chat(chat_id)
            
            # Asegurar que messages no sea None
            if messages is None:
                messages = []
            
            # Convertir a esquema de respuesta
            chat_response = self._map_to_chat_response(chat)
            
            # Mapear mensajes de forma segura
            mapped_messages = []
            for msg in messages:
                try:
                    mapped_msg = self._map_to_message_response(msg)
                    mapped_messages.append(mapped_msg)
                except Exception as e:
                    logger.warning(f"Error al mapear mensaje en chat {chat_id}: {str(e)}")
                    continue
            
            chat_response.messages = mapped_messages
            
            return chat_response
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error en servicio al obtener chat {chat_id}: {str(e)}")
            raise DatabaseException(f"Error al obtener chat: {str(e)}")
    
    def update_chat(self, chat_id: int, chat_data: ChatCreate, user_id: int) -> ChatResponse:
        """
        Actualiza la información de un chat.
        
        Args:
            chat_id: ID del chat a actualizar
            chat_data: Nuevos datos del chat
            user_id: ID del usuario propietario
            
        Returns:
            ChatResponse: Datos del chat actualizado
        """
        try:
            # Preparar datos para actualización
            data = {"name_chat": chat_data.name_chat}
            
            # Actualizar chat en la base de datos
            updated_chat = self.chat_repository.update_chat(chat_id, user_id, data)
            
            if not updated_chat:
                raise NotFoundException("Chat", chat_id)
            
            # Convertir a esquema de respuesta
            return self._map_to_chat_response(updated_chat)
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error en servicio al actualizar chat {chat_id}: {str(e)}")
            raise DatabaseException(f"Error al actualizar chat: {str(e)}")
    
    def delete_chat(self, chat_id: int, user_id: int) -> Dict[str, Any]:
        """
        Elimina un chat y todos sus mensajes asociados.
        
        Args:
            chat_id: ID del chat a eliminar
            user_id: ID del usuario propietario
            
        Returns:
            Dict[str, Any]: Respuesta con resultado de la operación
        """
        try:
            # Primero, eliminar todos los mensajes del chat
            deleted_messages = self.message_repository.delete_messages_by_chat(chat_id)
            
            # Luego, eliminar el chat
            success = self.chat_repository.delete_chat(chat_id, user_id)
            
            if not success:
                raise NotFoundException("Chat", chat_id)
            
            return {
                "status": "success",
                "message": f"Chat con ID {chat_id} eliminado correctamente",
                "deleted_messages": deleted_messages
            }
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error en servicio al eliminar chat {chat_id}: {str(e)}")
            raise DatabaseException(f"Error al eliminar chat: {str(e)}")
    
    # ==================== MÉTODOS DE MENSAJE ====================
    
    def get_chat_messages(self, chat_id: int, user_id: int, limit: int = 100, 
                         skip: int = 0, is_admin: bool = False) -> List[ChatMessage]:
        """
        Obtiene los mensajes de un chat con paginación.
        
        Args:
            chat_id: ID del chat
            user_id: ID del usuario propietario
            limit: Número máximo de mensajes a retornar
            skip: Número de mensajes a saltar (para paginación)
            is_admin: Si el usuario es administrador
            
        Returns:
            List[ChatMessage]: Lista de mensajes del chat
        """
        try:
            # Si es administrador, obtener el chat sin verificar pertenencia
            if is_admin:
                chat = self.chat_repository.get_chat_by_id(chat_id)
            else:
                # Si es usuario normal, verificar que el chat le pertenece
                chat = self.chat_repository.get_chat_by_id(chat_id, user_id)
            
            # Obtener mensajes del chat
            messages = self.message_repository.get_messages_by_chat(chat_id, limit, skip)
            
            # Asegurar que siempre se retorne una lista
            if messages is None:
                messages = []
            
            # Convertir a esquema de respuesta, filtrando mensajes inválidos
            response = []
            for msg in messages:
                try:
                    mapped_msg = self._map_to_message_response(msg)
                    response.append(mapped_msg)
                except Exception as map_error:
                    logger.warning(f"Error al mapear mensaje {getattr(msg, 'id', 'unknown')}: {str(map_error)}")
                    continue
            
            # Log informativo si no hay mensajes
            if not response:
                logger.info(f"No se encontraron mensajes válidos para el chat {chat_id}")
            
            return response
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error en servicio al obtener mensajes del chat {chat_id}: {str(e)}")
            raise DatabaseException(f"Error al obtener mensajes: {str(e)}")
    
    def create_message(self, chat_id: int, message_data: MessageCreate, user_id: int) -> ChatMessage:
        """
        Crea un nuevo mensaje en un chat y obtiene respuesta del modelo de IA,
        enriquecida con información relevante de los documentos (RAG).
        Utiliza servicios especializados para el procesamiento.
        
        Args:
            chat_id: ID del chat
            message_data: Datos del mensaje a crear
            user_id: ID del usuario remitente
            
        Returns:
            ChatMessage: Mensaje con la respuesta del chatbot
        """
        try:
            # Verificar que el chat existe y pertenece al usuario
            chat = self.chat_repository.get_chat_by_id(chat_id, user_id)
            
            # 1. Corrección ortográfica usando servicio especializado
            original_question = message_data.question
            corrected_question, correction_msg = self.spelling_service.correct_spelling(original_question)
            
            logger.info(f"Pregunta original: {original_question}")
            if correction_msg:
                logger.info(f"Correcciones aplicadas: {correction_msg}")
            
            # 2. Detección de contexto usando servicio especializado
            question_to_process = corrected_question if correction_msg else original_question
            is_out_of_context, context_category = self.context_service.detect_out_of_context(question_to_process)
            
            # Si es pregunta fuera de contexto, responder apropiadamente
            if is_out_of_context:
                logger.info(f"Pregunta fuera de contexto detectada. Categoría: {context_category}")
                ai_response = self.context_service.get_context_specific_response(context_category, question_to_process)
                
                # Añadir mensaje de corrección si hubo
                if correction_msg:
                    ai_response = correction_msg + "\n\n" + ai_response
                
                # Crear mensaje con respuesta para preguntas fuera de contexto
                response_message = self.message_repository.create_message(
                    chat_id=chat_id,
                    question=original_question,
                    answer=ai_response
                )
                
                return self._map_to_message_response(response_message)
            
            # 3. Extraer document_ids y n_results del message_data
            document_ids = getattr(message_data, 'document_ids', None)
            n_results = getattr(message_data, 'n_results', 5)
            
            # 4. Obtener mensajes previos para contexto
            previous_messages = self.message_repository.get_messages_by_chat(chat_id)
            
            question_lower = question_to_process.lower().strip()
            
            # 5. Detectar preguntas sobre listar documentos
            document_list_queries = [
                "qué documentos tengo", "que documentos tengo", "mis documentos",
                "listar documentos", "mostrar documentos", "cuáles son mis documentos",
                "documentos disponibles", "qué archivos tengo", "documentos subidos"
            ]
            
            # Si pregunta por listar sus documentos
            if any(phrase in question_lower for phrase in document_list_queries):
                logger.info(f"Usuario {user_id} pregunta por sus documentos")
                try:
                    all_documents = self.document_service.list_user_documents(user_id, limit=100)
                    if all_documents:
                        ai_response = self._build_document_list_response(all_documents)
                    else:
                        ai_response = "No tienes documentos subidos aún. Puedes subir documentos desde la sección 'Mis Documentos'."
                except Exception as doc_error:
                    logger.error(f"Error al obtener documentos: {str(doc_error)}")
                    raise DatabaseException("Error al obtener la lista de documentos")
            
            # 6. Detectar si es pregunta sobre contenido de documentos
            elif self._is_document_question(question_to_process):
                if document_ids and len(document_ids) > 0:
                    # Si hay documentos seleccionados, usar RAG
                    try:
                        rag_result = self.document_service.get_rag_response(
                            query=question_to_process,
                            user_id=user_id,
                            n_results=n_results,
                            document_ids=document_ids
                        )
                        ai_response = rag_result["response"]
                    except Exception as rag_error:
                        logger.error(f"Error en RAG: {str(rag_error)}")
                        raise ExternalServiceException("Error al procesar el documento seleccionado")
                else:
                    ai_response = (
                        "📚 **No puedo acceder a tus documentos todavía**\n\n"
                        "El chat NO tiene acceso automático a tus documentos (por privacidad).\n\n"
                        "Para que pueda leer tus documentos:\n"
                        "1. **DEBES hacer clic en el icono de carpeta** 📁 en la interfaz del chat\n"
                        "2. **SELECCIONA los documentos** que quieres usar\n"
                        "3. **Solo entonces** el chat podrá leer esos documentos\n\n"
                        "Una vez que selecciones los documentos, podrás preguntarme sobre su contenido."
                    )
            
            # 7. Respuesta normal sin documentos (chat general)
            else:
                try:
                    ai_response = self.ai_service.generate_response(
                        question=question_to_process,
                        chat_history=previous_messages[-10:] if previous_messages else None,
                        response_type="default",
                        temperature=self.config.default_temperature,
                        max_tokens=self.config.default_max_tokens
                    )
                except Exception as ai_error:
                    logger.error(f"Error al generar respuesta IA: {str(ai_error)}")
                    raise ExternalServiceException("Error al procesar tu consulta con el servicio de IA")
            
            # Añadir mensaje de corrección si hubo
            if correction_msg:
                ai_response = correction_msg + "\n\n" + ai_response
            
            # 5. Crear mensaje con la respuesta
            response_message = self.message_repository.create_message(
                chat_id=chat_id,
                question=original_question,  # Guardar siempre la pregunta original
                answer=ai_response
            )
            
            return self._map_to_message_response(response_message)
            
        except (NotFoundException, DatabaseException, ValidationException, ExternalServiceException):
            raise
        except Exception as e:
            logger.error(f"Error en servicio al crear mensaje en chat {chat_id}: {str(e)}")
            raise DatabaseException(f"Error al procesar mensaje: {str(e)}")
    
    def delete_message(self, chat_id: int, message_id: int, user_id: int) -> Dict[str, Any]:
        """
        Elimina un mensaje específico.
        
        Args:
            chat_id: ID del chat
            message_id: ID del mensaje a eliminar
            user_id: ID del usuario propietario
            
        Returns:
            Dict[str, Any]: Respuesta con resultado de la operación
        """
        try:
            # Verificar que el chat existe y pertenece al usuario
            chat = self.chat_repository.get_chat_by_id(chat_id, user_id)
            
            # Eliminar mensaje
            success = self.message_repository.delete_message(message_id, chat_id)
            
            if not success:
                raise NotFoundException("Mensaje", message_id)
            
            return {
                "status": "success",
                "message": f"Mensaje con ID {message_id} eliminado correctamente"
            }
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error en servicio al eliminar mensaje {message_id}: {str(e)}")
            raise DatabaseException(f"Error al eliminar mensaje: {str(e)}")
    
    def get_all_user_messages(self, user_id: int, limit: int = 100) -> List[ChatMessage]:
        """
        Obtiene todos los mensajes del usuario a través de todos sus chats.
        
        Args:
            user_id: ID del usuario
            limit: Número máximo total de mensajes a retornar
            
        Returns:
            List[ChatMessage]: Lista de todos los mensajes del usuario
        """
        try:
            # Obtener todos los chats del usuario
            chats = self.chat_repository.get_chats_by_user(user_id)
            
            all_messages = []
            remaining_limit = limit
            
            # Recopilar mensajes de cada chat
            for chat in chats:
                if remaining_limit <= 0:
                    break
                    
                # Obtener mensajes de este chat (con límite ajustado)
                chat_messages = self.message_repository.get_messages_by_chat(
                    chat.id, 
                    limit=remaining_limit
                )
                
                # Convertir a formato de respuesta
                formatted_messages = [self._map_to_message_response(msg) for msg in chat_messages]
                
                # Añadir información del chat a cada mensaje
                for msg in formatted_messages:
                    msg.chat_name = chat.name_chat
                
                # Agregar a la lista general
                all_messages.extend(formatted_messages)
                
                # Actualizar límite restante
                remaining_limit -= len(chat_messages)
            
            # Ordenar todos los mensajes por fecha (más recientes primero)
            all_messages.sort(key=lambda x: x.created_at, reverse=True)
            
            return all_messages
            
        except Exception as e:
            logger.error(f"Error al obtener todos los mensajes del usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al obtener mensajes: {str(e)}")
    
    # ==================== MÉTODOS ADMINISTRATIVOS ====================
    
    def get_all_chats(self, limit: int = 100, skip: int = 0, 
                     sort_by: str = 'created_at', order: str = 'desc') -> List[ChatResponse]:
        """
        Obtiene TODOS los chats del sistema (solo para administradores).
        
        Args:
            limit: Número máximo de chats a retornar
            skip: Número de chats a saltar (paginación)
            sort_by: Campo por el cual ordenar
            order: Orden (asc o desc)
            
        Returns:
            List[ChatResponse]: Lista de todos los chats del sistema
        """
        try:
            # Obtener todos los chats sin filtrar por usuario
            chats = self.chat_repository.get_all_chats(
                limit=limit,
                skip=skip,
                sort_by=sort_by,
                order=order
            )
            
            # Convertir a esquema de respuesta
            return [self._map_to_chat_response(chat) for chat in chats]
            
        except Exception as e:
            logger.error(f"Error al obtener todos los chats: {str(e)}")
            raise DatabaseException(f"Error al obtener chats: {str(e)}")
    
    def count_all_chats(self) -> int:
        """
        Cuenta el total de chats en el sistema.
        
        Returns:
            int: Número total de chats
        """
        try:
            return self.chat_repository.count_all_chats()
        except Exception as e:
            logger.error(f"Error al contar chats: {str(e)}")
            return 0
    
    def get_chats_count_by_user(self) -> Dict[str, int]:
        """
        Obtiene el conteo de chats por usuario.
        
        Returns:
            Dict[str, int]: Diccionario con username como clave y conteo como valor
        """
        try:
            return self.chat_repository.count_chats_by_user()
        except Exception as e:
            logger.error(f"Error al contar chats por usuario: {str(e)}")
            return {}
    
    def count_all_messages(self) -> int:
        """
        Cuenta el total de mensajes en el sistema.
        
        Returns:
            int: Número total de mensajes
        """
        try:
            return self.message_repository.count_all_messages()
        except Exception as e:
            logger.error(f"Error al contar mensajes: {str(e)}")
            return 0
    
    def get_active_chats_count(self, hours: int = 24) -> int:
        """
        Cuenta los chats activos en las últimas N horas.
        
        Args:
            hours: Número de horas hacia atrás para considerar
            
        Returns:
            int: Número de chats activos
        """
        try:
            return self.chat_repository.count_active_chats(hours)
        except Exception as e:
            logger.error(f"Error al contar chats activos: {str(e)}")
            return 0
    
    # ==================== MÉTODOS AUXILIARES ====================
    
    def _map_to_chat_response(self, chat: Chat) -> ChatResponse:
        """
        Convierte un objeto Chat del modelo de dominio a un esquema ChatResponse.
        
        Args:
            chat: Objeto Chat del modelo de dominio
            
        Returns:
            ChatResponse: Esquema de respuesta para la API
        """
        return ChatResponse(
            id=chat.id,
            name_chat=chat.name_chat,
            id_user=chat.id_user,
            created_at=chat.created_at,
            messages=[]  # Se llena cuando es necesario
        )
    
    def _map_to_message_response(self, message: Message) -> ChatMessage:
        """
        Convierte un objeto Message del modelo de dominio a un esquema ChatMessage.
        
        Args:
            message: Objeto Message del modelo de dominio
            
        Returns:
            ChatMessage: Esquema de respuesta para la API
        """
        # Validar que question no sea None antes de crear ChatMessage
        return ChatMessage(
            id=message.id,
            id_chat=message.id_chat,
            question=message.question or "",  # Usar string vacío si es None
            answer=message.answer,
            created_at=message.created_at
        )
    
    # ==================== MÉTODOS DE CONFIGURACIÓN ====================
    
    def get_service_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración actual del servicio.
        
        Returns:
            Dict[str, Any]: Configuración del servicio
        """
        return {
            "temperature": self.config.default_temperature,
            "max_tokens": self.config.default_max_tokens,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "enable_cache": self.config.enable_response_cache,
            "services_initialized": {
                "spelling": self.spelling_service is not None,
                "context": self.context_service is not None,
                "enrichment": self.enrichment_service is not None,
                "ai": self.ai_service is not None
            }
        }
    
    def update_service_config(self, **kwargs) -> Dict[str, Any]:
        """
        Actualiza la configuración del servicio dinámicamente.
        
        Args:
            **kwargs: Parámetros de configuración a actualizar
            
        Returns:
            Dict[str, Any]: Nueva configuración
        """
        try:
            # Actualizar configuración
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    logger.info(f"Configuración actualizada: {key} = {value}")
            
            # Reinicializar servicios si es necesario
            if any(key in kwargs for key in ['temperature', 'max_tokens']):
                self.ai_service = self.service_factory.create_ai_service()
                logger.info("Servicio de IA reinicializado con nueva configuración")
            
            return self.get_service_config()
            
        except Exception as e:
            logger.error(f"Error al actualizar configuración: {str(e)}")
            raise ValidationException(f"Error al actualizar configuración: {str(e)}")
    
    def _is_document_question(self, text: str) -> bool:
        """
        Detecta si una pregunta es sobre documentos.
        
        Args:
            text: Texto de la pregunta
            
        Returns:
            bool: True si es sobre documentos
        """
        text_lower = text.lower().strip()
        
        document_keywords = [
            "documento", "archivo", "pdf", "txt", "texto",
            "resume", "resumir", "resumen", "busca", "buscar", 
            "encuentra", "analiza", "analizar", "información",
            "tramite", "trámite", "contenido", "dice", "explica",
            "habla", "trata", "menciona", "contiene", "sobre",
            "este", "seleccion", "que va", "de que va", "que dice",
            "que contiene", "que hay en", "cuál es", "cuáles son",
            "tema", "asunto", "materia", "qué es", "que es"
        ]
        
        return any(keyword in text_lower for keyword in document_keywords)
    
    def _build_document_list_response(self, documents: List) -> str:
        """
        Construye una respuesta formateada con la lista de documentos.
        
        Args:
            documents: Lista de documentos
            
        Returns:
            str: Respuesta formateada
        """
        response_parts = [f"Tienes {len(documents)} documento(s) en tu biblioteca:\n"]
        
        # Agrupar por tipo
        docs_by_type = {}
        for doc in documents:
            doc_type = doc.content_type or "otro"
            if doc_type not in docs_by_type:
                docs_by_type[doc_type] = []
            docs_by_type[doc_type].append(doc)
        
        for doc_type, docs in docs_by_type.items():
            type_name = {
                "application/pdf": "📄 Documentos PDF",
                "text/plain": "📝 Documentos de texto (TXT)"
            }.get(doc_type, "📎 Otros archivos")
            
            response_parts.append(f"\n{type_name}:")
            for i, doc in enumerate(docs, 1):
                fecha = doc.created_at.strftime('%d/%m/%Y') if doc.created_at else "Fecha desconocida"
                response_parts.append(f"  {i}. {doc.title} (subido: {fecha})")
        
        response_parts.append("\n\n💡 Tip: Para hacer preguntas sobre un documento, selecciónalo con el botón de carpeta.")
        return "\n".join(response_parts)
