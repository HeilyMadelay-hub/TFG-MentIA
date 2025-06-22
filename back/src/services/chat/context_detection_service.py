"""
Servicio para detectar contexto y preguntas fuera de tema
"""
import re
import logging
from typing import Tuple, Dict, List, Optional
import unicodedata

logger = logging.getLogger(__name__)

class ContextDetectionService:
    """Servicio para detectar el contexto de las preguntas y manejar consultas fuera de tema"""
    
    def __init__(self):
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
        
        # Palabras clave relacionadas con documentos
        self.document_keywords = [
            "documento", "archivo", "pdf", "txt", "texto",
            "resume", "resumir", "resumen", "busca", "buscar", 
            "encuentra", "analiza", "analizar", "información",
            "tramite", "trámite", "contenido", "dice", "explica",
            "habla", "trata", "menciona", "contiene", "sobre"
        ]
    
    def detect_out_of_context(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Detecta si la pregunta está fuera del contexto de documentos.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Tuple[bool, Optional[str]]: (es_fuera_de_contexto, tipo_de_pregunta)
        """
        try:
            text_lower = text.lower().strip()
            text_no_accents = self.remove_accents(text_lower)
            
            # Verificar cada categoría
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
            
        except Exception as e:
            logger.error(f"Error detectando contexto: {str(e)}")
            return False, None
    
    def get_context_specific_response(self, category: str, original_text: str) -> str:
        """
        Obtiene una respuesta específica para preguntas fuera de contexto.
        
        Args:
            category: Categoría detectada
            original_text: Texto original de la pregunta
            
        Returns:
            str: Respuesta personalizada
        """
        try:
            base_response = self.out_of_context_responses.get(category, {}).get("response", "")
            
            # Personalizar respuesta según el contexto
            if category == "matematicas" and any(word in original_text.lower() for word in ["suma", "resta", "calcula"]):
                return self._handle_math_question(original_text, base_response)
            
            return base_response
            
        except Exception as e:
            logger.error(f"Error generando respuesta contextual: {str(e)}")
            return "Lo siento, no pude procesar tu pregunta correctamente."
    
    def _handle_math_question(self, text: str, base_response: str) -> str:
        """
        Maneja preguntas matemáticas básicas.
        
        Args:
            text: Texto con la pregunta matemática
            base_response: Respuesta base para matemáticas
            
        Returns:
            str: Respuesta personalizada con el cálculo
        """
        # Extraer números de la pregunta
        numbers = re.findall(r'\d+', text)
        if len(numbers) >= 2:
            try:
                num1, num2 = int(numbers[0]), int(numbers[1])
                
                if "suma" in text.lower() or "+" in text:
                    result = num1 + num2
                    return f"La suma de {num1} + {num2} es {result}. Aunque mi especialidad es analizar documentos, puedo hacer cálculos básicos. Si tienes documentos con datos numéricos, puedo ayudarte a analizarlos más profundamente."
                    
                elif "resta" in text.lower() or "-" in text:
                    result = num1 - num2
                    return f"La resta de {num1} - {num2} es {result}. Recuerda que también puedo analizar documentos con tablas numéricas y estadísticas."
                    
                elif "multiplica" in text.lower() or "*" in text or "x" in text:
                    result = num1 * num2
                    return f"La multiplicación de {num1} × {num2} es {result}. Si tienes documentos con cálculos o datos financieros, puedo ayudarte a interpretarlos."
                    
                elif "divide" in text.lower() or "/" in text:
                    if num2 != 0:
                        result = num1 / num2
                        return f"La división de {num1} ÷ {num2} es {result:.2f}. También puedo analizar documentos con datos estadísticos y proporciones."
            except:
                pass
        
        return base_response
    
    def is_document_related(self, text: str) -> bool:
        """
        Determina si una pregunta está relacionada con documentos.
        
        Args:
            text: Texto a analizar
            
        Returns:
            bool: True si está relacionada con documentos
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.document_keywords)
    
    def remove_accents(self, text: str) -> str:
        """
        Elimina los acentos del texto para comparaciones.
        
        Args:
            text: Texto con posibles acentos
            
        Returns:
            str: Texto sin acentos
        """
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
    
    def classify_intent(self, text: str) -> str:
        """
        Clasifica la intención del usuario basándose en el texto.
        
        Args:
            text: Texto a clasificar
            
        Returns:
            str: Tipo de intención detectada
        """
        text_lower = text.lower()
        
        # Detectar intenciones específicas
        if any(word in text_lower for word in ["buscar", "encontrar", "dónde", "donde"]):
            return "search"
        elif any(word in text_lower for word in ["resumir", "resumen", "resume"]):
            return "summarize"
        elif any(word in text_lower for word in ["analizar", "análisis", "analiza"]):
            return "analyze"
        elif any(word in text_lower for word in ["qué es", "que es", "definir", "explicar"]):
            return "explain"
        elif any(word in text_lower for word in ["listar", "mostrar", "cuáles", "cuales"]):
            return "list"
        else:
            return "general"
