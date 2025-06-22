"""
API Endpoints administrativos - VERSION REFACTORIZADA
Endpoints limpios y organizados siguiendo el patrón de documents.py:
- Lógica de negocio en AdminService
- Validaciones en AdminValidationService  
- Operaciones complejas en AdminEndpointHelpers
"""
from fastapi import APIRouter, Depends, Query, Path, Body
from typing import List, Optional, Dict, Any
import logging

# Schemas
from src.models.schemas.document import DocumentResponse
from src.models.schemas.chat import ChatResponse
from src.models.schemas.user import UserResponse
from src.models.domain import User
from datetime import datetime

# Servicios
from src.services.document_service import DocumentService
from src.services.chat_service import ChatService
from src.services.user_service import UserService
from src.services.admin_service import AdminService
from src.services.admin_validation_service import AdminValidationService

# Helpers
from src.api.helpers.admin_helpers import AdminEndpointHelpers

# Dependencias
from src.api.dependencies import (
    get_current_user, get_document_service, 
    get_chat_service, get_user_service
)

# Excepciones
from src.core.exceptions import (
    ForbiddenException, DatabaseException, ValidationException
)

logger = logging.getLogger(__name__)

# Crear router con prefijo y tags
router = APIRouter(prefix="/admin", tags=["admin"])

# Inicializar helpers y validador
admin_helpers = AdminEndpointHelpers()
admin_validator = AdminValidationService()

# Dependency para obtener AdminService
def get_admin_service(
    document_service: DocumentService = Depends(get_document_service),
    chat_service: ChatService = Depends(get_chat_service),
    user_service: UserService = Depends(get_user_service)
) -> AdminService:
    """Crea una instancia de AdminService con las dependencias necesarias"""
    return AdminService(document_service, chat_service, user_service)

# ==================== ENDPOINTS DE LISTADO ====================

@router.get("/documents", response_model=List[DocumentResponse])
async def get_all_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Obtiene TODOS los documentos del sistema.
    Solo accesible por administradores.
    """
    return await admin_helpers.handle_resource_listing(
        resource_type="documents",
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        order=order,
        admin_user=admin_user,
        admin_service=admin_service
    )

@router.get("/chats", response_model=List[ChatResponse])
async def get_all_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Obtiene TODOS los chats del sistema.
    Solo accesible por administradores.
    """
    return await admin_helpers.handle_resource_listing(
        resource_type="chats",
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        order=order,
        admin_user=admin_user,
        admin_service=admin_service
    )

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Obtiene TODOS los usuarios del sistema.
    Solo accesible por administradores.
    """
    return await admin_helpers.handle_resource_listing(
        resource_type="users",
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        order=order,
        admin_user=admin_user,
        admin_service=admin_service
    )

# ==================== ENDPOINTS DE ESTADÍSTICAS ====================

@router.get("/stats", response_model=Dict[str, Any])
async def get_system_overview(
    admin_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Obtiene una vista general del sistema con estadísticas.
    Solo accesible por administradores.
    """
    return await admin_helpers.handle_statistics_request(
        admin_user=admin_user,
        admin_service=admin_service
    )

@router.get("/stats/{resource_type}", response_model=Dict[str, Any])
async def get_resource_statistics(
    resource_type: str = Path(..., description="Tipo de recurso (documents, chats, users)"),
    time_period: Optional[str] = Query("all", description="Período de tiempo"),
    group_by: Optional[str] = Query(None, description="Campo de agrupación"),
    admin_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Obtiene estadísticas detalladas de un tipo de recurso.
    Solo accesible por administradores.
    """
    return await admin_helpers.handle_statistics_request(
        admin_user=admin_user,
        admin_service=admin_service,
        resource_type=resource_type,
        time_period=time_period,
        group_by=group_by
    )

# ==================== ENDPOINTS DE BÚSQUEDA ====================

@router.get("/search/{resource_type}", response_model=List[Dict[str, Any]])
async def search_resources(
    resource_type: str = Path(..., description="Tipo de recurso a buscar"),
    query: str = Query(..., description="Texto de búsqueda"),
    limit: int = Query(50, ge=1, le=100),
    admin_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Busca recursos por texto en todos los campos relevantes.
    Solo accesible por administradores.
    """
    return await admin_helpers.handle_search_request(
        query=query,
        resource_type=resource_type,
        admin_user=admin_user,
        admin_service=admin_service,
        limit=limit
    )

# ==================== ENDPOINTS DE OPERACIONES EN LOTE ====================

@router.post("/bulk/{operation}", response_model=Dict[str, Any])
async def bulk_operation(
    operation: str = Path(..., description="Operación a realizar (delete, export)"),
    resource_type: str = Body(..., embed=True),
    resource_ids: List[int] = Body(..., embed=True),
    admin_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Ejecuta operaciones en lote sobre múltiples recursos.
    Solo accesible por administradores.
    """
    return await admin_helpers.handle_bulk_operation(
        operation=operation,
        resource_type=resource_type,
        resource_ids=resource_ids,
        admin_user=admin_user,
        admin_service=admin_service
    )

# ==================== ENDPOINTS DE DETALLE ====================

@router.get("/{resource_type}/{resource_id}", response_model=Dict[str, Any])
async def get_resource_details(
    resource_type: str = Path(..., description="Tipo de recurso"),
    resource_id: int = Path(..., description="ID del recurso"),
    admin_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    chat_service: ChatService = Depends(get_chat_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Obtiene información detallada de un recurso específico.
    Solo accesible por administradores.
    """
    return await admin_helpers.get_resource_summary(
        resource_type=resource_type,
        resource_id=resource_id,
        admin_user=admin_user,
        document_service=document_service,
        chat_service=chat_service,
        user_service=user_service
    )

# ==================== ENDPOINTS DE MANTENIMIENTO ====================

@router.post("/maintenance/reindex-documents")
async def reindex_all_documents(
    admin_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Re-indexa todos los documentos en ChromaDB.
    Operación costosa - usar con precaución.
    """
    admin_validator.validate_admin_access(admin_user, "re-indexar documentos")
    
    try:
        count = document_service.reindex_all_documents()
        return {
            "message": f"Re-indexación iniciada para {count} documentos",
            "status": "processing"
        }
    except Exception as e:
        logger.error(f"Error en re-indexación: {str(e)}")
        raise DatabaseException(f"Error al re-indexar: {str(e)}")

@router.post("/maintenance/cleanup")
async def cleanup_orphaned_resources(
    admin_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Limpia recursos huérfanos del sistema.
    Solo accesible por administradores.
    """
    admin_validator.validate_admin_access(admin_user, "limpiar recursos")
    
    try:
        # TODO: Implementar limpieza real
        return {
            "message": "Limpieza programada",
            "status": "pending"
        }
    except Exception as e:
        logger.error(f"Error en limpieza: {str(e)}")
        raise DatabaseException(f"Error al limpiar: {str(e)}")

# ==================== ENDPOINTS DE CONFIGURACIÓN ====================

@router.get("/config/limits")
async def get_system_limits(
    admin_user: User = Depends(get_current_user)
):
    """
    Obtiene los límites configurados del sistema.
    Solo accesible por administradores.
    """
    admin_validator.validate_admin_access(admin_user, "ver configuración")
    
    return {
        "upload": {
            "max_file_size_mb": 100,
            "allowed_types": admin_validator.VALID_CONTENT_TYPES
        },
        "pagination": {
            "max_limit": admin_validator.MAX_LIMIT,
            "default_limit": admin_validator.DEFAULT_LIMIT
        },
        "processing": {
            "sync_threshold_mb": 3,
            "max_concurrent_tasks": 5
        }
    }

# ==================== ENDPOINTS DE DOCUMENTOS ADMIN ====================

@router.get("/documents/stats", response_model=Dict[str, Any])
async def get_documents_statistics_admin(
    time_period: Optional[str] = Query("all", description="Período: all, week, month, year"),
    group_by: Optional[str] = Query("user", description="Agrupar por: user, content_type, date"),
    admin_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    [ADMIN] Obtiene estadísticas avanzadas de documentos del sistema.
    Incluye métricas de uso, distribución por usuarios y tipos de archivo.
    """
    try:
        # Validar permisos de administrador
        if not document_service.is_admin_user(admin_user.id):
            raise ForbiddenException("Solo los administradores pueden acceder a estadísticas")
        
        # Obtener estadísticas base
        total_documents = document_service.count_all_documents()
        documents_by_user = document_service.get_documents_count_by_user()
        documents_by_type = document_service.get_documents_count_by_type()
        
        # Estadísticas avanzadas según período
        advanced_stats = {}
        if time_period != "all":
            # TODO: Implementar estadísticas por período en document_service
            advanced_stats = {"message": f"Estadísticas por {time_period} en desarrollo"}
        
        # Estadísticas de almacenamiento
        storage_stats = {
            "total_size_mb": 0,  # TODO: Implementar en document_service
            "average_size_mb": 0,
            "largest_document_mb": 0
        }
        
        stats_response = {
            "summary": {
                "total_documents": total_documents,
                "total_users_with_documents": len(documents_by_user),
                "avg_documents_per_user": round(total_documents / max(len(documents_by_user), 1), 2)
            },
            "distribution": {
                "by_user": documents_by_user,
                "by_content_type": documents_by_type
            },
            "storage": storage_stats,
            "time_period": time_period,
            "generated_at": datetime.utcnow().isoformat(),
            "generated_by": admin_user.username
        }
        
        if advanced_stats:
            stats_response["time_based"] = advanced_stats
        
        logger.info(f"Admin {admin_user.username} consultó estadísticas de documentos")
        return stats_response
        
    except (ForbiddenException, ValidationException):
        raise
    except Exception as e:
        logger.error(f"Error al obtener estadísticas de documentos: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al obtener estadísticas: {str(e)}")

@router.delete("/documents/{document_id}")
async def delete_document_admin(
    document_id: int = Path(..., description="ID del documento a eliminar"),
    force: bool = Query(False, description="Forzar eliminación sin validar propietario"),
    admin_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    [ADMIN] Elimina cualquier documento del sistema.
    Los administradores pueden eliminar documentos de cualquier usuario.
    """
    try:
        # Validar permisos de administrador
        if not document_service.is_admin_user(admin_user.id):
            raise ForbiddenException("Solo los administradores pueden eliminar documentos")
        
        # Obtener documento para logs
        document = document_service.get_document(document_id)
        if not document:
            raise NotFoundException("Documento", document_id)
        
        # Eliminar documento (admin override)
        success = document_service.delete_document(
            document_id=document_id,
            user_id=admin_user.id  # Admin override
        )
        
        if not success:
            raise DatabaseException("No se pudo eliminar el documento")
        
        logger.warning(f"Admin {admin_user.username} eliminó documento ID={document_id} "
                      f"'{document.title}' (propietario: {document.uploaded_by})")
        
        return {"message": f"Documento '{document.title}' eliminado exitosamente"}
        
    except (ForbiddenException, NotFoundException, ValidationException):
        raise
    except Exception as e:
        logger.error(f"Error eliminando documento como admin: {str(e)}")
        raise DatabaseException(f"Error al eliminar documento: {str(e)}")

# ==================== ENDPOINTS DE AUDITORÍA ====================

@router.get("/audit/recent-actions")
async def get_recent_admin_actions(
    limit: int = Query(50, ge=1, le=100),
    admin_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Obtiene las acciones administrativas recientes.
    Solo accesible por administradores.
    """
    admin_validator.validate_admin_access(admin_user, "ver auditoría")
    
    try:
        # TODO: Implementar sistema de auditoría real
        return {
            "message": "Sistema de auditoría en desarrollo",
            "actions": []
        }
    except Exception as e:
        logger.error(f"Error obteniendo auditoría: {str(e)}")
        raise DatabaseException(f"Error al obtener auditoría: {str(e)}")
