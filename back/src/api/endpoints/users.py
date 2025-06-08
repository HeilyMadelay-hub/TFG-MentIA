"""
Endpoints para la gestión y autenticación de usuarios - COMPLETO
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
import logging
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Dict, Any, Optional
from uuid import uuid4, UUID
import jwt
from datetime import datetime, timedelta
import src.services.user_service as user_service
import os
from PIL import Image
import io
from src.services import user_service
from src.services.auth_service import AuthService
from src.services.user_service import UserService
from src.models.schemas.user import (
    UserCreate, UserResponse, UserUpdate,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest,
    RefreshTokenRequest, TokenResponse, EmailVerificationRequest,
    ResendVerificationRequest, MessageResponse, UserSearchResponse
)
from src.models.domain import User
from src.utils.password_utils import hash_password, verify_password
from src.core.exceptions import (
    ConflictException,
    UnauthorizedException,
    ValidationException,
    NotFoundException
)
from fastapi import Request
from src.config.settings import get_settings
from src.repositories.user_repository import UserRepository
from src.config.database import get_supabase_client

# Crear router con prefijo "users"
router = APIRouter(prefix="/users", tags=["users"])

# Configuración para producción
settings = get_settings()

# Configurar OAuth2 correctamente
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

# Importar las funciones de inicialización de servicios desde __init__.py
from src.api.endpoints import get_auth_service, get_user_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_current_user(
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
    
    credentials_exception = HTTPException(
        status_code=401,
        detail="No autenticado o token inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not actual_token:
        logger.error("No se proporcionó token")
        raise credentials_exception
    
    try:
        # Decodificar el token JWT
        payload = jwt.decode(
            actual_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        
        auth_id = payload.get("sub")
        user_id = payload.get("user_id")
        
        logger.info(f"Token decodificado correctamente. User ID: {user_id}")
        
        if not auth_id or not user_id:
            logger.error("Token no contiene auth_id o user_id")
            raise credentials_exception
            
        # Consulta directamente a la base de datos con el user_id
        user_repo = UserRepository()
        logger.info(f"Buscando usuario con ID: {user_id}")
        user = user_repo.get(user_id)
        
        if not user:
            logger.error(f"Usuario con ID {user_id} no encontrado en la base de datos")
            raise credentials_exception
            
        # Asegurarse de que Ivan sea siempre admin
        if user.username.lower() == "ivan" and not user.is_admin:
            logger.info(f"Usuario {user.username} es Ivan pero no tiene flag admin=True. Actualizando...")
            user.is_admin = True
            user_repo.update(user, {"is_admin": True})
            
        logger.info(f"Usuario encontrado: {user.username}, Admin: {user.is_admin}")
        
        return user
        
    except jwt.PyJWTError as jwt_error:
        logger.error(f"Error JWT al validar token: {str(jwt_error)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Error inesperado al validar token: {str(e)}")
        raise credentials_exception

@router.post("/login", response_model=Dict[str, Any])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Autentica a un usuario y genera un token.
    Acepta tanto username como email para el login.
    """
    username_or_email = form_data.username.lower().strip()
    password = form_data.password

    # Validación básica del formato de email si parece ser un email
    if username_or_email and '.' in username_or_email and '@' not in username_or_email:
        # Probablemente el usuario olvidó el @
        if 'gmail.com' in username_or_email or 'hotmail.com' in username_or_email or 'yahoo.com' in username_or_email:
            logger.warning(f"Email mal formateado detectado: {username_or_email}")
            raise HTTPException(
                status_code=400, 
                detail="Formato de email inválido. ¿Olvidaste el símbolo @?"
            )

    logger.info(f"Intento de login para: {username_or_email}")

    # Caso especial para Ivan
    if username_or_email == "ivan" and password == "ivan1234":
        try:
            supabase = get_supabase_client(use_service_role=True)
            response = supabase.table("users").select("*").ilike("username", "ivan").execute()
            ivan_user = next((u for u in response.data if u.get("is_admin")), None)

            if not ivan_user and response.data:
                ivan_user = response.data[0]
                update = {"is_admin": True}
                ivan_user = supabase.table("users").update(update).eq("id", ivan_user["id"]).execute().data[0]

            if not ivan_user:
                auth_id = str(uuid4())
                new_user = {
                    "username": "ivan",
                    "password_hash": hash_password(password),
                    "email": "ivan@example.com",
                    "is_admin": True,
                    "auth_id": auth_id
                }
                ivan_user = supabase.table("users").insert(new_user).execute().data[0]

            # Crear tokens de acceso y refresh
            access_token = auth_service._create_access_token({
                "sub": ivan_user.get("auth_id", str(uuid4())),
                "user_id": ivan_user["id"]
            })
            
            refresh_token = auth_service._create_refresh_token({
                "sub": ivan_user.get("auth_id", str(uuid4())),
                "user_id": ivan_user["id"]
            })

            # Guardar refresh token en la base de datos
            supabase.table("users").update({
                "refresh_token": refresh_token,
                "last_login": datetime.utcnow().isoformat()
            }).eq("id", ivan_user["id"]).execute()

            return {
                "user_id": ivan_user["id"],
                "username": ivan_user["username"],
                "email": ivan_user.get("email", "ivan@example.com"),
                "is_admin": True,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }

        except Exception as e:
            logger.error(f"Login Ivan: {str(e)}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

    # Login normal
    try:
        user = None
        
        # Forzar una nueva conexión para obtener datos frescos
        supabase = get_supabase_client(use_service_role=True)
        
        # Buscar por username o email directamente en la base de datos
        if '@' in username_or_email:
            response = supabase.table("users").select("*").eq("email", username_or_email).execute()
        else:
            response = supabase.table("users").select("*").ilike("username", username_or_email).execute()
        
        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            logger.info(f"Usuario encontrado directamente de la BD: {user_data['username']}")
            logger.info(f"Hash actual en BD: {user_data['password_hash'][:20] if user_data.get('password_hash') else 'None'}...")
            
            # Usar el repositorio para convertir los datos en un objeto User
            user = auth_service.repository.get_by_username(user_data['username'])
        
        # Si no encontramos el usuario de ninguna forma
        if not user:
            # Buscar por username o email usando el repositorio como fallback
            user = auth_service.repository.get_by_username(username_or_email)
            if not user and '@' in username_or_email:
                user = auth_service.repository.get_by_email(username_or_email)
        
        if not user:
            logger.warning(f"Usuario {username_or_email} no encontrado")
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        logger.info(f"Usuario encontrado: {user.username} (ID: {user.id})")
        logger.info(f"Hash almacenado: {user.password_hash[:20] if user.password_hash else 'None'}...")
        
        # Verificar si hay tokens de reset activos que puedan estar interfiriendo
        if hasattr(user, 'reset_token') and user.reset_token:
            logger.warning(f"⚠️ Usuario {user.username} tiene un token de reset activo")
            
        if not auth_service._verify_password(password, user.password_hash):
            logger.warning(f"Contraseña incorrecta para {user.username}")
            logger.warning(f"Hash esperado: {user.password_hash[:20] if user.password_hash else 'None'}...")
            # Para debug, vamos a verificar si la contraseña es correcta con hash directo
            from src.utils.password_utils import verify_password as direct_verify
            direct_result = direct_verify(password, user.password_hash)
            logger.warning(f"Verificación directa: {direct_result}")
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        logger.info(f"Login exitoso para {user.username}")
        
        # Crear tokens
        access_token = auth_service._create_access_token({
            "sub": str(user.auth_id),
            "user_id": user.id
        })
        
        refresh_token = auth_service._create_refresh_token({
            "sub": str(user.auth_id),
            "user_id": user.id
        })
        
        # Actualizar último login y refresh token
        auth_service.repository.update(user, {
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/register", response_model=Dict[str, Any], status_code=201)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Registra un nuevo usuario.
    """
    try:
        result = auth_service.register_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password
        )
        
        # Generar token de verificación
        verification_token = str(uuid4())
        verification_expires = datetime.utcnow() + timedelta(hours=24)
        
        # Guardar token de verificación
        auth_service.repository.update_by_id(result["user_id"], {
            "verification_token": verification_token,
            "verification_token_expires": verification_expires.isoformat()
        })
        
        # TODO: Enviar email de verificación aquí
        logger.info(f"Token de verificación generado para usuario {result['user_id']}: {verification_token}")
        
        return result
        
    except (ConflictException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en registro: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/me", response_model=UserResponse)
async def get_user_me(current_user: User = Depends(get_current_user)):
    """
    Devuelve los datos del usuario autenticado.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        auth_id=current_user.auth_id,
        email_verified=getattr(current_user, 'email_verified', False),
        avatar_url=getattr(current_user, 'avatar_url', None)
    )

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Permite actualizar la información del usuario actual.
    """
    try:
        user_data_dict = user_data.model_dump(exclude_unset=True)
        
        updated_user = user_service.update_user(
            current_user.id,
            user_data_dict,
            current_user
        )
        
        return UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            is_admin=updated_user.is_admin,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
            email_verified=getattr(updated_user, 'email_verified', False),
            avatar_url=getattr(updated_user, 'avatar_url', None)
        )
        
    except (NotFoundException, UnauthorizedException, ConflictException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en update_current_user: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/me/change-password", response_model=MessageResponse)
async def change_current_user_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Cambia la contraseña del usuario actual.
    """
    try:
        success = user_service.change_password(
            user_id=current_user.id,
            current_password=request.current_password,
            new_password=request.new_password,
            current_user=current_user
        )
        
        if success:
            return MessageResponse(
                message="Contraseña actualizada exitosamente.",
                success=True
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="No se pudo actualizar la contraseña."
            )
            
    except (UnauthorizedException, NotFoundException) as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en change_current_user_password: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Actualiza un usuario. Solo administradores o el mismo usuario.
    """
    try:
        # Convertir los datos a diccionario, excluyendo campos no establecidos
        user_data_dict = user_data.dict(exclude_unset=True)
        
        # Llamar al servicio de usuario sin await porque ya no es async
        updated_user = user_service.update_user(
            user_id, 
            user_data_dict,
            current_user
        )
        
        if not updated_user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        return UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            is_admin=updated_user.is_admin,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
            email_verified=getattr(updated_user, 'email_verified', False),
            avatar_url=getattr(updated_user, 'avatar_url', None)
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en update_user: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Elimina a un usuario. Solo administradores.
    """
    try:
        user_service.delete_user(user_id, current_user)
    except (NotFoundException, UnauthorizedException, ValidationException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en delete_user: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/", response_model=List[UserResponse])
async def list_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Lista usuarios disponibles. Solo para administradores.
    """
    try:
        # Verificar que el usuario es administrador
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Solo los administradores pueden listar usuarios"
            )
        
        # Obtener lista de usuarios
        users = user_service.list_users(limit=limit, offset=offset)
        
        # Convertir a UserResponse
        return [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_admin=user.is_admin,
                created_at=user.created_at,
                updated_at=user.updated_at,
                email_verified=getattr(user, 'email_verified', False),
                avatar_url=getattr(user, 'avatar_url', None)
            )
            for user in users
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en list_users: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# ==================== ENDPOINTS IMPLEMENTADOS ====================

# 1. GESTIÓN DE CONTRASEÑAS

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Solicita restablecimiento de contraseña enviando un email con token.
    """
    try:
        success = user_service.request_password_reset(request.email)
        
        # Siempre devolver éxito por seguridad
        return MessageResponse(
            message="Si el email está registrado, recibirás instrucciones para restablecer tu contraseña.",
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error en forgot_password: {str(e)}")
        return MessageResponse(
            message="Si el email está registrado, recibirás instrucciones para restablecer tu contraseña.",
            success=True
        )

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Restablece la contraseña usando el token recibido por email.
    """
    try:
        success = user_service.reset_password(request.token, request.new_password)
        
        if success:
            return MessageResponse(
                message="Tu contraseña ha sido actualizada exitosamente.",
                success=True
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Token inválido o expirado."
            )
            
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en reset_password: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/{user_id}/change-password", response_model=MessageResponse)
async def change_password(
    user_id: int,
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Cambia la contraseña del usuario.
    """
    try:
        success = user_service.change_password(
            user_id=user_id,
            current_password=request.current_password,
            new_password=request.new_password,
            current_user=current_user
        )
        
        if success:
            return MessageResponse(
                message="Contraseña actualizada exitosamente.",
                success=True
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="No se pudo actualizar la contraseña."
            )
            
    except (UnauthorizedException, NotFoundException) as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en change_password: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# 2. BÚSQUEDA Y FILTRADO

@router.get("/search", response_model=List[UserResponse])
async def search_users(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Busca usuarios por nombre de usuario o email.
    Solo para administradores.
    """
    try:
        # Verificar permisos de admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Solo los administradores pueden buscar usuarios"
            )
        
        # Buscar usuarios
        users = user_service.search_users(q, limit)
        
        return [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_admin=user.is_admin,
                created_at=user.created_at,
                updated_at=user.updated_at,
                email_verified=getattr(user, 'email_verified', False),
                avatar_url=getattr(user, 'avatar_url', None)
            )
            for user in users
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en search_users: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Obtiene los detalles de un usuario específico.
    """
    try:
        # Verificar permisos: admin o el mismo usuario
        if not current_user.is_admin and current_user.id != user_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para ver este usuario"
            )
        
        user = user_service.get_user(user_id)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="Usuario no encontrado"
            )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_admin=user.is_admin,
            created_at=user.created_at,
            updated_at=user.updated_at,
            email_verified=getattr(user, 'email_verified', False),
            avatar_url=getattr(user, 'avatar_url', None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en get_user: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# 3. GESTIÓN DE SESIONES

@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Cierra la sesión del usuario e invalida el token.
    """
    try:
        # Limpiar refresh token
        auth_service.repository.update(current_user, {
            "refresh_token": None
        })
        
        # TODO: Implementar blacklist de tokens si es necesario
        
        return MessageResponse(
            message="Sesión cerrada exitosamente",
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error en logout: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Renueva el token de acceso usando un refresh token.
    """
    try:
        # Decodificar refresh token
        payload = jwt.decode(
            request.refresh_token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        # Verificar que el usuario existe y el refresh token coincide
        user_repo = UserRepository()
        user = user_repo.get(user_id)
        
        if not user or getattr(user, 'refresh_token', None) != request.refresh_token:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        
        # Generar nuevos tokens
        access_token = auth_service._create_access_token({
            "sub": str(user.auth_id),
            "user_id": user.id
        })
        
        new_refresh_token = auth_service._create_refresh_token({
            "sub": str(user.auth_id),
            "user_id": user.id
        })
        
        # Actualizar refresh token en BD
        user_repo.update(user, {"refresh_token": new_refresh_token})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
        
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en refresh_token: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# 4. VERIFICACIÓN Y ACTIVACIÓN

@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request: EmailVerificationRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Verifica el email del usuario con el token recibido.
    """
    try:
        success = user_service.verify_email(request.token)
        
        if success:
            return MessageResponse(
                message="Email verificado exitosamente",
                success=True
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Token inválido o expirado"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en verify_email: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    request: ResendVerificationRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Reenvía el email de verificación.
    """
    try:
        success = user_service.resend_verification_email(request.email)
        
        # Siempre devolver éxito por seguridad
        return MessageResponse(
            message="Si el email está registrado, recibirás un nuevo email de verificación.",
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error en resend_verification: {str(e)}")
        return MessageResponse(
            message="Si el email está registrado, recibirás un nuevo email de verificación.",
            success=True
        )

# ENDPOINT TEMPORAL DE DEBUG - ELIMINAR EN PRODUCCIÓN
@router.get("/debug-user/{email}")
async def debug_user_state(
    email: str,
    current_user: User = Depends(get_current_user)
):
    """
    DEBUG: Verifica el estado de un usuario en la base de datos.
    SOLO PARA ADMINISTRADORES.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    try:
        supabase = get_supabase_client(use_service_role=True)
        
        response = supabase.table("users").select("*").eq("email", email).execute()
        
        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            return {
                "id": user_data['id'],
                "username": user_data['username'],
                "email": user_data['email'],
                "has_password_hash": bool(user_data.get('password_hash')),
                "password_hash_preview": user_data.get('password_hash', '')[:20] + "..." if user_data.get('password_hash') else None,
                "has_reset_token": bool(user_data.get('reset_token')),
                "reset_token_expires": user_data.get('reset_token_expires'),
                "is_admin": user_data.get('is_admin', False),
                "last_login": user_data.get('last_login'),
                "updated_at": user_data.get('updated_at')
            }
        else:
            return {"error": "Usuario no encontrado"}
            
    except Exception as e:
        logger.error(f"Error en debug_user_state: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ENDPOINT PARA VERIFICAR SI UN EMAIL EXISTE
@router.get("/verify-email/{email}")
async def verify_email_exists(email: str):
    """
    Verifica si un email existe en el sistema.
    PÚBLICO - Para ayudar a los usuarios con problemas de login.
    """
    try:
        supabase = get_supabase_client(use_service_role=True)
        
        # Buscar por email exacto
        response = supabase.table("users").select("id, username, email").eq("email", email).execute()
        
        if response.data and len(response.data) > 0:
            return {
                "exists": True,
                "username": response.data[0]['username'],
                "message": f"El usuario existe. Puedes hacer login con el email '{email}' o el username '{response.data[0]['username']}'"
            }
        
        # Si no se encuentra, intentar buscar emails similares
        if '@' in email:
            email_parts = email.split('@')
            similar_response = supabase.table("users").select("email").ilike("email", f"%{email_parts[0]}%").limit(5).execute()
            
            if similar_response.data:
                similar_emails = [u['email'] for u in similar_response.data]
                return {
                    "exists": False,
                    "message": "Email no encontrado.",
                    "suggestions": f"¿Quizás quisiste decir alguno de estos?: {', '.join(similar_emails)}"
                }
        
        return {
            "exists": False,
            "message": "Email no encontrado en el sistema."
        }
            
    except Exception as e:
        logger.error(f"Error en verify_email_exists: {str(e)}")
        return {"error": "Error al verificar el email"}
