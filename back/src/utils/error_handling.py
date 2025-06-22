"""
Utilidades para manejo consistente de errores
"""

from functools import wraps
from typing import Type, Tuple, Callable
import logging

from src.core.exceptions import AppException, DatabaseException

logger = logging.getLogger(__name__)


def handle_service_errors(*exception_mappings: Tuple[Type[Exception], Type[AppException]]):
    """
    Decorador para manejar errores en métodos de servicio.
    Mapea excepciones genéricas a excepciones personalizadas.
    
    Uso:
    @handle_service_errors(
        (ValueError, ValidationException),
        (KeyError, NotFoundException)
    )
    def mi_metodo(self):
        # código que puede lanzar ValueError o KeyError
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AppException:
                # Re-lanzar excepciones ya manejadas
                raise
            except Exception as e:
                # Buscar mapeo de excepción
                for source_exc, target_exc in exception_mappings:
                    if isinstance(e, source_exc):
                        logger.error(f"Mapeando {source_exc.__name__} a {target_exc.__name__}: {str(e)}")
                        raise target_exc(str(e))
                
                # Si no hay mapeo, lanzar DatabaseException genérica
                logger.exception(f"Error no mapeado en {func.__name__}")
                raise DatabaseException(
                    f"Error en {func.__name__}",
                    original_error=e
                )
        return wrapper
    return decorator


def convert_http_to_app_exception(http_exception):
    """
    Convierte HTTPException a AppException apropiada.
    Útil para migración gradual del código.
    """
    from src.core.exceptions import (
        NotFoundException,
        UnauthorizedException,
        ForbiddenException,
        ValidationException,
        ConflictException
    )
    
    status_to_exception = {
        400: ValidationException,
        401: UnauthorizedException,
        403: ForbiddenException,
        404: NotFoundException,
        409: ConflictException
    }
    
    exception_class = status_to_exception.get(
        http_exception.status_code,
        AppException
    )
    
    return exception_class(http_exception.detail)
