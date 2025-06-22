"""
Servicio dedicado a la corrección ortográfica de mensajes
"""
import re
import unicodedata
from typing import Tuple, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class SpellingCorrectionService:
    """Servicio para corregir errores ortográficos comunes en español"""
    
    def __init__(self):
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
        
        # Patrones comunes de errores
        self.correction_patterns = [
            # Dobles consonantes incorrectas
            (r'\b(\w*)rr(\w*)\b', self._check_double_r),
            (r'\b(\w*)ll(\w*)\b', self._check_double_l),
            # Confusión b/v
            (r'\b(h?)[aeiou]ber\b', r'\1aber'),  # haber, aber -> haber
            # Falta de h inicial
            (r'\b(a)(cer|ora|oy)\b', r'h\1\2'),  # acer -> hacer, aora -> ahora
        ]
    
    def correct_spelling(self, text: str) -> Tuple[str, str]:
        """
        Intenta corregir errores ortográficos comunes.
        
        Args:
            text: Texto a corregir
            
        Returns:
            Tuple[str, str]: (texto_corregido, explicación_de_correcciones)
        """
        try:
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
                    # Aplicar patrones de corrección
                    corrected_word = self._apply_patterns(word)
                    if corrected_word != word:
                        corrected_words.append(corrected_word)
                        corrections_made.append(f"'{word}' → '{corrected_word}'")
                    else:
                        corrected_words.append(word)
            
            corrected_text = ' '.join(corrected_words)
            
            correction_message = ""
            if corrections_made:
                correction_message = f"💡 He detectado y corregido algunos errores: {', '.join(corrections_made)}. "
            
            return corrected_text, correction_message
            
        except Exception as e:
            logger.error(f"Error en corrección ortográfica: {str(e)}")
            return text, ""
    
    def normalize_text(self, text: str) -> str:
        """
        Normaliza el texto eliminando acentos, caracteres especiales y normalizando espacios.
        
        Args:
            text: Texto a normalizar
            
        Returns:
            str: Texto normalizado
        """
        # Convertir a minúsculas
        text = text.lower().strip()
        
        # Normalizar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        
        # Eliminar caracteres especiales al inicio y final
        text = re.sub(r'^[^a-zA-Z0-9áéíóúñü]+|[^a-zA-Z0-9áéíóúñü]+$', '', text)
        
        return text
    
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
    
    def _apply_patterns(self, word: str) -> str:
        """
        Aplica patrones de corrección a una palabra.
        
        Args:
            word: Palabra a corregir
            
        Returns:
            str: Palabra corregida
        """
        corrected = word
        for pattern, replacement in self.correction_patterns:
            if callable(replacement):
                corrected = replacement(corrected)
            else:
                corrected = re.sub(pattern, replacement, corrected)
        return corrected
    
    def _check_double_r(self, word: str) -> str:
        """Verifica y corrige el uso de doble r"""
        # Lista de palabras que sí llevan rr
        valid_rr = ['perro', 'carro', 'arriba', 'correr', 'error', 'horror']
        if word.lower() not in valid_rr and 'rr' in word:
            return word.replace('rr', 'r')
        return word
    
    def _check_double_l(self, word: str) -> str:
        """Verifica y corrige el uso de doble l"""
        # Lista de palabras que sí llevan ll
        valid_ll = ['llama', 'llegar', 'llevar', 'llover', 'calle', 'silla']
        if not any(word.lower().startswith(v) for v in valid_ll) and 'll' in word:
            return word.replace('ll', 'l')
        return word
    
    def suggest_corrections(self, text: str) -> List[str]:
        """
        Sugiere posibles correcciones para un texto.
        
        Args:
            text: Texto a analizar
            
        Returns:
            List[str]: Lista de sugerencias
        """
        suggestions = []
        words = text.split()
        
        for word in words:
            word_lower = word.lower()
            # Buscar palabras similares en el diccionario
            for correct_word in self.common_corrections.keys():
                if self._is_similar(word_lower, correct_word):
                    suggestions.append(f"¿Quisiste decir '{correct_word}'?")
        
        return suggestions
    
    def _is_similar(self, word1: str, word2: str) -> bool:
        """
        Determina si dos palabras son similares (distancia de edición).
        
        Args:
            word1: Primera palabra
            word2: Segunda palabra
            
        Returns:
            bool: True si son similares
        """
        # Implementación simple de distancia de Levenshtein
        if abs(len(word1) - len(word2)) > 2:
            return False
        
        # Comparar caracteres
        differences = sum(c1 != c2 for c1, c2 in zip(word1, word2))
        return differences <= 2
