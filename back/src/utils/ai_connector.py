"""
Conector para la API de Gemini con patrón singleton.
Gestiona las llamadas a Gemini para generación de texto y embeddings.
"""
import os
from typing import List, Dict, Optional, Any
import google.generativeai as genai
from src.core.logging_config import get_logger
from src.core.exceptions import ValidationException, ExternalServiceException
from src.config.settings import get_settings
from src.core.interfaces.connectors import IAIConnector

logger = get_logger(__name__)
settings = get_settings()

class GeminiConnector(IAIConnector):
    """
    Implementación del patrón Singleton para las conexiones a Gemini.
    Maneja la autenticación y las llamadas a la API.
    Implementa la interfaz IAIConnector.
    """
    # Atributo de clase que almacenará la única instancia (Singleton)
    _instance: Optional['GeminiConnector'] = None 
    # Atributos para almacenar la configuración
    _client = None
    _embedding_model = None
    
    def __new__(cls):
        # Si no existe una instancia previa de la clase, se crea una nueva
        if cls._instance is None:
            cls._instance = super(GeminiConnector, cls).__new__(cls)
        # Devuelve la instancia única (Singleton)
        return cls._instance
    
    def __init__(self):
        # Inicializa los clientes
        self._client = None
        self._embedding_model = None
    
    def get_client(self):
        """
        Configura y obtiene el cliente de Gemini, inicializándolo si es necesario.
        """
        # Si el cliente aún no ha sido inicializado
        if self._client is None:
            # Obtiene la API key desde las variables de entorno
            api_key = os.getenv("GEMINI_API_KEY")
            
            # Si no se encuentra la API key, lanza un error
            if not api_key:
                raise ValidationException(
                    "La variable de entorno GEMINI_API_KEY es requerida. "
                    "Asegúrate de configurarla en el archivo .env"
                )
            
            # Registra un mensaje indicando que se está inicializando el cliente
            logger.info("Inicializando cliente de Gemini")
            
            # Configurar la API de Gemini
            genai.configure(api_key=api_key)
            self._client = genai
        
        # Devuelve el cliente inicializado
        return self._client
    
    def get_embedding_model(self):
        """
        Obtiene el modelo de embedding, inicializándolo si es necesario.
        Gemini no tiene embeddings completos, así que usamos SentenceTransformer.
        """
        if self._embedding_model is None:
            try:
                # Importar SentenceTransformer solo cuando se necesite
                from sentence_transformers import SentenceTransformer
                # Usar SentenceTransformer como alternativa a Gemini para embeddings
                logger.info(f"Inicializando modelo de embeddings ({settings.SENTENCE_TRANSFORMER_MODEL})")
                self._embedding_model = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)
            except ImportError as e:
                logger.error(f"Error importando SentenceTransformer: {e}")
                raise ExternalServiceException("SentenceTransformer no está instalado. Ejecuta: pip install sentence-transformers")
        return self._embedding_model
    
    def create_embeddings(self, texts: List[str], model: str = None) -> List[List[float]]:
        """
        Genera embeddings vectoriales para una lista de textos.
        
        Args:
            texts: Lista de textos para generar embeddings
            model: Parámetro mantenido por compatibilidad (ignorado)
        
        Returns:
            Lista de vectores (embeddings)
        """
        try:
            # Usar SentenceTransformer para embeddings
            embedding_model = self.get_embedding_model()
            # Generar embeddings
            embeddings = embedding_model.encode(texts, convert_to_numpy=True)
            # Convertir a lista de listas para mantener compatibilidad
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error al generar embeddings: {str(e)}", exc_info=True)
            raise ExternalServiceException(f"Error generando embeddings: {str(e)}")
    
    def generate_chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,  # Mantenido por compatibilidad
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Genera una respuesta de chat usando Gemini.
        
        Args:
            messages: Lista de mensajes en formato [{"role": "...", "content": "..."}]
            model: Parámetro mantenido por compatibilidad (se ignora y usa config global)
            temperature: Temperatura para la generación (0-1)
            max_tokens: Máximo número de tokens a generar
        
        Returns:
            Texto generado por el modelo
        """
        try:
            # Obtiene el cliente de Gemini
            client = self.get_client()
            
            # Obtener el modelo de la configuración
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            gemini_model = client.GenerativeModel(model_name)
            
            # Separar el último mensaje del historial
            if not messages:
                raise ValidationException("No hay mensajes para procesar")
            
            # Obtener el último mensaje (que será el prompt actual)
            last_message = messages[-1]
            history_messages = messages[:-1] if len(messages) > 1 else []
            
            # Convertir historial a formato Gemini
            gemini_history = []
            for msg in history_messages:
                # Gemini usa "user" y "model" como roles
                if msg["role"].lower() == "user":
                    role = "user"
                elif msg["role"].lower() in ["assistant", "system"]:
                    role = "model"
                else:
                    role = "user"  # Por defecto
                
                content = msg["content"]
                if content and content.strip():  # Solo añadir si hay contenido
                    gemini_history.append({
                        "role": role, 
                        "parts": [{"text": content}]
                    })
            
            # Crear configuración de generación
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            # Si hay historial, usar chat
            if gemini_history:
                chat = gemini_model.start_chat(history=gemini_history)
                # Enviar el último mensaje
                response = chat.send_message(
                    last_message["content"],
                    generation_config=generation_config
                )
            else:
                # Si no hay historial, generar directamente
                response = gemini_model.generate_content(
                    last_message["content"],
                    generation_config=generation_config
                )
            
            # Devolver el texto generado
            return response.text
            
        except ValidationException:
            raise  # Re-lanzar excepciones ya manejadas
        except Exception as e:
            logger.error(f"Error al generar respuesta: {str(e)}", exc_info=True)
            raise ExternalServiceException(f"Error al generar respuesta con Gemini: {str(e)}")
    
    def generate_rag_response(
        self,
        query: str,
        context: List[str],
        system_template: str = "Eres un asistente útil que responde preguntas basándose en el siguiente contexto:\n\n{context}",
        model: str = None,  # Mantenido por compatibilidad
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Genera una respuesta basada en RAG (Retrieval-Augmented Generation).
        
        Args:
            query: Pregunta del usuario
            context: Lista de fragmentos de texto relevantes
            system_template: Plantilla para el mensaje de sistema
            model: Modelo a utilizar (se ignora y usa config global)
            temperature: Temperatura para la generación (0-1)
            max_tokens: Máximo número de tokens a generar
            
        Returns:
            Texto generado por el modelo
        """
        try:
            # Validar que hay contexto
            if not context or not any(c.strip() for c in context):
                raise ValidationException("El contexto está vacío")
            
            # Une los fragmentos de contexto en un solo string, numerándolos
            context_text = "\n\n".join([f"Fragmento {i+1}: {text}" for i, text in enumerate(context) if text and text.strip()])
            
            # Crea el mensaje de sistema usando la plantilla y el contexto
            system_message = system_template.format(context=context_text)
            
            # Para Gemini, combinar el sistema y la pregunta del usuario en un solo prompt
            combined_prompt = f"{system_message}\n\nPregunta: {query}\n\nRespuesta:"
            
            # Usar el modelo directamente con el prompt combinado
            client = self.get_client()
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            gemini_model = client.GenerativeModel(model_name)
            
            # Generar respuesta
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            response = gemini_model.generate_content(
                combined_prompt,
                generation_config=generation_config
            )
            
            return response.text
            
        except ValidationException:
            raise  # Re-lanzar excepciones ya manejadas
        except Exception as e:
            logger.error(f"Error al generar respuesta RAG: {str(e)}", exc_info=True)
            raise ExternalServiceException(f"Error al generar respuesta RAG con Gemini: {str(e)}")
    
    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: str = None  # Mantenido por compatibilidad
    ):
        """
        Genera respuesta en streaming usando Gemini
        
        Args:
            messages: Lista de mensajes de conversación
            temperature: Temperatura de generación
            max_tokens: Máximo de tokens
            model: Modelo a usar (se ignora y usa config global)
            
        Yields:
            str: Chunks de la respuesta
        """
        try:
            # Obtener el cliente de Gemini
            client = self.get_client()
            
            # Obtener el modelo de la configuración
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            gemini_model = client.GenerativeModel(model_name)
            
            # Separar el último mensaje del historial
            if not messages:
                yield "[Error: No hay mensajes para procesar]"
                return
            
            # Obtener el último mensaje (que será el prompt actual)
            last_message = messages[-1]
            history_messages = messages[:-1] if len(messages) > 1 else []
            
            # Convertir historial a formato Gemini
            gemini_history = []
            for msg in history_messages:
                # Gemini usa "user" y "model" como roles
                if msg["role"].lower() == "user":
                    role = "user"
                elif msg["role"].lower() in ["assistant", "system"]:
                    role = "model"
                else:
                    role = "user"  # Por defecto
                
                content = msg["content"]
                if content and content.strip():  # Solo añadir si hay contenido
                    gemini_history.append({
                        "role": role, 
                        "parts": [{"text": content}]
                    })
            
            # Crear configuración de generación
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            # Si hay historial, usar chat
            if gemini_history:
                chat = gemini_model.start_chat(history=gemini_history)
                # Enviar el último mensaje con streaming
                response = chat.send_message(
                    last_message["content"],
                    generation_config=generation_config,
                    stream=True  # Habilitar streaming
                )
            else:
                # Si no hay historial, generar directamente con streaming
                response = gemini_model.generate_content(
                    last_message["content"],
                    generation_config=generation_config,
                    stream=True  # Habilitar streaming
                )
            
            # Yield chunks de la respuesta
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Error en streaming Gemini: {str(e)}")
            yield f"\n[Error: {str(e)}]"
    
    def count_tokens(self, text: str) -> int:
        """
        Cuenta los tokens en un texto.
        
        Args:
            text: Texto a analizar
            
        Returns:
            int: Número estimado de tokens
        """
        # Estimación simple: ~4 caracteres por token
        # Para una estimación más precisa, usar el tokenizer de Gemini
        return len(text) // 4

# Función auxiliar para obtener la instancia del conector
def get_gemini_connector() -> GeminiConnector:
    """
    Función auxiliar para obtener la instancia del conector de Gemini.
    """
    return GeminiConnector()

# Mantener compatibilidad con el código existente
OpenAIConnector = GeminiConnector
get_openai_connector = get_gemini_connector
