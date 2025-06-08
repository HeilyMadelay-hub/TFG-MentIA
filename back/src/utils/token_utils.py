"""
Utilidades para generación y validación de tokens.
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple
import hashlib
import base64

class TokenUtils:
    """Utilidades para manejo de tokens de seguridad."""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Genera un token aleatorio seguro.
        
        Args:
            length: Longitud del token
            
        Returns:
            str: Token generado
        """
        # Caracteres permitidos (sin caracteres ambiguos como 0, O, l, 1)
        alphabet = string.ascii_letters + string.digits
        alphabet = alphabet.replace('0', '').replace('O', '').replace('l', '').replace('1', '')
        
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_short_code(length: int = 6) -> str:
        """
        Genera un código corto para emails (más fácil de escribir).
        
        Args:
            length: Longitud del código (por defecto 6)
            
        Returns:
            str: Código generado en mayúsculas
        """
        # Solo letras mayúsculas y números, sin ambiguos
        alphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_url_safe_token(length: int = 32) -> str:
        """
        Genera un token seguro para URLs.
        
        Returns:
            str: Token URL-safe
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """
        Genera un hash del token para almacenar en base de datos.
        
        Args:
            token: Token original
            
        Returns:
            str: Hash del token
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    @staticmethod
    def generate_token_with_expiry(hours: int = 1) -> Tuple[str, datetime]:
        """
        Genera un token con fecha de expiración.
        
        Args:
            hours: Horas hasta que expire el token
            
        Returns:
            Tuple[str, datetime]: Token y fecha de expiración
        """
        token = TokenUtils.generate_url_safe_token()
        expiry = datetime.utcnow() + timedelta(hours=hours)
        return token, expiry
    
    @staticmethod
    def is_token_expired(expiry_date: Optional[datetime]) -> bool:
        """
        Verifica si un token ha expirado.
        
        Args:
            expiry_date: Fecha de expiración del token
            
        Returns:
            bool: True si ha expirado o no hay fecha
        """
        if not expiry_date:
            return True
        return datetime.utcnow() > expiry_date
    
    @staticmethod
    def encode_email_token(email: str, token: str) -> str:
        """
        Codifica email y token juntos para URLs.
        
        Args:
            email: Email del usuario
            token: Token generado
            
        Returns:
            str: Token codificado
        """
        combined = f"{email}:{token}"
        encoded = base64.urlsafe_b64encode(combined.encode()).decode()
        return encoded
    
    @staticmethod
    def decode_email_token(encoded_token: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Decodifica un token que contiene email.
        
        Args:
            encoded_token: Token codificado
            
        Returns:
            Tuple[Optional[str], Optional[str]]: Email y token, o None si falla
        """
        try:
            decoded = base64.urlsafe_b64decode(encoded_token.encode()).decode()
            email, token = decoded.split(':', 1)
            return email, token
        except Exception:
            return None, None

# Exportar utilidades
token_utils = TokenUtils()
