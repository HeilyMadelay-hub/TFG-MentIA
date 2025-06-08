"""
Parche de mejoras para chat_service.py
Este archivo contiene las funciones mejoradas para integrar en tu ChatService existente
"""

import re
from difflib import get_close_matches, SequenceMatcher
import unicodedata
from typing import List, Optional, Tuple
import random

# =======================
# DICCIONARIOS DE DATOS
# =======================

SPELLING_CORRECTIONS = {
    # Errores de acentuación
    "que": ["qué", "que"],
    "como": ["cómo", "como"],
    "cuando": ["cuándo", "cuando"],
    "donde": ["dónde", "donde"],
    "porque": ["por qué", "porque", "porqué"],
    "quien": ["quién", "quien"],
    "cual": ["cuál", "cual"],
    "cuales": ["cuáles", "cuales"],
    
    # Errores comunes
    "aver": "a ver",
    "haber": "a ver",
    "ahi": "ahí",
    "halla": "haya",
    "alla": "allá",
    "valla": "vaya",
    "balla": "vaya",
    
    # Documentos
    "documento": ["documento", "documeto", "ducumento", "docmento", "dokumento"],
    "archivo": ["archivo", "archibo", "arcivo", "archvo"],
    "pdf": ["pdf", "pfd", "dpf"],
    "resumen": ["resumen", "resumne", "resmen", "rezumen"],
    "información": ["información", "informacion", "imformacion"],
    
    # Saludos
    "hola": ["hola", "ola", "holaa", "hla"],
    "gracias": ["gracias", "grasias", "gracas", "graciass"],
}

CONTEXT_RESPONSES = {
    "saludos": {
        "patterns": ["hola", "buenos días", "buenas tardes", "hey", "qué tal"],
        "responses": [
            "¡Hola! 👋 Soy MentIA, tu asistente para documentos. ¿En qué puedo ayudarte?",
            "¡Bienvenido! Estoy aquí para ayudarte con tus documentos. ¿Qué necesitas?"
        ]
    },
    "identidad": {
        "patterns": ["quién eres", "qué eres", "tu nombre", "cómo te llamas"],
        "responses": [
            "Soy MentIA, tu asistente inteligente de DocuMente. 🤖 Mi especialidad es ayudarte con:\n\n📄 Análisis de documentos\n🔍 Búsqueda de información\n📝 Resúmenes\n❓ Responder preguntas\n\n¿Qué te gustaría hacer?"
        ]
    },
    "capacidades": {
        "patterns": ["qué puedes hacer", "ayuda", "help", "funciones"],
        "responses": [
            "¡Puedo ayudarte con:\n\n📄 **Análisis de documentos**\n🔍 **Búsqueda de información**\n📝 **Resúmenes**\n❓ **Responder preguntas**\n📊 **Extracción de datos**\n\n¿Qué necesitas?"
        ]
    },
    "matematicas": {
        "patterns": ["cuánto es", "suma", "resta", "multiplica", "divide", "calcula"],
        "responses": [
            "Puedo hacer cálculos, pero mi especialidad es analizar documentos con datos numéricos. 🔢"
        ]
    }
}

# =======================
# FUNCIONES DE MEJORA
# =======================

def normalize_text(text: str) -> str:
    """Normaliza el texto para comparaciones"""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'^[^a-zA-Z0-9áéíóúñü]+|[^a-zA-Z0-9áéíóúñü]+$', '', text)
    return text

def remove_accents(text: str) -> str:
    """Elimina acentos para comparaciones flexibles"""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

def find_best_correction(word: str, possible_corrections: List[str], threshold: float = 0.8) -> Optional[str]:
    """Encuentra la mejor corrección para una palabra"""
    word_lower = word.lower()
    word_no_accent = remove_accents(word_lower)
    
    best_match = None
    best_score = 0
    
    for correction in possible_corrections:
        correction_lower = correction.lower()
        correction_no_accent = remove_accents(correction_lower)
        
        score1 = SequenceMatcher(None, word_lower, correction_lower).ratio()
        score2 = SequenceMatcher(None, word_no_accent, correction_no_accent).ratio()
        
        max_score = max(score1, score2)
        
        if max_score > best_score and max_score >= threshold:
            best_score = max_score
            best_match = correction
    
    return best_match

def correct_spelling_advanced(text: str, corrections_dict: dict = SPELLING_CORRECTIONS) -> Tuple[str, List[str]]:
    """
    Corrección ortográfica avanzada
    Retorna: (texto_corregido, lista_de_correcciones)
    """
    corrections_made = []
    
    # Correcciones de frases
    text_lower = text.lower()
    phrase_corrections = {
        "por que": "por qué",
        "haber si": "a ver si",
        "aver si": "a ver si",
        "por fabor": "por favor",
        "porfabor": "por favor",
        "muchas grasias": "muchas gracias",
        "buenos dias": "buenos días",
        "buenas tarde": "buenas tardes",
    }
    
    for wrong, correct in phrase_corrections.items():
        if wrong in text_lower:
            text = re.sub(re.escape(wrong), correct, text, flags=re.IGNORECASE)
            corrections_made.append(f"'{wrong}' → '{correct}'")
    
    # Corrección palabra por palabra
    words = text.split()
    corrected_words = []
    
    for word in words:
        word_lower = word.lower()
        corrected = False
        
        # Buscar corrección directa
        if word_lower in corrections_dict:
            correction = corrections_dict[word_lower]
            if isinstance(correction, str):
                corrected_words.append(correction)
                if word_lower != correction.lower():
                    corrections_made.append(f"'{word}' → '{correction}'")
                corrected = True
            elif isinstance(correction, list):
                best = find_best_correction(word, correction)
                if best and word_lower != best.lower():
                    corrected_words.append(best)
                    corrections_made.append(f"'{word}' → '{best}'")
                    corrected = True
        
        if not corrected:
            corrected_words.append(word)
    
    return ' '.join(corrected_words), corrections_made

def detect_context_advanced(text: str, context_dict: dict = CONTEXT_RESPONSES) -> Tuple[bool, str, float]:
    """
    Detecta si la pregunta está fuera del contexto de documentos
    Retorna: (es_fuera_contexto, categoría, confianza)
    """
    text_lower = normalize_text(text)
    text_no_accents = remove_accents(text_lower)
    
    best_category = None
    best_score = 0
    
    for category, data in context_dict.items():
        for pattern in data["patterns"]:
            pattern_lower = pattern.lower()
            pattern_no_accents = remove_accents(pattern_lower)
            
            # Coincidencia exacta
            if pattern_lower == text_lower or pattern_no_accents == text_no_accents:
                return True, category, 1.0
            
            # Coincidencia parcial
            if pattern_lower in text_lower or pattern_no_accents in text_no_accents:
                score = len(pattern_lower) / len(text_lower)
                if score > best_score:
                    best_score = score
                    best_category = category
            
            # Similitud
            similarity = SequenceMatcher(None, text_no_accents, pattern_no_accents).ratio()
            if similarity > best_score and similarity > 0.85:
                best_score = similarity
                best_category = category
    
    if best_score > 0.7:
        return True, best_category, best_score
    
    return False, None, 0

def get_contextual_response(category: str, text: str, confidence: float, context_dict: dict = CONTEXT_RESPONSES) -> str:
    """Genera respuesta contextual apropiada"""
    if category == "matematicas":
        # Intentar resolver operación
        numbers = re.findall(r'-?\d+\.?\d*', text)
        if len(numbers) >= 2:
            try:
                num1, num2 = float(numbers[0]), float(numbers[1])
                
                if any(op in text.lower() for op in ["suma", "+", "mas", "más"]):
                    result = num1 + num2
                    return f"El resultado de {num1} + {num2} es {result}. 🔢\n\nTambién puedo analizar documentos con datos numéricos."
                
                elif any(op in text.lower() for op in ["resta", "-", "menos"]):
                    result = num1 - num2
                    return f"El resultado de {num1} - {num2} es {result}. 🔢\n\nPuedo trabajar con documentos financieros también."
                
                elif any(op in text.lower() for op in ["multiplica", "*", "x", "por"]):
                    result = num1 * num2
                    return f"El resultado de {num1} × {num2} es {result}. 🔢\n\nSi tienes documentos con cálculos, puedo analizarlos."
                
                elif any(op in text.lower() for op in ["divide", "/", "entre"]):
                    if num2 != 0:
                        result = num1 / num2
                        return f"El resultado de {num1} ÷ {num2} es {result:.2f}. 🔢\n\nTambién analizo documentos con estadísticas."
            except:
                pass
    
    if category in context_dict:
        responses = context_dict[category]["responses"]
        response = random.choice(responses)
        
        if confidence < 0.9:
            response += "\n\n¿Hay algo relacionado con tus documentos en lo que pueda ayudarte?"
        
        return response
    
    return "Interesante pregunta. Mi especialidad es el análisis de documentos. ¿Tienes algún archivo que necesites revisar?"

# =======================
# FUNCIÓN DE INTEGRACIÓN
# =======================

def enhance_create_message(original_create_message_method):
    """
    Decorador para mejorar el método create_message existente
    Úsalo así en tu ChatService:
    
    @enhance_create_message
    def create_message(self, chat_id, message_data, user_id):
        # tu código actual
    """
    def wrapper(self, chat_id: int, message_data, user_id: int):
        # 1. Corrección ortográfica
        original_question = message_data.question
        corrected_question, corrections = correct_spelling_advanced(original_question)
        
        correction_message = ""
        if corrections:
            if len(corrections) == 1:
                correction_message = f"💡 He corregido: {corrections[0]}\n\n"
            else:
                correction_message = f"💡 He realizado algunas correcciones: {', '.join(corrections[:3])}"
                if len(corrections) > 3:
                    correction_message += f" y {len(corrections) - 3} más"
                correction_message += "\n\n"
        
        # 2. Detección de contexto
        is_out_of_context, context_category, confidence = detect_context_advanced(corrected_question)
        
        # 3. Si está fuera de contexto, responder apropiadamente
        if is_out_of_context and confidence > 0.7:
            ai_response = get_contextual_response(context_category, corrected_question, confidence)
            
            if correction_message:
                ai_response = correction_message + ai_response
            
            # Crear mensaje de respuesta
            response_message = self.message_repository.create_message(
                chat_id=chat_id,
                question=original_question,
                answer=ai_response
            )
            
            return self._map_to_message_response(response_message)
        
        # 4. Si no está fuera de contexto, modificar la pregunta y continuar
        message_data.question = corrected_question
        result = original_create_message_method(self, chat_id, message_data, user_id)
        
        # Añadir mensaje de corrección si hubo
        if correction_message and hasattr(result, 'answer'):
            result.answer = correction_message + result.answer
        
        return result
    
    return wrapper

# =======================
# INSTRUCCIONES DE USO
# =======================

"""
OPCIÓN 1: Integración manual
----------------------------
1. Copia las funciones que necesites a tu chat_service.py
2. Añade los diccionarios SPELLING_CORRECTIONS y CONTEXT_RESPONSES a tu __init__
3. En tu método create_message, añade al principio:

    # Corrección ortográfica
    original_question = message_data.question
    corrected_question, corrections = correct_spelling_advanced(original_question)
    
    # Detección de contexto  
    is_out_of_context, category, confidence = detect_context_advanced(corrected_question)
    
    if is_out_of_context and confidence > 0.7:
        # Generar respuesta contextual
        ...


OPCIÓN 2: Usar el decorador
---------------------------
1. Importa este archivo
2. Decora tu método create_message:

    from chat_service_improved_patch import enhance_create_message
    
    class ChatService:
        @enhance_create_message
        def create_message(self, chat_id, message_data, user_id):
            # tu código actual sin cambios


OPCIÓN 3: Heredar y extender
----------------------------
1. Crea una nueva clase que herede de ChatService
2. Sobrescribe solo el método create_message con las mejoras

¡Elige la opción que mejor se adapte a tu código!
"""
