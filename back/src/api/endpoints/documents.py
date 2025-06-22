"""
API Endpoints para la gestión de documentos - VERSION REFACTORIZADA
Este módulo implementa endpoints limpios y organizados para documentos:
- Lógica de negocio movida a servicios especializados
- Endpoints divididos en funciones pequeñas y manejables
- Validaciones centralizadas en servicios de validación
"""
from fastapi import APIRouter, Depends, Query, Path, Body, Form, UploadFile, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

# Schemas
from src.models.schemas.document import (
    DocumentBase, DocumentCreate, DocumentResponse, DocumentShare, 
    DocumentUserLink, DocumentUploadResponse, DocumentResponseHybrid,
    ShareDocumentRequest, DocumentUpdate
)
from src.models.schemas.document_secure import (
    DocumentWithSignedURL, SecureFileAccessRequest, SecureFileAccessResponse
)
from src.models.schemas.user import UserResponse 
from src.models.domain import User, Document

# Servicios
from src.services.document_service import DocumentService
from src.services.user_service import UserService
from src.services.signed_url_service import signed_url_service

# Helpers y validaciones
from src.api.helpers.document_helpers import DocumentEndpointHelpers

# Dependencias y middleware
from src.api.dependencies import get_current_user, get_document_service, get_user_service
from src.core.rate_limit import rate_limit_upload
from fastapi import Request as FastAPIRequest

# Excepciones
from src.core.exceptions import (
    NotFoundException, ValidationException, ForbiddenException,
    UnauthorizedException, ConflictException, DatabaseException,
    ExternalServiceException
)

logger = logging.getLogger(__name__)

# Crear router
router = APIRouter(prefix="/documents", tags=["documents"])

# Inicializar helpers
document_helpers = DocumentEndpointHelpers()

# ==================== ENDPOINTS DE SUBIDA ====================

@router.post("/upload", response_model=DocumentResponseHybrid)
@rate_limit_upload
async def upload_document(
    request: FastAPIRequest,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Sube un archivo y lo procesa con enfoque híbrido:
    - Archivos pequeños: procesamiento síncrono
    - Archivos grandes: procesamiento asíncrono
    
    La lógica compleja se maneja en DocumentEndpointHelpers.
    """
    try:
        return await document_helpers.handle_document_upload(
            file=file,
            title=title,
            current_user=current_user,
            document_service=document_service,
            background_tasks=background_tasks
        )
    except (ValidationException, DatabaseException):
        raise
    except Exception as e:
        logger.error(f"Error en upload endpoint: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al procesar el documento: {str(e)}")

@router.post("/", response_model=DocumentResponse)
async def create_document(
    document: DocumentCreate,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Crea un nuevo documento con contenido directo.
    Para subir archivos, usar /upload endpoint.
    """
    try:
        return document_service.create_document(
            uploaded_by=current_user.id,
            title=document.title,
            content=document.content,
            content_type=document.content_type,
            tags=document.tags
        )
    except Exception as e:
        logger.error(f"Error al crear documento: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al crear documento: {str(e)}")

# ==================== ENDPOINTS DE GESTIÓN ====================

@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int = Path(..., description="ID del documento a actualizar"),
    document_update: DocumentUpdate = Body(..., description="Datos a actualizar"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Actualiza la metadata de un documento específico.
    Solo el propietario del documento o un administrador puede actualizarlo.
    """
    try:
        # Verificar documento existe
        document = document_service.get_document(document_id)
        if not document:
            raise NotFoundException("Documento", document_id)
        
        # Verificar permisos
        is_admin = document_service.is_admin_user(current_user.id)
        is_owner = document.uploaded_by == current_user.id
        
        if not is_owner and not is_admin:
            raise ForbiddenException("No tienes permisos para actualizar este documento")
        
        # Actualizar
        update_data = document_update.model_dump(exclude_unset=True)
        updated_document = document_service.update_document(
            document_id=document_id,
            title=update_data.get('title'),
            content=update_data.get('content'),
            tags=update_data.get('tags') if 'tags' in update_data else None,
            file_url=update_data.get('file_url')
        )
        
        return updated_document
        
    except (ValidationException, NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"Error al actualizar documento {document_id}: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al actualizar documento: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: int = Path(..., description="ID del documento a eliminar"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Elimina un documento del sistema.
    Verifica permisos y elimina tanto de BD como de ChromaDB.
    """
    try:
        success = document_service.delete_document(document_id, current_user.id)
        
        if not success:
            raise DatabaseException("No se pudo eliminar el documento")
        
        return None  # 204 No Content
        
    except ValueError as ve:
        raise ForbiddenException(str(ve))
    except (ValidationException, NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"Error eliminando documento {document_id}: {str(e)}")
        raise DatabaseException(f"Error al eliminar documento: {str(e)}")

# ==================== ENDPOINTS DE COMPARTIR ====================

@router.post("/{document_id}/validate-share")
async def validate_share(
    document_id: int = Path(..., description="ID del documento"),
    request: ShareDocumentRequest = Body(..., description="Request con lista de IDs de usuarios"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Valida una solicitud de compartir antes de ejecutarla.
    Útil para mostrar advertencias o confirmaciones al usuario.
    """
    try:
        # Verificar que el documento existe
        document = document_service.get_document(document_id)
        if not document:
            raise NotFoundException("Documento", document_id)
        
        # Verificar permisos
        if document.uploaded_by != current_user.id and not document_service.is_admin_user(current_user.id):
            raise ForbiddenException("No tienes permisos para compartir este documento")
        
        # Obtener usuarios que ya tienen acceso
        existing_shares = document_service.get_existing_shares(document_id, request.user_ids)
        existing_user_ids = [share["id"] for share in existing_shares]
        new_user_ids = [uid for uid in request.user_ids if uid not in existing_user_ids]
        
        return {
            "can_share": len(new_user_ids) > 0,
            "document": {
                "id": document.id,
                "title": document.title,
                "owner_id": document.uploaded_by
            },
            "validation": {
                "total_requested": len(request.user_ids),
                "already_shared": existing_shares,
                "new_users": new_user_ids,
                "all_have_access": len(existing_shares) == len(request.user_ids)
            }
        }
    except (ValidationException, NotFoundException, ForbiddenException):
        raise
    except Exception as e:
        logger.error(f"Error al validar compartir: {str(e)}", exc_info=True)
        raise DatabaseException("Error al validar compartir")

@router.post("/{document_id}/share")
async def share_document(
    document_id: int = Path(..., description="ID del documento a compartir"),
    request: ShareDocumentRequest = Body(..., description="Request con lista de IDs de usuarios"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Comparte un documento con usuarios específicos.
    Solo el propietario del documento o un administrador puede compartirlo.
    
    La lógica de validación se maneja en DocumentEndpointHelpers.
    Valida automáticamente usuarios que ya tienen acceso.
    """
    try:
        result = document_helpers.handle_document_sharing(
            document_id=document_id,
            user_ids=request.user_ids,
            current_user=current_user,
            document_service=document_service
        )
        
        # Transformar respuesta para el frontend
        return {
            "success": result["success"],
            "message": result["message"],
            "successful_shares": result["successful_shares"],
            "already_shared": result["already_shared"],
            "failed_shares": result["failed_shares"],
            "share_summary": result["share_summary"]
        }
    except (ValidationException, NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"Error al compartir documento: {str(e)}", exc_info=True)
        raise DatabaseException("Error al compartir el documento")

@router.delete("/{document_id}/share/{user_id}")
async def revoke_document_access(
    document_id: int = Path(..., description="ID del documento"),
    user_id: int = Path(..., description="ID del usuario"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Revoca el acceso de un usuario a un documento.
    Solo el propietario del documento puede revocar accesos.
    """
    try:
        return document_helpers.handle_document_access_revocation(
            document_id=document_id,
            user_id=user_id,
            current_user=current_user,
            document_service=document_service
        )
    except (ValidationException, NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"Error al revocar acceso: {str(e)}")
        raise DatabaseException("Error al revocar acceso")

# ==================== ENDPOINTS DE CONSULTA ====================

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = Query(0, description="Número de documentos a saltar para paginación"),
    limit: int = Query(100, description="Número máximo de documentos a retornar"),
    sort_by: Optional[str] = Query(None, description="Campo por el cual ordenar"),
    order: Optional[str] = Query(None, description="Orden de clasificación (asc, desc)"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Lista todos los documentos del usuario actual.
    IMPORTANTE: Siempre devuelve solo los documentos del usuario actual.
    Para todos los documentos del sistema, usar /admin/all.
    """
    try:
        # Valores por defecto
        sort_by = sort_by or 'created_at'
        order = order or 'desc'
        
        documents = document_service.list_user_documents(
            user_id=current_user.id,
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            order=order
        )
        
        return documents
    except Exception as e:
        logger.error(f"Error al listar documentos: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al listar documentos: {str(e)}")

@router.get("/search", response_model=List[Dict[str, Any]])
async def search_documents(
    query: str = Query(..., description="Texto a buscar en documentos"),
    tags: Optional[List[str]] = Query(None, description="Filtrar por etiquetas"),
    n_results: int = Query(5, description="Número de resultados a retornar"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Busca documentos por contenido usando búsqueda semántica.
    """
    try:
        results = document_service.search_documents(
            query=query,
            user_id=current_user.id,
            n_results=n_results,
            tags=tags
        )
        return results
    except Exception as e:
        logger.error(f"Error en búsqueda: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error en búsqueda: {str(e)}")

@router.get("/shared-with-me", response_model=List[DocumentResponse])
async def get_shared_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Obtiene documentos compartidos con el usuario actual.
    """
    try:
        documents = document_service.get_shared_documents(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        return documents
    except Exception as e:
        logger.error(f"Error obteniendo documentos compartidos: {e}")
        raise DatabaseException("Error al obtener documentos compartidos")

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int = Path(..., description="ID del documento a obtener"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Obtiene la información detallada de un documento específico.
    Verifica que el usuario tenga acceso al documento.
    """
    try:
        document = document_service.get_document(document_id)
        
        if not document:
            raise NotFoundException("Documento", document_id)
        
        # Verificar acceso
        if not document_service.check_user_access(document_id, current_user.id):
            raise ForbiddenException("No tienes permiso para acceder a este documento")
            
        return document
    except (ValidationException, NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"Error obteniendo documento {document_id}: {str(e)}")
        raise DatabaseException(f"Error al obtener documento: {str(e)}")

@router.get("/{document_id}/status", response_model=Dict[str, Any])
async def get_document_status(
    document_id: int = Path(..., description="ID del documento a consultar"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Obtiene el estado de procesamiento de un documento.
    Útil para polling desde el frontend.
    """
    try:
        # Verificar acceso
        if not document_service.check_user_access(document_id, current_user.id):
            raise ForbiddenException("No tienes permiso para acceder a este documento")
            
        document = document_service.get_document(document_id)
        if not document:
            raise NotFoundException("Documento", document_id)
            
        return {
            "document_id": document_id,
            "title": document.title,
            "status": getattr(document, 'status', 'unknown'),
            "message": getattr(document, 'status_message', ''),
            "content_type": document.content_type,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
            "file_url": getattr(document, 'file_url', None),
            "completed": getattr(document, 'status', '') == 'completed'
        }
    except (ValidationException, NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"Error al obtener estado del documento {document_id}: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al obtener estado: {str(e)}")

# ==================== ENDPOINTS DE UTILIDAD ====================

@router.get("/{document_id}/access")
async def check_document_access(
    document_id: int = Path(..., description="ID del documento"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Verifica si el usuario tiene acceso a un documento.
    """
    has_access = document_service.check_user_access(
        document_id=document_id,
        user_id=current_user.id
    )
    
    if not has_access:
        raise ForbiddenException("No tienes acceso a este documento")
    
    return {"has_access": True}

@router.get("/{document_id}/users", response_model=List[Dict[str, Any]])
async def list_document_users(
    document_id: int = Path(..., description="ID del documento"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Lista todos los usuarios con acceso a un documento específico.
    """
    try:
        document = document_service.get_document(document_id)
        
        if not document:
            raise NotFoundException("Documento", document_id)
        
        # Verificar acceso
        if not document_service.check_user_access(document_id, current_user.id):
            raise ForbiddenException("No tienes permiso para ver los usuarios de este documento")
        
        users = document_service.list_document_users(document_id, current_user.id)
        return users
        
    except ValueError as ve:
        raise ForbiddenException(str(ve))
    except (ValidationException, NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"Error al listar usuarios del documento {document_id}: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al listar usuarios: {str(e)}")

@router.post("/{document_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    document_id: int = Path(..., description="ID del documento a re-indexar"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Re-indexa un documento en ChromaDB.
    Útil para documentos que existen en la BD pero no están indexados.
    """
    try:
        document = document_service.get_document(document_id)
        if not document:
            raise NotFoundException("Documento", document_id)
            
        if document.uploaded_by != current_user.id and not document_service.is_admin_user(current_user.id):
            raise ForbiddenException("Sin permisos")
            
        if not hasattr(document, 'content') or not document.content:
            if hasattr(document, 'file_url') and document.file_url:
                logger.info(f"Descargando contenido desde: {document.file_url}")
                import requests
                response = requests.get(document.file_url)
                if document.content_type == "application/pdf":
                    content = document_service.extract_text_from_pdf(response.content)
                else:
                    content = response.text
                document = document_service.update_document(
                    document_id=document_id,
                    content=content
                )
            else:
                raise ValidationException("El documento no tiene contenido ni archivo asociado")
        else:
            document = document_service.update_document(
                document_id=document_id,
                content=document.content
            )
        return document
    except Exception as e:
        logger.error(f"Error re-indexando documento {document_id}: {str(e)}")
        raise DatabaseException(str(e))

@router.get("/{document_id}/verify-index", response_model=Dict[str, Any])
async def verify_document_index(
    document_id: int,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Verifica si un documento está correctamente indexado en ChromaDB.
    """
    try:
        document = document_service.get_document(document_id)
        if not document:
            raise NotFoundException("Documento", document_id)
        
        # Verificar acceso
        if document.uploaded_by != current_user.id and not current_user.is_admin:
            if not document_service.check_user_access(document_id, current_user.id):
                raise ForbiddenException("No tienes acceso a este documento")
        
        is_indexed = document_service.verify_document_indexed(document_id)
        
        return {
            "document_id": document_id,
            "title": document.title,
            "is_indexed": is_indexed,
            "status": document.status if hasattr(document, 'status') else "unknown",
            "message": "Documento correctamente indexado" if is_indexed else "Documento no encontrado en el índice"
        }
        
    except (ValidationException, NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"Error al verificar indexación: {str(e)}")
        raise DatabaseException(f"Error al verificar documento: {str(e)}")

# ==================== ENDPOINTS DE SEGURIDAD ====================

@router.post("/{document_id}/secure-access", response_model=SecureFileAccessResponse)
async def generate_secure_access_urls(
    document_id: int = Path(..., description="ID del documento"),
    request: SecureFileAccessRequest = Body(...),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Genera URLs firmadas para acceso seguro a un documento.
    Solo usuarios con acceso al documento pueden generar URLs.
    """
    try:
        document = document_service.get_document(document_id)
        if not document:
            raise NotFoundException("Documento", document_id)
        
        # Verificar acceso
        if not document_service.check_user_access(document_id, current_user.id):
            raise ForbiddenException("No tienes acceso a este documento")
        
        # Verificar archivo asociado
        if not hasattr(document, 'file_url') or not document.file_url:
            raise ValidationException("Este documento no tiene archivo asociado")
        
        # Extraer ruta del archivo
        parts = document.file_url.split('/api/files/')
        if len(parts) > 1:
            file_path = parts[1]
        else:
            file_path = f"{document.uploaded_by}/{document.id}_{document.original_filename}"
        
        # Generar URLs firmadas
        preview_url = signed_url_service.generate_preview_url(
            document_id=document_id,
            user_id=current_user.id,
            file_path=file_path
        )
        
        download_url = signed_url_service.generate_download_url(
            document_id=document_id,
            user_id=current_user.id,
            file_path=file_path
        )
        
        # Calcular expiración
        from datetime import datetime, timedelta
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        return SecureFileAccessResponse(
            document_id=document_id,
            preview_url=preview_url,
            download_url=download_url,
            expires_at=expires_at
        )
        
    except (ValidationException, NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"Error generando URLs seguras: {str(e)}")
        raise DatabaseException("Error al generar URLs de acceso")



# ==================== ENDPOINTS DEPRECADOS ====================

@router.post("/share", deprecated=True)
async def share_document_legacy(
    share_data: DocumentShare,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    [DEPRECADO] Comparte un documento con usuarios específicos.
    Use POST /api/documents/{document_id}/share en su lugar.
    """
    try:
        success = document_service.share_document(
            document_id=share_data.document_id,
            user_ids=share_data.user_ids,
            requester_id=current_user.id
        )
        
        if not success:
            raise DatabaseException("No se pudo compartir el documento")
        
        return {"message": "Documento compartido exitosamente"}
    except ValueError as ve:
        raise ForbiddenException(str(ve))
    except Exception as e:
        logger.error(f"Error al compartir documento: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al compartir documento: {str(e)}")

@router.post("/{document_id}/users")
async def link_document_to_users(
    user_link: DocumentUserLink,
    document_id: int = Path(..., description="ID del documento"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Vincula un documento a usuarios específicos.
    """
    try:
        document = document_service.get_document(document_id)
        
        if not document:
            raise NotFoundException("Documento", document_id)
        
        if document.uploaded_by != current_user.id:
            raise ForbiddenException("Solo el propietario puede vincular este documento")
        
        success = document_service.link_users_to_document(
            document_id, 
            user_link.user_ids,
            current_user.id
        )
           
        if not success:
            raise DatabaseException("No se pudo vincular los usuarios al documento")
        
        return {"message": "Usuarios vinculados exitosamente al documento"}
    except (ValidationException, NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"Error vinculando usuarios: {str(e)}")
        raise DatabaseException(f"Error al vincular usuarios: {str(e)}")

@router.get("/shared", response_model=List[DocumentResponse])
async def list_shared_documents(
    skip: int = Query(0, description="Número de documentos a saltar"),
    limit: int = Query(100, description="Número máximo de documentos a retornar"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    [DEPRECADO] Lista documentos compartidos con el usuario.
    Use /shared-with-me en su lugar.
    """
    try:
        documents = document_service.get_shared_documents(
            user_id=current_user.id,
            limit=limit,
            skip=skip
        )
        return documents
    except Exception as e:
        logger.error(f"Error al listar documentos compartidos: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al listar documentos compartidos: {str(e)}")

@router.delete("/{document_id}/users/{user_id}")
async def remove_user_access(
    document_id: int = Path(..., description="ID del documento"),
    user_id: int = Path(..., description="ID del usuario a eliminar acceso"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    [DEPRECADO] Elimina el acceso de un usuario a un documento.
    Use DELETE /documents/{document_id}/share/{user_id} en su lugar.
    """
    try:
        document = document_service.get_document(document_id)
        
        if not document:
            raise NotFoundException("Documento", document_id)
        
        if document.uploaded_by != current_user.id:
            raise ForbiddenException("Solo el propietario puede eliminar acceso a este documento")
        
        success = document_service.remove_user_access(document_id, user_id, current_user.id)
        
        if not success:
            raise DatabaseException("No se pudo eliminar el acceso del usuario")
        
        return None  # 204 No Content
    except ValueError as ve:
        raise ValidationException(str(ve))
    except (ValidationException, NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"Error al eliminar acceso: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al eliminar acceso: {str(e)}")
