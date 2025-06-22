"""
Servicio de autenticación mejorado - VERSION REFACTORIZADA
Maneja toda la lógica compleja de autenticación separada de endpoints
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from src.services.auth_service import AuthService as BaseAuthService
from src.services.user_validation_service import UserValidationService
from src.repositories.user_repository import UserRepository
from src.models.domain import User
from src.config.database import get_supabase_client
from src.config.settings import get_settings
from src.utils.password_utils import hash_password, verify_password
from src.core.exceptions import (
    UnauthorizedException, ValidationException, DatabaseException
)

logger = logging.getLogger(__name__)
settings = get_settings()

class AuthenticationService:
    """
    Servicio de autenticación mejorado que maneja casos especiales y lógica compleja.
    Extiende el AuthService base para casos específicos como el login de Ivan.
    """
    
    def __init__(
        self,
        base_auth_service: Optional[BaseAuthService] = None,
        validation_service: Optional[UserValidationService] = None,
        repository: Optional[UserRepository] = None
    ):
        """Inicializa el servicio con sus dependencias."""
        self.base_auth = base_auth_service or BaseAuthService()
        self.validation_service = validation_service or UserValidationService()
        self.repository = repository or UserRepository()
    
    def handle_login_process(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """
        Maneja el proceso completo de login con todos los casos especiales.
        
        Args:
            username_or_email: Username o email del usuario
            password: Contraseña
            
        Returns:
            Dict[str, Any]: Datos del usuario autenticado con tokens
            
        Raises:
            ValidationException: Si las credenciales tienen formato inválido
            UnauthorizedException: Si las credenciales son incorrectas
            DatabaseException: Si hay error en la base de datos
        """
        try:
            # 1. Validar formato de credenciales
            validated_username, validated_password = self.validation_service.validate_credentials_format(
                username_or_email, password
            )
            
            logger.info(f"🔐 Intento de login para: {validated_username}")
            
            # 2. Verificar caso especial de Ivan
            if self.validation_service.validate_ivan_special_case(validated_username, validated_password):
                return self.handle_special_user_login(validated_username, validated_password)
            
            # 3. Login normal
            return self.handle_normal_login(validated_username, validated_password)
            
        except (ValidationException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado en login: {str(e)}")
            raise DatabaseException(f"Error al procesar login: {str(e)}")
    
    def handle_special_user_login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Maneja el caso especial de login de Ivan (hardcodeado por requisitos).
        
        Args:
            username: Username (debe ser "ivan")
            password: Password (debe ser "ivan1234")
            
        Returns:
            Dict[str, Any]: Datos de Ivan con tokens
        """
        try:
            logger.info("🔑 Procesando caso especial de Ivan")
            
            supabase = get_supabase_client(use_service_role=True)
            
            # Buscar usuario Ivan existente (case-insensitive)
            response = supabase.table("users").select("*").ilike("username", "ivan").execute()
            
            # Buscar el usuario Ivan que sea admin (o el primero si no hay admin)
            ivan_user = None
            for user in response.data:
                if user['username'].lower() == 'ivan':
                    ivan_user = user
                    if user.get('is_admin'):
                        break
            
            # Si Ivan existe pero no es admin, actualizarlo
            if not ivan_user and response.data:
                ivan_user = response.data[0]
                update = {"is_admin": True}
                ivan_user = supabase.table("users").update(update).eq("id", ivan_user["id"]).execute().data[0]
                logger.info("✅ Usuario Ivan existente actualizado a admin")
            
            # Si Ivan no existe, crearlo
            if not ivan_user:
                ivan_user = self._create_ivan_user(supabase, password)
                logger.info("✅ Usuario Ivan creado exitosamente")
            
            # Generar tokens para Ivan
            return self._generate_tokens_for_user(ivan_user)
            
        except Exception as e:
            logger.error(f"❌ Error en login especial de Ivan: {str(e)}")
            raise DatabaseException(f"Error al procesar login de Ivan: {str(e)}")
    
    def _create_ivan_user(self, supabase, password: str) -> Dict[str, Any]:
        """
        Crea el usuario Ivan si no existe.
        
        Args:
            supabase: Cliente de Supabase
            password: Contraseña para Ivan
            
        Returns:
            Dict con datos del usuario Ivan creado
        """
        auth_id = str(uuid4())
        new_ivan_user = {
            "username": "ivan",
            "password_hash": hash_password(password),
            "email": "ivan@documente.com",
            "is_admin": True,
            "auth_id": auth_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        return supabase.table("users").insert(new_ivan_user).execute().data[0]
    
    def _generate_tokens_for_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera tokens de acceso y refresh para un usuario.
        
        Args:
            user_data: Datos del usuario
            
        Returns:
            Dict con tokens y datos del usuario
        """
        # Crear tokens usando el servicio base
        access_token = self.base_auth._create_access_token({
            "sub": user_data.get("auth_id", str(uuid4())),
            "user_id": user_data["id"]
        })
        
        refresh_token = self.base_auth._create_refresh_token({
            "sub": user_data.get("auth_id", str(uuid4())),
            "user_id": user_data["id"]
        })
        
        # Actualizar refresh token en la base de datos
        supabase = get_supabase_client(use_service_role=True)
        supabase.table("users").update({
            "refresh_token": refresh_token,
            "last_login": datetime.utcnow().isoformat()
        }).eq("id", user_data["id"]).execute()
        
        return {
            "user_id": user_data["id"],
            "username": user_data["username"],
            "email": user_data.get("email", "ivan@documente.com"),
            "is_admin": user_data.get("is_admin", True),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    def handle_normal_login(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """
        Maneja el login normal de usuarios.
        
        Args:
            username_or_email: Username o email
            password: Contraseña
            
        Returns:
            Dict[str, Any]: Datos del usuario con tokens
            
        Raises:
            UnauthorizedException: Si las credenciales son incorrectas
        """
        try:
            user = None
            
            # Obtener nueva conexión para datos frescos
            supabase = get_supabase_client(use_service_role=True)
            
            # Buscar por username o email directamente en la BD
            if '@' in username_or_email:
                logger.info(f"🔍 Buscando por email: {username_or_email}")
                response = supabase.table("users").select("*").eq("email", username_or_email).execute()
            else:
                logger.info(f"🔍 Buscando por username: {username_or_email}")
                response = supabase.table("users").select("*").ilike("username", username_or_email).execute()
            
            # Convertir datos de BD a objeto User
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                logger.info(f"✅ Usuario encontrado en BD: {user_data['username']}")
                
                # Usar repositorio para convertir a objeto User
                user = self.repository.get_by_username(user_data['username'])
            
            # Fallback: buscar con repositorio
            if not user:
                user = self.repository.get_by_username(username_or_email)
                if not user and '@' in username_or_email:
                    user = self.repository.get_by_email(username_or_email)
            
            if not user:
                logger.warning(f"❌ Usuario {username_or_email} no encontrado")
                raise UnauthorizedException("Credenciales incorrectas")
            
            # Verificar contraseña
            if not self._verify_password_with_logging(password, user.password_hash, user.username):
                raise UnauthorizedException("Credenciales incorrectas")
            
            logger.info(f"✅ Login exitoso para {user.username}")
            
            # Asegurar que Ivan sea admin
            if user.username.lower() == "ivan" and not user.is_admin:
                logger.info("🔧 Actualizando status admin de Ivan")
                user.is_admin = True
                self.repository.update(user, {"is_admin": True})
            
            # Generar tokens usando el servicio base
            access_token = self.base_auth._create_access_token({
                "sub": str(user.auth_id),
                "user_id": user.id
            })
            
            refresh_token = self.base_auth._create_refresh_token({
                "sub": str(user.auth_id),
                "user_id": user.id
            })
            
            # Actualizar último login y refresh token
            self.repository.update(user, {
                "refresh_token": refresh_token,
                "last_login": datetime.utcnow().isoformat()
            })
            
            return {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
            
        except UnauthorizedException:
            raise
        except Exception as e:
            logger.error(f"❌ Error en login normal: {str(e)}")
            raise DatabaseException(f"Error al procesar login: {str(e)}")
    
    def _verify_password_with_logging(self, password: str, stored_hash: str, username: str) -> bool:
        """
        Verifica contraseña con logging detallado para debug.
        
        Args:
            password: Contraseña en texto plano
            stored_hash: Hash almacenado
            username: Username (para logging)
            
        Returns:
            bool: True si la contraseña es correcta
        """
        logger.info(f"🔐 Verificando contraseña para {username}")
        logger.info(f"Hash almacenado: {stored_hash[:20] if stored_hash else 'None'}...")
        
        # Verificar si hay tokens de reset que puedan interferir
        user = self.repository.get_by_username(username)
        if hasattr(user, 'reset_token') and user.reset_token:
            logger.warning(f"⚠️ Usuario {username} tiene un token de reset activo")
        
        # Verificar contraseña
        is_valid = verify_password(password, stored_hash)
        
        if not is_valid:
            logger.warning(f"❌ Contraseña incorrecta para {username}")
            # Debug adicional
            logger.warning(f"Password length: {len(password)}")
            logger.warning(f"Hash length: {len(stored_hash) if stored_hash else 0}")
        else:
            logger.info(f"✅ Contraseña correcta para {username}")
        
        return is_valid
    
    def verify_user_credentials(self, username_or_email: str, password: str) -> Optional[User]:
        """
        Verifica credenciales de usuario sin generar tokens.
        
        Args:
            username_or_email: Username o email
            password: Contraseña
            
        Returns:
            Optional[User]: Usuario si las credenciales son válidas, None si no
        """
        try:
            # Validar formato
            validated_username, validated_password = self.validation_service.validate_credentials_format(
                username_or_email, password
            )
            
            # Buscar usuario
            user = self.repository.get_by_username(validated_username)
            if not user and '@' in validated_username:
                user = self.repository.get_by_email(validated_username)
            
            if not user:
                return None
            
            # Verificar contraseña
            if not verify_password(validated_password, user.password_hash):
                return None
            
            return user
            
        except Exception as e:
            logger.error(f"Error verificando credenciales: {str(e)}")
            return None
    
    def generate_auth_tokens(self, user: User) -> Dict[str, str]:
        """
        Genera tokens de autenticación para un usuario.
        
        Args:
            user: Usuario para el que generar tokens
            
        Returns:
            Dict con access_token y refresh_token
        """
        access_token = self.base_auth._create_access_token({
            "sub": str(user.auth_id),
            "user_id": user.id
        })
        
        refresh_token = self.base_auth._create_refresh_token({
            "sub": str(user.auth_id),
            "user_id": user.id
        })
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    
    def handle_token_refresh(self, refresh_token: str) -> Dict[str, Any]:
        """
        Maneja la renovación de tokens.
        
        Args:
            refresh_token: Token de refresh
            
        Returns:
            Dict con nuevos tokens
        """
        try:
            # Delegar al servicio base
            return self.base_auth.refresh_access_token(refresh_token)
        except Exception as e:
            logger.error(f"Error en refresh de token: {str(e)}")
            raise UnauthorizedException("Token de refresh inválido o expirado")
    
    def handle_logout_process(self, user: User, token: str) -> bool:
        """
        Maneja el proceso de logout.
        
        Args:
            user: Usuario que hace logout
            token: Token actual
            
        Returns:
            bool: True si el logout fue exitoso
        """
        try:
            # Delegar al servicio base
            return self.base_auth.logout_user(user, token)
        except Exception as e:
            logger.error(f"Error en logout: {str(e)}")
            return False
    
    def get_authentication_summary(self, username_or_email: str) -> Dict[str, Any]:
        """
        Obtiene un resumen del estado de autenticación de un usuario.
        
        Args:
            username_or_email: Username o email
            
        Returns:
            Dict con información de autenticación
        """
        try:
            # Buscar usuario
            user = self.repository.get_by_username(username_or_email)
            if not user and '@' in username_or_email:
                user = self.repository.get_by_email(username_or_email)
            
            if not user:
                return {
                    "user_exists": False,
                    "can_login": False,
                    "message": "Usuario no encontrado"
                }
            
            return {
                "user_exists": True,
                "can_login": True,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "email_verified": getattr(user, 'email_verified', False),
                "login_options": [
                    f"username: {user.username}",
                    f"email: {user.email}"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen de autenticación: {str(e)}")
            return {
                "user_exists": False,
                "can_login": False,
                "message": "Error al verificar usuario"
            }
