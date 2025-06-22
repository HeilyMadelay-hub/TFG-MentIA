"""
Módulo de autenticación y manejo de tokens JWT
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext
from src.models.domain import User
from src.repositories.user_repository import UserRepository
from src.services.token_blacklist_service import token_blacklist

logger = logging.getLogger(__name__)

# Configuración
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Contexto de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Inicializar servicios
user_repository = UserRepository()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera hash de una contraseña"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token de acceso JWT con JTI único para blacklist"""
    to_encode = data.copy()
    # Agregar JTI único para blacklist
    to_encode["jti"] = str(uuid.uuid4())
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Crea un token de refresh JWT con JTI único"""
    to_encode = data.copy()
    # Agregar JTI único para blacklist
    to_encode["jti"] = str(uuid.uuid4())
    
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[User]:
    """
    Verifica un token JWT y retorna el usuario si es válido
    
    Args:
        token: Token JWT
        
    Returns:
        Usuario si el token es válido, None en caso contrario
    """
    try:
        # Decodificar token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Usar user_id del payload, no sub (que es el auth_id)
        user_id: int = payload.get("user_id")
        
        if user_id is None:
            return None
            
        # Verificar en blacklist usando JTI
        jti = payload.get("jti")
        if jti and token_blacklist.is_revoked(jti):
            logger.warning(f"Token con JTI {jti} está en blacklist")
            return None
            
        # Obtener usuario
        user = user_repository.get(user_id)
        return user
        
    except JWTError:
        return None
    except Exception as e:
        logger.error(f"Error verificando token: {str(e)}")
        return None


def verify_websocket_token(token: str) -> Optional[User]:
    """
    Verifica token para conexiones WebSocket
    
    Args:
        token: Token JWT
        
    Returns:
        Usuario si el token es válido, None en caso contrario
    """
    try:
        # Decodificar token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Usar user_id del payload, no sub (que es el auth_id)
        user_id: int = payload.get("user_id")
        
        if user_id is None:
            return None
            
        # Verificar en blacklist usando JTI
        jti = payload.get("jti")
        if jti and token_blacklist.is_revoked(jti):
            logger.warning(f"Token WebSocket con JTI {jti} está en blacklist")
            return None
            
        # Obtener usuario directamente del repositorio
        user = user_repository.get(user_id)
        return user
        
    except JWTError:
        return None
    except Exception as e:
        logger.error(f"Error verificando token WebSocket: {str(e)}")
        return None


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodifica un token JWT sin verificar
    
    Args:
        token: Token JWT
        
    Returns:
        Payload del token si es válido, None en caso contrario
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(token: str) -> Optional[User]:
    """
    Obtiene el usuario actual desde un token
    
    Args:
        token: Token JWT
        
    Returns:
        Usuario si el token es válido, None en caso contrario
    """
    return verify_token(token)


def authenticate_user(email: str, password: str) -> Optional[User]:
    """
    Autentica un usuario por email y contraseña
    
    Args:
        email: Email del usuario
        password: Contraseña en texto plano
        
    Returns:
        Usuario si las credenciales son válidas, None en caso contrario
    """
    user = user_repository.get_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
