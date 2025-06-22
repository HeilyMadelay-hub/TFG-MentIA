"""
Validador de emails para prevenir duplicados y aplicar reglas específicas
"""
import re
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class EmailValidator:
    """
    Valida emails y previene registros duplicados con diferentes dominios
    """
    
    # Dominios de Gmail válidos por país
    GMAIL_DOMAINS = {
        'gmail.com': 'Internacional (por defecto)',
        'googlemail.com': 'Alemania y Reino Unido'
    }
    
    # Otros proveedores comunes que siempre deben usar .com
    COM_ONLY_PROVIDERS = [
        'hotmail', 'outlook', 'yahoo', 'aol', 'icloud', 'protonmail', 'zoho'
    ]
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """
        Normaliza un email para comparación
        """
        if not email:
            return ""
        return email.lower().strip()
    
    @staticmethod
    def extract_email_parts(email: str) -> Tuple[str, str]:
        """
        Extrae el nombre de usuario y dominio de un email
        
        Returns:
            Tuple[username, domain]
        """
        email = EmailValidator.normalize_email(email)
        if '@' not in email:
            return email, ""
        
        parts = email.split('@')
        if len(parts) != 2:
            return email, ""
        
        return parts[0], parts[1]
    
    @staticmethod
    def validate_email_format(email: str) -> Tuple[bool, Optional[str]]:
        """
        Valida el formato de un email
        
        Returns:
            Tuple[is_valid, error_message]
        """
        email = EmailValidator.normalize_email(email)
        
        # Validación básica de formato
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Formato de email inválido"
        
        username, domain = EmailValidator.extract_email_parts(email)
        
        # Validar longitud del username
        if len(username) < 3:
            return False, "El nombre de usuario del email debe tener al menos 3 caracteres"
        
        # Validar caracteres especiales consecutivos
        if '..' in email or '--' in email or '__' in email:
            return False, "El email no puede contener caracteres especiales consecutivos"
        
        # Validar que no empiece o termine con caracteres especiales
        if username[0] in '.-_' or username[-1] in '.-_':
            return False, "El nombre de usuario no puede empezar o terminar con caracteres especiales"
        
        return True, None
    
    @staticmethod
    def validate_gmail_domain(email: str) -> Tuple[bool, Optional[str]]:
        """
        Valida específicamente emails de Gmail
        
        Returns:
            Tuple[is_valid, corrected_email_or_error]
        """
        username, domain = EmailValidator.extract_email_parts(email)
        
        # Detectar si es un intento de Gmail
        domain_lower = domain.lower()
        
        # Casos comunes de error en Gmail
        gmail_typos = {
            'gmail.es': 'gmail.com',
            'gmail.com.es': 'gmail.com',
            'gmail.co': 'gmail.com',
            'gmail.cm': 'gmail.com',
            'gmai.com': 'gmail.com',
            'gmial.com': 'gmail.com',
            'gmal.com': 'gmail.com',
            'gmil.com': 'gmail.com',
            'gmail.con': 'gmail.com',
            'gmail.om': 'gmail.com'
        }
        
        # Si es un typo conocido, sugerir corrección
        if domain_lower in gmail_typos:
            correct_email = f"{username}@{gmail_typos[domain_lower]}"
            return False, f"Gmail siempre usa .com. ¿Quisiste decir {correct_email}?"
        
        # Si contiene "gmail" pero no es un dominio válido
        if 'gmail' in domain_lower and domain_lower not in EmailValidator.GMAIL_DOMAINS:
            return False, f"Dominio de Gmail inválido. Use @gmail.com"
        
        return True, None
    
    @staticmethod
    def validate_provider_domain(email: str) -> Tuple[bool, Optional[str]]:
        """
        Valida dominios de proveedores conocidos
        """
        username, domain = EmailValidator.extract_email_parts(email)
        
        # Verificar proveedores que solo usan .com
        for provider in EmailValidator.COM_ONLY_PROVIDERS:
            if domain.startswith(provider + '.') and not domain.endswith('.com'):
                correct_email = f"{username}@{provider}.com"
                return False, f"{provider.capitalize()} usa dominio .com. ¿Quisiste decir {correct_email}?"
        
        return True, None
    
    @staticmethod
    def check_similar_emails(email: str, existing_emails: list) -> Optional[str]:
        """
        Busca emails similares que podrían ser el mismo usuario
        
        Args:
            email: Email a verificar
            existing_emails: Lista de emails existentes en el sistema
            
        Returns:
            Email similar encontrado o None
        """
        username, domain = EmailValidator.extract_email_parts(email)
        
        for existing in existing_emails:
            existing_user, existing_domain = EmailValidator.extract_email_parts(existing)
            
            # Mismo username, diferente dominio
            if username == existing_user and domain != existing_domain:
                # Verificar si son dominios del mismo proveedor
                if EmailValidator._same_provider(domain, existing_domain):
                    return existing
        
        return None
    
    @staticmethod
    def _same_provider(domain1: str, domain2: str) -> bool:
        """
        Verifica si dos dominios pertenecen al mismo proveedor
        """
        # Gmail y sus variantes
        gmail_domains = ['gmail.com', 'googlemail.com', 'gmail.es', 'gmail.co.uk']
        if domain1 in gmail_domains and domain2 in gmail_domains:
            return True
        
        # Hotmail/Outlook y sus variantes
        microsoft_domains = ['hotmail.com', 'hotmail.es', 'outlook.com', 'outlook.es', 'live.com']
        if domain1 in microsoft_domains and domain2 in microsoft_domains:
            return True
        
        # Yahoo y sus variantes
        yahoo_domains = ['yahoo.com', 'yahoo.es', 'yahoo.co.uk', 'ymail.com']
        if domain1 in yahoo_domains and domain2 in yahoo_domains:
            return True
        
        return False
    
    @staticmethod
    def suggest_corrections(email: str) -> list:
        """
        Sugiere correcciones para un email mal escrito
        """
        suggestions = []
        username, domain = EmailValidator.extract_email_parts(email)
        
        # Si falta el @
        if '@' not in email and '.' in email:
            # Buscar posibles posiciones del @
            parts = email.split('.')
            if len(parts) >= 2:
                # Intentar gmail, hotmail, etc
                for provider in ['gmail', 'hotmail', 'yahoo', 'outlook']:
                    if provider in email.lower():
                        idx = email.lower().index(provider)
                        if idx > 0:
                            suggested = email[:idx] + '@' + email[idx:]
                            suggestions.append(suggested)
        
        # Dominios mal escritos comunes
        domain_corrections = {
            'gmai.com': 'gmail.com',
            'gmial.com': 'gmail.com',
            'gmail.co': 'gmail.com',
            'gmail.es': 'gmail.com',
            'gmail.cm': 'gmail.com',
            'hotmai.com': 'hotmail.com',
            'hotmal.com': 'hotmail.com',
            'hotmial.com': 'hotmail.com',
            'outlok.com': 'outlook.com',
            'outloo.com': 'outlook.com',
            'yaho.com': 'yahoo.com',
            'yahho.com': 'yahoo.com'
        }
        
        if domain in domain_corrections:
            suggestions.append(f"{username}@{domain_corrections[domain]}")
        
        return suggestions
    
    @staticmethod
    def validate_and_suggest(email: str, existing_emails: list = None) -> dict:
        """
        Valida un email y devuelve sugerencias completas
        
        Returns:
            dict con:
            - is_valid: bool
            - error: str or None
            - suggestions: list of str
            - similar_email: str or None
        """
        result = {
            'is_valid': True,
            'error': None,
            'suggestions': [],
            'similar_email': None
        }
        
        # Normalizar
        email = EmailValidator.normalize_email(email)
        
        # Validar formato básico
        is_valid, error = EmailValidator.validate_email_format(email)
        if not is_valid:
            result['is_valid'] = False
            result['error'] = error
            result['suggestions'] = EmailValidator.suggest_corrections(email)
            return result
        
        # Validar Gmail
        is_valid, error = EmailValidator.validate_gmail_domain(email)
        if not is_valid:
            result['is_valid'] = False
            result['error'] = error
            return result
        
        # Validar otros proveedores
        is_valid, error = EmailValidator.validate_provider_domain(email)
        if not is_valid:
            result['is_valid'] = False
            result['error'] = error
            return result
        
        # Buscar emails similares si se proporciona la lista
        if existing_emails:
            similar = EmailValidator.check_similar_emails(email, existing_emails)
            if similar:
                result['similar_email'] = similar
                result['is_valid'] = False
                result['error'] = f"Ya existe una cuenta con un email similar: {similar}"
        
        return result


# Función helper para usar fácilmente
def validate_email_registration(email: str, existing_emails: list = None) -> Tuple[bool, Optional[str]]:
    """
    Valida un email para registro
    
    Returns:
        Tuple[is_valid, error_message]
    """
    validation = EmailValidator.validate_and_suggest(email, existing_emails)
    
    if validation['is_valid']:
        return True, None
    
    error_msg = validation['error']
    if validation['suggestions']:
        error_msg += f"\nSugerencias: {', '.join(validation['suggestions'])}"
    
    return False, error_msg
