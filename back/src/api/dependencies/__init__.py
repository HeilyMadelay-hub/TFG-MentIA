"""
Dependencias para la API.
Este módulo contiene las dependencias utilizadas en los endpoints de documentos.
"""
from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime
from typing import Optional
from src.models.schemas.user import UserResponse
from src.models.domain import User  # Import agregado
from src.services.document_service import DocumentService
from src.services.user_service import UserService
from src.services.statistics_service import StatisticsService
from src.services.statistics_validation_service import StatisticsValidationService
from src.services.chat_service import ChatService
from src.api.helpers.statistics_helpers import StatisticsHelpers
from src.config.settings import get_settings
from src.core.exceptions import UnauthorizedException
from uuid import uuid4, UUID
import logging

logger = logging.getLogger(__name__)

# OAuth2PasswordBearer para autenticación
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login", auto_error=False)
settings = get_settings()

# Instancias de servicios
document_service = DocumentService()
user_service = UserService()
statistics_service = StatisticsService()
statistics_validation_service = StatisticsValidationService()
statistics_helpers = StatisticsHelpers()
chat_service = ChatService()

def get_document_service() -> DocumentService:
    """
    Retorna una instancia del servicio de documentos.
    
    Returns:
        DocumentService: Servicio para operaciones con documentos
    """
    return document_service

def get_statistics_service() -> StatisticsService:
    """
    Retorna una instancia del servicio de estadísticas.
    
    Returns:
        StatisticsService: Servicio para operaciones con estadísticas
    """
    return statistics_service

def get_user_service() -> UserService:
    """
    Retorna una instancia del servicio de usuarios.
    
    Returns:
        UserService: Servicio para operaciones con usuarios
    """
    return user_service

def get_chat_service() -> ChatService:
    """
    Retorna una instancia del servicio de chats.
    
    Returns:
        ChatService: Servicio para operaciones con chats
    """
    return chat_service

def get_statistics_validation_service() -> StatisticsValidationService:
    """
    Retorna una instancia del servicio de validación de estadísticas.
    
    Returns:
        StatisticsValidationService: Servicio para validaciones de estadísticas
    """
    return statistics_validation_service

def get_statistics_helpers() -> StatisticsHelpers:
    """
    Retorna una instancia de los helpers de estadísticas.
    
    Returns:
        StatisticsHelpers: Helpers para operaciones complejas de estadísticas
    """
    return statistics_helpers

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), 
    token_query: Optional[str] = Query(None, alias="token")
) -> User:
    """
    Valida el token JWT y devuelve el usuario autenticado.
    Acepta token tanto del encabezado Authorization como del parámetro de consulta 'token'.
    """
    
    # Usar token del parámetro de consulta si está disponible y no hay token en el encabezado
    actual_token = token_query or token
    
    logger.info(f"Token recibido: {actual_token[:10] if actual_token else 'No token'}...")
    
    credentials_exception = UnauthorizedException("No autenticado o token inválido")
    
    if not actual_token:
        logger.error("No se proporcionó token")
        raise credentials_exception
    
    try:
        # Decodificar el token JWT
        payload = jwt.decode(
            actual_token, 
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        auth_id = payload.get("sub")
        user_id = payload.get("user_id")
        
        logger.info(f"Token decodificado correctamente. User ID: {user_id}")
        
        if not auth_id or not user_id:
            logger.error("Token no contiene auth_id o user_id")
            raise credentials_exception
            
        # Buscar el usuario por ID directamente
        user = user_service.get_user(user_id)
            
        if not user:
            logger.error(f"Usuario con user_id {user_id} no encontrado")
            raise credentials_exception
            
        # Asegurarse de que Ivan sea siempre admin
        if user.username.lower() == "ivan" and not user.is_admin:
            logger.info(f"Usuario {user.username} es Ivan pero no tiene flag admin=True. Actualizando...")
            user.is_admin = True
            user_service.repository.update(user, {"is_admin": True})
            
        logger.info(f"Usuario encontrado: {user.username}, Admin: {user.is_admin}")
        
        return user
        
    except JWTError as jwt_error:
        logger.error(f"Error JWT al validar token: {str(jwt_error)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Error inesperado al validar token: {str(e)}")
        raise credentials_exception

def verify_token(token: str) -> dict:
    """
    Verifica un token JWT y devuelve el payload.
    
    Args:
        token: Token JWT a verificar
        
    Returns:
        dict: Payload del token
        
    Raises:
        Exception: Si el token es inválido
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise Exception(f"Token inválido: {str(e)}")

def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme), 
    token_query: Optional[str] = Query(None, alias="token")
) -> Optional[User]:
    """
    Igual que get_current_user pero no lanza excepción si no hay token.
    Retorna None si no hay usuario autenticado.
    """
    # Usar token del parámetro de consulta si está disponible y no hay token en el encabezado
    actual_token = token_query or token
    
    if not actual_token:
        return None
    
    try:
        # Decodificar el token JWT
        payload = jwt.decode(
            actual_token, 
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        auth_id = payload.get("sub")
        user_id = payload.get("user_id")
        
        if not auth_id or not user_id:
            return None
            
        # Buscar el usuario por ID directamente
        user = user_service.get_user(user_id)
            
        if not user:
            return None
            
        # Asegurarse de que Ivan sea siempre admin
        if user.username.lower() == "ivan" and not user.is_admin:
            user.is_admin = True
            user_service.repository.update(user, {"is_admin": True})
            
        return user
        
    except:
        return None
