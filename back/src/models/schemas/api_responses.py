"""
Modelos de respuesta estándar para la documentación OpenAPI.
Define schemas para respuestas exitosas y de error.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# ===============================
# RESPUESTAS ESTÁNDAR DE ERROR
# ===============================

class ErrorResponse(BaseModel):
    """Respuesta estándar para errores de la API"""
    error_code: str = Field(..., description="Código único del error", example="VALIDATION_ERROR")
    message: str = Field(..., description="Mensaje de error legible", example="Los datos proporcionados no son válidos")
    details: Optional[Dict[str, Any]] = Field(default={}, description="Información adicional del error")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Momento cuando ocurrió el error")

class ValidationErrorResponse(BaseModel):
    """Respuesta para errores de validación (422)"""
    detail: str = Field(..., description="Detalle del error de validación", example="El email no tiene un formato válido")

class UnauthorizedResponse(BaseModel):
    """Respuesta para errores de autenticación (401)"""
    error_code: str = Field(default="UNAUTHORIZED", example="UNAUTHORIZED")
    message: str = Field(..., description="Mensaje de error", example="Token de acceso requerido")
    details: Dict[str, str] = Field(default={"hint": "Incluye el header Authorization: Bearer <token>"})

class ForbiddenResponse(BaseModel):
    """Respuesta para errores de autorización (403)"""
    error_code: str = Field(default="FORBIDDEN", example="FORBIDDEN")
    message: str = Field(..., description="Mensaje de error", example="Sin permisos para esta acción")
    details: Dict[str, str] = Field(default={})

class NotFoundResponse(BaseModel):
    """Respuesta para recursos no encontrados (404)"""
    error_code: str = Field(default="NOT_FOUND", example="NOT_FOUND")
    message: str = Field(..., description="Mensaje de error", example="Documento no encontrado")
    details: Dict[str, Any] = Field(default={})

class RateLimitResponse(BaseModel):
    """Respuesta para rate limiting (429)"""
    detail: str = Field(..., description="Mensaje de rate limit", example="Rate limit exceeded: 10/minute")

class ServerErrorResponse(BaseModel):
    """Respuesta para errores del servidor (500)"""
    error_code: str = Field(default="INTERNAL_ERROR", example="INTERNAL_ERROR")
    message: str = Field(..., description="Mensaje de error", example="Ha ocurrido un error interno del servidor")
    details: Dict[str, str] = Field(default={})

# ===============================
# RESPUESTAS ESTÁNDAR DE ÉXITO
# ===============================

class SuccessResponse(BaseModel):
    """Respuesta estándar para operaciones exitosas"""
    success: bool = Field(default=True, description="Indica si la operación fue exitosa")
    message: str = Field(..., description="Mensaje de confirmación", example="Operación completada exitosamente")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Datos adicionales de la respuesta")

class MessageResponse(BaseModel):
    """Respuesta simple con mensaje"""
    message: str = Field(..., description="Mensaje de respuesta", example="Operación completada")

# ===============================
# MODELOS DE AUTENTICACIÓN
# ===============================

class TokenResponse(BaseModel):
    """Respuesta al hacer login exitoso"""
    access_token: str = Field(..., description="Token de acceso JWT", example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    refresh_token: str = Field(..., description="Token para refrescar el acceso", example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(default="bearer", description="Tipo de token", example="bearer")
    expires_in: int = Field(..., description="Segundos hasta que expire el token", example=3600)
    user: Dict[str, Any] = Field(..., description="Información del usuario autenticado")

class RefreshTokenResponse(BaseModel):
    """Respuesta al refrescar tokens"""
    access_token: str = Field(..., description="Nuevo token de acceso", example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    refresh_token: Optional[str] = Field(None, description="Nuevo refresh token (si rotación está habilitada)")
    expires_in: int = Field(..., description="Segundos hasta que expire el nuevo token", example=3600)

# ===============================
# MODELOS DE DOCUMENTOS
# ===============================

class DocumentUploadResponse(BaseModel):
    """Respuesta al subir un documento"""
    document_id: int = Field(..., description="ID único del documento", example=123)
    filename: str = Field(..., description="Nombre del archivo", example="documento.pdf")
    size_mb: float = Field(..., description="Tamaño en MB", example=2.5)
    content_type: str = Field(..., description="Tipo MIME", example="application/pdf")
    status: str = Field(..., description="Estado del procesamiento", example="processing")
    message: str = Field(..., description="Mensaje informativo", example="Documento subido y procesándose")

class DocumentProcessingStatus(BaseModel):
    """Estado del procesamiento de un documento"""
    document_id: int = Field(..., description="ID del documento")
    status: str = Field(..., description="Estado: processing, completed, failed", example="completed")
    progress: float = Field(..., description="Progreso en porcentaje", example=100.0)
    chunks_created: Optional[int] = Field(None, description="Número de chunks creados", example=25)
    processing_time: Optional[float] = Field(None, description="Tiempo de procesamiento en segundos", example=15.3)

# ===============================
# MODELOS DE CHAT
# ===============================

class ChatQuestionResponse(BaseModel):
    """Respuesta a una pregunta de chat"""
    question: str = Field(..., description="Pregunta realizada", example="¿Qué dice el documento sobre marketing?")
    answer: str = Field(..., description="Respuesta generada por IA", example="Según los documentos, el marketing digital es...")
    sources: List[Dict[str, Any]] = Field(..., description="Fuentes utilizadas para la respuesta")
    conversation_id: Optional[str] = Field(None, description="ID de la conversación", example="conv_123")
    tokens_used: Optional[int] = Field(None, description="Tokens utilizados", example=150)
    response_time: Optional[float] = Field(None, description="Tiempo de respuesta en segundos", example=2.3)

class ChatHistoryResponse(BaseModel):
    """Historial de conversaciones"""
    conversations: List[Dict[str, Any]] = Field(..., description="Lista de conversaciones")
    total: int = Field(..., description="Total de conversaciones", example=5)
    page: int = Field(..., description="Página actual", example=1)
    per_page: int = Field(..., description="Elementos por página", example=20)

# ===============================
# MODELOS DE ESTADÍSTICAS
# ===============================

class StatisticsResponse(BaseModel):
    """Respuesta de estadísticas del sistema"""
    total_users: int = Field(..., description="Total de usuarios registrados", example=1250)
    total_documents: int = Field(..., description="Total de documentos subidos", example=3420)
    total_conversations: int = Field(..., description="Total de conversaciones", example=8900)
    total_questions: int = Field(..., description="Total de preguntas realizadas", example=15600)
    avg_response_time: float = Field(..., description="Tiempo promedio de respuesta en segundos", example=2.1)
    top_documents: List[Dict[str, Any]] = Field(..., description="Documentos más consultados")
    recent_activity: List[Dict[str, Any]] = Field(..., description="Actividad reciente")

# ===============================
# RESPUESTAS COMBINADAS PARA OPENAPI
# ===============================

# Respuestas comunes que se usan en múltiples endpoints
COMMON_RESPONSES = {
    401: {
        "model": UnauthorizedResponse,
        "description": "No autenticado - Token requerido o inválido"
    },
    403: {
        "model": ForbiddenResponse, 
        "description": "Sin permisos para esta acción"
    },
    404: {
        "model": NotFoundResponse,
        "description": "Recurso no encontrado"
    },
    422: {
        "model": ValidationErrorResponse,
        "description": "Error de validación en los datos enviados"
    },
    429: {
        "model": RateLimitResponse,
        "description": "Límite de velocidad excedido"
    },
    500: {
        "model": ServerErrorResponse,
        "description": "Error interno del servidor"
    }
}

# Respuestas para endpoints que requieren autenticación
AUTHENTICATED_RESPONSES = {
    **COMMON_RESPONSES,
    401: {
        "model": UnauthorizedResponse,
        "description": "Token de autenticación requerido",
        "content": {
            "application/json": {
                "example": {
                    "error_code": "UNAUTHORIZED",
                    "message": "Token de acceso requerido",
                    "details": {
                        "hint": "Incluye el header Authorization: Bearer <token>"
                    }
                }
            }
        }
    }
}

# Respuestas para endpoints de administrador
ADMIN_RESPONSES = {
    **AUTHENTICATED_RESPONSES,
    403: {
        "model": ForbiddenResponse,
        "description": "Permisos de administrador requeridos",
        "content": {
            "application/json": {
                "example": {
                    "error_code": "FORBIDDEN", 
                    "message": "Solo los administradores pueden acceder a este recurso",
                    "details": {}
                }
            }
        }
    }
}
