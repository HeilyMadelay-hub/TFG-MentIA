"""
Endpoints para la gestión de chats y mensajes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from src.models.schemas.chat import ChatCreate, ChatResponse, MessageCreate, ChatMessage, ChatRename
from src.services.chat_service import ChatService
from src.api.dependencies import get_current_user
from src.models.domain import User

logger = logging.getLogger(__name__)

# Crear router
router = APIRouter(prefix="/chats", tags=["chats"])

# Inicializar servicio
chat_service = ChatService()

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Crea un nuevo chat para el usuario.
    
    **IMPORTANTE**: Según la BD, name_chat es OPCIONAL (campo nullable en tabla chats).
    
    Args:
        chat_data: Datos del chat a crear
            - name_chat: OPCIONAL - Nombre del chat (si no se envía, el servicio asigna uno por defecto)
        current_user: Usuario autenticado
    
    Returns:
        ChatResponse: Chat creado con su ID y fecha de creación
    
    Example:
        ```json
        // Con nombre
        {"name_chat": "Mi chat de consultas"}
        
        // Sin nombre (se asignará uno por defecto)
        {}
        ```
    """
    # Usar la instancia global del servicio
    return chat_service.create_chat(
        user_id=current_user.id,  # Usa el ID del usuario autenticado
        name_chat=chat_data.name_chat  # Puede ser None
    )

@router.get("/", response_model=List[ChatResponse])
async def list_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: Optional[str] = Query(None, description="Campo por el cual ordenar (created_at, updated_at)"),
    order: Optional[str] = Query(None, description="Orden de clasificación (asc, desc)"),
    current_user: User = Depends(get_current_user)
):
    """
    Lista todos los chats del usuario actual.
    IMPORTANTE: Este endpoint SIEMPRE devuelve los chats del usuario actual,
    independientemente de si es administrador o no.
    Para obtener todos los chats del sistema, usar /admin/all.
    """
    try:
        # Validar y establecer valores por defecto para ordenamiento
        if sort_by is None:
            sort_by = 'updated_at'  # Por defecto ordenar por última actualización
        if order is None:
            order = 'desc'
        
        # SIEMPRE devolver solo los chats del usuario actual
        # No importa si es admin o no, "Mis Conversaciones" debe mostrar solo SUS chats
        return chat_service.get_user_chats(
            user_id=current_user.id,
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            order=order
        )
    except Exception as e:
        logger.error(f"Error al listar chats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar chats: {str(e)}"
        )

@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene un chat específico con sus mensajes.
    Si el usuario es administrador, puede ver cualquier chat.
    """
    try:
        return chat_service.get_chat(
            chat_id=chat_id, 
            user_id=current_user.id,
            is_admin=current_user.is_admin
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener chat: {str(e)}"
        )

@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza la información de un chat (nombre).
    """
    try:
        return chat_service.update_chat(chat_id, chat_data, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar chat: {str(e)}"
        )

@router.put("/{chat_id}/rename", response_model=ChatResponse)
async def rename_chat(
    chat_id: int,
    rename_data: ChatRename,  # Usar el nuevo schema
    current_user: User = Depends(get_current_user)
):
    """
    Renombra un chat existente.
    
    Args:
        chat_id: ID del chat a renombrar
        rename_data: Objeto con el nuevo nombre del chat
        current_user: Usuario autenticado
        
    Returns:
        ChatResponse: Chat con el nombre actualizado
        
    Example:
        ```json
        {
            "name": "Mi nuevo nombre de chat"
        }
        ```
    """
    try:
        # Crear objeto ChatCreate con el nuevo nombre
        chat_data = ChatCreate(name_chat=rename_data.name)
        
        # Actualizar el chat
        return chat_service.update_chat(chat_id, chat_data, current_user.id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al renombrar chat {chat_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al renombrar chat: {str(e)}"
        )

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un chat y todos sus mensajes.
    """
    try:
        chat_service.delete_chat(chat_id, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar chat: {str(e)}"
        )

@router.post("/{chat_id}/messages", response_model=ChatMessage)
async def send_message(
    chat_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Envía un mensaje al chatbot y recibe respuesta con RAG.
    Si se especifican document_ids, busca solo en esos documentos.
    Si no se especifican, busca en todos los documentos del usuario.
    """
    try:
        # LOG: Ver qué datos están llegando desde el frontend
        logger.info(f"\n=== ENDPOINT: Mensaje recibido ===")
        logger.info(f"Chat ID: {chat_id}")
        logger.info(f"User ID: {current_user.id}")
        logger.info(f"Message data: {message.dict()}")
        logger.info(f"Document IDs: {message.document_ids}")
        logger.info(f"N Results: {message.n_results}")
        
        # Pasar los parámetros de RAG al servicio
        return chat_service.create_message(
            chat_id=chat_id,
            message_data=message,  # Pasar el objeto MessageCreate completo
            user_id=current_user.id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al enviar mensaje: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al enviar mensaje: {str(e)}"
        )

@router.get("/{chat_id}/messages", response_model=List[ChatMessage])
async def get_messages(
    chat_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todos los mensajes de un chat.
    Si el usuario es administrador, puede ver cualquier chat.
    """
    try:
        # Pasar el flag is_admin al servicio
        return chat_service.get_chat_messages(
            chat_id=chat_id, 
            user_id=current_user.id, 
            limit=limit, 
            skip=skip,
            is_admin=current_user.is_admin
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener mensajes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener mensajes: {str(e)}"
        )

@router.delete("/{chat_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    chat_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un mensaje específico.
    """
    try:
        chat_service.delete_message(chat_id, message_id, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar mensaje: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar mensaje: {str(e)}"
        )

# ==================== ENDPOINTS ADMINISTRATIVOS ====================

@router.get("/admin/all", response_model=List[ChatResponse])
async def list_all_chats_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: Optional[str] = Query("updated_at", description="Campo por el cual ordenar (created_at, updated_at)"),
    order: Optional[str] = Query("desc", description="Orden de clasificación (asc, desc)"),
    current_user: User = Depends(get_current_user)
):
    """
    Lista TODOS los chats del sistema.
    Solo disponible para administradores.
    """
    try:
        # Verificar que el usuario es admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden acceder a este endpoint"
            )
        
        # Obtener TODOS los chats del sistema
        return chat_service.get_all_chats(
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            order=order
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al listar todos los chats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar chats: {str(e)}"
        )

@router.get("/admin/stats", response_model=Dict[str, Any])
async def get_chats_stats_admin(
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene estadísticas detalladas de los chats.
    Solo disponible para administradores.
    """
    try:
        # Verificar que el usuario es admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden acceder a este endpoint"
            )
        
        # Obtener estadísticas
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener estadísticas de chats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )

@router.get("/admin/user/{user_id}", response_model=List[ChatResponse])
async def get_user_chats_admin(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene los chats de un usuario específico.
    Solo disponible para administradores.
    """
    try:
        # Verificar que el usuario es admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden acceder a este endpoint"
            )
        
        # Obtener chats del usuario especificado
        return chat_service.get_user_chats(
            user_id=user_id,
            limit=limit,
            skip=skip
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener chats del usuario {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener chats: {str(e)}"
        )
