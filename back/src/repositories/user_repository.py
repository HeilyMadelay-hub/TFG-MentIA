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
        try:
            # Hash de la contraseña
            hashed_password = hash_password(user_data.password)
            
            # Guarda el email original para usarlo después
            original_email = user_data.email
            
            # Preparar datos para Supabase
            user_insert_data = {
                "username": user_data.username,
                "password_hash": hashed_password,
                "auth_id": str(user_data.auth_id or uuid.uuid4())
            }
            
            # Insertar en Supabase con clave de servicio
            supabase = get_supabase_client(use_service_role=True)
            response = supabase.table(self.table_name).insert(user_insert_data).execute()
            
            if not response.data or len(response.data) == 0:
                raise ValueError("No se recibieron datos tras insertar el usuario")
            
            # Los datos que devuelve Supabase
            response_data = response.data[0]
            user_id = response_data['id']
            
            # Convertir a objeto User
            user = User(
                id=response_data['id'],
                username=response_data['username'],
                email=original_email,  # Usar el email original del parámetro
                password_hash=response_data['password_hash'],
                is_admin=response_data.get('is_admin', False),
                auth_id=UUID(response_data['auth_id']) if response_data.get('auth_id') else None,
                created_at=response_data.get('created_at'),
                updated_at=response_data.get('updated_at')
            )
            
            # Establecer el email por separado 
            try:
                supabase.table(self.table_name)\
                    .update({"email": original_email})\
                    .eq('id', user_id)\
                    .execute()
            except Exception as e:
                logger.warning(f"No se pudo actualizar el email: {str(e)}")
            
            return user
            
        except Exception as e:
            logger.error(f"Error al crear usuario: {str(e)}")
            raise ValueError(f"No se pudo registrar el usuario: {str(e)}")

    def update(self, user: User, user_data: dict) -> bool:
        """
        Actualiza un usuario existente.
        """
        try:
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
            success = response.data is not None and len(response.data) > 0
            
            if success:
                logger.info(f"Usuario {user.id} actualizado con éxito")
                
                # Actualizar el objeto user con los nuevos datos
                for key, value in update_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                        
                return True
            else:
                logger.warning(f"No se pudo actualizar el usuario {user.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error al actualizar usuario {user.id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def update_by_id(self, user_id: int, user_data: dict) -> bool:
        """
        Actualiza un usuario por su ID sin necesidad de obtener el objeto User primero.
        """
        try:
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
            
            logger.info(f"Respuesta de actualización: {response.data}")
            
            # Verificar si la actualización fue exitosa
            success = response.data is not None and len(response.data) > 0
            
            if success:
                logger.info(f"Usuario {user_id} actualizado con éxito")
            else:
                logger.warning(f"No se pudo actualizar el usuario {user_id}")
                
            return success
                
        except Exception as e:
            logger.error(f"Error al actualizar usuario {user_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
   
    def delete(self, user_id: int) -> bool:
        """
        Elimina un usuario por su ID.
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            logger.info(f"Eliminando usuario con ID {user_id}")
            
            response = supabase.table(self.table_name).delete().eq('id', user_id).execute()
            
            success = response.data is not None
            
            if success:
                verify_response = supabase.table(self.table_name).select('*').eq('id', user_id).execute()
                if verify_response.data and len(verify_response.data) > 0:
                    logger.warning(f"Se recibió código de éxito, pero el usuario {user_id} sigue existiendo")
                    return False
                    
                logger.info(f"Usuario {user_id} eliminado con éxito")
            else:
                logger.warning(f"No se pudo eliminar el usuario {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al eliminar usuario {user_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get(self, user_id: int) -> Optional[User]:
        """
        Obtiene un usuario por su ID.
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
                return None
                
        except Exception as e:
            logger.error(f"Error al obtener usuario {user_id}: {str(e)}")
            return None
    
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Obtiene un usuario por su nombre de usuario (case-insensitive).
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
            import traceback
            logger.error(traceback.format_exc())
            return None

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Obtiene un usuario por su dirección de correo electrónico.
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
    
    # ==================== MÉTODOS DE RESET PASSWORD ====================
    
    def store_reset_token(self, user_id: int, token_hash: str, expires: datetime) -> bool:
        """
        Almacena el token de restablecimiento de contraseña.
        """
        try:
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
            
            success = response.data is not None and len(response.data) > 0
            
            if success:
                logger.info(f"✅ Reset token almacenado para usuario {user_id}")
            else:
                logger.error(f"❌ No se pudo almacenar reset token para usuario {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al guardar reset token para usuario {user_id}: {str(e)}")
            return False
    
    def get_by_reset_token(self, token_hash: str) -> Optional[User]:
        """
        Busca un usuario por su token de restablecimiento.
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
        """
        try:
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
            
            success = response.data is not None and len(response.data) > 0
            
            if success:
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
                    else:
                        logger.error(f"❌ ERROR: La contraseña no se guardó correctamente!")
                        return False
                
            else:
                logger.error(f"❌ No se pudo actualizar contraseña para usuario {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al actualizar contraseña para usuario {user_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def clear_reset_token(self, user_id: int) -> bool:
        """
        Limpia el token de restablecimiento de un usuario.
        """
        try:
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
            
            success = response.data is not None and len(response.data) > 0
            
            if success:
                logger.info(f"✅ Reset token limpiado para usuario {user_id}")
            else:
                logger.error(f"❌ No se pudo limpiar reset token para usuario {user_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error al limpiar reset token para usuario {user_id}: {str(e)}")
            return False
    
    # ==================== MÉTODOS ADICIONALES ====================
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        """Lista todos los usuarios."""
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
            return []
    
    def search_by_username(self, username_query: str, limit: int = 100) -> List[User]:
        """Busca usuarios por username."""
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
            raise

    def search_by_email(self, email_query: str, limit: int = 100) -> List[User]:
        """Busca usuarios por email."""
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
            raise
    
    def update_role(self, user_id: int, is_admin: bool) -> bool:
        """Actualiza el rol de un usuario."""
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            user_data = {
                "is_admin": is_admin,
                "updated_at": datetime.now().isoformat()
            }
            
            response = supabase.table(self.table_name).update(user_data).eq('id', user_id).execute()
            
            success = response.data is not None and len(response.data) > 0
            if success:
                logger.info(f"Rol de usuario {user_id} actualizado a admin={is_admin}")
            else:
                logger.warning(f"No se pudo actualizar el rol del usuario {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al actualizar rol de usuario {user_id}: {str(e)}")
            raise
    
    def update_last_login(self, user_id: int) -> bool:
        """Actualiza la fecha de último login."""
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            update_data = {
                "last_login": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            response = supabase.table(self.table_name)\
                .update(update_data)\
                .eq('id', user_id)\
                .execute()
            
            success = response.data is not None and len(response.data) > 0
            
            if success:
                logger.info(f"Fecha de último login actualizada para usuario {user_id}")
            else:
                logger.warning(f"No se pudo actualizar la fecha de último login para usuario {user_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error al actualizar fecha de último login para usuario {user_id}: {str(e)}")
            return False
    
    def update_email_verified(self, user_id: int, verified: bool = True) -> bool:
        """Actualiza el estado de verificación del email."""
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            update_data = {
                "email_verified": verified,
                "updated_at": datetime.now().isoformat()
            }
            
            if verified:
                update_data["email_verified_at"] = datetime.now().isoformat()
            
            response = supabase.table(self.table_name)\
                .update(update_data)\
                .eq('id', user_id)\
                .execute()
            
            success = response.data is not None and len(response.data) > 0
            
            if success:
                logger.info(f"Estado de verificación de email actualizado para usuario {user_id}: verified={verified}")
            else:
                logger.warning(f"No se pudo actualizar el estado de verificación de email para usuario {user_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error al actualizar estado de verificación de email para usuario {user_id}: {str(e)}")
            return False
