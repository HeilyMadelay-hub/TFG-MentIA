"""
Este archivo define una jerarquía de excepciones que:

Permite capturar y manejar diferentes tipos de errores de forma consistente.
Facilita la conversión a códigos HTTP apropiados en los endpoints:

NotFoundException → HTTP 404 (Not Found)
UnauthorizedException → HTTP 401/403 (Unauthorized/Forbidden)
ValidationException → HTTP 400 (Bad Request)
ConflictException → HTTP 409 (Conflict)
DatabaseException → HTTP 500 (Internal Server Error)
ExternalServiceException → HTTP 502/503 (Bad Gateway/Service Unavailable)

Son excepciones personalizadas para la aplicación.
Estas excepciones se utilizan para manejar errores específicos
y son convertidas automáticamente a respuestas HTTP apropiadas.
"""

from typing import Optional, Dict, Any


class AppException(Exception):
    """Excepción base para todas las excepciones de la aplicación."""
    http_status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    
    def __init__(self, message: str = "Error de aplicación", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la excepción a un diccionario para respuesta JSON."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class NotFoundException(AppException):
    """Excepción para recursos no encontrados (HTTP 404)."""
    http_status_code = 404
    error_code = "NOT_FOUND"
    
    def __init__(self, resource: str = "Recurso", resource_id: Optional[Any] = None):
        message = f"{resource} no encontrado"
        if resource_id:
            message = f"{resource} con ID {resource_id} no encontrado"
        super().__init__(message)


class DocumentNotFoundException(NotFoundException):
    """Excepción específica para documentos no encontrados."""
    error_code = "DOCUMENT_NOT_FOUND"
    
    def __init__(self, document_id: Optional[int] = None):
        super().__init__(resource="Documento", resource_id=document_id)


class UserNotFoundException(NotFoundException):
    """Excepción específica para usuarios no encontrados."""
    error_code = "USER_NOT_FOUND"
    
    def __init__(self, user_id: Optional[int] = None):
        super().__init__(resource="Usuario", resource_id=user_id)


class UnauthorizedException(AppException):
    """Excepción para accesos no autorizados (HTTP 401)."""
    http_status_code = 401
    error_code = "UNAUTHORIZED"
    
    def __init__(self, message: str = "No autorizado para realizar esta acción"):
        super().__init__(message)


class ForbiddenException(AppException):
    """Excepción para accesos prohibidos (HTTP 403)."""
    http_status_code = 403
    error_code = "FORBIDDEN"
    
    def __init__(self, message: str = "No tienes permisos para acceder a este recurso"):
        super().__init__(message)


class ValidationException(AppException):
    """Excepción para errores de validación (HTTP 400)."""
    http_status_code = 400
    error_code = "VALIDATION_ERROR"
    
    def __init__(self, message: str = "Error de validación en los datos", field_errors: Optional[Dict[str, str]] = None):
        super().__init__(message, details={"field_errors": field_errors or {}})


class ConflictException(AppException):
    """Excepción para conflictos de datos (HTTP 409)."""
    http_status_code = 409
    error_code = "CONFLICT"
    
    def __init__(self, message: str = "Conflicto con datos existentes"):
        super().__init__(message)


class DatabaseException(AppException):
    """Excepción para errores de base de datos (HTTP 500)."""
    http_status_code = 500
    error_code = "DATABASE_ERROR"
    
    def __init__(self, message: str = "Error en la base de datos", original_error: Optional[Exception] = None):
        details = {}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, details)


class ExternalServiceException(AppException):
    """Excepción para errores en servicios externos (HTTP 502/503)."""
    http_status_code = 503
    error_code = "EXTERNAL_SERVICE_ERROR"
    
    def __init__(self, service_name: str, message: Optional[str] = None):
        if not message:
            message = f"Error en servicio externo: {service_name}"
        super().__init__(message, details={"service": service_name})


class RateLimitException(AppException):
    """Excepción para límite de tasa excedido (HTTP 429)."""
    http_status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    
    def __init__(self, message: str = "Límite de solicitudes excedido", retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, details)
