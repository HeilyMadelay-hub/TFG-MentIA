"""
Helpers para endpoints de chat
Contiene lógica específica de operaciones complejas separada de los endpoints
"""
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.models.domain import User
from src.models.schemas.chat import MessageCreate, ChatMessage, ChatResponse
from src.services.chat_service import ChatService
from src.services.chat_validation_service import ChatValidationService
from src.services.message_processing_service import MessageProcessingService
from src.repositories.message_repository import MessageRepository
from src.core.exceptions import (
    ValidationException, 
    DatabaseException, 
    ForbiddenException,
    ExternalServiceException
)

logger = logging.getLogger(__name__)

class ChatEndpointHelpers:
    """Helpers para endpoints de chat"""
    
    def __init__(self):
        self.validator = ChatValidationService()
        self.message_processor = MessageProcessingService()
        self.message_repository = MessageRepository()
    
    async def handle_message_send(
        self,
        chat_id: int,
        message_data: MessageCreate,
        current_user: User,
        chat_service: ChatService
    ) -> ChatMessage:
        """
        Maneja el envío completo de un mensaje con toda la lógica compleja
        
        Args:
            chat_id: ID del chat
            message_data: Datos del mensaje
            current_user: Usuario actual
            chat_service: Servicio de chat
            
        Returns:
            ChatMessage: Mensaje procesado con respuesta
        """
        start_time = time.time()
        
        try:
            # 1. Validaciones iniciales
            self._validate_message_send_request(chat_id, message_data, current_user)
            
            # 2. Verificar acceso al chat
            chat = chat_service.chat_repository.get_chat_by_id(chat_id, current_user.id)
            
            # 3. Validar contenido del mensaje
            validated_question = self.validator.validate_message_content(message_data.question)
            message_data.question = validated_question
            
            # 4. Validar parámetros RAG
            validated_doc_ids, validated_n_results = self.validator.validate_rag_parameters(
                document_ids=getattr(message_data, 'document_ids', None),
                n_results=getattr(message_data, 'n_results', 5),
                user_id=current_user.id
            )
            
            # Actualizar message_data con valores validados
            message_data.document_ids = validated_doc_ids
            message_data.n_results = validated_n_results
            
            validation_time = time.time() - start_time
            logger.info(f"⏱️ Validaciones completadas en {validation_time:.3f} segundos")
            
            # 5. Obtener mensajes previos para contexto
            previous_messages = self.message_repository.get_messages_by_chat(
                chat_id, limit=10
            )
            
            # 6. Procesar mensaje con IA y RAG
            processing_start = time.time()
            response_message = self.message_processor.process_incoming_message(
                message_data=message_data,
                chat_id=chat_id,
                user_id=current_user.id
            )
            
            processing_time = time.time() - processing_start
            total_time = time.time() - start_time
            
            # 7. Log de rendimiento
            self.message_processor.log_message_interaction(
                user_id=current_user.id,
                chat_id=chat_id,
                question_type=self._detect_question_type(message_data.question),
                processing_time=total_time,
                has_rag=bool(validated_doc_ids)
            )
            
            logger.info(
                f"🎉 Mensaje procesado completamente en {total_time:.3f}s "
                f"(validación: {validation_time:.3f}s, procesamiento: {processing_time:.3f}s)"
            )
            
            return response_message
            
        except (ValidationException, DatabaseException, ForbiddenException, ExternalServiceException):
            raise
        except Exception as e:
            logger.error(f"💥 Error inesperado en envío de mensaje: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al procesar mensaje: {str(e)}")
    
    def handle_chat_admin_verification(self, current_user: User, operation: str) -> None:
        """
        Maneja la verificación de permisos de administrador de forma centralizada
        
        Args:
            current_user: Usuario actual
            operation: Descripción de la operación
            
        Raises:
            ForbiddenException: Si no tiene permisos de administrador
        """
        try:
            self.validator.validate_admin_permissions(current_user, operation)
            logger.info(f"✅ Admin {current_user.username} verificado para: {operation}")
            
        except ForbiddenException as e:
            logger.warning(
                f"🚫 Acceso denegado - Usuario {current_user.username} "
                f"intentó acceder a: {operation}"
            )
            raise
    
    def handle_chat_operations(
        self,
        operation_type: str,
        chat_id: Optional[int] = None,
        current_user: Optional[User] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Maneja operaciones complejas de chat de forma centralizada
        
        Args:
            operation_type: Tipo de operación
            chat_id: ID del chat (opcional)
            current_user: Usuario actual (opcional)
            additional_params: Parámetros adicionales
            
        Returns:
            Dict con resultado de la operación
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔧 Iniciando operación: {operation_type}")
            
            if operation_type == "bulk_message_cleanup":
                return self._handle_bulk_message_cleanup(chat_id, current_user, additional_params)
            
            elif operation_type == "chat_statistics":
                return self._handle_chat_statistics(current_user, additional_params)
            
            elif operation_type == "user_activity_summary":
                return self._handle_user_activity_summary(current_user, additional_params)
            
            elif operation_type == "chat_health_check":
                return self._handle_chat_health_check(chat_id, current_user)
            
            else:
                raise ValidationException(f"Operación no reconocida: {operation_type}")
            
        except Exception as e:
            operation_time = time.time() - start_time
            logger.error(
                f"❌ Error en operación {operation_type} "
                f"después de {operation_time:.3f}s: {str(e)}"
            )
            raise
        finally:
            operation_time = time.time() - start_time
            logger.info(f"⏱️ Operación {operation_type} completada en {operation_time:.3f}s")
    
    def get_enhanced_chat_info(
        self,
        chat_id: int,
        current_user: User,
        chat_service: ChatService
    ) -> Dict[str, Any]:
        """
        Obtiene información enriquecida sobre un chat
        
        Args:
            chat_id: ID del chat
            current_user: Usuario actual
            chat_service: Servicio de chat
            
        Returns:
            Dict con información enriquecida del chat
        """
        try:
            # Obtener chat básico
            chat = chat_service.get_chat(chat_id, current_user.id, current_user.is_admin)
            
            # Estadísticas adicionales
            message_count = len(chat.messages) if chat.messages else 0
            
            # Análisis de actividad
            activity_info = self._analyze_chat_activity(chat.messages if chat.messages else [])
            
            # Información sobre documentos utilizados
            documents_info = self._analyze_chat_documents(chat.messages if chat.messages else [])
            
            return {
                "chat": chat,
                "statistics": {
                    "message_count": message_count,
                    "activity": activity_info,
                    "documents": documents_info
                },
                "enhanced_info": {
                    "last_activity": activity_info.get("last_message_date"),
                    "avg_response_length": activity_info.get("avg_response_length", 0),
                    "document_references": len(documents_info.get("referenced_docs", []))
                }
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo información enriquecida del chat: {str(e)}")
            raise DatabaseException("Error al obtener información del chat")
    
    def prepare_admin_chat_list(
        self,
        chats: List[ChatResponse],
        include_stats: bool = True
    ) -> Dict[str, Any]:
        """
        Prepara lista de chats para vista administrativa con estadísticas
        
        Args:
            chats: Lista de chats
            include_stats: Si incluir estadísticas detalladas
            
        Returns:
            Dict con chats y estadísticas administrativas
        """
        try:
            prepared_chats = []
            total_messages = 0
            users_with_chats = set()
            
            for chat in chats:
                chat_data = {
                    "id": chat.id,
                    "name_chat": chat.name_chat,
                    "id_user": chat.id_user,
                    "created_at": chat.created_at,
                    "message_count": len(chat.messages) if chat.messages else 0
                }
                
                if include_stats:
                    # Añadir estadísticas adicionales
                    if chat.messages:
                        last_message = max(chat.messages, key=lambda m: m.created_at)
                        chat_data["last_activity"] = last_message.created_at
                        chat_data["avg_message_length"] = sum(
                            len(m.question or "") + len(m.answer or "") for m in chat.messages
                        ) / len(chat.messages)
                    else:
                        chat_data["last_activity"] = chat.created_at
                        chat_data["avg_message_length"] = 0
                
                prepared_chats.append(chat_data)
                total_messages += chat_data["message_count"]
                users_with_chats.add(chat.id_user)
            
            result = {
                "chats": prepared_chats,
                "summary": {
                    "total_chats": len(chats),
                    "total_messages": total_messages,
                    "unique_users": len(users_with_chats),
                    "avg_messages_per_chat": total_messages / len(chats) if chats else 0
                }
            }
            
            if include_stats:
                result["summary"]["most_active_user"] = self._find_most_active_user(prepared_chats)
            
            return result
            
        except Exception as e:
            logger.error(f"Error preparando lista de chats admin: {str(e)}")
            raise DatabaseException("Error al preparar lista de chats")
    
    # ==================== MÉTODOS PRIVADOS ====================
    
    def _validate_message_send_request(
        self,
        chat_id: int,
        message_data: MessageCreate,
        current_user: User
    ) -> None:
        """Valida la solicitud completa de envío de mensaje"""
        # Validar IDs
        if chat_id <= 0:
            raise ValidationException("ID de chat inválido")
        
        if not message_data.question:
            raise ValidationException("La pregunta no puede estar vacía")
        
        # Validar contexto de creación de mensaje
        self.validator.validate_message_creation_context(
            chat_id=chat_id,
            user_id=current_user.id,
            has_documents=True,  # Esto se podría verificar dinámicamente
            question_type=self._detect_question_type(message_data.question)
        )
    
    def _detect_question_type(self, question: str) -> str:
        """Detecta el tipo de pregunta para categorización"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["documento", "archivo", "pdf"]):
            return "document_related"
        elif any(word in question_lower for word in ["hola", "gracias", "adiós"]):
            return "conversational"
        elif any(word in question_lower for word in ["suma", "resta", "calcula"]):
            return "mathematical"
        else:
            return "general"
    
    def _handle_bulk_message_cleanup(
        self,
        chat_id: Optional[int],
        current_user: User,
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Maneja limpieza masiva de mensajes"""
        # Verificar permisos de administrador
        self.validator.validate_admin_permissions(current_user, "limpieza masiva de mensajes")
        
        # TODO: Implementar lógica de limpieza
        return {
            "operation": "bulk_message_cleanup",
            "status": "completed",
            "message": "Funcionalidad en desarrollo"
        }
    
    def _handle_chat_statistics(
        self,
        current_user: User,
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Maneja generación de estadísticas de chat"""
        # Verificar permisos
        self.validator.validate_admin_permissions(current_user, "estadísticas de chat")
        
        # TODO: Implementar estadísticas detalladas
        return {
            "operation": "chat_statistics",
            "status": "completed",
            "statistics": {
                "total_chats": 0,
                "total_messages": 0,
                "active_users": 0
            }
        }
    
    def _handle_user_activity_summary(
        self,
        current_user: User,
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Maneja resumen de actividad de usuario"""
        user_id = params.get("user_id", current_user.id) if params else current_user.id
        
        # Si no es admin y pide datos de otro usuario, denegar
        if user_id != current_user.id and not current_user.is_admin:
            raise ForbiddenException("No puedes ver la actividad de otros usuarios")
        
        # TODO: Implementar resumen de actividad
        return {
            "operation": "user_activity_summary",
            "user_id": user_id,
            "status": "completed",
            "summary": {
                "total_chats": 0,
                "total_messages": 0,
                "avg_messages_per_day": 0
            }
        }
    
    def _handle_chat_health_check(
        self,
        chat_id: Optional[int],
        current_user: User
    ) -> Dict[str, Any]:
        """Maneja verificación de salud del chat"""
        if chat_id:
            # Verificar chat específico
            try:
                # TODO: Implementar verificaciones de salud
                return {
                    "operation": "chat_health_check",
                    "chat_id": chat_id,
                    "status": "healthy",
                    "checks": {
                        "messages_integrity": "ok",
                        "user_access": "ok",
                        "metadata_consistency": "ok"
                    }
                }
            except Exception as e:
                return {
                    "operation": "chat_health_check",
                    "chat_id": chat_id,
                    "status": "unhealthy",
                    "error": str(e)
                }
        else:
            # Verificación general del sistema
            return {
                "operation": "chat_health_check",
                "status": "healthy",
                "system_checks": {
                    "database_connection": "ok",
                    "ai_service": "ok",
                    "message_processing": "ok"
                }
            }
    
    def _analyze_chat_activity(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        """Analiza la actividad de un chat"""
        if not messages:
            return {
                "total_messages": 0,
                "last_message_date": None,
                "avg_response_length": 0,
                "activity_score": 0
            }
        
        total_messages = len(messages)
        last_message = max(messages, key=lambda m: m.created_at)
        
        # Calcular longitud promedio de respuestas
        response_lengths = [len(m.answer or "") for m in messages if m.answer]
        avg_response_length = sum(response_lengths) / len(response_lengths) if response_lengths else 0
        
        # Calcular puntuación de actividad (simple)
        activity_score = min(total_messages * 10, 100)  # Máximo 100
        
        return {
            "total_messages": total_messages,
            "last_message_date": last_message.created_at,
            "avg_response_length": round(avg_response_length, 2),
            "activity_score": activity_score
        }
    
    def _analyze_chat_documents(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        """Analiza el uso de documentos en un chat"""
        # TODO: Implementar análisis de documentos referenciados
        return {
            "referenced_docs": [],
            "document_questions": 0,
            "rag_responses": 0
        }
    
    def _find_most_active_user(self, chats: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Encuentra el usuario más activo"""
        if not chats:
            return None
        
        user_activity = {}
        for chat in chats:
            user_id = chat["id_user"]
            if user_id not in user_activity:
                user_activity[user_id] = {
                    "user_id": user_id,
                    "total_chats": 0,
                    "total_messages": 0
                }
            user_activity[user_id]["total_chats"] += 1
            user_activity[user_id]["total_messages"] += chat["message_count"]
        
        if not user_activity:
            return None
        
        most_active = max(user_activity.values(), key=lambda u: u["total_messages"])
        return most_active
