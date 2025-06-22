"""
Middleware para el manejo automático de tokens expirados
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from src.core.exceptions import UnauthorizedException
from jose import JWTError, jwt
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class TokenMiddleware(BaseHTTPMiddleware):
    """
    Middleware que intercepta errores de token expirado y sugiere usar refresh token
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Procesa la petición y maneja errores relacionados con tokens
        """
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Si es un error de token expirado, devolver respuesta específica
            if isinstance(e, UnauthorizedException):
                error_detail = str(e.message).lower()
                if "expired" in error_detail or "expirado" in error_detail:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "detail": "Token expirado",
                            "error_code": "TOKEN_EXPIRED",
                            "message": "Tu sesión ha expirado. Por favor, usa tu refresh token para obtener uno nuevo.",
                            "refresh_endpoint": "/api/users/refresh-token"
                        },
                        headers={"WWW-Authenticate": "Bearer"}
                    )
            
            # Para otros errores, re-lanzar
            logger.error(f"Error no manejado en TokenMiddleware: {str(e)}")
            raise e

def check_token_expiry_soon(token: str, secret_key: str, algorithm: str = "HS256", minutes_before: int = 5) -> bool:
    """
    Verifica si un token está próximo a expirar
    
    Args:
        token: JWT token
        secret_key: Clave secreta
        algorithm: Algoritmo JWT
        minutes_before: Minutos antes de expiración para considerar "próximo"
        
    Returns:
        bool: True si el token expira pronto
    """
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            options={"verify_exp": False}  # No lanzar excepción por expiración
        )
        
        exp = payload.get("exp")
        if exp:
            expiry_time = datetime.fromtimestamp(exp)
            time_left = expiry_time - datetime.utcnow()
            
            # Si quedan menos de X minutos, está próximo a expirar
            if time_left.total_seconds() < (minutes_before * 60):
                return True
                
    except Exception:
        pass
        
    return False

def add_refresh_hint_to_response(response: JSONResponse, token_expires_soon: bool) -> JSONResponse:
    """
    Agrega una sugerencia en los headers si el token está próximo a expirar
    """
    if token_expires_soon:
        response.headers["X-Token-Expires-Soon"] = "true"
        response.headers["X-Refresh-Endpoint"] = "/api/users/refresh-token"
    
    return response
