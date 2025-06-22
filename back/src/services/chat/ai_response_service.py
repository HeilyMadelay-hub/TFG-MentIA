"""
Servicio para generar respuestas de IA
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.interfaces.connectors import IAIConnector
from src.repositories.message_repository import MessageRepository
from src.models.domain import Message

logger = logging.getLogger(__name__)

class AIResponseService:
    """Servicio especializado en generar respuestas de IA"""
    
    def __init__(self, ai_connector: IAIConnector):
        """
        Inicializa el servicio
        
        Args:
            ai_connector: Implementación de IAIConnector
        """
        self.ai_connector = ai_connector
        self.message_repository = MessageRepository()
        
        # Configuración de prompts del sistema
        self.system_prompts = {
            "default": (
                "Eres MentIA, un asistente inteligente especializado en el análisis de documentos. "
                "Tu función principal es ayudar a los usuarios a gestionar, buscar y comprender "
                "el contenido de sus documentos PDF y archivos de texto. Sé amigable, profesional y útil."
            ),
            "with_documents": (
                "Eres MentIA, un asistente inteligente. Basándote en el contexto proporcionado "
                "de los documentos, responde de manera precisa y útil. Si la información no está "
                "en el contexto, indícalo claramente."
            ),
            "math": (
                "Eres MentIA. Aunque tu especialidad es el análisis de documentos, puedes ayudar "
                "con cálculos matemáticos básicos cuando sea necesario."
            )
        }
        
        # Configuración de parámetros por defecto
        self.default_params = {
            "temperature": 0.7,
            "max_tokens": 1000,
            "model": None  # Usará el modelo por defecto del conector
        }
    
    def generate_response(
        self,
        question: str,
        context: Optional[str] = None,
        chat_history: Optional[List[Message]] = None,
        response_type: str = "default",
        **kwargs
    ) -> str:
        """
        Genera una respuesta de IA
        
        Args:
            question: Pregunta del usuario
            context: Contexto adicional (ej: de documentos)
            chat_history: Historial de mensajes del chat
            response_type: Tipo de respuesta a generar
            **kwargs: Parámetros adicionales para la generación
            
        Returns:
            str: Respuesta generada
        """
        try:
            # Construir mensajes para el modelo
            messages = self._build_messages(
                question=question,
                context=context,
                chat_history=chat_history,
                response_type=response_type
            )
            
            # Obtener parámetros de generación
            params = self._get_generation_params(**kwargs)
            
            # Generar respuesta
            response = self.ai_connector.generate_chat_completion(
                messages=messages,
                **params
            )
            
            logger.info(f"Respuesta generada exitosamente. Tipo: {response_type}")
            return response
            
        except Exception as e:
            logger.error(f"Error generando respuesta de IA: {str(e)}")
            raise Exception(f"Error al generar respuesta: {str(e)}")
    
    def generate_document_response(
        self,
        question: str,
        document_context: str,
        chat_history: Optional[List[Message]] = None,
        **kwargs
    ) -> str:
        """
        Genera una respuesta basada en documentos
        
        Args:
            question: Pregunta del usuario
            document_context: Contexto extraído de documentos
            chat_history: Historial del chat
            **kwargs: Parámetros adicionales
            
        Returns:
            str: Respuesta generada
        """
        # Prompt específico para respuestas basadas en documentos
        enhanced_context = (
            f"Contexto de los documentos:\n{document_context}\n\n"
            "Basándote ÚNICAMENTE en el contexto anterior, responde la siguiente pregunta. "
            "Si la información no está en el contexto, indica que no puedes responder "
            "basándote en los documentos proporcionados."
        )
        
        return self.generate_response(
            question=question,
            context=enhanced_context,
            chat_history=chat_history,
            response_type="with_documents",
            **kwargs
        )
    
    def generate_summary(
        self,
        text: str,
        max_length: int = 500,
        style: str = "concise"
    ) -> str:
        """
        Genera un resumen de texto
        
        Args:
            text: Texto a resumir
            max_length: Longitud máxima del resumen
            style: Estilo del resumen (concise, detailed, bullet_points)
            
        Returns:
            str: Resumen generado
        """
        style_prompts = {
            "concise": "Resume el siguiente texto de manera concisa en un párrafo:",
            "detailed": "Proporciona un resumen detallado del siguiente texto:",
            "bullet_points": "Resume el siguiente texto en puntos clave:"
        }
        
        prompt = f"{style_prompts.get(style, style_prompts['concise'])}\n\n{text}"
        
        messages = [
            {"role": "system", "content": self.system_prompts["default"]},
            {"role": "user", "content": prompt}
        ]
        
        return self.ai_connector.generate_chat_completion(
            messages=messages,
            max_tokens=max_length
        )
    
    def _build_messages(
        self,
        question: str,
        context: Optional[str],
        chat_history: Optional[List[Message]],
        response_type: str
    ) -> List[Dict[str, str]]:
        """
        Construye la lista de mensajes para el modelo
        
        Args:
            question: Pregunta actual
            context: Contexto adicional
            chat_history: Historial del chat
            response_type: Tipo de respuesta
            
        Returns:
            List[Dict[str, str]]: Lista de mensajes formateados
        """
        messages = []
        
        # Agregar prompt del sistema
        system_prompt = self.system_prompts.get(response_type, self.system_prompts["default"])
        messages.append({"role": "system", "content": system_prompt})
        
        # Agregar contexto si existe
        if context:
            messages.append({"role": "system", "content": f"Contexto adicional: {context}"})
        
        # Agregar historial del chat
        if chat_history:
            for msg in chat_history[-10:]:  # Últimos 10 mensajes para no exceder límites
                if msg.question:
                    messages.append({"role": "user", "content": msg.question})
                if msg.answer:
                    messages.append({"role": "assistant", "content": msg.answer})
        
        # Agregar pregunta actual
        messages.append({"role": "user", "content": question})
        
        return messages
    
    def _get_generation_params(self, **kwargs) -> Dict[str, Any]:
        """
        Obtiene los parámetros de generación
        
        Args:
            **kwargs: Parámetros opcionales
            
        Returns:
            Dict[str, Any]: Parámetros de generación
        """
        params = self.default_params.copy()
        
        # Actualizar con parámetros proporcionados
        for key in ['temperature', 'max_tokens', 'model']:
            if key in kwargs:
                params[key] = kwargs[key]
        
        return params
    
    def count_tokens(self, text: str) -> int:
        """
        Cuenta los tokens en un texto
        
        Args:
            text: Texto a analizar
            
        Returns:
            int: Número de tokens
        """
        return self.ai_connector.count_tokens(text)
    
    def estimate_cost(self, input_tokens: int, output_tokens: int, model: Optional[str] = None) -> float:
        """
        Estima el costo de una generación
        
        Args:
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            model: Modelo usado
            
        Returns:
            float: Costo estimado en dólares
        """
        # Precios aproximados por 1K tokens (actualizar según el proveedor)
        pricing = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "default": {"input": 0.002, "output": 0.002}
        }
        
        model_pricing = pricing.get(model or "default", pricing["default"])
        
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost
