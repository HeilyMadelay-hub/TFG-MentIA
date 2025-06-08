"""
Dependencias para la API.
Este módulo contiene las dependencias utilizadas en los endpoints de documentos.
"""
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime
from typing import Optional
from src.models.schemas.user import UserResponse
from src.models.domain import User
from src.services.document_service import DocumentService
from src.services.user_service import UserService
from src.services.statistics_service import StatisticsService
from src.config.settings import get_settings
from uuid import uuid4
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

# Restaura la definición de OAuth2PasswordBearer (está comentada en tu código)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login", auto_error=False)
settings = get_settings()

# Instancias de servicios
document_service = DocumentService()
user_service = UserService()
statistics_service = StatisticsService()

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

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), 
    token_query: Optional[str] = Query(None, alias="token")
) -> UserResponse:
    """
    Valida el token JWT y devuelve el usuario autenticado.
    Acepta token tanto del encabezado Authorization como del parámetro de consulta 'token'.
    """
    
    # Usar token del parámetro de consulta si está disponible y no hay token en el encabezado
    actual_token = token_query or token
    
    logger.info(f"Token recibido: {actual_token[:10] if actual_token else 'No token'}...")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado o token inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
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
            
        # Buscar el usuario por auth_id
        user = user_service.get_user_by_auth_id(UUID(auth_id))
        if not user:
            # Intentar buscar por ID como alternativa
            user = user_service.get_user(user_id)
            
        if not user:
            logger.error(f"Usuario con auth_id {auth_id} / user_id {user_id} no encontrado")
            raise credentials_exception
            
        # Asegurarse de que Ivan sea siempre admin
        if user.username and user.username.lower() == "ivan" and not user.is_admin:
            logger.info(f"Usuario {user.username} es Ivan pero no tiene flag admin=True. Actualizando...")
            user.is_admin = True
            # Actualizar usando el servicio, no el repositorio directamente
            from src.services.user_service import UserService
            user_service_instance = UserService()
            user_service_instance.update_user(user.id, {"is_admin": True})
            
            logger.info(f"Usuario encontrado: {user.username}, Admin: {user.is_admin}")
            
        # Convertir el modelo domain User a UserResponse para la API
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_admin=user.is_admin,
            auth_id=user.auth_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
            email_encrypted=user.email_encrypted
        )
        
    except JWTError as jwt_error:
        logger.error(f"Error JWT al validar token: {str(jwt_error)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Error inesperado al validar token: {str(e)}")
        raise credentials_exception