"""
Middleware y decoradores para rate limiting
"""
from functools import wraps
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.config.settings import get_settings

settings = get_settings()

# Crear limiter global
limiter = Limiter(key_func=get_remote_address)

# Decoradores específicos para diferentes endpoints
rate_limit_register = limiter.limit(settings.RATE_LIMIT_REGISTER)
rate_limit_login = limiter.limit(settings.RATE_LIMIT_LOGIN)
rate_limit_chat = limiter.limit(settings.RATE_LIMIT_CHAT)
rate_limit_upload = limiter.limit(settings.RATE_LIMIT_UPLOAD)
rate_limit_default = limiter.limit(settings.RATE_LIMIT_DEFAULT)

def get_client_ip(request):
    """
    Obtiene la IP real del cliente, considerando proxies
    """
    # Headers comunes usados por proxies y balanceadores de carga
    headers_to_check = [
        'X-Forwarded-For',
        'X-Real-IP',
        'CF-Connecting-IP',  # Cloudflare
        'X-Client-IP',
        'X-Forwarded',
        'Forwarded-For',
        'Forwarded'
    ]
    
    for header in headers_to_check:
        ip = request.headers.get(header)
        if ip:
            # X-Forwarded-For puede contener múltiples IPs
            if header == 'X-Forwarded-For':
                ip = ip.split(',')[0].strip()
            return ip
    
    # Si no hay headers de proxy, usar la IP directa
    return request.client.host
