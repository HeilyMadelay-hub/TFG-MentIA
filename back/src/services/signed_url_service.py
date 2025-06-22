"""
Servicio para generar y validar URLs firmadas para acceso seguro a archivos.
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import logging
from src.config.settings import get_settings
from src.core.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)
settings = get_settings()

class SignedURLService:
    """
    Servicio para generar URLs firmadas con tiempo de expiración.
    Utiliza JWT para crear tokens seguros y temporales.
    """
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.default_expiration_hours = 24  # URLs válidas por 24 horas por defecto
    
    def generate_signed_url(
        self, 
        document_id: int, 
        user_id: int,
        file_path: str,
        expiration_hours: Optional[int] = None
    ) -> str:
        """
        Genera una URL firmada para acceso temporal a un archivo.
        
        Args:
            document_id: ID del documento
            user_id: ID del usuario que solicita acceso
            file_path: Ruta relativa del archivo (e.g., "19/uuid_file.pdf")
            expiration_hours: Horas de validez (default: 24)
            
        Returns:
            URL completa con token firmado
        """
        try:
            # Tiempo de expiración
            exp_hours = expiration_hours or self.default_expiration_hours
            expiration = datetime.utcnow() + timedelta(hours=exp_hours)
            
            # Payload del token
            payload = {
                "document_id": document_id,
                "user_id": user_id,
                "file_path": file_path,
                "exp": expiration,
                "iat": datetime.utcnow(),
                "type": "file_access"
            }
            
            # Generar token JWT
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # Construir URL completa
            base_url = f"{settings.FRONTEND_URL.replace(':53793', ':' + str(settings.PORT))}/api/files/secure/{document_id}"
            query_params = urlencode({"token": token})
            signed_url = f"{base_url}?{query_params}"
            
            logger.info(f"URL firmada generada para documento {document_id}, usuario {user_id}")
            return signed_url
            
        except Exception as e:
            logger.error(f"Error generando URL firmada: {str(e)}", exc_info=True)
            raise ExternalServiceException(f"Error generando URL firmada: {str(e)}")
    
    def validate_signed_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Valida un token de URL firmada.
        
        Args:
            token: Token JWT a validar
            
        Returns:
            Payload del token si es válido, None si no
        """
        try:
            # Decodificar y validar token
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Verificar que es un token de acceso a archivo
            if payload.get("type") != "file_access":
                logger.warning("Token no es de tipo file_access")
                return None
            
            # Verificar campos requeridos
            required_fields = ["document_id", "user_id", "file_path"]
            if not all(field in payload for field in required_fields):
                logger.warning("Token no contiene todos los campos requeridos")
                return None
            
            logger.info(f"Token válido para documento {payload['document_id']}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expirado")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token inválido: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error validando token: {str(e)}", exc_info=True)
            return None
    
    def generate_preview_url(
        self, 
        document_id: int, 
        user_id: int,
        file_path: str
    ) -> str:
        """
        Genera una URL de vista previa con expiración corta (1 hora).
        Ideal para vistas previas temporales.
        
        Args:
            document_id: ID del documento
            user_id: ID del usuario
            file_path: Ruta del archivo
            
        Returns:
            URL firmada con expiración corta
        """
        return self.generate_signed_url(
            document_id=document_id,
            user_id=user_id,
            file_path=file_path,
            expiration_hours=1  # Solo 1 hora para preview
        )
    
    def generate_download_url(
        self, 
        document_id: int, 
        user_id: int,
        file_path: str
    ) -> str:
        """
        Genera una URL de descarga con expiración estándar (24 horas).
        
        Args:
            document_id: ID del documento
            user_id: ID del usuario
            file_path: Ruta del archivo
            
        Returns:
            URL firmada para descarga
        """
        return self.generate_signed_url(
            document_id=document_id,
            user_id=user_id,
            file_path=file_path,
            expiration_hours=24
        )
    
    def revoke_token(self, token: str):
        """
        Revoca un token (para implementar con Redis/cache en producción).
        
        Args:
            token: Token a revocar
        """
        # TODO: Implementar lista de tokens revocados en Redis/Memcached
        # Por ahora solo log
        logger.info(f"Token marcado para revocación: {token[:20]}...")

# Instancia global del servicio
signed_url_service = SignedURLService()
