"""
Servicio de seguridad para archivos
Centraliza la autenticación, autorización y validaciones de permisos para acceso a archivos
"""
import logging
from typing import Optional, Dict, Any
import jwt
from src.core.exceptions import (
    UnauthorizedException, 
    ForbiddenException, 
    ValidationException
)
from src.models.domain import User
from src.services.document_service import DocumentService
from src.services.user_service import UserService
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class FileSecurityService:
    """Servicio de seguridad para archivos"""
    
    def __init__(self):
        self.document_service = DocumentService()
        self.user_service = UserService()

    def authenticate_file_request(
        self, 
        token: Optional[str], 
        current_user: Optional[User]
    ) -> Optional[User]:
        """
        Autentica una petición de archivo usando token o usuario actual
        
        Args:
            token: Token JWT opcional
            current_user: Usuario actual (si está autenticado)
            
        Returns:
            Optional[User]: Usuario autenticado o None
        """
        # Si ya hay usuario autenticado, usar ese
        if current_user:
            logger.info(f"🔐 Usuario autenticado: {current_user.id}")
            return current_user
        
        # Intentar autenticar con token
        if token:
            try:
                payload = jwt.decode(
                    token, 
                    settings.JWT_SECRET_KEY, 
                    algorithms=[settings.JWT_ALGORITHM]
                )
                
                user_id = payload.get("sub")
                if user_id:
                    authenticated_user = self.user_service.get_user(int(user_id))
                    if authenticated_user:
                        logger.info(f"🔐 Usuario autenticado por token: {authenticated_user.id}")
                        return authenticated_user
                    
            except Exception as e:
                logger.warning(f"⚠️ Error autenticando con token: {str(e)}")
        
        # Sin autenticación
        logger.info("🌐 Acceso sin autenticación")
        return None

    def authorize_file_access(
        self, 
        user_id: int, 
        filename: str, 
        current_user: Optional[User]
    ) -> bool:
        """
        Autoriza el acceso a un archivo específico
        
        Args:
            user_id: ID del propietario del archivo
            filename: Nombre del archivo
            current_user: Usuario actual
            
        Returns:
            bool: True si tiene acceso
            
        Raises:
            ForbiddenException: Si no tiene permisos
        """
        # Acceso público permitido para visualización
        if not current_user:
            logger.info(f"🌐 Acceso público autorizado para: {filename}")
            return True
        
        # Verificar si es propietario
        if current_user.id == user_id:
            logger.info(f"✅ Acceso autorizado como propietario: {filename}")
            return True
        
        # Verificar si es administrador
        if getattr(current_user, 'is_admin', False):
            logger.info(f"👑 Acceso autorizado como administrador: {filename}")
            return True
        
        # Por ahora permitir acceso entre usuarios (política flexible)
        # En producción, verificar si el documento está compartido
        logger.warning(
            f"⚠️ Acceso cruzado permitido: usuario {current_user.id} "
            f"accede a archivo de usuario {user_id}"
        )
        return True

    def authorize_document_file_access(
        self, 
        document_id: int, 
        current_user: User
    ) -> bool:
        """
        Autoriza el acceso a un archivo de documento
        
        Args:
            document_id: ID del documento
            current_user: Usuario actual
            
        Returns:
            bool: True si tiene acceso
            
        Raises:
            ForbiddenException: Si no tiene permisos
        """
        try:
            # Verificar que el documento existe
            document = self.document_service.get_document(document_id)
            if not document:
                raise ForbiddenException(f"Documento {document_id} no encontrado")
            
            # Verificar acceso al documento
            has_access = self.document_service.check_user_access(document_id, current_user.id)
            is_admin = getattr(current_user, 'is_admin', False)
            
            if not has_access and not is_admin:
                logger.warning(
                    f"🚫 Acceso denegado al documento {document_id} "
                    f"para usuario {current_user.id}"
                )
                raise ForbiddenException("No tienes acceso a este documento")
            
            logger.info(f"✅ Acceso autorizado al documento {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"💥 Error autorizando acceso a documento: {str(e)}")
            raise ForbiddenException("Error verificando permisos de documento")

    def validate_token_permissions(
        self, 
        token: str, 
        document_id: int
    ) -> Dict[str, Any]:
        """
        Valida un token firmado y sus permisos
        
        Args:
            token: Token JWT firmado
            document_id: ID del documento solicitado
            
        Returns:
            Dict: Payload del token validado
            
        Raises:
            UnauthorizedException: Si el token es inválido
            ForbiddenException: Si el token no autoriza este documento
        """
        try:
            # Decodificar token
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Verificar tipo de token
            if payload.get("type") != "file_access":
                raise UnauthorizedException("Token no es de acceso a archivos")
            
            # Verificar que el token es para este documento
            token_doc_id = payload.get("document_id")
            if token_doc_id != document_id:
                logger.warning(
                    f"🚫 Token para documento {token_doc_id} "
                    f"usado en documento {document_id}"
                )
                raise ForbiddenException("Token no válido para este documento")
            
            # Verificar campos requeridos
            required_fields = ["document_id", "user_id", "file_path"]
            missing_fields = [field for field in required_fields if field not in payload]
            
            if missing_fields:
                raise UnauthorizedException(f"Token incompleto: {missing_fields}")
            
            logger.info(
                f"🔒 Token validado para documento {document_id} "
                f"usuario {payload['user_id']}"
            )
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("🕰️ Token expirado en validación de permisos")
            raise UnauthorizedException("Token expirado")
        except jwt.InvalidTokenError as e:
            logger.warning(f"🔒 Token inválido en validación: {str(e)}")
            raise UnauthorizedException("Token inválido")
        except (UnauthorizedException, ForbiddenException):
            raise
        except Exception as e:
            logger.error(f"💥 Error validando permisos de token: {str(e)}")
            raise UnauthorizedException("Error validando token")

    def check_document_permissions(
        self, 
        document_id: int, 
        user_id: int
    ) -> Dict[str, Any]:
        """
        Verifica permisos detallados sobre un documento
        
        Args:
            document_id: ID del documento
            user_id: ID del usuario
            
        Returns:
            Dict: Información de permisos
        """
        try:
            document = self.document_service.get_document(document_id)
            if not document:
                return {
                    "has_access": False,
                    "reason": "Documento no encontrado",
                    "is_owner": False,
                    "is_admin": False
                }
            
            # Verificar permisos
            has_access = self.document_service.check_user_access(document_id, user_id)
            is_owner = document.uploaded_by == user_id
            
            # Verificar si es admin (requiere cargar el usuario)
            user = self.user_service.get_user(user_id)
            is_admin = getattr(user, 'is_admin', False) if user else False
            
            permissions = {
                "has_access": has_access or is_admin,
                "reason": "Acceso autorizado" if (has_access or is_admin) else "Sin permisos",
                "is_owner": is_owner,
                "is_admin": is_admin,
                "document_exists": True,
                "document_id": document_id,
                "uploaded_by": document.uploaded_by
            }
            
            logger.info(f"🔍 Permisos verificados para documento {document_id}: {permissions}")
            return permissions
            
        except Exception as e:
            logger.error(f"💥 Error verificando permisos: {str(e)}")
            return {
                "has_access": False,
                "reason": f"Error: {str(e)}",
                "is_owner": False,
                "is_admin": False,
                "document_exists": False
            }

    def log_security_event(
        self, 
        event_type: str, 
        user_id: Optional[int], 
        details: Dict[str, Any],
        severity: str = "INFO"
    ):
        """
        Registra eventos de seguridad para auditoría
        
        Args:
            event_type: Tipo de evento de seguridad
            user_id: ID del usuario involucrado
            details: Detalles del evento
            severity: Severidad del evento (INFO, WARNING, ERROR)
        """
        log_entry = {
            "event": event_type,
            "user_id": user_id,
            "severity": severity,
            "details": details
        }
        
        log_message = f"🔒 Evento de seguridad [{severity}]: {event_type} - {details}"
        
        if severity == "ERROR":
            logger.error(log_message)
        elif severity == "WARNING":
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def generate_access_report(
        self, 
        user_id: int, 
        document_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Genera un reporte de acceso para auditoría
        
        Args:
            user_id: ID del usuario
            document_id: ID del documento (opcional)
            
        Returns:
            Dict: Reporte de acceso
        """
        try:
            user = self.user_service.get_user(user_id)
            if not user:
                return {"error": "Usuario no encontrado"}
            
            report = {
                "user_id": user_id,
                "username": getattr(user, 'username', 'desconocido'),
                "is_admin": getattr(user, 'is_admin', False),
                "timestamp": "now",  # En producción usar datetime.utcnow()
            }
            
            if document_id:
                permissions = self.check_document_permissions(document_id, user_id)
                report["document_permissions"] = permissions
            
            logger.info(f"📊 Reporte de acceso generado para usuario {user_id}")
            return report
            
        except Exception as e:
            logger.error(f"💥 Error generando reporte de acceso: {str(e)}")
            return {"error": str(e)}
