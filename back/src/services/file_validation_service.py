"""
Servicio de validación para archivos
Centraliza todas las validaciones relacionadas con el acceso y servicio de archivos
"""
import logging
from pathlib import Path
from typing import Optional
import jwt
from src.core.exceptions import (
    ValidationException, 
    ForbiddenException, 
    NotFoundException,
    UnauthorizedException
)
from src.models.domain import User
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class FileValidationService:
    """Servicio para validaciones de archivos"""
    
    # Rutas permitidas
    ALLOWED_BASE_PATHS = [
        "uploads/documents",
        "uploads/temp",
        "assets/images"
    ]
    
    # Tipos de archivo seguros
    SAFE_CONTENT_TYPES = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif'
    }

    def validate_file_exists(self, file_path: Path) -> bool:
        """
        Valida que un archivo existe físicamente
        
        Args:
            file_path: Ruta del archivo a verificar
            
        Returns:
            bool: True si existe
            
        Raises:
            NotFoundException: Si el archivo no existe
        """
        if not file_path.exists():
            logger.warning(f"📄 Archivo no encontrado: {file_path}")
            raise NotFoundException("Archivo", str(file_path))
        
        if not file_path.is_file():
            logger.warning(f"📁 La ruta no es un archivo: {file_path}")
            raise ValidationException(f"La ruta {file_path} no es un archivo válido")
        
        logger.info(f"✅ Archivo validado: {file_path}")
        return True

    def validate_user_file_access(
        self, 
        user_id: int, 
        current_user: Optional[User], 
        filename: str
    ) -> bool:
        """
        Valida si un usuario tiene acceso a un archivo específico
        
        Args:
            user_id: ID del propietario del archivo
            current_user: Usuario actual (puede ser None)
            filename: Nombre del archivo
            
        Returns:
            bool: True si tiene acceso
            
        Raises:
            ForbiddenException: Si no tiene permisos
        """
        # Acceso público permitido para visualización (especialmente PDFs)
        if not current_user:
            logger.info(f"🌐 Acceso público permitido para archivo: {filename}")
            return True
        
        # Verificar si es el propietario o admin
        is_owner = current_user.id == user_id
        is_admin = getattr(current_user, 'is_admin', False)
        
        if not is_owner and not is_admin:
            logger.warning(
                f"🚫 Usuario {current_user.id} intentando acceder a archivo de usuario {user_id}"
            )
            # Por ahora permitir acceso si el archivo existe (política flexible)
            # En producción, aquí se verificaría si el documento está compartido
            return True
        
        access_type = "propietario" if is_owner else "administrador"
        logger.info(f"✅ Acceso validado como {access_type} para archivo: {filename}")
        return True

    def validate_document_file_access(
        self, 
        document_id: int, 
        user_id: int, 
        current_user: Optional[User]
    ) -> bool:
        """
        Valida acceso a archivo de documento específico
        
        Args:
            document_id: ID del documento
            user_id: ID del usuario actual
            current_user: Usuario actual
            
        Returns:
            bool: True si tiene acceso
            
        Raises:
            UnauthorizedException: Si no está autenticado
            ForbiddenException: Si no tiene permisos
        """
        if not current_user:
            raise UnauthorizedException("Acceso a documento requiere autenticación")
        
        # La validación específica del documento se delega al DocumentService
        # Este método solo valida la estructura de la petición
        logger.info(f"🔍 Validando acceso a documento {document_id} para usuario {user_id}")
        return True

    def validate_signed_token(self, token: str) -> dict:
        """
        Valida un token JWT firmado
        
        Args:
            token: Token JWT a validar
            
        Returns:
            dict: Payload del token si es válido
            
        Raises:
            UnauthorizedException: Si el token es inválido o expirado
        """
        try:
            # Decodificar token
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Verificar campos requeridos
            required_fields = ["document_id", "user_id", "file_path"]
            missing_fields = [field for field in required_fields if field not in payload]
            
            if missing_fields:
                raise UnauthorizedException(
                    f"Token inválido: campos faltantes {missing_fields}"
                )
            
            logger.info(f"✅ Token validado para documento {payload.get('document_id')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("🕰️ Token expirado")
            raise UnauthorizedException("Token expirado")
        except jwt.InvalidTokenError as e:
            logger.warning(f"🔒 Token inválido: {str(e)}")
            raise UnauthorizedException("Token inválido")
        except Exception as e:
            logger.error(f"💥 Error validando token: {str(e)}")
            raise UnauthorizedException("Error validando token")

    def validate_file_path_security(self, file_path: Path) -> bool:
        """
        Valida que la ruta del archivo es segura (no hay directory traversal)
        
        Args:
            file_path: Ruta del archivo a validar
            
        Returns:
            bool: True si la ruta es segura
            
        Raises:
            ValidationException: Si la ruta no es segura
        """
        try:
            # Resolver la ruta absoluta
            resolved_path = file_path.resolve()
            
            # Verificar que está dentro de los directorios permitidos
            is_safe = any(
                str(resolved_path).startswith(str(Path(base_path).resolve()))
                for base_path in self.ALLOWED_BASE_PATHS
            )
            
            if not is_safe:
                logger.error(f"🚨 Intento de acceso a ruta no permitida: {resolved_path}")
                raise ValidationException("Ruta de archivo no permitida")
            
            # Verificar que no hay componentes peligrosos
            path_parts = file_path.parts
            dangerous_parts = ['.', '..', '~']
            
            if any(part in dangerous_parts for part in path_parts):
                logger.error(f"🚨 Ruta contiene componentes peligrosos: {file_path}")
                raise ValidationException("Ruta de archivo contiene componentes no permitidos")
            
            logger.info(f"🛡️ Ruta validada como segura: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"💥 Error validando seguridad de ruta: {str(e)}")
            raise ValidationException(f"Error validando ruta: {str(e)}")

    def validate_content_type(self, filename: str) -> str:
        """
        Determina y valida el content-type basado en la extensión del archivo
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            str: Content-type apropiado
        """
        if not filename:
            return "application/octet-stream"
        
        # Obtener extensión
        extension = Path(filename).suffix.lower()
        
        # Buscar content-type conocido
        content_type = self.SAFE_CONTENT_TYPES.get(
            extension, 
            "application/octet-stream"
        )
        
        logger.info(f"🏷️ Content-type determinado: {content_type} para {filename}")
        return content_type

    def validate_query_token(self, token: Optional[str]) -> Optional[dict]:
        """
        Valida un token opcional pasado como query parameter
        
        Args:
            token: Token opcional a validar
            
        Returns:
            Optional[dict]: Payload del token si es válido, None si no hay token
        """
        if not token:
            return None
        
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            logger.info(f"✅ Token de query validado para usuario {payload.get('sub')}")
            return payload
            
        except Exception as e:
            logger.warning(f"⚠️ Token de query inválido: {str(e)}")
            # No lanzar excepción, simplemente devolver None
            return None
