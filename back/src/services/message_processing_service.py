"""
Servicio especializado para el procesamiento de mensajes
Extrae la lógica compleja de procesamiento RAG y análisis de contenido
"""
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from src.models.schemas.chat import MessageCreate, ChatMessage
from src.models.domain import User, Message
from src.services.document_service import DocumentService
from src.utils.ai_connector import OpenAIConnector
from src.repositories.message_repository import MessageRepository
from src.core.exceptions import (
    ValidationException, 
    ExternalServiceException, 
    DatabaseException
)

logger = logging.getLogger(__name__)

class MessageProcessingService:
    """Servicio para procesar mensajes con IA y RAG"""
    
    def __init__(self):
        self.document_service = DocumentService()
        self.ai_connector = OpenAIConnector()
        self.message_repository = MessageRepository()
        
        # Configuración de correcciones ortográficas
        self.spelling_corrections = self._load_spelling_corrections()
        
        # Configuración de respuestas contextuales
        self.context_responses = self._load_context_responses()
    
    def process_incoming_message(
        self, 
        message_data: MessageCreate, 
        chat_id: int, 
        user_id: int
    ) -> ChatMessage:
        """
        Procesa un mensaje entrante y genera una respuesta completa
        
        Args:
            message_data: Datos del mensaje
            chat_id: ID del chat
            user_id: ID del usuario
            
        Returns:
            ChatMessage: Mensaje procesado con respuesta
        """
        try:
            # 1. Preparar y corregir la pregunta
            original_question = message_data.question
            corrected_question, correction_msg = self._correct_spelling(original_question)
            
            # 2. Detectar tipo de contexto
            context_type, is_out_of_context = self._detect_message_context(corrected_question)
            
            # 3. Procesar según el tipo de mensaje
            if is_out_of_context:
                response = self._handle_out_of_context_message(
                    context_type, corrected_question, correction_msg
                )
            else:
                response = self._handle_document_related_message(
                    corrected_question, message_data, user_id, correction_msg
                )
            
            # 4. Crear y retornar mensaje
            return self._create_message_record(
                chat_id=chat_id,
                original_question=original_question,
                response=response
            )
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            raise DatabaseException(f"Error al procesar mensaje: {str(e)}")
    
    def prepare_rag_context(
        self, 
        question: str, 
        document_ids: Optional[List[int]], 
        user_id: int, 
        n_results: int = 5
    ) -> Dict[str, Any]:
        """
        Prepara el contexto RAG para una pregunta
        
        Args:
            question: Pregunta del usuario
            document_ids: IDs de documentos específicos
            user_id: ID del usuario
            n_results: Número de resultados
            
        Returns:
            Dict con contexto RAG preparado
        """
        try:
            logger.info(f"🔍 Preparando contexto RAG para usuario {user_id}")
            logger.info(f"   Pregunta: {question[:100]}...")
            logger.info(f"   Documentos: {document_ids}")
            logger.info(f"   N_results: {n_results}")
            
            # Obtener respuesta RAG del servicio de documentos
            rag_result = self.document_service.get_rag_response(
                query=question,
                user_id=user_id,
                n_results=n_results,
                document_ids=document_ids
            )
            
            documents_used = rag_result.get("documents", [])
            
            # Log información sobre documentos utilizados
            if documents_used:
                logger.info(f"✅ RAG: Utilizados {len(documents_used)} fragmentos de documentos")
                for doc in documents_used:
                    logger.debug(f"   - Doc ID {doc['document_id']}: {doc['title']}")
            else:
                logger.info("⚠️ RAG: No se encontraron documentos relevantes")
            
            return {
                "response": rag_result["response"],
                "documents_used": documents_used,
                "has_context": len(documents_used) > 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error preparando contexto RAG: {str(e)}")
            raise ExternalServiceException("Error al procesar documentos seleccionados")
    
    def handle_message_creation(
        self, 
        question: str, 
        context: Optional[str] = None,
        previous_messages: Optional[List[Message]] = None
    ) -> str:
        """
        Maneja la creación de respuesta usando IA
        
        Args:
            question: Pregunta del usuario
            context: Contexto adicional (RAG)
            previous_messages: Mensajes previos para contexto
            
        Returns:
            str: Respuesta generada
        """
        try:
            # Preparar mensajes para la IA
            messages_context = self._build_conversation_context(previous_messages)
            
            # Añadir mensaje del sistema
            system_message = self._get_system_message(has_context=bool(context))
            messages_with_system = [system_message] + messages_context
            
            # Añadir contexto RAG si existe
            if context:
                enhanced_question = f"""
Contexto de documentos:
{context}

Pregunta del usuario: {question}
"""
            else:
                enhanced_question = question
            
            # Añadir pregunta actual
            messages_with_system.append({"role": "user", "content": enhanced_question})
            
            # Generar respuesta con IA
            response = self.ai_connector.generate_chat_completion(
                messages=messages_with_system,
                temperature=0.7,
                max_tokens=1000
            )
            
            logger.info(f"✅ Respuesta IA generada: {len(response)} caracteres")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error generando respuesta IA: {str(e)}")
            raise ExternalServiceException("Error al procesar tu consulta con el servicio de IA")
    
    def format_response_message(
        self, 
        response: str, 
        correction_msg: Optional[str] = None,
        documents_used: Optional[List[Dict]] = None
    ) -> str:
        """
        Formatea la respuesta final con información adicional
        
        Args:
            response: Respuesta base
            correction_msg: Mensaje de correcciones ortográficas
            documents_used: Documentos utilizados en RAG
            
        Returns:
            str: Respuesta formateada
        """
        formatted_parts = []
        
        # Añadir mensaje de corrección si existe
        if correction_msg:
            formatted_parts.append(correction_msg)
        
        # Añadir respuesta principal
        formatted_parts.append(response)
        
        # Añadir información de documentos utilizados si corresponde
        if documents_used and len(documents_used) > 0:
            doc_info = self._format_documents_info(documents_used)
            if doc_info:
                formatted_parts.append(doc_info)
        
        return "\n\n".join(formatted_parts)
    
    def log_message_interaction(
        self, 
        user_id: int, 
        chat_id: int, 
        question_type: str,
        processing_time: float,
        has_rag: bool = False
    ) -> None:
        """
        Registra información sobre la interacción del mensaje
        
        Args:
            user_id: ID del usuario
            chat_id: ID del chat
            question_type: Tipo de pregunta procesada
            processing_time: Tiempo de procesamiento en segundos
            has_rag: Si se utilizó RAG
        """
        logger.info(
            f"📊 Mensaje procesado - Usuario: {user_id}, Chat: {chat_id}, "
            f"Tipo: {question_type}, Tiempo: {processing_time:.3f}s, RAG: {has_rag}"
        )
    
    # ==================== MÉTODOS PRIVADOS ====================
    
    def _correct_spelling(self, text: str) -> Tuple[str, str]:
        """Corrige errores ortográficos comunes"""
        try:
            # Intentar usar función avanzada si existe
            from .chat_service_improved_patch import correct_spelling_advanced
            return correct_spelling_advanced(text)
        except ImportError:
            # Fallback a implementación básica
            return self._basic_spelling_correction(text)
    
    def _basic_spelling_correction(self, text: str) -> Tuple[str, str]:
        """Implementación básica de corrección ortográfica"""
        corrections_made = []
        words = text.split()
        corrected_words = []
        
        for word in words:
            word_lower = word.lower()
            corrected = False
            
            # Buscar en correcciones comunes
            for correct_word, variations in self.spelling_corrections.items():
                if isinstance(variations, list):
                    if word_lower in [v.lower() for v in variations]:
                        corrected_words.append(correct_word)
                        if word_lower != correct_word.lower():
                            corrections_made.append(f"'{word}' → '{correct_word}'")
                        corrected = True
                        break
                elif isinstance(variations, str) and word_lower == correct_word.lower():
                    corrected_words.append(variations)
                    corrections_made.append(f"'{word}' → '{variations}'")
                    corrected = True
                    break
            
            if not corrected:
                corrected_words.append(word)
        
        corrected_text = ' '.join(corrected_words)
        correction_message = ""
        if corrections_made:
            correction_message = f"💡 Correcciones: {', '.join(corrections_made[:3])}"
            if len(corrections_made) > 3:
                correction_message += f" y {len(corrections_made) - 3} más"
        
        return corrected_text, correction_message
    
    def _detect_message_context(self, text: str) -> Tuple[str, bool]:
        """Detecta el contexto del mensaje"""
        try:
            # Intentar usar función avanzada si existe
            from .chat_service_improved_patch import detect_context_advanced
            is_out_of_context, category = detect_context_advanced(text)
            return category or "general", is_out_of_context
        except ImportError:
            # Fallback a implementación básica
            return self._basic_context_detection(text)
    
    def _basic_context_detection(self, text: str) -> Tuple[str, bool]:
        """Implementación básica de detección de contexto"""
        text_lower = text.lower().strip()
        
        # Patrones para preguntas fuera de contexto
        for category, patterns in self.context_responses.items():
            for pattern in patterns.get("patterns", []):
                if pattern.lower() in text_lower:
                    return category, True
        
        # Detectar preguntas sobre documentos
        document_keywords = [
            "documento", "archivo", "pdf", "txt", "resume", "resumir", 
            "busca", "buscar", "encuentra", "analiza", "información"
        ]
        
        if any(keyword in text_lower for keyword in document_keywords):
            return "document_question", False
        
        return "general", False
    
    def _handle_out_of_context_message(
        self, 
        context_type: str, 
        question: str, 
        correction_msg: str
    ) -> str:
        """Maneja mensajes fuera de contexto de documentos"""
        try:
            # Intentar usar función avanzada si existe
            from .chat_service_improved_patch import get_contextual_response
            base_response = get_contextual_response(context_type, question)
        except ImportError:
            # Fallback a implementación básica
            base_response = self.context_responses.get(context_type, {}).get(
                "response", 
                "Soy MentIA, tu asistente para documentos. ¿Hay algo específico sobre tus documentos en lo que pueda ayudarte?"
            )
        
        # Personalizar respuesta según el contexto específico
        if context_type == "matematicas":
            enhanced_response = self._handle_math_question(question, base_response)
        else:
            enhanced_response = base_response
        
        return self.format_response_message(enhanced_response, correction_msg)
    
    def _handle_document_related_message(
        self, 
        question: str, 
        message_data: MessageCreate, 
        user_id: int, 
        correction_msg: str
    ) -> str:
        """Maneja mensajes relacionados con documentos"""
        question_lower = question.lower().strip()
        
        # 1. Detectar preguntas sobre listar documentos
        if self._is_document_list_question(question_lower):
            return self._handle_document_list_request(user_id, correction_msg)
        
        # 2. Verificar si hay documentos seleccionados
        document_ids = getattr(message_data, 'document_ids', None)
        n_results = getattr(message_data, 'n_results', 5)
        
        # 3. Si es pregunta sobre documentos pero no hay documentos seleccionados
        if self._is_document_content_question(question_lower) and not document_ids:
            response = (
                "Para responder preguntas sobre documentos, primero debes seleccionar "
                "un documento usando el botón de carpeta en la parte superior del chat.\n\n"
                "Una vez seleccionado el documento, podrás hacer preguntas sobre su contenido "
                "y recibirás respuestas basadas en la información que contiene."
            )
            return self.format_response_message(response, correction_msg)
        
        # 4. Si hay documentos seleccionados, usar RAG
        if document_ids:
            rag_context = self.prepare_rag_context(question, document_ids, user_id, n_results)
            response = rag_context["response"]
            return self.format_response_message(
                response, 
                correction_msg, 
                rag_context.get("documents_used")
            )
        
        # 5. Respuesta general sin documentos
        general_response = self.handle_message_creation(question)
        return self.format_response_message(general_response, correction_msg)
    
    def _handle_document_list_request(self, user_id: int, correction_msg: str) -> str:
        """Maneja solicitudes de listar documentos del usuario"""
        try:
            logger.info(f"📋 Usuario {user_id} solicita lista de sus documentos")
            
            all_documents = self.document_service.list_user_documents(user_id, limit=100)
            
            if all_documents:
                logger.info(f"✅ Encontrados {len(all_documents)} documentos del usuario")
                
                # Agrupar por tipo
                docs_by_type = {}
                for doc in all_documents:
                    doc_type = doc.content_type or "otro"
                    if doc_type not in docs_by_type:
                        docs_by_type[doc_type] = []
                    docs_by_type[doc_type].append(doc)
                
                # Construir respuesta formateada
                response_parts = [f"📚 Tienes {len(all_documents)} documento(s) en tu biblioteca:\n"]
                
                for doc_type, docs in docs_by_type.items():
                    type_name = {
                        "application/pdf": "📄 Documentos PDF",
                        "text/plain": "📝 Documentos de texto (TXT)"
                    }.get(doc_type, "📁 Otros archivos")
                    
                    response_parts.append(f"\n{type_name}:")
                    for i, doc in enumerate(docs, 1):
                        fecha = doc.created_at.strftime('%d/%m/%Y') if doc.created_at else "Fecha desconocida"
                        response_parts.append(f"  {i}. {doc.title} (subido: {fecha})")
                
                response_parts.append(
                    "\n\n💡 Para hacer preguntas sobre un documento específico, "
                    "selecciónalo con el botón de carpeta en la parte superior."
                )
                
                response = "\n".join(response_parts)
            else:
                response = (
                    "📭 No tienes documentos subidos aún.\n\n"
                    "💡 Puedes subir documentos desde la sección 'Mis Documentos' en el menú principal. "
                    "Acepto archivos PDF y TXT."
                )
            
            return self.format_response_message(response, correction_msg)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo documentos del usuario: {str(e)}")
            raise DatabaseException("Error al obtener la lista de documentos")
    
    def _handle_math_question(self, question: str, base_response: str) -> str:
        """Maneja preguntas matemáticas básicas"""
        # Extraer números de la pregunta
        numbers = re.findall(r'\d+', question)
        if len(numbers) >= 2:
            try:
                num1, num2 = int(numbers[0]), int(numbers[1])
                question_lower = question.lower()
                
                if "suma" in question_lower or "+" in question:
                    result = num1 + num2
                    return f"🧮 {num1} + {num2} = {result}\n\n{base_response}"
                elif "resta" in question_lower or "-" in question:
                    result = num1 - num2
                    return f"🧮 {num1} - {num2} = {result}\n\n{base_response}"
                elif any(word in question_lower for word in ["multiplica", "*", "×"]):
                    result = num1 * num2
                    return f"🧮 {num1} × {num2} = {result}\n\n{base_response}"
                elif "divide" in question_lower or "/" in question:
                    if num2 != 0:
                        result = num1 / num2
                        return f"🧮 {num1} ÷ {num2} = {result:.2f}\n\n{base_response}"
            except (ValueError, ZeroDivisionError):
                pass
        
        return base_response
    
    def _is_document_list_question(self, question_lower: str) -> bool:
        """Detecta si es una pregunta sobre listar documentos"""
        list_patterns = [
            "qué documentos tengo", "que documentos tengo", "mis documentos",
            "listar documentos", "mostrar documentos", "cuáles son mis documentos",
            "documentos disponibles", "qué archivos tengo", "mis archivos"
        ]
        return any(pattern in question_lower for pattern in list_patterns)
    
    def _is_document_content_question(self, question_lower: str) -> bool:
        """Detecta si es una pregunta sobre contenido de documentos"""
        content_keywords = [
            "resume", "resumir", "resumen", "busca", "buscar", "encuentra",
            "analiza", "analizar", "información", "contenido", "dice",
            "explica", "habla", "trata", "menciona", "contiene"
        ]
        return any(keyword in question_lower for keyword in content_keywords)
    
    def _build_conversation_context(self, previous_messages: Optional[List[Message]]) -> List[Dict[str, str]]:
        """Construye el contexto de la conversación para la IA"""
        if not previous_messages:
            return []
        
        context = []
        for msg in previous_messages[-10:]:  # Últimos 10 mensajes
            if msg.question:
                context.append({"role": "user", "content": msg.question})
            if msg.answer:
                context.append({"role": "assistant", "content": msg.answer})
        
        return context
    
    def _get_system_message(self, has_context: bool = False) -> Dict[str, str]:
        """Obtiene el mensaje del sistema para la IA"""
        if has_context:
            content = (
                "Eres MentIA, un asistente especializado en análisis de documentos. "
                "El usuario te ha proporcionado contexto específico de sus documentos. "
                "Responde basándote principalmente en esa información, siendo preciso y útil. "
                "Si no puedes responder con la información proporcionada, dilo claramente."
            )
        else:
            content = (
                "Eres MentIA, un asistente inteligente especializado en análisis de documentos. "
                "Ayuda al usuario con consultas generales pero siempre recuerda tu función principal "
                "de asistir con documentos. Sé amigable, profesional y útil."
            )
        
        return {"role": "system", "content": content}
    
    def _format_documents_info(self, documents_used: List[Dict]) -> str:
        """Formatea información sobre documentos utilizados"""
        if not documents_used:
            return ""
        
        if len(documents_used) == 1:
            doc = documents_used[0]
            return f"📄 *Información basada en: {doc['title']}*"
        else:
            doc_titles = [doc['title'] for doc in documents_used[:3]]
            info = f"📚 *Información basada en {len(documents_used)} documento(s): {', '.join(doc_titles)}"
            if len(documents_used) > 3:
                info += f" y {len(documents_used) - 3} más*"
            else:
                info += "*"
            return info
    
    def _create_message_record(self, chat_id: int, original_question: str, response: str) -> ChatMessage:
        """Crea el registro del mensaje en la base de datos"""
        try:
            # Crear mensaje en la base de datos
            message = self.message_repository.create_message(
                chat_id=chat_id,
                question=original_question,
                answer=response
            )
            
            # Convertir a esquema de respuesta
            return ChatMessage(
                id=message.id,
                id_chat=message.id_chat,
                question=message.question or "",
                answer=message.answer,
                created_at=message.created_at
            )
            
        except Exception as e:
            logger.error(f"❌ Error creando registro de mensaje: {str(e)}")
            raise DatabaseException(f"Error al guardar mensaje: {str(e)}")
    
    def _load_spelling_corrections(self) -> Dict[str, Any]:
        """Carga configuración de correcciones ortográficas"""
        return {
            "qué": ["que", "qué"],
            "cómo": ["como", "cómo"], 
            "cuándo": ["cuando", "cuándo"],
            "dónde": ["donde", "dónde"],
            "documento": ["documento", "documeto", "ducumento"],
            "archivo": ["archivo", "archibo", "arcivo"],
            "información": ["información", "informacion", "imformacion"],
            "buscar": ["buscar", "buskar", "busqar"],
            "análisis": ["análisis", "analisis", "analicis"]
        }
    
    def _load_context_responses(self) -> Dict[str, Dict[str, Any]]:
        """Carga configuración de respuestas contextuales"""
        return {
            "saludos": {
                "patterns": ["hola", "buenos días", "buenas tardes", "hey", "saludos"],
                "response": "¡Hola! Soy MentIA, tu asistente para documentos. ¿En qué puedo ayudarte hoy?"
            },
            "despedidas": {
                "patterns": ["adiós", "chao", "hasta luego", "bye"],
                "response": "¡Hasta luego! Ha sido un placer ayudarte con tus documentos."
            },
            "agradecimientos": {
                "patterns": ["gracias", "muchas gracias", "te agradezco"],
                "response": "¡De nada! Me alegra haberte sido de ayuda con tus documentos."
            },
            "identidad": {
                "patterns": ["quién eres", "qué eres", "tu nombre"],
                "response": "Soy MentIA, tu asistente inteligente para análisis de documentos."
            },
            "matematicas": {
                "patterns": ["cuánto es", "suma", "resta", "multiplica", "divide"],
                "response": "Puedo hacer cálculos básicos, pero mi especialidad es analizar documentos."
            }
        }
