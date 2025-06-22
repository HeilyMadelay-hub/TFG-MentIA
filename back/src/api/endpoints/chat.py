"""
API Endpoints para la gestión de chats y mensajes - VERSION REFACTORIZADA
Este módulo implementa endpoints limpios y organizados para chats:
- Lógica de negocio movida a servicios especializados
- Endpoints divididos en funciones pequeñas y manejables  
- Validaciones centralizadas en servicios de validación
"""
from fastapi import APIRouter, Depends, status, Query, Path, Request
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Schemas
from src.models.schemas.chat import (
    ChatCreate, ChatResponse, MessageCreate, ChatMessage, ChatRename
)
from src.models.domain import User

# Servicios especializados
from src.services.chat_service import ChatService
from src.services.chat_validation_service import ChatValidationService
from src.services.message_processing_service import MessageProcessingService

# Helpers
from src.api.helpers.chat_helpers import ChatEndpointHelpers

# Dependencias y middleware
from src.api.dependencies import get_current_user
from src.core.rate_limit import rate_limit_chat

# Excepciones
from src.core.exceptions import (
    NotFoundException, DatabaseException, ValidationException,
    ForbiddenException, ExternalServiceException
)

logger = logging.getLogger(__name__)

# Crear router
router = APIRouter(prefix="/chats", tags=["chats"])

# Inicializar servicios y helpers
chat_service = ChatService()
chat_validator = ChatValidationService()
chat_helpers = ChatEndpointHelpers()

# ==================== ENDPOINTS DE GESTIÓN BÁSICA ====================

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Crea un nuevo chat para el usuario.
    El nombre es opcional - se asigna uno por defecto si no se proporciona.
    """
    try:
        validated_name = chat_validator.validate_chat_name(chat_data.name_chat)
        return chat_service.create_chat(
            user_id=current_user.id,
            name_chat=validated_name
        )
    except Exception as e:
        logger.error(f"Error al crear chat: {str(e)}")
        raise DatabaseException(f"Error al crear chat: {str(e)}")

@router.get("/", response_model=List[ChatResponse])
async def list_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Lista todos los chats del usuario actual.
    Siempre devuelve solo los chats del usuario actual.
    """
    try:
        # Validar parámetros
        skip, limit = chat_validator.validate_pagination_parameters(skip, limit)
        sort_by, order = chat_validator.validate_sort_parameters(sort_by, order)
        
        return chat_service.get_user_chats(
            user_id=current_user.id,
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            order=order
        )
    except Exception as e:
        logger.error(f"Error al listar chats: {str(e)}")
        raise DatabaseException(f"Error al listar chats: {str(e)}")

@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int = Path(..., description="ID del chat"),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene un chat específico con sus mensajes.
    """
    try:
        return chat_service.get_chat(
            chat_id=chat_id,
            user_id=current_user.id,
            is_admin=current_user.is_admin
        )
    except (NotFoundException, DatabaseException):
        raise
    except Exception as e:
        logger.error(f"Error al obtener chat: {str(e)}")
        raise DatabaseException(f"Error al obtener chat: {str(e)}")

@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_data: ChatCreate,
    chat_id: int = Path(..., description="ID del chat"),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza la información de un chat (nombre).
    """
    try:
        validated_name = chat_validator.validate_chat_name(chat_data.name_chat)
        chat_data.name_chat = validated_name
        
        return chat_service.update_chat(chat_id, chat_data, current_user.id)
    except (NotFoundException, DatabaseException):
        raise
    except Exception as e:
        logger.error(f"Error al actualizar chat: {str(e)}")
        raise DatabaseException(f"Error al actualizar chat: {str(e)}")

@router.put("/{chat_id}/rename", response_model=ChatResponse)
async def rename_chat(
    rename_data: ChatRename,
    chat_id: int = Path(..., description="ID del chat"),
    current_user: User = Depends(get_current_user)
):
    """
    Renombra un chat existente.
    """
    try:
        validated_name = chat_validator.validate_chat_name(rename_data.name)
        chat_data = ChatCreate(name_chat=validated_name)
        
        return chat_service.update_chat(chat_id, chat_data, current_user.id)
    except (NotFoundException, DatabaseException):
        raise
    except Exception as e:
        logger.error(f"Error al renombrar chat: {str(e)}")
        raise DatabaseException(f"Error al renombrar chat: {str(e)}")

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: int = Path(..., description="ID del chat"),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un chat y todos sus mensajes.
    """
    try:
        chat_service.delete_chat(chat_id, current_user.id)
    except (NotFoundException, DatabaseException):
        raise
    except Exception as e:
        logger.error(f"Error al eliminar chat: {str(e)}")
        raise DatabaseException(f"Error al eliminar chat: {str(e)}")

# ==================== ENDPOINTS DE MENSAJES ====================

@router.post("/{chat_id}/messages", response_model=ChatMessage)
@rate_limit_chat
async def send_message(
    request: Request,
    message: MessageCreate,
    chat_id: int = Path(..., description="ID del chat"),
    current_user: User = Depends(get_current_user)
):
    """
    Envía un mensaje al chatbot y recibe respuesta con RAG.
    Lógica compleja manejada por ChatEndpointHelpers.
    """
    try:
        return await chat_helpers.handle_message_send(
            chat_id=chat_id,
            message_data=message,
            current_user=current_user,
            chat_service=chat_service
        )
    except (NotFoundException, DatabaseException, ValidationException, ExternalServiceException):
        raise
    except Exception as e:
        logger.error(f"Error al enviar mensaje: {str(e)}")
        raise DatabaseException(f"Error al enviar mensaje: {str(e)}")

@router.get("/{chat_id}/messages", response_model=List[ChatMessage])
async def get_messages(
    chat_id: int = Path(..., description="ID del chat"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todos los mensajes de un chat.
    """
    try:
        # Validar parámetros de paginación
        skip, limit = chat_validator.validate_pagination_parameters(skip, limit)
        
        return chat_service.get_chat_messages(
            chat_id=chat_id,
            user_id=current_user.id,
            limit=limit,
            skip=skip,
            is_admin=current_user.is_admin
        )
    except (NotFoundException, DatabaseException):
        raise
    except Exception as e:
        logger.error(f"Error al obtener mensajes: {str(e)}")
        raise DatabaseException(f"Error al obtener mensajes: {str(e)}")

@router.delete("/{chat_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    chat_id: int = Path(..., description="ID del chat"),
    message_id: int = Path(..., description="ID del mensaje"),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un mensaje específico.
    """
    try:
        chat_service.delete_message(chat_id, message_id, current_user.id)
    except (NotFoundException, DatabaseException):
        raise
    except Exception as e:
        logger.error(f"Error al eliminar mensaje: {str(e)}")
        raise DatabaseException(f"Error al eliminar mensaje: {str(e)}")

# ==================== ENDPOINTS ADMINISTRATIVOS ====================

@router.get("/admin/all", response_model=List[ChatResponse])
async def list_all_chats_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: Optional[str] = Query("updated_at"),
    order: Optional[str] = Query("desc"),
    current_user: User = Depends(get_current_user)
):
    """
    Lista TODOS los chats del sistema.
    Solo disponible para administradores.
    """
    try:
        # Verificación de admin centralizada en helper
        chat_helpers.handle_chat_admin_verification(current_user, "listar todos los chats")
        
        # Validar parámetros
        skip, limit = chat_validator.validate_pagination_parameters(skip, limit)
        sort_by, order = chat_validator.validate_sort_parameters(sort_by, order)
        
        chats = chat_service.get_all_chats(
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            order=order
        )
        
        # Preparar respuesta administrativa con estadísticas
        admin_response = chat_helpers.prepare_admin_chat_list(chats, include_stats=True)
        return admin_response["chats"]
        
    except (ForbiddenException, DatabaseException):
        raise
    except Exception as e:
        logger.error(f"Error al listar todos los chats: {str(e)}")
        raise DatabaseException(f"Error al listar chats: {str(e)}")

@router.get("/admin/stats", response_model=Dict[str, Any])
async def get_chats_stats_admin(
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene estadísticas detalladas de los chats.
    Solo disponible para administradores.
    """
    try:
        # Verificación de admin centralizada
        chat_helpers.handle_chat_admin_verification(current_user, "estadísticas de chats")
        
        # Obtener estadísticas básicas
        total_chats = chat_service.count_all_chats()
        chats_by_user = chat_service.get_chats_count_by_user()
        messages_count = chat_service.count_all_messages()
        active_chats_last_24h = chat_service.get_active_chats_count(hours=24)
        
        return {
            "total_chats": total_chats,
            "chats_by_user": chats_by_user,
            "total_messages": messages_count,
            "active_chats_last_24h": active_chats_last_24h,
            "last_updated": datetime.now()
        }
    except ForbiddenException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {str(e)}")
        raise DatabaseException(f"Error al obtener estadísticas: {str(e)}")

@router.get("/admin/user/{user_id}", response_model=List[ChatResponse])
async def get_user_chats_admin(
    user_id: int = Path(..., description="ID del usuario"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene los chats de un usuario específico.
    Solo disponible para administradores.
    """
    try:
        # Verificación de admin centralizada
        chat_helpers.handle_chat_admin_verification(
            current_user, 
            f"chats del usuario {user_id}"
        )
        
        # Validar parámetros
        skip, limit = chat_validator.validate_pagination_parameters(skip, limit)
        
        return chat_service.get_user_chats(
            user_id=user_id,
            limit=limit,
            skip=skip
        )
    except (ForbiddenException, DatabaseException):
        raise
    except Exception as e:
        logger.error(f"Error al obtener chats del usuario {user_id}: {str(e)}")
        raise DatabaseException(f"Error al obtener chats: {str(e)}")

# ==================== ENDPOINTS DE UTILIDAD ====================

@router.get("/{chat_id}/enhanced-info", response_model=Dict[str, Any])
async def get_enhanced_chat_info(
    chat_id: int = Path(..., description="ID del chat"),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene información enriquecida sobre un chat con estadísticas.
    """
    try:
        return chat_helpers.get_enhanced_chat_info(
            chat_id=chat_id,
            current_user=current_user,
            chat_service=chat_service
        )
    except (NotFoundException, ForbiddenException, DatabaseException):
        raise
    except Exception as e:
        logger.error(f"Error obteniendo información enriquecida: {str(e)}")
        raise DatabaseException("Error al obtener información del chat")

@router.post("/admin/operations/{operation_type}")
async def execute_admin_operation(
    operation_type: str = Path(..., description="Tipo de operación"),
    chat_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Ejecuta operaciones administrativas avanzadas.
    Solo disponible para administradores.
    """
    try:
        # Verificación de admin
        chat_helpers.handle_chat_admin_verification(
            current_user, 
            f"operación administrativa: {operation_type}"
        )
        
        # Ejecutar operación usando helper
        result = chat_helpers.handle_chat_operations(
            operation_type=operation_type,
            chat_id=chat_id,
            current_user=current_user
        )
        
        return result
        
    except (ForbiddenException, ValidationException, DatabaseException):
        raise
    except Exception as e:
        logger.error(f"Error en operación admin {operation_type}: {str(e)}")
        raise DatabaseException(f"Error en operación: {str(e)}")

# ==================== ENDPOINTS DE SALUD ====================

@router.get("/health/check")
async def chat_health_check(
    current_user: User = Depends(get_current_user)
):
    """
    Verifica el estado del sistema de chats.
    """
    try:
        # Verificación básica de salud usando helper
        health_result = chat_helpers.handle_chat_operations(
            operation_type="chat_health_check",
            current_user=current_user
        )
        
        return health_result
        
    except Exception as e:
        logger.error(f"Error en verificación de salud: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now()
        }
