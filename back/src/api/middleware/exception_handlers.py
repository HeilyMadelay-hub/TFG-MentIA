"""
Manejadores de excepciones para convertir excepciones personalizadas a respuestas HTTP
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from src.core.exceptions import AppException

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException):
    """
    Manejador global para excepciones personalizadas de la aplicación.
    Convierte AppException y sus subclases en respuestas JSON apropiadas.
    """
    logger.error(f"AppException capturada: {exc.__class__.__name__} - {exc.message}")
    
    return JSONResponse(
        status_code=exc.http_status_code,
        content=exc.to_dict()
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Manejador para HTTPException estándar de FastAPI.
    Mantiene compatibilidad con código existente.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "details": {}
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    Manejador para excepciones no capturadas.
    Registra el error y devuelve una respuesta genérica.
    """
    logger.exception("Excepción no manejada:", exc_info=exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "Ha ocurrido un error interno del servidor",
            "details": {}
        }
    )
