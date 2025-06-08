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
y pueden ser convertidas a respuestas HTTP apropiadas.
"""

class AppException(Exception):
    """Excepción base para todas las excepciones de la aplicación."""
    def __init__(self, message: str = "Error de aplicación"):
        self.message = message
        super().__init__(self.message)


class NotFoundException(AppException):
    """Excepción para recursos no encontrados (HTTP 404)."""
    def __init__(self, message: str = "Recurso no encontrado"):
        super().__init__(message)


class UnauthorizedException(AppException):
    """Excepción para accesos no autorizados (HTTP 401/403)."""
    def __init__(self, message: str = "No autorizado para realizar esta acción"):
        super().__init__(message)


class ValidationException(AppException):
    """Excepción para errores de validación (HTTP 400)."""
    def __init__(self, message: str = "Error de validación en los datos"):
        super().__init__(message)


class ConflictException(AppException):
    """Excepción para conflictos de datos (HTTP 409)."""
    def __init__(self, message: str = "Conflicto con datos existentes"):
        super().__init__(message)


class DatabaseException(AppException):
    """Excepción para errores de base de datos (HTTP 500)."""
    def __init__(self, message: str = "Error en la base de datos"):
        super().__init__(message)


class ExternalServiceException(AppException):
    """Excepción para errores en servicios externos (HTTP 502/503)."""
    def __init__(self, message: str = "Error en servicio externo"):
        super().__init__(message)