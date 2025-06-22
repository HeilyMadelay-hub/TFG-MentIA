from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from uuid import uuid4, UUID
from jose import jwt, JWTError
import logging
from functools import lru_cache
from src.utils.password_utils import hash_password, verify_password
from src.utils.admin_utils import ensure_admin_status, has_admin_privileges
from src.utils.email_validator import EmailValidator, validate_email_registration
from src.models.domain import User
from src.models.schemas.user import UserCreate
from src.repositories.user_repository import UserRepository
from src.core.exceptions import ConflictException, ValidationException, UnauthorizedException
from src.config import settings
from src.config.database import get_supabase_client
import secrets
import hashlib
from src.services.token_blacklist_service import token_blacklist

# Configuración de logging
logger = logging.getLogger(__name__)

class AuthService:
    """
    Servicio que implementa la lógica de autenticación de usuarios con soporte completo de refresh tokens.
    """
    
    def __init__(self, repository=None):
        """Inicializa el servicio con el repositorio de usuarios."""
        self.repository = repository or UserRepository()
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
        self.refresh_token_rotate = settings.REFRESH_TOKEN_ROTATE
    

    def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """
        Registra un nuevo usuario.
        
        Args:
            username: Nombre de usuario
            email: Correo electrónico
            password: Contraseña
            
        Returns:
            Dict[str, Any]: Datos del usuario registrado y tokens
            
        Raises:
            ConflictException: Si el usuario ya existe
            ValidationException: Si los datos no son válidos
        """
        # Validaciones de username
        if not username or len(username.strip()) == 0:
            raise ValidationException("El nombre de usuario no puede estar vacío")
            
        username = username.strip().lower()
        
        # Verificar longitud
        if len(username) < 3:
            raise ValidationException("El nombre de usuario debe tener al menos 3 caracteres")
            
        if len(username) > 20:
            raise ValidationException("El nombre de usuario no puede tener más de 20 caracteres")
        
        # Verificar caracteres válidos
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValidationException("El nombre de usuario solo puede contener letras, números, guiones y guiones bajos")
        
        # Verificar que no empiece con números o caracteres especiales
        if username[0] in '0123456789_-':
            raise ValidationException("El nombre de usuario debe empezar con una letra")
        
        # Verificar que el username no sea similar a "Ivan"
        if username.lower() == "ivan" or username.lower().startswith("ivan"):
            raise ValidationException("No se permite registrar usuarios con nombres similares a 'Ivan'")
        
        # Lista de nombres reservados
        reserved_names = ['admin', 'root', 'system', 'user', 'test', 'demo', 'api']
        if username.lower() in reserved_names:
            raise ValidationException(f"El nombre '{username}' está reservado. Por favor, elige otro.")
        
        # Verificar que el usuario no exista
        existing_user = self.repository.get_by_username(username)
        if existing_user:
            raise ConflictException(f"El nombre de usuario '{username}' ya está registrado")
        
        # Validar formato y reglas del email
        if email:
            # Obtener todos los emails existentes para validación
            supabase = get_supabase_client(use_service_role=True)
            all_users = supabase.table("users").select("email").execute()
            existing_emails = [u['email'] for u in all_users.data if u.get('email')]
            
            # Validar email con todas las reglas
            is_valid, error = validate_email_registration(email, existing_emails)
            if not is_valid:
                raise ValidationException(error)
            
            # Verificación adicional: mismo usuario con diferente dominio
            email_validator = EmailValidator()
            username_part, domain = email_validator.extract_email_parts(email)
            
            # Buscar emails con el mismo username pero diferente dominio
            for existing_email in existing_emails:
                existing_username, existing_domain = email_validator.extract_email_parts(existing_email)
                if username_part.lower() == existing_username.lower() and domain != existing_domain:
                    raise ConflictException(
                        f"Ya existe una cuenta con el email {existing_email}. "
                        f"No se permite crear múltiples cuentas con el mismo nombre de email."
                    )
            
            # Verificar que el email exacto no esté en uso
            existing_user = self.repository.get_by_email(email)
            if existing_user:
                raise ConflictException(f"Email '{email}' ya está en uso")
        
        # Crear el usuario
        auth_id = uuid4()
        user_data = UserCreate(
            username=username,
            email=email,
            password=password,
            auth_id=auth_id
        )
        
        user = self.repository.create_user(user_data)
        
        # Generar tokens
        access_token = self._create_access_token({
            "sub": str(user.auth_id),
            "user_id": user.id
        })
        
        refresh_token = self._create_refresh_token({
            "sub": str(user.auth_id),
            "user_id": user.id
        })
        
        # Guardar refresh token en la base de datos
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
            "token_type": "bearer"
        }

    def _get_password_hash(self, password: str) -> str:
        """Genera un hash de la contraseña."""
        return hash_password(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica si la contraseña coincide con el hash."""
        from src.utils.password_utils import verify_password
        return verify_password(plain_password, hashed_password)

    def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """Autentica a un usuario y genera tokens."""
        if not username or not password:
            raise ValidationException("Usuario y contraseña son obligatorios")
            
        # Buscar usuario por username (case insensitive)
        user = self.repository.get_by_username(username)
        
        if not user or not self._verify_password(password, user.password_hash):
            # Usar un tiempo constante para prevenir timing attacks
            self._verify_password("dummy_password", "$2b$12$dummyhashfordummypassword")
            raise UnauthorizedException("Credenciales incorrectas")
        
        if ensure_admin_status(user) and not user.is_admin:
            user.is_admin = True
            self.repository.update(user, {"is_admin": True})
        
        # Generar tokens
        access_token = self._create_access_token(
            data={"sub": str(user.auth_id), "user_id": user.id}
        )
        
        refresh_token = self._create_refresh_token(
            data={"sub": str(user.auth_id), "user_id": user.id}
        )
        
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
            "token_type": "bearer"
        }
    
    def get_current_user(self, token: str) -> User:
        """Obtiene el usuario actual a partir del token."""
        if not token:
            raise UnauthorizedException("No se proporcionó token de autenticación")
        
        # Verificar si el token está revocado
        if self._is_token_revoked(token):
            raise UnauthorizedException("Token revocado")
            
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Verificar que es un access token (no refresh)
            if payload.get("type") == "refresh":
                raise UnauthorizedException("No se puede usar un refresh token como access token")
            
            auth_id = payload.get("sub")
            user_id = payload.get("user_id")
            
            if auth_id is None or user_id is None:
                raise UnauthorizedException("Token inválido: falta identificador de usuario")
            
            # Buscar por user_id directamente
            user = self.repository.get(user_id)
            
            if user is None:
                raise UnauthorizedException("Usuario no encontrado")

            if ensure_admin_status(user) and not user.is_admin:
                user.is_admin = True
                self.repository.update(user, {"is_admin": True})
                
            return user
            
        except JWTError as e:
            raise UnauthorizedException(f"Token inválido: {str(e)}")
        except Exception as e:
            logger.error(f"Error al validar token: {str(e)}")
            raise UnauthorizedException("Error en la validación del token")
    
    def _create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Crea un token JWT de acceso."""
        to_encode = data.copy()
        
        # Establecer tiempo de expiración
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
            
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),  # Tiempo de emisión
            "iss": "chatbot-backend",   # Emisor del token
            "type": "access",          # Tipo de token
            "jti": str(uuid4())        # ID único del token
        })
        
        # Generar token
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error al generar token: {str(e)}")
            raise ValidationException("No se pudo generar el token de autenticación")
    
    def _create_refresh_token(self, data: Dict[str, Any]) -> str:
        """
        Crea un refresh token con mayor duración que el access token.
        
        Args:
            data: Datos a incluir en el token
            
        Returns:
            str: Refresh token JWT
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": "chatbot-backend",
            "type": "refresh",         # Identificar como refresh token
            "jti": str(uuid4()),       # ID único del token
            # Agregar un hash único para mayor seguridad
            "token_hash": hashlib.sha256(secrets.token_bytes(32)).hexdigest()
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error al generar refresh token: {str(e)}")
            raise ValidationException("No se pudo generar el refresh token")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Genera un nuevo access token usando un refresh token válido.
        
        Args:
            refresh_token: Token de actualización
            
        Returns:
            Dict[str, Any]: Nuevo access token y opcionalmente nuevo refresh token
            
        Raises:
            UnauthorizedException: Si el refresh token es inválido
        """
        if not refresh_token:
            raise UnauthorizedException("No se proporcionó refresh token")
        
        # Verificar si el token está revocado
        if self._is_token_revoked(refresh_token):
            raise UnauthorizedException("Refresh token revocado")
        
        try:
            # Decodificar y verificar refresh token
            payload = jwt.decode(
                refresh_token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Verificar que es un refresh token
            if payload.get("type") != "refresh":
                raise UnauthorizedException("Token inválido: no es un refresh token")
            
            user_id = payload.get("user_id")
            if not user_id:
                raise UnauthorizedException("Token inválido: falta user_id")
            
            # Buscar usuario
            user = self.repository.get(user_id)
            if not user:
                raise UnauthorizedException("Usuario no encontrado")
            
            # Verificar que el refresh token coincide con el almacenado
            if user.refresh_token != refresh_token:
                logger.warning(f"Intento de uso de refresh token no válido para usuario {user_id}")
                raise UnauthorizedException("Refresh token no válido")
            
            # Generar nuevo access token
            new_access_token = self._create_access_token({
                "sub": str(user.auth_id),
                "user_id": user.id
            })
            
            response = {
                "access_token": new_access_token,
                "token_type": "bearer"
            }
            
            # Si está habilitada la rotación de tokens, generar nuevo refresh token
            if self.refresh_token_rotate:
                # Revocar el refresh token anterior
                self._revoke_token(refresh_token)
                
                # Generar nuevo refresh token
                new_refresh_token = self._create_refresh_token({
                    "sub": str(user.auth_id),
                    "user_id": user.id
                })
                
                # Actualizar en la base de datos
                self.repository.update(user, {
                    "refresh_token": new_refresh_token
                })
                
                response["refresh_token"] = new_refresh_token
                
                logger.info(f"Refresh token rotado para usuario {user.username}")
            
            return response
            
        except JWTError as e:
            logger.error(f"Error al validar refresh token: {str(e)}")
            raise UnauthorizedException("Refresh token inválido o expirado")
        except Exception as e:
            logger.error(f"Error en refresh_access_token: {str(e)}")
            raise UnauthorizedException("Error al actualizar token")
    
    def logout_user(self, user: User, token: str) -> bool:
        """
        Invalida los tokens del usuario (logout).
        
        Args:
            user: Usuario que hace logout
            token: Access token actual a revocar
            
        Returns:
            bool: True si el logout fue exitoso
        """
        try:
            # Revocar el access token actual
            if token:
                self._revoke_token(token)
            
            # Revocar el refresh token del usuario
            if user.refresh_token:
                self._revoke_token(user.refresh_token)
            
            # Limpiar refresh token de la base de datos
            self.repository.update(user, {
                "refresh_token": None
            })
            
            logger.info(f"Usuario {user.username} cerró sesión exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error en logout: {str(e)}")
            return False
    
    def _revoke_token(self, token: str) -> None:
        """
        Agrega un token a la lista de revocados.
        """
        if token:
            try:
                payload = jwt.decode(
                    token, 
                    self.secret_key, 
                    algorithms=[self.algorithm],
                    options={"verify_exp": False}
                )
                jti = payload.get("jti")
                exp = payload.get("exp")
                
                if jti and exp:
                    expiry_time = datetime.fromtimestamp(exp)
                    token_blacklist.add_token(jti, expiry_time)
                    logger.info(f"Token {jti} agregado a blacklist")
            except Exception as e:
                logger.warning(f"No se pudo decodificar token para revocar: {str(e)}")
    
    def _is_token_revoked(self, token: str) -> bool:
        """
        Verifica si un token está revocado.
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            jti = payload.get("jti")
            
            if jti:
                return token_blacklist.is_revoked(jti)
            
            return False
            
        except Exception:
            # Si hay error al decodificar, considerar el token como inválido
            return True
    
    def revoke_all_user_tokens(self, user_id: int) -> bool:
        """
        Revoca todos los tokens de un usuario.
        Útil para cerrar todas las sesiones cuando se cambia la contraseña.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            bool: True si se revocaron los tokens exitosamente
        """
        try:
            user = self.repository.get(user_id)
            if user:
                # Revocar refresh token actual si existe
                if user.refresh_token:
                    self._revoke_token(user.refresh_token)
                
                # Limpiar refresh token de la base de datos
                self.repository.update(user, {
                    "refresh_token": None
                })
                
                logger.info(f"Todos los tokens del usuario {user_id} fueron revocados")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error al revocar tokens del usuario {user_id}: {str(e)}")
            return False
    
    def validate_refresh_token(self, refresh_token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Valida un refresh token sin generar uno nuevo.
        
        Args:
            refresh_token: Token a validar
            
        Returns:
            Tuple[bool, Optional[Dict]]: (es_válido, payload_del_token)
        """
        try:
            if self._is_token_revoked(refresh_token):
                return False, None
            
            payload = jwt.decode(
                refresh_token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            if payload.get("type") != "refresh":
                return False, None
            
            return True, payload
            
        except JWTError:
            return False, None
