"""
Helpers para endpoints de archivos
Contiene lógica específica de operaciones complejas separada de los endpoints
"""
import logging
from typing import Optional
from fastapi.responses import FileResponse
from pathlib import Path

from src.models.domain import User
from src.services.document_service import DocumentService
from src.services.file_validation_service import FileValidationService
from src.services.file_serving_service import FileServingService
from src.services.file_security_service import FileSecurityService
from src.services.signed_url_service import signed_url_service
from src.core.exceptions import (
    NotFoundException, 
    ForbiddenException, 
    UnauthorizedException,
    DatabaseException
)

logger = logging.getLogger(__name__)

class FileEndpointHelpers:
    """Helpers para endpoints de archivos"""
    
    def __init__(self):
        self.validator = FileValidationService()
        self.serving_service = FileServingService()
        self.security_service = FileSecurityService()
        self.document_service = DocumentService()

    def handle_direct_file_request(
        self,
        user_id: int,
        filename: str,
        token: Optional[str] = None,
        current_user: Optional[User] = None
    ) -> FileResponse:
        """
        Maneja peticiones directas de archivos por user_id/filename
        
        Args:
            user_id: ID del usuario propietario
            filename: Nombre del archivo
            token: Token opcional para autenticación
            current_user: Usuario actual (si está autenticado)
            
        Returns:
            FileResponse: Respuesta con el archivo
        """
        try:
            # 1. Autenticación (opcional para acceso público)
            authenticated_user = self.security_service.authenticate_file_request(
                token, current_user
            )
            
            # 2. Autorización
            self.security_service.authorize_file_access(
                user_id, filename, authenticated_user
            )
            
            # 3. Construcción de ruta
            file_path = self.serving_service.construct_file_path(user_id, filename)
            
            # 4. Validación de seguridad de ruta
            self.validator.validate_file_path_security(file_path)
            
            # 5. Validación de existencia
            self.validator.validate_file_exists(file_path)
            
            # 6. Determinación de content-type
            content_type = self.serving_service.determine_content_type(filename)
            
            # 7. Logging de acceso
            self.serving_service.log_file_access(
                filename=filename,
                user_id=authenticated_user.id if authenticated_user else None,
                access_type="direct"
            )
            
            # 8. Preparar respuesta
            return self.serving_service.prepare_file_response(
                file_path=file_path,
                filename=filename,
                content_type=content_type
            )
            
        except (NotFoundException, ForbiddenException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"💥 Error en petición directa de archivo: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al servir archivo: {str(e)}")

    def handle_document_file_request(
        self,
        document_id: int,
        token: Optional[str] = None,
        current_user: Optional[User] = None
    ) -> FileResponse:
        """
        Maneja peticiones de archivos por ID de documento
        
        Args:
            document_id: ID del documento
            token: Token opcional para autenticación
            current_user: Usuario actual (si está autenticado)
            
        Returns:
            FileResponse: Respuesta con el archivo
        """
        try:
            # 1. Autenticación
            authenticated_user = self.security_service.authenticate_file_request(
                token, current_user
            )
            
            if not authenticated_user:
                raise UnauthorizedException("Acceso a documento requiere autenticación")
            
            # 2. Autorización del documento
            self.security_service.authorize_document_file_access(
                document_id, authenticated_user
            )
            
            # 3. Obtener documento
            document = self.document_service.get_document(document_id)
            if not document:
                raise NotFoundException("Documento", document_id)
            
            # 4. Verificar archivo asociado
            if not getattr(document, 'file_url', None):
                raise NotFoundException("Archivo asociado al documento", document_id)
            
            # 5. Construcción de ruta del archivo
            file_path = self.serving_service.construct_document_file_path(
                file_url=document.file_url,
                document_id=document.id,
                uploaded_by=document.uploaded_by,
                original_filename=getattr(document, 'original_filename', None)
            )
            
            # 6. Validaciones
            self.validator.validate_file_path_security(file_path)
            self.validator.validate_file_exists(file_path)
            
            # 7. Determinación de content-type
            content_type = self.serving_service.determine_content_type(
                filename=getattr(document, 'original_filename', ''),
                document_content_type=getattr(document, 'content_type', None)
            )
            
            # 8. Logging de acceso
            self.serving_service.log_file_access(
                filename=getattr(document, 'original_filename', f"document_{document_id}"),
                user_id=authenticated_user.id,
                access_type="document"
            )
            
            # 9. Preparar respuesta
            response_filename = (
                getattr(document, 'original_filename', None) or 
                f"document_{document_id}.pdf"
            )
            
            return self.serving_service.prepare_file_response(
                file_path=file_path,
                filename=response_filename,
                content_type=content_type
            )
            
        except (NotFoundException, ForbiddenException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"💥 Error en petición de archivo de documento: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al servir archivo de documento: {str(e)}")

    def handle_secure_file_request(
        self,
        document_id: int,
        token: str,
        download: bool = False
    ) -> FileResponse:
        """
        Maneja peticiones seguras de archivos usando URLs firmadas
        
        Args:
            document_id: ID del documento
            token: Token JWT firmado
            download: Si forzar descarga en lugar de vista previa
            
        Returns:
            FileResponse: Respuesta con el archivo
        """
        try:
            # 1. Validar token firmado
            payload = signed_url_service.validate_signed_token(token)
            if not payload:
                raise UnauthorizedException("Token inválido o expirado")
            
            # 2. Verificar que el token es para este documento
            if payload["document_id"] != document_id:
                raise ForbiddenException("Token no válido para este documento")
            
            # 3. Obtener documento para verificar existencia
            document = self.document_service.get_document(document_id)
            if not document:
                raise NotFoundException("Documento", document_id)
            
            # 4. Usar el servicio de serving para manejo seguro
            return self.serving_service.handle_secure_file_access(
                document_id=document_id,
                file_path=payload['file_path'],
                original_filename=getattr(document, 'original_filename', None),
                content_type=getattr(document, 'content_type', 'application/octet-stream'),
                download=download
            )
            
        except (NotFoundException, ForbiddenException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"💥 Error en petición segura de archivo: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al servir archivo seguro: {str(e)}")

    def validate_file_access_permissions(
        self,
        user_id: int,
        filename: str,
        current_user: Optional[User]
    ) -> dict:
        """
        Valida permisos de acceso a un archivo y retorna información detallada
        
        Args:
            user_id: ID del propietario del archivo
            filename: Nombre del archivo
            current_user: Usuario actual
            
        Returns:
            dict: Información de validación
        """
        try:
            # Construir ruta y validar
            file_path = self.serving_service.construct_file_path(user_id, filename)
            self.validator.validate_file_path_security(file_path)
            
            # Estadísticas del archivo
            file_stats = self.serving_service.get_file_stats(file_path)
            
            # Información de permisos
            has_access = self.security_service.authorize_file_access(
                user_id, filename, current_user
            )
            
            return {
                "has_access": has_access,
                "file_exists": file_stats.get("exists", False),
                "file_stats": file_stats,
                "user_id": user_id,
                "filename": filename,
                "authenticated": current_user is not None
            }
            
        except Exception as e:
            logger.error(f"💥 Error validando permisos de archivo: {str(e)}")
            return {
                "has_access": False,
                "error": str(e),
                "file_exists": False
            }

    def get_file_preview_info(
        self,
        user_id: int,
        filename: str
    ) -> dict:
        """
        Obtiene información para vista previa de un archivo
        
        Args:
            user_id: ID del propietario
            filename: Nombre del archivo
            
        Returns:
            dict: Información de vista previa
        """
        try:
            file_path = self.serving_service.construct_file_path(user_id, filename)
            file_stats = self.serving_service.get_file_stats(file_path)
            content_type = self.serving_service.determine_content_type(filename)
            
            # Determinar si se puede previsualizar
            can_preview = content_type in self.serving_service.INLINE_CONTENT_TYPES
            
            return {
                "filename": filename,
                "content_type": content_type,
                "can_preview": can_preview,
                "file_stats": file_stats,
                "preview_url": f"/api/files/{user_id}/{filename}" if file_stats.get("exists") else None
            }
            
        except Exception as e:
            logger.error(f"💥 Error obteniendo info de preview: {str(e)}")
            return {
                "filename": filename,
                "error": str(e),
                "can_preview": False
            }

    def log_access_attempt(
        self,
        access_type: str,
        user_id: Optional[int],
        target: str,
        success: bool,
        error: Optional[str] = None
    ):
        """
        Registra intentos de acceso para auditoría
        
        Args:
            access_type: Tipo de acceso (direct, document, secure)
            user_id: ID del usuario (si está autenticado)
            target: Archivo o documento objetivo
            success: Si el acceso fue exitoso
            error: Error si ocurrió alguno
        """
        event_type = f"file_access_{access_type}"
        severity = "INFO" if success else "WARNING"
        
        details = {
            "target": target,
            "success": success,
            "error": error,
            "access_type": access_type
        }
        
        self.security_service.log_security_event(
            event_type=event_type,
            user_id=user_id,
            details=details,
            severity=severity
        )
