"""
Endpoints para servir archivos - VERSION REFACTORIZADA
Aplicando el patrón exitoso de documents.py:
- Endpoints simplificados (~15 líneas cada uno)
- Lógica delegada a servicios especializados
- Validaciones centralizadas
- Logging mejorado y performance optimizada
"""
from fastapi import APIRouter, Depends, Query, Path
from fastapi.responses import FileResponse
from typing import Optional
import logging

# Schemas y modelos
from src.models.domain import User

# Servicios y helpers
from src.api.helpers.file_helpers import FileEndpointHelpers

# Dependencias
from src.api.dependencies import get_current_user, get_current_user_optional

# Excepciones
from src.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    UnauthorizedException,
    DatabaseException
)

# Configuración
logger = logging.getLogger(__name__)
router = APIRouter(tags=["files"])

# Inicializar helpers
file_helpers = FileEndpointHelpers()

# ==================== ENDPOINTS REFACTORIZADOS ====================

@router.get("/files/{user_id}/{filename}")
async def get_file(
    user_id: int = Path(..., description="ID del usuario propietario del archivo"),
    filename: str = Path(..., description="Nombre del archivo"),
    token: Optional[str] = Query(None, description="Token de autenticación opcional"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Endpoint para servir archivos almacenados localmente.
    Permite acceso sin autenticación para visualizar PDFs en el navegador.
    
    La lógica compleja se maneja en FileEndpointHelpers.
    """
    try:
        return file_helpers.handle_direct_file_request(
            user_id=user_id,
            filename=filename,
            token=token,
            current_user=current_user
        )
    except (NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"💥 Error en endpoint get_file: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al servir archivo: {str(e)}")

@router.get("/files/documents/{document_id}")
async def get_document_file(
    document_id: int = Path(..., description="ID del documento"),
    token: Optional[str] = Query(None, description="Token de autenticación opcional"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Endpoint para servir archivos de documentos por ID.
    Acepta token como query parameter para casos donde no se pueden enviar headers.
    
    La lógica compleja se maneja en FileEndpointHelpers.
    """
    try:
        return file_helpers.handle_document_file_request(
            document_id=document_id,
            token=token,
            current_user=current_user
        )
    except (NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"💥 Error en endpoint get_document_file: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al servir archivo de documento: {str(e)}")

@router.get("/files/secure/{document_id}")
async def get_file_secure(
    document_id: int = Path(..., description="ID del documento"),
    token: str = Query(..., description="Token de acceso firmado"),
    download: bool = Query(False, description="Forzar descarga en lugar de vista previa")
):
    """
    Endpoint seguro para servir archivos usando URLs firmadas.
    Requiere un token JWT válido que contenga los permisos de acceso.
    
    La lógica compleja se maneja en FileEndpointHelpers.
    """
    try:
        return file_helpers.handle_secure_file_request(
            document_id=document_id,
            token=token,
            download=download
        )
    except (NotFoundException, ForbiddenException, UnauthorizedException):
        raise
    except Exception as e:
        logger.error(f"💥 Error en endpoint get_file_secure: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al servir archivo seguro: {str(e)}")

# ==================== ENDPOINTS DE UTILIDAD ====================

@router.get("/files/{user_id}/{filename}/info")
async def get_file_info(
    user_id: int = Path(..., description="ID del usuario propietario"),
    filename: str = Path(..., description="Nombre del archivo"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Obtiene información detallada de un archivo sin descargarlo.
    Útil para validaciones y previsualizaciones.
    """
    try:
        return file_helpers.validate_file_access_permissions(
            user_id=user_id,
            filename=filename,
            current_user=current_user
        )
    except Exception as e:
        logger.error(f"💥 Error obteniendo info de archivo: {str(e)}")
        return {"error": str(e), "has_access": False}

@router.get("/files/{user_id}/{filename}/preview")
async def get_file_preview_info(
    user_id: int = Path(..., description="ID del usuario propietario"),
    filename: str = Path(..., description="Nombre del archivo")
):
    """
    Obtiene información para vista previa de un archivo.
    No requiere autenticación para información básica.
    """
    try:
        return file_helpers.get_file_preview_info(
            user_id=user_id,
            filename=filename
        )
    except Exception as e:
        logger.error(f"💥 Error obteniendo preview info: {str(e)}")
        return {"error": str(e), "can_preview": False}
