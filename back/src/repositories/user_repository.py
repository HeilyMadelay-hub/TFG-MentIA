"""
Repositorio para operaciones CRUD de usuarios en Supabase.
Maneja el acceso a datos para la entidad User.
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID  
from src.models.domain import User
from src.models.schemas.user import UserCreate 
import uuid 
from src.utils.password_utils import hash_password, verify_password
from src.config.database import get_supabase_client

# Importar excepciones personalizadas
from src.core.exceptions import (
    UserNotFoundException,
    DatabaseException,
    ValidationException,
    ConflictException
)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserRepository:
    """
    Repositorio para gestionar usuarios en Supabase.
    Implementa operaciones CRUD básicas y consultas específicas.
    """
    
    def __init__(self):
        """Inicializa el repositorio con el cliente de Supabase."""
        self.table_name = "users"

    def create_user(self, user_data: UserCreate) -> User:
        """
        Crea un nuevo usuario en la base de datos.
        
        Args:
            user_data: Datos del usuario a crear
            
        Returns:
            User: Usuario creado
            
        Raises:
            ValidationException: Si los datos no son válidos
            ConflictException: Si el usuario ya existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Validación básica
            if not user_data.username or not user_data.username.strip():
                raise ValidationException(
                    "El nombre de usuario es requerido",
                    field_errors={"username": "Campo requerido"}
                )
            
            if not user_data.email or not user_data.email.strip():
                raise ValidationException(
                    "El email es requerido",
                    field_errors={"email": "Campo requerido"}
                )
            
            # Verificar si el usuario ya existe
            supabase = get_supabase_client(use_service_role=True)
            
            # Verificar username
            existing_username = supabase.table(self.table_name)\
                .select('id')\
                .ilike('username', user_data.username)\
                .execute()
            
            if existing_username.data:
                raise ConflictException(f"El nombre de usuario '{user_data.username}' ya está en uso")
            
            # Verificar email
            existing_email = supabase.table(self.table_name)\
                .select('id')\
                .eq('email', user_data.email)\
                .execute()
            
            if existing_email.data:
                raise ConflictException(f"El email '{user_data.email}' ya está registrado")
            
            # Hash de la contraseña
            hashed_password = hash_password(user_data.password)
            
            # Preparar datos para Supabase
            user_insert_data = {
                "username": user_data.username,
                "email": user_data.email,
                "password_hash": hashed_password,
                "auth_id": str(user_data.auth_id or uuid.uuid4())
            }
            
            # Insertar en Supabase
            response = supabase.table(self.table_name).insert(user_insert_data).execute()
            
            if not response.data or len(response.data) == 0:
                raise DatabaseException("No se recibieron datos tras insertar el usuario")
            
            # Los datos que devuelve Supabase
            response_data = response.data[0]
            
            # Convertir a objeto User
            user = User(
                id=response_data['id'],
                username=response_data['username'],
                email=response_data['email'],
                password_hash=response_data['password_hash'],
                is_admin=response_data.get('is_admin', False),
                auth_id=UUID(response_data['auth_id']) if response_data.get('auth_id') else None,
                created_at=response_data.get('created_at'),
                updated_at=response_data.get('updated_at')
            )
            
            logger.info(f"Usuario creado exitosamente: {user.username} (ID: {user.id})")
            return user
            
        except (ValidationException, ConflictException):
            # Re-lanzar excepciones conocidas
            raise
        except Exception as e:
            logger.error(f"Error al crear usuario: {str(e)}")
            raise DatabaseException(f"No se pudo registrar el usuario: {str(e)}", original_error=e)

    def update(self, user: User, user_data: dict) -> bool:
        """
        Actualiza un usuario existente.
        
        Args:
            user: Usuario a actualizar
            user_data: Datos a actualizar
            
        Returns:
            bool: True si la actualización fue exitosa
            
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar que el usuario existe
            self.get(user.id)  # Lanzará UserNotFoundException si no existe
            
            # Usar la clave de servicio para tener permisos completos
            supabase = get_supabase_client(use_service_role=True)
            
            # Preparar datos para actualización
            update_data = user_data.copy()
            
            # Si hay un cambio en la contraseña y está en formato texto plano, hashearla
            if 'password' in update_data:
                update_data['password_hash'] = hash_password(update_data.pop('password'))
            
            # Añadir timestamp de actualización
            update_data['updated_at'] = datetime.now().isoformat()
            
            logger.info(f"Actualizando usuario {user.id} con datos: {update_data}")
            
            # Actualizar en Supabase
            response = supabase.table(self.table_name).update(update_data).eq('id', user.id).execute()
            
            logger.info(f"Respuesta de actualización: {response.data}")
            
            # Verificar si la actualización fue exitosa
            if response.data is not None and len(response.data) > 0:
                logger.info(f"Usuario {user.id} actualizado con éxito")
                
                # Actualizar el objeto user con los nuevos datos
                for key, value in update_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                        
                return True
            else:
                raise DatabaseException(f"No se pudo actualizar el usuario {user.id}")
                
        except (UserNotFoundException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al actualizar usuario {user.id}: {str(e)}")
            raise DatabaseException(f"Error al actualizar usuario {user.id}", original_error=e)
    
    def update_by_id(self, user_id: int, user_data: dict) -> bool:
        """
        Actualiza un usuario por su ID sin necesidad de obtener el objeto User primero.
        
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar que el usuario existe
            self.get(user_id)  # Lanzará UserNotFoundException si no existe
            
            # Usar la clave de servicio para tener permisos completos
            supabase = get_supabase_client(use_service_role=True)
            
            # Preparar datos para actualización
            update_data = user_data.copy()
            
            # Si hay un cambio en la contraseña y está en formato texto plano, hashearla
            if 'password' in update_data:
                update_data['password_hash'] = hash_password(update_data.pop('password'))
            
            # Añadir timestamp de actualización
            update_data['updated_at'] = datetime.now().isoformat()
            
            logger.info(f"Actualizando usuario {user_id} con datos: {update_data}")
            
            # Actualizar en Supabase
            response = supabase.table(self.table_name).update(update_data).eq('id', user_id).execute()
            
            if response.data is not None and len(response.data) > 0:
                logger.info(f"Usuario {user_id} actualizado con éxito")
                return True
            else:
                raise DatabaseException(f"No se pudo actualizar el usuario {user_id}")
                
        except (UserNotFoundException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al actualizar usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al actualizar usuario {user_id}", original_error=e)
   
    def delete(self, user_id: int) -> bool:
        """
        Elimina un usuario por su ID.
        
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar que el usuario existe
            self.get(user_id)  # Lanzará UserNotFoundException si no existe
            
            supabase = get_supabase_client(use_service_role=True)
            
            logger.info(f"Eliminando usuario con ID {user_id}")
            
            response = supabase.table(self.table_name).delete().eq('id', user_id).execute()
            
            if response.data is not None:
                # Verificar que realmente se eliminó
                verify_response = supabase.table(self.table_name).select('*').eq('id', user_id).execute()
                if verify_response.data and len(verify_response.data) > 0:
                    logger.warning(f"Se recibió código de éxito, pero el usuario {user_id} sigue existiendo")
                    raise DatabaseException(f"No se pudo eliminar el usuario {user_id}")
                    
                logger.info(f"Usuario {user_id} eliminado con éxito")
                return True
            else:
                raise DatabaseException(f"No se pudo eliminar el usuario {user_id}")
            
        except (UserNotFoundException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al eliminar usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al eliminar usuario {user_id}", original_error=e)
    
    def get(self, user_id: int) -> User:
        """
        Obtiene un usuario por su ID.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            User: Usuario encontrado
            
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            logger.info(f"Consultando usuario con ID {user_id} en Supabase (con permisos de servicio)")
            
            response = supabase.table(self.table_name).select('*').eq('id', user_id).execute()
            
            logger.info(f"Respuesta de Supabase para usuario ID {user_id}: {response.data}")
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                
                user = User()
                user.id = user_data['id']
                user.username = user_data['username']
                user.email = user_data.get('email')
                user.password_hash = user_data.get('password_hash')
                user.is_admin = user_data.get('is_admin', False)
                
                if user_data.get('auth_id'):
                    user.auth_id = UUID(user_data['auth_id'])
                else:
                    user.auth_id = None
                
                if user_data.get('created_at'):
                    try:
                        user.created_at = datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        user.created_at = datetime.now()
                else:
                    user.created_at = datetime.now()
                    
                if user_data.get('updated_at'):
                    try:
                        user.updated_at = datetime.fromisoformat(user_data['updated_at'].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        user.updated_at = datetime.now()
                else:
                    user.updated_at = datetime.now()
                
                return user
            else:
                logger.error(f"Usuario con ID {user_id} no encontrado")
                raise UserNotFoundException(user_id)
                
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al obtener usuario {user_id}", original_error=e)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Obtiene un usuario por su nombre de usuario (case-insensitive).
        
        NOTA: Este método aún retorna Optional[User] para mantener compatibilidad.
        Usar get_by_username_strict() para obtener excepciones.
        """
        try:
            username = username.strip()
            supabase = get_supabase_client(use_service_role=True)
            
            logger.info(f"Buscando usuario: '{username}' (case-insensitive)")
            response = supabase.table(self.table_name) \
                .select('*') \
                .ilike('username', username) \
                .limit(1) \
                .execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                logger.info(f"✅ Usuario encontrado: '{user_data['username']}'")
                
                # Log adicional para verificar el estado del reset_token
                if user_data.get('reset_token'):
                    logger.warning(f"⚠️ Usuario {user_data['username']} tiene un reset_token activo")
                    if user_data.get('reset_token_expires'):
                        expires = datetime.fromisoformat(user_data['reset_token_expires'].replace('Z', '+00:00'))
                        if datetime.now(timezone.utc) > expires:
                            logger.warning(f"❗ El reset_token ha expirado")
                        else:
                            logger.warning(f"⚠️ El reset_token sigue activo hasta {expires}")
                
                return User(
                    id=user_data['id'],
                    username=user_data['username'],
                    email=user_data.get('email', ''),
                    password_hash=user_data.get('password_hash', ''),
                    is_admin=user_data.get('is_admin', False),
                    auth_id=UUID(user_data['auth_id']) if user_data.get('auth_id') else None,
                    created_at=user_data.get('created_at'),
                    updated_at=user_data.get('updated_at'),
                    reset_token=user_data.get('reset_token'),
                    reset_token_expires=user_data.get('reset_token_expires'),
                    email_verified=user_data.get('email_verified', False),
                    last_login=user_data.get('last_login'),
                    refresh_token=user_data.get('refresh_token')
                )
            
            logger.warning(f"❌ Usuario no encontrado: '{username}'")
            return None
            
        except Exception as e:
            logger.error(f"Error al buscar usuario '{username}': {str(e)}")
            return None
    
    def get_by_username_strict(self, username: str) -> User:
        """
        Obtiene un usuario por su nombre de usuario (case-insensitive).
        Versión estricta que lanza excepciones.
        
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        user = self.get_by_username(username)
        if not user:
            raise UserNotFoundException(f"Usuario '{username}' no encontrado")
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Obtiene un usuario por su dirección de correo electrónico.
        
        NOTA: Este método aún retorna Optional[User] para mantener compatibilidad.
        Usar get_by_email_strict() para obtener excepciones.
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            logger.info(f"Buscando usuario con email {email}")
            
            response = supabase.table(self.table_name).select('*').eq('email', email).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                
                # Log adicional para verificar el estado del reset_token
                if user_data.get('reset_token'):
                    logger.warning(f"⚠️ Usuario {user_data['username']} tiene un reset_token activo")
                    if user_data.get('reset_token_expires'):
                        expires = datetime.fromisoformat(user_data['reset_token_expires'].replace('Z', '+00:00'))
                        if datetime.now(timezone.utc) > expires:
                            logger.warning(f"❗ El reset_token ha expirado")
                        else:
                            logger.warning(f"⚠️ El reset_token sigue activo hasta {expires}")
                
                return User(
                    id=user_data['id'],
                    username=user_data['username'],
                    email=user_data.get('email', ''),
                    password_hash=user_data.get('password_hash', ''),
                    is_admin=user_data.get('is_admin', False),
                    auth_id=UUID(user_data['auth_id']) if user_data.get('auth_id') else None,
                    created_at=user_data.get('created_at'),
                    updated_at=user_data.get('updated_at'),
                    reset_token=user_data.get('reset_token'),
                    reset_token_expires=user_data.get('reset_token_expires'),
                    email_verified=user_data.get('email_verified', False),
                    last_login=user_data.get('last_login'),
                    refresh_token=user_data.get('refresh_token')
                )
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error al buscar usuario con email {email}: {str(e)}")
            return None
    
    def get_by_email_strict(self, email: str) -> User:
        """
        Obtiene un usuario por su email.
        Versión estricta que lanza excepciones.
        
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        user = self.get_by_email(email)
        if not user:
            raise UserNotFoundException(f"Usuario con email '{email}' no encontrado")
        return user
    
    # ==================== MÉTODOS DE RESET PASSWORD ====================
    
    def store_reset_token(self, user_id: int, token_hash: str, expires: datetime) -> bool:
        """
        Almacena el token de restablecimiento de contraseña.
        
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar que el usuario existe
            self.get(user_id)  # Lanzará UserNotFoundException si no existe
            
            supabase = get_supabase_client(use_service_role=True)
            
            update_data = {
                "reset_token": token_hash,
                "reset_token_expires": expires.isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            logger.info(f"🔑 Almacenando reset token para usuario {user_id}")
            
            response = supabase.table(self.table_name)\
                .update(update_data)\
                .eq('id', user_id)\
                .execute()
            
            if response.data is not None and len(response.data) > 0:
                logger.info(f"✅ Reset token almacenado para usuario {user_id}")
                return True
            else:
                logger.error(f"❌ No se pudo almacenar reset token para usuario {user_id}")
                raise DatabaseException(f"No se pudo almacenar reset token para usuario {user_id}")
            
        except (UserNotFoundException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al guardar reset token para usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al guardar reset token", original_error=e)
    
    def get_by_reset_token(self, token_hash: str) -> Optional[User]:
        """
        Busca un usuario por su token de restablecimiento.
        
        NOTA: Este método aún retorna Optional[User] para mantener compatibilidad.
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            logger.info(f"🔍 Buscando usuario por reset token")
            
            response = supabase.table(self.table_name)\
                .select("*")\
                .eq('reset_token', token_hash)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                logger.warning("❌ Token de reset no encontrado")
                return None
                
            user_data = response.data[0]
            
            # Verificar si el token ha expirado
            if user_data.get('reset_token_expires'):
                expires = datetime.fromisoformat(user_data['reset_token_expires'].replace('Z', '+00:00'))
                if datetime.now(timezone.utc) > expires:
                    logger.warning(f"❌ Token expirado para usuario {user_data['id']}")
                    return None
            
            logger.info(f"✅ Usuario encontrado por reset token: {user_data['username']}")
            
            user = User()
            user.id = user_data['id']
            user.username = user_data['username']
            user.email = user_data.get('email')
            user.password_hash = user_data.get('password_hash')
            user.is_admin = user_data.get('is_admin', False)
            
            if user_data.get('auth_id'):
                user.auth_id = UUID(user_data['auth_id'])
                
            return user
            
        except Exception as e:
            logger.error(f"Error al buscar usuario por reset token: {str(e)}")
            return None
    
    def update_password(self, user_id: int, new_password_hash: str) -> bool:
        """
        Actualiza SOLO la contraseña de un usuario.
        
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar que el usuario existe
            self.get(user_id)  # Lanzará UserNotFoundException si no existe
            
            supabase = get_supabase_client(use_service_role=True)
            
            update_data = {
                "password_hash": new_password_hash,
                "updated_at": datetime.now().isoformat()
            }
            
            logger.info(f"🔐 Actualizando contraseña para usuario {user_id}")
            
            response = supabase.table(self.table_name)\
                .update(update_data)\
                .eq('id', user_id)\
                .execute()
            
            if response.data is not None and len(response.data) > 0:
                logger.info(f"✅ Contraseña actualizada para usuario {user_id}")
                
                # Verificar que se guardó correctamente
                verify_response = supabase.table(self.table_name)\
                    .select('password_hash')\
                    .eq('id', user_id)\
                    .execute()
                
                if verify_response.data and len(verify_response.data) > 0:
                    saved_hash = verify_response.data[0]['password_hash']
                    if saved_hash == new_password_hash:
                        logger.info(f"✅ Verificación: Contraseña guardada correctamente")
                        return True
                    else:
                        logger.error(f"❌ ERROR: La contraseña no se guardó correctamente!")
                        raise DatabaseException("La contraseña no se guardó correctamente")
                
                return True
            else:
                logger.error(f"❌ No se pudo actualizar contraseña para usuario {user_id}")
                raise DatabaseException(f"No se pudo actualizar contraseña para usuario {user_id}")
            
        except (UserNotFoundException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al actualizar contraseña para usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al actualizar contraseña", original_error=e)
    
    def clear_reset_token(self, user_id: int) -> bool:
        """
        Limpia el token de restablecimiento de un usuario.
        
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar que el usuario existe
            self.get(user_id)  # Lanzará UserNotFoundException si no existe
            
            supabase = get_supabase_client(use_service_role=True)
            
            update_data = {
                "reset_token": None,
                "reset_token_expires": None,
                "updated_at": datetime.now().isoformat()
            }
            
            logger.info(f"🧹 Limpiando reset token para usuario {user_id}")
            
            response = supabase.table(self.table_name)\
                .update(update_data)\
                .eq('id', user_id)\
                .execute()
            
            if response.data is not None and len(response.data) > 0:
                logger.info(f"✅ Reset token limpiado para usuario {user_id}")
                return True
            else:
                logger.error(f"❌ No se pudo limpiar reset token para usuario {user_id}")
                raise DatabaseException(f"No se pudo limpiar reset token para usuario {user_id}")
                
        except (UserNotFoundException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al limpiar reset token para usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al limpiar reset token", original_error=e)
    
    # ==================== MÉTODOS ADICIONALES ====================
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        """
        Lista todos los usuarios.
        
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            response = supabase.table(self.table_name)\
                .select('*')\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            users = []
            if response.data:
                for user_data in response.data:
                    try:
                        user = User()
                        user.id = user_data['id']
                        user.username = user_data['username']
                        user.email = user_data.get('email')
                        user.is_admin = user_data.get('is_admin', False)
                        
                        if user_data.get('auth_id'):
                            user.auth_id = UUID(user_data['auth_id'])
                        
                        if user_data.get('created_at'):
                            try:
                                user.created_at = datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00'))
                            except (ValueError, TypeError):
                                user.created_at = datetime.now()
                        
                        if user_data.get('updated_at'):
                            try:
                                user.updated_at = datetime.fromisoformat(user_data['updated_at'].replace('Z', '+00:00'))
                            except (ValueError, TypeError):
                                user.updated_at = datetime.now()
                        
                        users.append(user)
                    except Exception as e:
                        logger.error(f"Error al procesar usuario {user_data.get('id')}: {str(e)}")
            
            return users
            
        except Exception as e:
            logger.error(f"Error al listar usuarios: {str(e)}")
            raise DatabaseException("Error al listar usuarios", original_error=e)
    
    def search_by_username(self, username_query: str, limit: int = 100) -> List[User]:
        """
        Busca usuarios por username.
        
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            response = supabase.table(self.table_name)\
                .select('*')\
                .ilike('username', f'%{username_query}%')\
                .limit(limit)\
                .execute()
            
            users = []
            if response.data:
                for user_data in response.data:
                    user = User(
                        id=user_data['id'],
                        username=user_data['username'],
                        email=user_data['email'],
                        password_hash=user_data['password_hash'],
                        is_admin=user_data['is_admin'],
                        auth_id=UUID(user_data['auth_id']) if user_data.get('auth_id') else None,
                        created_at=user_data['created_at'],
                        updated_at=user_data['updated_at']
                    )
                    users.append(user)
            
            return users
            
        except Exception as e:
            logger.error(f"Error al buscar usuarios por username '{username_query}': {str(e)}")
            raise DatabaseException(f"Error al buscar usuarios por username", original_error=e)

    def search_by_email(self, email_query: str, limit: int = 100) -> List[User]:
        """
        Busca usuarios por email.
        
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            response = supabase.table(self.table_name)\
                .select('*')\
                .ilike('email', f'%{email_query}%')\
                .limit(limit)\
                .execute()
            
            users = []
            if response.data:
                for user_data in response.data:
                    user = User(
                        id=user_data['id'],
                        username=user_data['username'],
                        email=user_data.get('email', ''),
                        password_hash=user_data.get('password_hash', ''),
                        is_admin=user_data.get('is_admin', False),
                        auth_id=UUID(user_data['auth_id']) if user_data.get('auth_id') else None,
                        created_at=user_data.get('created_at'),
                        updated_at=user_data.get('updated_at')
                    )
                    users.append(user)
            
            return users
            
        except Exception as e:
            logger.error(f"Error al buscar usuarios por email '{email_query}': {str(e)}")
            raise DatabaseException(f"Error al buscar usuarios por email", original_error=e)
    
    def update_role(self, user_id: int, is_admin: bool) -> bool:
        """
        Actualiza el rol de un usuario.
        
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar que el usuario existe
            self.get(user_id)  # Lanzará UserNotFoundException si no existe
            
            supabase = get_supabase_client(use_service_role=True)
            
            user_data = {
                "is_admin": is_admin,
                "updated_at": datetime.now().isoformat()
            }
            
            response = supabase.table(self.table_name).update(user_data).eq('id', user_id).execute()
            
            if response.data is not None and len(response.data) > 0:
                logger.info(f"Rol de usuario {user_id} actualizado a admin={is_admin}")
                return True
            else:
                logger.warning(f"No se pudo actualizar el rol del usuario {user_id}")
                raise DatabaseException(f"No se pudo actualizar el rol del usuario {user_id}")
            
        except (UserNotFoundException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al actualizar rol de usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al actualizar rol de usuario", original_error=e)
    
    def update_last_login(self, user_id: int) -> bool:
        """
        Actualiza la fecha de último login.
        
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar que el usuario existe
            self.get(user_id)  # Lanzará UserNotFoundException si no existe
            
            supabase = get_supabase_client(use_service_role=True)
            
            update_data = {
                "last_login": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            response = supabase.table(self.table_name)\
                .update(update_data)\
                .eq('id', user_id)\
                .execute()
            
            if response.data is not None and len(response.data) > 0:
                logger.info(f"Fecha de último login actualizada para usuario {user_id}")
                return True
            else:
                logger.warning(f"No se pudo actualizar la fecha de último login para usuario {user_id}")
                raise DatabaseException(f"No se pudo actualizar última fecha de login")
                
        except (UserNotFoundException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al actualizar fecha de último login para usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al actualizar última fecha de login", original_error=e)
    

    def update_email_verified(self, user_id: int, verified: bool = True) -> bool:
        """
        Actualiza el estado de verificación del email.
        
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar que el usuario existe
            self.get(user_id)  # Lanzará UserNotFoundException si no existe
            
            supabase = get_supabase_client(use_service_role=True)
            
            update_data = {
                "email_verified": verified,
                "updated_at": datetime.now().isoformat()
            }
            
            logger.info(f"📧 Actualizando email_verified={verified} para usuario ID: {user_id}")
            
            response = supabase.table(self.table_name)\
                .update(update_data)\
                .eq('id', user_id)\
                .execute()
            
            if response.data is not None and len(response.data) > 0:
                logger.info(f"Estado de verificación de email actualizado para usuario {user_id}: verified={verified}")
                
                # Verificar que se guardó correctamente
                verify_response = supabase.table(self.table_name)\
                    .select("email_verified")\
                    .eq('id', user_id)\
                    .execute()
                
                if verify_response.data and len(verify_response.data) > 0:
                    actual_verified = verify_response.data[0]['email_verified']
                    if actual_verified == verified:
                        logger.info(f"✅ CONFIRMADO: email_verified = {actual_verified} en la base de datos")
                        return True
                    else:
                        logger.error(f"❌ ERROR: Se esperaba email_verified={verified} pero se encontró {actual_verified}")
                        raise DatabaseException("El estado de verificación no se guardó correctamente")
                        
                return True
            else:
                logger.warning(f"No se pudo actualizar el estado de verificación de email para usuario {user_id}")
                raise DatabaseException(f"No se pudo actualizar el estado de verificación de email")
                
        except (UserNotFoundException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al actualizar estado de verificación de email para usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al actualizar estado de verificación de email", original_error=e)
    
    # ==================== MÉTODOS DE COMPATIBILIDAD ====================
    
    def get_by_id(self, user_id: int) -> User:
        """
        Alias para el método get() para compatibilidad.
        Obtiene un usuario por su ID.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            User: Usuario encontrado
            
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error de base de datos
        """
        return self.get(user_id)
    
    def find_by_email(self, email: str) -> Optional[User]:
        """
        Alias para get_by_email() para compatibilidad.
        """
        return self.get_by_email(email)
    
    def update_user(self, user_id: int, data: dict) -> bool:
        """
        Alias para update_by_id() para compatibilidad.
        """
        return self.update_by_id(user_id, data)
    
    def exists(self, user_id: int) -> bool:
        """
        Verifica si un usuario existe.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            bool: True si existe, False si no
        """
        try:
            self.get(user_id)
            return True
        except UserNotFoundException:
            return False
        except Exception:
            return False
