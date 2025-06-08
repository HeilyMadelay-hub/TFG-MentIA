"""
Servicio para la gestión de chats y mensajes.
Implementa la lógica de negocio relacionada con la comunicación entre usuarios y el sistema.
"""
from typing import List, Dict, Any, Optional, Union
from fastapi import HTTPException, status
import logging
import uuid
from datetime import datetime
from src.models.domain import Chat, Message
from src.repositories.chat_repository import ChatRepository
from src.repositories.message_repository import MessageRepository
from src.models.schemas.chat import ChatCreate, ChatResponse, ChatMessage, MessageCreate
from src.utils.ai_connector import OpenAIConnector
from src.utils.chromadb_connector import ChromaDBConnector
from src.config.database import get_supabase_client
from src.repositories.document_repository import DocumentRepository
from src.models.domain import Document
from src.services.document_service import DocumentService
import re
from difflib import get_close_matches
import unicodedata
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
        self.document_service = DocumentService()  # Añadir servicio de documentos
        self.supabase = get_supabase_client(use_service_role=True)
        self.table_name = "chats"
        
        # Diccionario de correcciones ortográficas comunes
        self.common_corrections = {
            # Errores comunes de acentuación
            "que": ["qué", "que"],
            "como": ["cómo", "como"],
            "cuando": ["cuándo", "cuando"],
            "donde": ["dónde", "donde"],
            "porque": ["por qué", "porque"],
            "quien": ["quién", "quien"],
            # Errores de escritura comunes
            "aver": "a ver",
            "haber": "a ver",
            "haver": "a ver",
            "ahi": "ahí",
            "hai": "ahí",
            "ay": "ahí",
            "halla": "haya",
            "alla": "allá",
            "valla": "vaya",
            "balla": "vaya",
            # Palabras relacionadas con documentos
            "documento": ["documento", "documeto", "ducumento", "docmento"],
            "archivo": ["archivo", "archibo", "arcivo", "archvo"],
            "pdf": ["pdf", "pfd", "dpf", "pdef"],
            "texto": ["texto", "testo", "texo", "textto"],
            "resumen": ["resumen", "resumne", "resmen", "resumenn"],
            "información": ["información", "informacion", "imformacion", "infromacion"],
            "contenido": ["contenido", "cotenido", "contenio", "comtenido"],
            "buscar": ["buscar", "buskar", "busqar", "buscarr"],
            "encontrar": ["encontrar", "encontar", "emcontrar", "encontrrar"],
            "análisis": ["análisis", "analisis", "analicis", "analisiss"],
            # Saludos y expresiones comunes
            "hola": ["hola", "ola", "holaa", "hla", "hoal"],
            "buenos dias": ["buenos días", "buenos dias", "buen dia", "buenas dias"],
            "buenas tardes": ["buenas tardes", "buenas tarde", "buena tardes", "buenas tardess"],
            "gracias": ["gracias", "grasias", "gracas", "graciass"],
            "por favor": ["por favor", "porfavor", "porfabor", "por fabor"],
        }
        
        # Frases comunes fuera de contexto y sus respuestas
        self.out_of_context_responses = {
            "saludos": {
                "patterns": ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "saludos", "qué tal"],
                "response": "¡Hola! Soy MentIA, tu asistente para documentos. Puedo ayudarte a buscar información en tus documentos, hacer resúmenes o responder preguntas sobre ellos. ¿En qué puedo ayudarte hoy?"
            },
            "despedidas": {
                "patterns": ["adiós", "adios", "chao", "hasta luego", "bye", "nos vemos"],
                "response": "¡Hasta luego! Ha sido un placer ayudarte. Recuerda que estaré aquí cuando necesites consultar tus documentos. ¡Que tengas un excelente día!"
            },
            "agradecimientos": {
                "patterns": ["gracias", "muchas gracias", "te agradezco", "thanks", "ty"],
                "response": "¡De nada! Me alegra haberte sido de ayuda. Si tienes más preguntas sobre tus documentos, no dudes en consultarme."
            },
            "estado": {
                "patterns": ["cómo estás", "como estas", "qué tal estás", "cómo te encuentras"],
                "response": "¡Excelente! Estoy aquí para ayudarte con tus documentos. Puedo buscar información, hacer resúmenes, analizar contenido y responder cualquier pregunta que tengas sobre los archivos que has subido."
            },
            "identidad": {
                "patterns": ["quién eres", "quien eres", "qué eres", "que eres", "tu nombre", "cómo te llamas"],
                "response": "Soy MentIA, tu asistente inteligente de DocuMente. Mi función es ayudarte a gestionar y comprender mejor tus documentos. Puedo analizar PDFs y archivos de texto, hacer resúmenes, buscar información específica y responder preguntas sobre el contenido de tus documentos."
            },
            "capacidades": {
                "patterns": ["qué puedes hacer", "que puedes hacer", "qué sabes hacer", "para qué sirves", "ayuda", "help"],
                "response": "Puedo ayudarte con:\n\n📄 **Análisis de documentos**: Leo y comprendo el contenido de tus PDFs y archivos de texto\n\n🔍 **Búsqueda de información**: Encuentro datos específicos dentro de tus documentos\n\n📝 **Resúmenes**: Creo resúmenes concisos de documentos largos\n\n❓ **Responder preguntas**: Contesto preguntas basándome en el contenido de tus archivos\n\n📊 **Análisis**: Extraigo información clave y patrones de tus documentos\n\n¿Qué te gustaría hacer?"
            },
            "insultos": {
                "patterns": ["eres tonto", "eres estúpido", "eres idiota", "eres malo", "no sirves"],
                "response": "Entiendo que puedas estar frustrado. Mi objetivo es ayudarte de la mejor manera posible con tus documentos. Si algo no está funcionando como esperas, por favor dime cómo puedo mejorar mi asistencia."
            },
            "clima": {
                "patterns": ["qué tiempo hace", "como esta el clima", "va a llover", "hace frío", "hace calor"],
                "response": "No tengo acceso a información meteorológica, pero puedo ayudarte con tus documentos. Si tienes algún documento sobre meteorología o clima, puedo analizarlo para ti."
            },
            "deportes": {
                "patterns": ["fútbol", "futbol", "barcelona", "real madrid", "messi", "cristiano"],
                "response": "Veo que te interesa el deporte. Aunque no puedo darte resultados deportivos actuales, si tienes documentos relacionados con deportes, puedo analizarlos y extraer información relevante para ti."
            },
            "comida": {
                "patterns": ["tengo hambre", "qué comer", "receta", "cocinar", "restaurante"],
                "response": "¡La comida es importante! Aunque no puedo recomendarte restaurantes, si tienes documentos con recetas o información nutricional, puedo ayudarte a analizarlos y extraer la información que necesites."
            },
            "bromas": {
                "patterns": ["cuéntame un chiste", "cuentame un chiste", "dime algo gracioso", "hazme reír"],
                "response": "¡Me encantaría contarte un chiste sobre documentos! ¿Por qué el PDF fue al psicólogo? Porque tenía problemas de formato... 😄 Pero hablando en serio, ¿hay algo en lo que pueda ayudarte con tus documentos?"
            },
            "matematicas": {
                "patterns": ["cuánto es", "cuanto es", "suma", "resta", "multiplica", "divide", "calcula"],
                "response": "Puedo hacer cálculos básicos, pero mi especialidad es el análisis de documentos. Si tienes documentos con datos numéricos, tablas o estadísticas, puedo ayudarte a interpretarlos y analizarlos."
            }
        }
    
    def normalize_text(self, text: str) -> str:
        """
        Normaliza el texto eliminando acentos, caracteres especiales y normalizando espacios.
        """
        # Convertir a minúsculas
        text = text.lower().strip()
        
        # Normalizar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        
        # Eliminar caracteres especiales al inicio y final
        text = re.sub(r'^[^a-zA-Z0-9áéíóúñü]+|[^a-zA-Z0-9áéíóúñü]+$', '', text)
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener chats: {str(e)}"
            )
    
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
                chat = self.chat_repository.get_chat_by_id(chat_id)  # Sin user_id
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
                chat = self.chat_repository.get_chat_by_id(chat_id)  # Sin user_id
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
            
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chat con ID {chat_id} no encontrado"
                )
            
            # ============ NUEVO: CORRECCIÓN ORTOGRÁFICA ============
            original_question = message_data.question
            corrected_question, correction_msg = self.correct_spelling(original_question)
            
            # Si hubo correcciones, usar la pregunta corregida
            if correction_msg:
                logger.info(f"Pregunta original: {original_question}")
                logger.info(f"Pregunta corregida: {corrected_question}")
                logger.info(f"Correcciones: {correction_msg}")
                question_to_process = corrected_question
            else:
                question_to_process = original_question
            
            # ============ NUEVO: DETECCIÓN DE CONTEXTO ============
            is_out_of_context, context_category = self.detect_out_of_context(question_to_process)
            
            # Si es pregunta fuera de contexto, responder apropiadamente
            if is_out_of_context:
                logger.info(f"Pregunta fuera de contexto detectada. Categoría: {context_category}")
                ai_response = self.get_context_specific_response(context_category, question_to_process)
                
                # Si hubo correcciones, añadirlas a la respuesta
                if correction_msg:
                    ai_response = correction_msg + "\n\n" + ai_response
                
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
            messages_context.append({"role": "user", "content": question_to_process})
            
            question_lower = question_to_process.lower().strip()
            
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
                    if correction_msg:
                        ai_response = correction_msg + "\n\n" + ai_response
                    
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
                    "Para responder preguntas sobre documentos, primero debes seleccionar "
                    "un documento usando el botón de carpeta en la parte superior del chat.\n\n"
                    "Una vez seleccionado el documento, podrás hacer preguntas sobre su contenido "
                    "y recibirás respuestas basadas en la información que contiene."
                )
                
                # Añadir mensaje de corrección si hubo
                if correction_msg:
                    ai_response = correction_msg + "\n\n" + ai_response
                
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
                    logger.info(f"Pregunta procesada: {question_to_process[:100]}...")
                    
                    # Usar el servicio de documentos para obtener respuesta RAG
                    rag_result = self.document_service.get_rag_response(
                        query=question_to_process,  # Usar pregunta corregida
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
                    if correction_msg:
                        ai_response = correction_msg + "\n\n" + ai_response
                    
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
                    if correction_msg:
                        ai_response = correction_msg + "\n\n" + ai_response
                    
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
                    msg.chat_name = chat.name_chat  # Añadir esta propiedad al schema ChatMessage si es necesario
                
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
        
    async def process_question(
        self,
        chat_id: int,
        question: str,
        user_id: int
    ) -> str:
        """
        Procesa una pregunta considerando solo documentos accesibles
        """
        try:
            # 1. Obtener IDs de documentos accesibles para el usuario
            accessible_doc_ids = await self._get_accessible_document_ids(user_id)
            
            if not accessible_doc_ids:
                return "No tienes documentos disponibles para consultar. Sube o solicita acceso a documentos para comenzar."
            
            # 2. Buscar en ChromaDB solo en documentos accesibles
            relevant_chunks = await self.chroma.search_relevant_chunks(
                query=question,
                document_ids=accessible_doc_ids,  # Filtrar por documentos accesibles
                n_results=5
            )
            
            if not relevant_chunks:
                return "No encontré información relevante en los documentos a los que tienes acceso."
            
            # 3. Construir contexto
            context = self._build_context(relevant_chunks)
            
            # 4. Generar respuesta con IA
            response = await self._generate_ai_response(question, context)
            
            # 5. Guardar en historial
            await self._save_message(
                chat_id=chat_id,
                question=question,
                answer=response,
                context_used=context
            )
            
            return response
            
        except Exception as e:
            print(f"Error procesando pregunta: {e}")
            return "Lo siento, ocurrió un error al procesar tu pregunta."
    
    async def _get_accessible_document_ids(self, user_id: int) -> List[int]:
        """
        Obtiene todos los IDs de documentos accesibles para un usuario
        """
        accessible_ids = []
        
        # 1. Documentos propios
        own_docs = await self.document_service.get_user_documents(user_id)
        accessible_ids.extend([doc.id for doc in own_docs])
        
        # 2. Documentos compartidos
        shared_docs = await self.document_service.get_shared_with_user(user_id)
        accessible_ids.extend([doc.id for doc in shared_docs])
        
        return list(set(accessible_ids))  # Eliminar duplicados
    
    def _build_context(self, chunks: List[dict]) -> str:
        """
        Construye el contexto a partir de los chunks relevantes
        """
        context_parts = []
        
        for chunk in chunks:
            doc_title = chunk.get('metadata', {}).get('document_title', 'Documento')
            content = chunk.get('content', '')
            
            context_parts.append(f"[{doc_title}]: {content}")
        
        return "\n\n".join(context_parts)
    
    async def _generate_ai_response(self, question: str, context: str) -> str:
        """
        Genera respuesta usando IA con el contexto
        """
        # Aquí integrarías con OpenAI, Claude, etc.
        # Por ahora un ejemplo simple
        
        prompt = f"""
        Basándote en el siguiente contexto, responde la pregunta del usuario.
        Si la información no está en el contexto, indica que no tienes esa información.
        
        Contexto:
        {context}
        
        Pregunta: {question}
        
        Respuesta:
        """
        
        # TODO: Integrar con servicio de IA
        # response = await ai_service.generate(prompt)
        
        # Respuesta temporal
        return f"Basándome en los documentos disponibles: [Aquí iría la respuesta de IA basada en el contexto]"
    
    # ==================== MÉTODOS ADMINISTRATIVOS ====================
    
    def get_all_chats(self, limit: int = 100, skip: int = 0, sort_by: str = 'created_at', order: str = 'desc') -> List[ChatResponse]:
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener chats: {str(e)}"
            )
    
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
                    
        return text
                
    def remove_accents(self, text: str) -> str:
        """
        Elimina los acentos del texto para comparaciones.
        """
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
    
    def correct_spelling(self, text: str) -> tuple[str, str]:
        """
        Intenta corregir errores ortográficos comunes.
        Retorna: (texto_corregido, explicación_de_correcciones)
        """
        corrections_made = []
        words = text.split()
        corrected_words = []
        
        for word in words:
            word_lower = word.lower()
            corrected = False
            
            # Buscar en correcciones comunes directas
            if word_lower in self.common_corrections:
                correction = self.common_corrections[word_lower]
                if isinstance(correction, str):
                    corrected_words.append(correction)
                    corrections_made.append(f"'{word}' → '{correction}'")
                    corrected = True
            
            if not corrected:
                # Buscar en las listas de variaciones
                for correct_word, variations in self.common_corrections.items():
                    if isinstance(variations, list):
                        # Buscar coincidencias sin acentos
                        word_no_accent = self.remove_accents(word_lower)
                        for variation in variations:
                            if self.remove_accents(variation.lower()) == word_no_accent:
                                corrected_words.append(variation)
                                if word_lower != variation.lower():
                                    corrections_made.append(f"'{word}' → '{variation}'")
                                corrected = True
                                break
                    if corrected:
                        break
            
            if not corrected:
                corrected_words.append(word)
        
        corrected_text = ' '.join(corrected_words)
        
        # Aplicar correcciones de frases comunes
        phrase_corrections = {
            "aver": "a ver",
            "haber si": "a ver si",
            "por que": "por qué",
            "por fabor": "por favor",
            "porfabor": "por favor",
            "de nada": "de nada",
            "muchas grasias": "muchas gracias",
            "buenos días": "buenos días",
            "buenas tarde": "buenas tardes"
        }
        
        for wrong, correct in phrase_corrections.items():
            if wrong in corrected_text:
                corrected_text = corrected_text.replace(wrong, correct)
                corrections_made.append(f"'{wrong}' → '{correct}'")
        
        correction_message = ""
        if corrections_made:
            correction_message = f"He detectado y corregido algunos errores: {', '.join(corrections_made)}. "
        
        return corrected_text, correction_message
    
    def detect_out_of_context(self, text: str) -> tuple[bool, str]:
        """
        Detecta si la pregunta está fuera del contexto de documentos.
        Retorna: (es_fuera_de_contexto, tipo_de_pregunta)
        """
        text_lower = text.lower().strip()
        text_no_accents = self.remove_accents(text_lower)
        
        for category, data in self.out_of_context_responses.items():
            for pattern in data["patterns"]:
                pattern_no_accents = self.remove_accents(pattern.lower())
                # Buscar coincidencia exacta o parcial
                if pattern_no_accents in text_no_accents or text_no_accents in pattern_no_accents:
                    return True, category
                # Buscar palabras clave
                pattern_words = pattern_no_accents.split()
                text_words = text_no_accents.split()
                if any(pw in text_words for pw in pattern_words if len(pw) > 3):
                    return True, category
        
        return False, None
    
    def get_context_specific_response(self, category: str, original_text: str) -> str:
        """
        Obtiene una respuesta específica para preguntas fuera de contexto,
        pero intentando relacionarla con documentos cuando sea posible.
        """
        base_response = self.out_of_context_responses.get(category, {}).get("response", "")
        
        # Personalizar respuesta según el contexto
        if category == "matematicas" and any(word in original_text.lower() for word in ["suma", "resta", "calcula"]):
            # Extraer números de la pregunta
            numbers = re.findall(r'\d+', original_text)
            if len(numbers) >= 2:
                try:
                    num1, num2 = int(numbers[0]), int(numbers[1])
                    if "suma" in original_text.lower() or "+" in original_text:
                        result = num1 + num2
                        return f"La suma de {num1} + {num2} es {result}. Aunque mi especialidad es analizar documentos, puedo hacer cálculos básicos. Si tienes documentos con datos numéricos, puedo ayudarte a analizarlos más profundamente."
                    elif "resta" in original_text.lower() or "-" in original_text:
                        result = num1 - num2
                        return f"La resta de {num1} - {num2} es {result}. Recuerda que también puedo analizar documentos con tablas numéricas y estadísticas."
                    elif "multiplica" in original_text.lower() or "*" in original_text or "x" in original_text:
                        result = num1 * num2
                        return f"La multiplicación de {num1} × {num2} es {result}. Si tienes documentos con cálculos o datos financieros, puedo ayudarte a interpretarlos."
                    elif "divide" in original_text.lower() or "/" in original_text:
                        if num2 != 0:
                            result = num1 / num2
                            return f"La división de {num1} ÷ {num2} es {result:.2f}. También puedo analizar documentos con datos estadísticos y proporciones."
                except:
                    pass
        
        return base_response
    
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener chats: {str(e)}"
            )
    
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
                chat = self.chat_repository.get_chat_by_id(chat_id)  # Sin user_id
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
                chat = self.chat_repository.get_chat_by_id(chat_id)  # Sin user_id
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
            
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chat con ID {chat_id} no encontrado"
                )
            
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
            messages_context.append({"role": "user", "content": message_data.question})
            
            question_lower = message_data.question.lower().strip()
            
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
                    
                    # Crear mensaje con la lista de documentos
                    response_message = self.message_repository.create_message(
                        chat_id=chat_id,
                        question=message_data.question,
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
                    "Para responder preguntas sobre documentos, primero debes seleccionar "
                    "un documento usando el botón de carpeta en la parte superior del chat.\n\n"
                    "Una vez seleccionado el documento, podrás hacer preguntas sobre su contenido "
                    "y recibirás respuestas basadas en la información que contiene."
                )
                
                # Crear mensaje con esta respuesta
                response_message = self.message_repository.create_message(
                    chat_id=chat_id,
                    question=message_data.question,
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
                    logger.info(f"Pregunta: {message_data.question[:100]}...")
                    
                    # Usar el servicio de documentos para obtener respuesta RAG
                    rag_result = self.document_service.get_rag_response(
                        query=message_data.question,
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
                    
                except Exception as rag_error:
                    logger.error(f"Error en RAG: {str(rag_error)}")
                    ai_response = "Lo siento, hubo un error al procesar el documento seleccionado. Por favor, intenta de nuevo."
            
            # 4. CUARTO: Respuesta normal sin documentos (chat general)
            else:
                try:
                    ai_response = self.ai_connector.generate_chat_completion(
                        messages=messages_context,
                        temperature=0.7,
                        max_tokens=1000
                    )
                except Exception as ai_error:
                    logger.error(f"Error al generar respuesta IA: {str(ai_error)}")
                    ai_response = "Lo siento, ha ocurrido un error al procesar tu consulta. Por favor, intenta de nuevo."
            
            # Crear mensaje con la respuesta
            response_message = self.message_repository.create_message(
                chat_id=chat_id,
                question=message_data.question,
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
                    msg.chat_name = chat.name_chat  # Añadir esta propiedad al schema ChatMessage si es necesario
                
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
        
    async def process_question(
        self,
        chat_id: int,
        question: str,
        user_id: int
    ) -> str:
        """
        Procesa una pregunta considerando solo documentos accesibles
        """
        try:
            # 1. Obtener IDs de documentos accesibles para el usuario
            accessible_doc_ids = await self._get_accessible_document_ids(user_id)
            
            if not accessible_doc_ids:
                return "No tienes documentos disponibles para consultar. Sube o solicita acceso a documentos para comenzar."
            
            # 2. Buscar en ChromaDB solo en documentos accesibles
            relevant_chunks = await self.chroma.search_relevant_chunks(
                query=question,
                document_ids=accessible_doc_ids,  # Filtrar por documentos accesibles
                n_results=5
            )
            
            if not relevant_chunks:
                return "No encontré información relevante en los documentos a los que tienes acceso."
            
            # 3. Construir contexto
            context = self._build_context(relevant_chunks)
            
            # 4. Generar respuesta con IA
            response = await self._generate_ai_response(question, context)
            
            # 5. Guardar en historial
            await self._save_message(
                chat_id=chat_id,
                question=question,
                answer=response,
                context_used=context
            )
            
            return response
            
        except Exception as e:
            print(f"Error procesando pregunta: {e}")
            return "Lo siento, ocurrió un error al procesar tu pregunta."
    
    async def _get_accessible_document_ids(self, user_id: int) -> List[int]:
        """
        Obtiene todos los IDs de documentos accesibles para un usuario
        """
        accessible_ids = []
        
        # 1. Documentos propios
        own_docs = await self.document_service.get_user_documents(user_id)
        accessible_ids.extend([doc.id for doc in own_docs])
        
        # 2. Documentos compartidos
        shared_docs = await self.document_service.get_shared_with_user(user_id)
        accessible_ids.extend([doc.id for doc in shared_docs])
        
        return list(set(accessible_ids))  # Eliminar duplicados
    
    def _build_context(self, chunks: List[dict]) -> str:
        """
        Construye el contexto a partir de los chunks relevantes
        """
        context_parts = []
        
        for chunk in chunks:
            doc_title = chunk.get('metadata', {}).get('document_title', 'Documento')
            content = chunk.get('content', '')
            
            context_parts.append(f"[{doc_title}]: {content}")
        
        return "\n\n".join(context_parts)
    
    async def _generate_ai_response(self, question: str, context: str) -> str:
        """
        Genera respuesta usando IA con el contexto
        """
        # Aquí integrarías con OpenAI, Claude, etc.
        # Por ahora un ejemplo simple
        
        prompt = f"""
        Basándote en el siguiente contexto, responde la pregunta del usuario.
        Si la información no está en el contexto, indica que no tienes esa información.
        
        Contexto:
        {context}
        
        Pregunta: {question}
        
        Respuesta:
        """
        
        # TODO: Integrar con servicio de IA
        # response = await ai_service.generate(prompt)
        
        # Respuesta temporal
        return f"Basándome en los documentos disponibles: [Aquí iría la respuesta de IA basada en el contexto]"
    
    # ==================== MÉTODOS ADMINISTRATIVOS ====================
    
    def get_all_chats(self, limit: int = 100, skip: int = 0, sort_by: str = 'created_at', order: str = 'desc') -> List[ChatResponse]:
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener chats: {str(e)}"
            )
    
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
