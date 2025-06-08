"""
Endpoints administrativos para el panel de administración.
Solo accesibles por usuarios con rol de administrador.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging
from src.models.domain import User
from src.api.dependencies import get_current_user
from src.services.document_service import DocumentService
from src.services.chat_service import ChatService
from src.services.user_service import UserService
from src.api.dependencies import get_document_service, get_chat_service, get_user_service
from src.models.schemas.document import DocumentResponse
from src.models.schemas.chat import ChatResponse
from src.models.schemas.user import UserResponse

logger = logging.getLogger(__name__)

# Crear router con prefijo y tags para la documentación automática
router = APIRouter(prefix="/admin", tags=["admin"])

# Dependency para verificar si el usuario es administrador
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden acceder a este recurso"
        )
    return current_user

@router.get("/documents", response_model=List[DocumentResponse])
async def get_all_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    admin_user: User = Depends(require_admin),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Obtiene TODOS los documentos del sistema.
    Solo accesible por administradores.
    """
    try:
        documents = document_service.list_all_documents(
            limit=limit,
            skip=skip,
            sort_by='created_at',
            order='desc'
        )
        return documents
    except Exception as e:
        logger.error(f"Error al obtener todos los documentos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener documentos: {str(e)}"
        )

@router.get("/chats", response_model=List[ChatResponse])
async def get_all_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    admin_user: User = Depends(require_admin),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Obtiene TODOS los chats del sistema.
    Solo accesible por administradores.
    """
    try:
        chats = chat_service.get_all_chats(
            limit=limit,
            skip=skip,
            sort_by='created_at',
            order='desc'
        )
        return chats
    except Exception as e:
        logger.error(f"Error al obtener todos los chats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener chats: {str(e)}"
        )

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    admin_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    Obtiene TODOS los usuarios del sistema.
    Solo accesible por administradores.
    """
    try:
        users = user_service.get_all_users(
            skip=skip,
            limit=limit
        )
        return users
    except Exception as e:
        logger.error(f"Error al obtener todos los usuarios: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener usuarios: {str(e)}"
        )