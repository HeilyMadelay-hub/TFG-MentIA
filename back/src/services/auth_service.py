from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import uuid4, UUID
from jose import jwt, JWTError
import logging
from functools import lru_cache
from src.utils.password_utils import hash_password, verify_password
from src.utils.admin_utils import ensure_admin_status, has_admin_privileges
from src.models.domain import User
from src.models.schemas.user import UserCreate
from src.repositories.user_repository import UserRepository
from src.core.exceptions import ConflictException, ValidationException, UnauthorizedException
from src.config import settings

# Configuración de logging
logger = logging.getLogger(__name__)

class AuthService:
    """
    Servicio que implementa la lógica de autenticación de usuarios.
    """
    
    def __init__(self, repository=None):
        """Inicializa el servicio con el repositorio de usuarios."""
        self.repository = repository or UserRepository()
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    

    def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """
        Registra un nuevo usuario.
        
        Args:
            username: Nombre de usuario
            email: Correo electrónico
            password: Contraseña
            
        Returns:
            Dict[str, Any]: Datos del usuario registrado y token
            
        Raises:
            ConflictException: Si el usuario ya existe
            ValidationException: Si los datos no son válidos
        """
        # Verificar que el username no sea similar a "Ivan"
        if username.lower() == "ivan" or username.lower().startswith("ivan"):
            raise ValidationException("No se permite registrar usuarios con nombres similares a 'Ivan'")
        
        # Verificar que el usuario no exista
        existing_user = self.repository.get_by_username(username)
        if existing_user:
            raise ConflictException(f"Usuario con username '{username}' ya existe")
        
        # Verificar que el email no esté en uso
        if email:
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
        
        # Generar token
        token = self._create_access_token({
            "sub": str(user.auth_id),
            "user_id": user.id
        })
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "access_token": token,
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
        """Autentica a un usuario y genera un token."""
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
            self.repository.update(user)
        
        # Generar token de acceso
        access_token = self._create_access_token(
            data={"sub": str(user.auth_id), "user_id": user.id}
        )
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    def get_current_user(self, token: str) -> User:
        """Obtiene el usuario actual a partir del token."""
        if not token:
            raise UnauthorizedException("No se proporcionó token de autenticación")
            
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            auth_id = payload.get("sub")
            
            if auth_id is None:
                raise UnauthorizedException("Token inválido: falta identificador de usuario")
            
            user = self.repository.get_by_auth_id(UUID(auth_id))
            
            if user is None:
                raise UnauthorizedException("Usuario no encontrado")

            if ensure_admin_status(user) and not user.is_admin:
                user.is_admin = True
                self.repository.update(user)
                
            return user
            
        except JWTError as e:
            raise UnauthorizedException(f"Token inválido: {str(e)}")
        except Exception as e:
            logger.error(f"Error al validar token: {str(e)}")
            raise UnauthorizedException("Error en la validación del token")
    
    def _create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Crea un token JWT."""
        to_encode = data.copy()
        
        # Establecer tiempo de expiración
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
            
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),  # Tiempo de emisión
            "iss": "fastapi-app"       # Emisor del token
        })
        
        # Generar token
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error al generar token: {str(e)}")
            raise ValidationException("No se pudo generar el token de autenticación")
    
    # ==================== MÉTODOS ADICIONALES ====================
    
    def logout_user(self, token: str) -> bool:
        """
        Invalida el token del usuario (logout).
        
        Args:
            token: Token a invalidar
            
        Returns:
            bool: True si el logout fue exitoso
            
        Note:
            En una implementación real, esto agregaría el token a una lista negra
            o usaría Redis para mantener tokens revocados.
        """
        pass  # TODO: Implementar
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Genera un nuevo access token usando un refresh token válido.
        
        Args:
            refresh_token: Token de actualización
            
        Returns:
            Dict[str, Any]: Nuevo access token y refresh token
            
        Raises:
            UnauthorizedException: Si el refresh token es inválido
        """
        pass  # TODO: Implementar
    
    def _create_refresh_token(self, data: Dict[str, Any]) -> str:
        """
        Crea un refresh token con mayor duración que el access token.
        
        Args:
            data: Datos a incluir en el token
            
        Returns:
            str: Refresh token JWT
        """
        # Por ahora, crear un refresh token similar al access token pero con más duración
        # En producción, esto debería tener una lógica diferente
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)  # 7 días de duración
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": "fastapi-app",
            "type": "refresh"  # Identificar como refresh token
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error al generar refresh token: {str(e)}")
            # En caso de error, devolver un token vacío temporal
            return "temporary_refresh_token"
    
    def _verify_refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Verifica y decodifica un refresh token.
        
        Args:
            refresh_token: Token a verificar
            
        Returns:
            Dict[str, Any]: Payload del token
            
        Raises:
            UnauthorizedException: Si el token es inválido
        """
        pass  # TODO: Implementar