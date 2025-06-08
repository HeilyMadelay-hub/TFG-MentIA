"""
Servicio para la gestión de chats y mensajes.
Implementa la lógica de negocio relacionada con la comunicación entre usuarios y el sistema.
"""
from typing import List, Dict, Any, Optional, Union
from fastapi import HTTPException, status
import logging
from datetime import datetime

# Importaciones del proyecto
from src.models.domain import Chat, Message
from src.repositories.chat_repository import ChatRepository
from src.repositories.message_repository import MessageRepository
from src.models.schemas.chat import ChatCreate, ChatResponse, ChatMessage, MessageCreate
from src.utils.ai_connector import OpenAIConnector
from src.utils.chromadb_connector import ChromaDBConnector
from src.config.database import get_supabase_client
from src.repositories.document_repository import DocumentRepository
from src.services.document_service import DocumentService

# Importar las funciones mejoradas del patch
from .chat_service_improved_patch import (
    correct_spelling_advanced,
    detect_context_advanced,
    get_contextual_response,
    SPELLING_CORRECTIONS,
    CONTEXT_RESPONSES
)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatService:
    """
    Servicio para gestionar la lógica de negocio relacionada con chats y mensajes
    """
    
    def __init__(self):
        """Inicializa el servicio con sus dependencias"""
        self.chat_repository = ChatRepository()
        self.message_repository = MessageRepository()
        self.ai_connector = OpenAIConnector()
        self.db = ChromaDBConnector()
        self.document_repo = DocumentRepository()
        self.document_service = DocumentService()
        self.supabase = get_supabase_client(use_service_role=True)
        self.table_name = "chats"
        
        # Usar los diccionarios importados del patch
        self.spelling_corrections = SPELLING_CORRECTIONS
        self.context_responses = CONTEXT_RESPONSES
    
    def create_chat(self, user_id: int, name_chat: str = None) -> ChatResponse:
        """
        Crea un nuevo chat para el usuario usando el repositorio.
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
            
        except Exception as e:
            logger.error(f"Error al crear chat: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear chat: {str(e)}"
            )
    
    def list_chats(self, user_id: int, limit: int = 100, skip: int = 0, sort_by: str = 'created_at', order: str = 'desc') -> List[ChatResponse]:
        """Alias para get_user_chats - para mantener compatibilidad"""
        return self.get_user_chats(user_id, limit, skip, sort_by, order)
    
    def get_user_chats(self, user_id: int, limit: int = 100, skip: int = 0, sort_by: str = 'created_at', order: str = 'desc') -> List[ChatResponse]:
        """
        Obtiene todos los chats del usuario.
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener chats: {str(e)}"
            )
    
    def get_chat(self, chat_id: int, user_id: int, is_admin: bool = False) -> ChatResponse:
        """
        Obtiene un chat específico por su ID.
        """
        try:
            # Si es administrador, obtener el chat sin verificar pertenencia
            if is_admin:
                chat = self.chat_repository.get_chat_by_id(chat_id)
            else:
                # Si es usuario normal, verificar que el chat le pertenece
                chat = self.chat_repository.get_chat_by_id(chat_id, user_id)
            
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chat con ID {chat_id} no encontrado"
                )
            
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
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en servicio al obtener chat {chat_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener chat: {str(e)}"
            )
    
    def update_chat(self, chat_id: int, chat_data: ChatCreate, user_id: int) -> ChatResponse:
        """
        Actualiza la información de un chat.
        """
        try:
            # Preparar datos para actualización
            data = {"name_chat": chat_data.name_chat}
            
            # Actualizar chat en la base de datos
            updated_chat = self.chat_repository.update_chat(chat_id, user_id, data)
            
            if not updated_chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chat con ID {chat_id} no encontrado"
                )
            
            # Convertir a esquema de respuesta
            return self._map_to_chat_response(updated_chat)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en servicio al actualizar chat {chat_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar chat: {str(e)}"
            )
    
    def delete_chat(self, chat_id: int, user_id: int) -> Dict[str, Any]:
        """
        Elimina un chat y todos sus mensajes asociados.
        """
        try:
            # Primero, eliminar todos los mensajes del chat
            deleted_messages = self.message_repository.delete_messages_by_chat(chat_id)
            
            # Luego, eliminar el chat
            success = self.chat_repository.delete_chat(chat_id, user_id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chat con ID {chat_id} no encontrado"
                )
            
            return {
                "status": "success",
                "message": f"Chat con ID {chat_id} eliminado correctamente",
                "deleted_messages": deleted_messages
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en servicio al eliminar chat {chat_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al eliminar chat: {str(e)}"
            )
    
    def get_chat_messages(self, chat_id: int, user_id: int, limit: int = 100, skip: int = 0, is_admin: bool = False) -> List[ChatMessage]:
        """
        Obtiene los mensajes de un chat con paginación.
        """
        try:
            # Si es administrador, obtener el chat sin verificar pertenencia
            if is_admin:
                chat = self.chat_repository.get_chat_by_id(chat_id)
            else:
                # Si es usuario normal, verificar que el chat le pertenece
                chat = self.chat_repository.get_chat_by_id(chat_id, user_id)
            
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chat con ID {chat_id} no encontrado"
                )
            
            # Obtener mensajes del chat
            messages = self.message_repository.get_messages_by_chat(chat_id, limit, skip)
            
            # Asegurar que siempre se retorne una lista
            if messages is None:
                messages = []
            
            # Convertir a esquema de respuesta, filtrando mensajes inválidos
            response = []
            for msg in messages:
                try:
                    # Intentar mapear cada mensaje
                    mapped_msg = self._map_to_message_response(msg)
                    response.append(mapped_msg)
                except Exception as map_error:
                    # Si falla el mapeo de un mensaje, logear pero continuar
                    logger.warning(f"Error al mapear mensaje {getattr(msg, 'id', 'unknown')}: {str(map_error)}")
                    continue
            
            # Log informativo si no hay mensajes
            if not response:
                logger.info(f"No se encontraron mensajes válidos para el chat {chat_id}")
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en servicio al obtener mensajes del chat {chat_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener mensajes: {str(e)}"
            )
    
    def delete_message(self, chat_id: int, message_id: int, user_id: int) -> Dict[str, Any]:
        """
        Elimina un mensaje específico.
        """
        try:
            # Verificar que el chat existe y pertenece al usuario
            chat = self.chat_repository.get_chat_by_id(chat_id, user_id)
            
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chat con ID {chat_id} no encontrado"
                )
            
            # Eliminar mensaje
            success = self.message_repository.delete_message(message_id, chat_id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Mensaje con ID {message_id} no encontrado"
                )
            
            return {
                "status": "success",
                "message": f"Mensaje con ID {message_id} eliminado correctamente"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en servicio al eliminar mensaje {message_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al eliminar mensaje: {str(e)}"
            )
    
    def _map_to_chat_response(self, chat: Chat) -> ChatResponse:
        """
        Convierte un objeto Chat del modelo de dominio a un esquema ChatResponse.
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
        """
        # IMPORTANTE: Validar que question no sea None antes de crear ChatMessage
        # Si question es None, usar string vacío como valor por defecto
        return ChatMessage(
            id=message.id,
            id_chat=message.id_chat,
            question=message.question or "",  # Usar string vacío si es None
            answer=message.answer,
            created_at=message.created_at
        )
    
    def create_message(self, chat_id: int, message_data: MessageCreate, user_id: int) -> ChatMessage:
        """
        Crea un nuevo mensaje en un chat y obtiene respuesta del modelo de IA,
        enriquecida con información relevante de los documentos (RAG).
        """
        try:
            # Verificar que el chat existe y pertenece al usuario
            chat = self.chat_repository.get_chat_by_id(chat_id, user_id)
            
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chat con ID {chat_id} no encontrado"
                )
            
            # ============ CORRECCIÓN ORTOGRÁFICA MEJORADA ============
            original_question = message_data.question
            corrected_question, corrections = correct_spelling_advanced(original_question, self.spelling_corrections)
            
            correction_message = ""
            if corrections:
                if len(corrections) == 1:
                    correction_message = f"💡 He corregido: {corrections[0]}\n\n"
                else:
                    correction_message = f"💡 He realizado algunas correcciones: {', '.join(corrections[:3])}"
                    if len(corrections) > 3:
                        correction_message += f" y {len(corrections) - 3} más"
                    correction_message += "\n\n"
            
            # ============ DETECCIÓN DE CONTEXTO MEJORADA ============
            is_out_of_context, context_category, confidence = detect_context_advanced(corrected_question, self.context_responses)
            
            # Si es pregunta fuera de contexto, responder apropiadamente
            if is_out_of_context and confidence > 0.7:
                logger.info(f"Pregunta fuera de contexto detectada. Categoría: {context_category} (confianza: {confidence})")
                ai_response = get_contextual_response(context_category, corrected_question, confidence, self.context_responses)
                
                # Si hubo correcciones, añadirlas a la respuesta
                if correction_message:
                    ai_response = correction_message + ai_response
                
                # Crear mensaje con respuesta para preguntas fuera de contexto
                response_message = self.message_repository.create_message(
                    chat_id=chat_id,
                    question=original_question,  # Guardar la pregunta original
                    answer=ai_response
                )
                
                return self._map_to_message_response(response_message)
            
            # ============ CONTINUACIÓN DEL FLUJO NORMAL ============
            
            # Extraer document_ids y n_results al principio
            document_ids = getattr(message_data, 'document_ids', None)
            n_results = getattr(message_data, 'n_results', 5)
            
            # Obtener mensajes previos para contexto
            previous_messages = self.message_repository.get_messages_by_chat(chat_id)
            
            # Preparar contexto para la IA
            messages_context = []
            for msg in previous_messages:
                if msg.question:
                    messages_context.append({"role": "user", "content": msg.question})
                if msg.answer:
                    messages_context.append({"role": "assistant", "content": msg.answer})
            
            # Añadir el mensaje actual al contexto
            messages_context.append({"role": "user", "content": corrected_question})
            
            question_lower = corrected_question.lower().strip()
            
            # 1. PRIMERO: Detectar preguntas sobre listar documentos
            document_list_queries = [
                "qué documentos tengo",
                "que documentos tengo", 
                "mis documentos",
                "listar documentos",
                "listar mis documentos",
                "mostrar documentos",
                "mostrar mis documentos",
                "cuáles son mis documentos",
                "cuales son mis documentos",
                "dime que documentos tengo",
                "dime qué documentos tengo",
                "documentos disponibles",
                "qué archivos tengo",
                "que archivos tengo",
                "mis archivos",
                "documentos subidos",
                "archivos subidos"
            ]
            
            # Si pregunta por listar sus documentos
            if any(phrase in question_lower for phrase in document_list_queries):
                logger.info(f"\n=== PREGUNTA SOBRE DOCUMENTOS DETECTADA ===")
                logger.info(f"Usuario {user_id} pregunta por sus documentos")
                try:
                    all_documents = self.document_service.list_user_documents(user_id, limit=100)
                    
                    if all_documents:
                        logger.info(f"Encontrados {len(all_documents)} documentos del usuario")
                        
                        # Agrupar por tipo de contenido
                        docs_by_type = {}
                        for doc in all_documents:
                            doc_type = doc.content_type or "otro"
                            if doc_type not in docs_by_type:
                                docs_by_type[doc_type] = []
                            docs_by_type[doc_type].append(doc)
                        
                        # Construir respuesta formateada
                        response_parts = [f"Tienes {len(all_documents)} documento(s) en tu biblioteca:\n"]
                        
                        for doc_type, docs in docs_by_type.items():
                            type_name = {
                                "application/pdf": "Documentos PDF",
                                "text/plain": "Documentos de texto (TXT)"
                            }.get(doc_type, "Otros archivos")
                            
                            response_parts.append(f"\n{type_name}:")
                            for i, doc in enumerate(docs, 1):
                                fecha = doc.created_at.strftime('%d/%m/%Y') if doc.created_at else "Fecha desconocida"
                                response_parts.append(f"  {i}. {doc.title} (subido: {fecha})")
                        
                        response_parts.append("\n\nPara hacer preguntas sobre un documento, selecciónalo con el botón de carpeta en la parte superior.")
                        ai_response = "\n".join(response_parts)
                    else:
                        ai_response = "No tienes documentos subidos aún. \n\nPuedes subir documentos desde la sección 'Mis Documentos' en el menú principal. Acepto archivos PDF y TXT."
                    
                    # Añadir mensaje de corrección si hubo
                    if correction_message:
                        ai_response = correction_message + ai_response
                    
                    # Crear mensaje con la lista de documentos
                    response_message = self.message_repository.create_message(
                        chat_id=chat_id,
                        question=original_question,
                        answer=ai_response
                    )
                    
                    return self._map_to_message_response(response_message)
                    
                except Exception as doc_error:
                    logger.error(f"Error al obtener documentos del usuario: {str(doc_error)}")
            
            # 2. SEGUNDO: Detectar si es pregunta sobre contenido de documentos
            document_keywords = [
                "documento", "archivo", "pdf", "txt",
                "resume", "resumir", "resumen", "busca", "buscar", 
                "encuentra", "analiza", "analizar", "información",
                "tramite", "trámite", "contenido", "dice", "explica",
                "habla", "trata", "menciona", "contiene", "sobre"
            ]
            
            is_document_question = any(keyword in question_lower for keyword in document_keywords)
            
            # Si es pregunta sobre documentos pero NO hay documento seleccionado
            if is_document_question and (document_ids is None or len(document_ids) == 0):
                ai_response = (
                    "📁 Para responder preguntas sobre documentos, primero debes seleccionar "
                    "un documento usando el botón de carpeta en la parte superior del chat.\n\n"
                    "Una vez seleccionado el documento, podrás hacer preguntas sobre su contenido "
                    "y recibirás respuestas basadas en la información que contiene."
                )
                
                # Añadir mensaje de corrección si hubo
                if correction_message:
                    ai_response = correction_message + ai_response
                
                # Crear mensaje con esta respuesta
                response_message = self.message_repository.create_message(
                    chat_id=chat_id,
                    question=original_question,
                    answer=ai_response
                )
                
                return self._map_to_message_response(response_message)
            
            # 3. TERCERO: Si hay documentos seleccionados, usar RAG
            if document_ids and len(document_ids) > 0:
                try:
                    logger.info(f"\n=== MENSAJE CON RAG ===")
                    logger.info(f"Chat ID: {chat_id}")
                    logger.info(f"User ID: {user_id}")
                    logger.info(f"Document IDs seleccionados: {document_ids}")
                    logger.info(f"Número de resultados solicitados: {n_results}")
                    logger.info(f"Pregunta procesada: {corrected_question[:100]}...")
                    
                    # Usar el servicio de documentos para obtener respuesta RAG
                    rag_result = self.document_service.get_rag_response(
                        query=corrected_question,  # Usar pregunta corregida
                        user_id=user_id,
                        n_results=n_results,
                        document_ids=document_ids
                    )
                    
                    ai_response = rag_result["response"]
                    documents_used = rag_result.get("documents", [])
                    
                    # Log información sobre los documentos usados
                    if documents_used:
                        logger.info(f"RAG: Usados {len(documents_used)} fragmentos de documentos para la respuesta")
                        for doc in documents_used:
                            logger.debug(f"  - Documento ID {doc['document_id']}: {doc['title']}")
                    else:
                        logger.info("RAG: No se encontraron documentos relevantes, usando respuesta sin contexto")
                    
                    # Añadir mensaje de corrección si hubo
                    if correction_message:
                        ai_response = correction_message + ai_response
                    
                except Exception as rag_error:
                    logger.error(f"Error en RAG: {str(rag_error)}")
                    ai_response = "Lo siento, hubo un error al procesar el documento seleccionado. Por favor, intenta de nuevo."
            
            # 4. CUARTO: Respuesta normal sin documentos (chat general)
            else:
                try:
                    # Añadir mensaje del sistema para mejorar las respuestas
                    system_message = {
                        "role": "system",
                        "content": (
                            "Eres MentIA, un asistente inteligente especializado en el análisis de documentos. "
                            "Tu función principal es ayudar a los usuarios a gestionar, buscar y comprender "
                            "el contenido de sus documentos PDF y archivos de texto. Cuando no haya documentos "
                            "seleccionados, puedes mantener conversaciones generales pero siempre intenta "
                            "relacionar tus respuestas con tu función principal de asistente de documentos. "
                            "Sé amigable, profesional y útil."
                        )
                    }
                    
                    # Insertar el mensaje del sistema al principio
                    messages_with_system = [system_message] + messages_context
                    
                    ai_response = self.ai_connector.generate_chat_completion(
                        messages=messages_with_system,
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    # Añadir mensaje de corrección si hubo
                    if correction_message:
                        ai_response = correction_message + ai_response
                    
                except Exception as ai_error:
                    logger.error(f"Error al generar respuesta IA: {str(ai_error)}")
                    ai_response = "Lo siento, ha ocurrido un error al procesar tu consulta. Por favor, intenta de nuevo."
            
            # Crear mensaje con la respuesta
            response_message = self.message_repository.create_message(
                chat_id=chat_id,
                question=original_question,  # Guardar siempre la pregunta original
                answer=ai_response
            )
            
            return self._map_to_message_response(response_message)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en servicio al crear mensaje en chat {chat_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al procesar mensaje: {str(e)}"
            )
    
    def get_all_user_messages(self, user_id: int, limit: int = 100) -> List[ChatMessage]:
        """
        Obtiene todos los mensajes del usuario a través de todos sus chats.
        """
        try:
            # Obtener todos los chats del usuario
            chats = self.chat_repository.get_chats_by_user(user_id)
            
            all_messages = []
            remaining_limit = limit
            
            # Recopilar mensajes de cada chat
            for chat in chats:
                # Si ya alcanzamos el límite, salir del bucle
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener mensajes: {str(e)}"
            )
    
    # ==================== MÉTODOS ADMINISTRATIVOS ====================
    
    def get_all_chats(self, limit: int = 100, skip: int = 0, sort_by: str = 'created_at', order: str = 'desc') -> List[ChatResponse]:
        """
        Obtiene TODOS los chats del sistema (solo para administradores).
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener chats: {str(e)}"
            )
    
    def count_all_chats(self) -> int:
        """
        Cuenta el total de chats en el sistema.
        """
        try:
            return self.chat_repository.count_all_chats()
        except Exception as e:
            logger.error(f"Error al contar chats: {str(e)}")
            return 0
    
    def get_chats_count_by_user(self) -> Dict[str, int]:
        """
        Obtiene el conteo de chats por usuario.
        """
        try:
            return self.chat_repository.count_chats_by_user()
        except Exception as e:
            logger.error(f"Error al contar chats por usuario: {str(e)}")
            return {}
    
    def count_all_messages(self) -> int:
        """
        Cuenta el total de mensajes en el sistema.
        """
        try:
            return self.message_repository.count_all_messages()
        except Exception as e:
            logger.error(f"Error al contar mensajes: {str(e)}")
            return 0
    
    def get_active_chats_count(self, hours: int = 24) -> int:
        """
        Cuenta los chats activos en las últimas N horas.
        """
        try:
            return self.chat_repository.count_active_chats(hours)
        except Exception as e:
            logger.error(f"Error al contar chats activos: {str(e)}")
            return 0
