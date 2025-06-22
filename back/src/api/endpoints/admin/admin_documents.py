"""
Endpoints de administración para documentos.
Solo accesibles por usuarios administradores.
"""
from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional, Dict, Any
import logging

from src.models.schemas.document import DocumentResponse
from src.models.domain import User
from src.services.document_service import DocumentService
from src.api.dependencies import get_current_user, get_document_service
from src.core.exceptions import ForbiddenException, DatabaseException

logger = logging.getLogger(__name__)

# Crear router con prefijo admin
router = APIRouter(prefix="/admin/documents", tags=["admin", "documents"])

def verify_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verifica que el usuario actual sea administrador"""
    if not current_user.is_admin:
        raise ForbiddenException("Solo los administradores pueden acceder a este recurso")
    return current_user

@router.get("/all", response_model=List[DocumentResponse])
async def get_all_documents(
    skip: int = Query(0, description="Número de documentos a saltar"),
    limit: int = Query(100, description="Número máximo de documentos a retornar"),
    exclude_self: bool = Query(True, description="Excluir documentos del admin actual"),
    sort_by: Optional[str] = Query("created_at", description="Campo por el cual ordenar"),
    order: Optional[str] = Query("desc", description="Orden de clasificación (asc, desc)"),
    current_admin: User = Depends(verify_admin),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Obtiene todos los documentos del sistema.
    
    - **exclude_self**: Si es True, excluye los documentos del administrador actual
    - **skip**: Offset para paginación
    - **limit**: Límite de documentos a retornar
    - **sort_by**: Campo para ordenar (created_at, updated_at, title)
    - **order**: Orden ascendente (asc) o descendente (desc)
    """
    try:
        # Obtener todos los documentos
        all_documents = document_service.get_all_documents(
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            order=order
        )
        
        # Si exclude_self es True, filtrar documentos del admin actual
        if exclude_self:
            filtered_documents = [
                doc for doc in all_documents 
                if doc.uploaded_by != current_admin.id
            ]
            logger.info(f"Admin {current_admin.username} solicitó documentos. Total: {len(all_documents)}, Filtrados: {len(filtered_documents)}")
            return filtered_documents
        
        return all_documents
        
    except (ForbiddenException,):
        raise  # Re-lanzar excepciones ya manejadas
    except Exception as e:
        logger.error(f"Error al obtener documentos para admin: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al obtener documentos: {str(e)}")

@router.get("/stats", response_model=Dict[str, Any])
async def get_documents_stats(
    exclude_self: bool = Query(True, description="Excluir documentos del admin actual"),
    current_admin: User = Depends(verify_admin),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Obtiene estadísticas de documentos del sistema.
    
    - Total de documentos
    - Documentos por tipo
    - Documentos compartidos
    - Actividad reciente
    """
    try:
        stats = document_service.get_document_statistics(
            exclude_user_id=current_admin.id if exclude_self else None
        )
        
        return {
            "total_documents": stats.get("total", 0),
            "documents_by_type": stats.get("by_type", {}),
            "shared_documents": stats.get("shared", 0),
            "recent_uploads": stats.get("recent", []),
            "exclude_self": exclude_self
        }
        
    except Exception as e:
        logger.error(f"Error al obtener estadísticas de documentos: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al obtener estadísticas: {str(e)}")

@router.get("/user/{user_id}", response_model=List[DocumentResponse])
async def get_user_documents(
    user_id: int,
    skip: int = Query(0, description="Número de documentos a saltar"),
    limit: int = Query(50