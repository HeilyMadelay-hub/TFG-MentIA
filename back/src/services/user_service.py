"""
Servicio para la gestión de usuarios en la aplicación.
Este módulo implementa la lógica de negocio relacionada con usuarios.
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, UTC, timedelta
import uuid
import hashlib
import secrets

from fastapi import HTTPException

from src.repositories.user_repository import UserRepository
from src.models.domain import User
from src.models.schemas.user import UserCreate, UserUpdate, UserResponse
from src.utils.password_utils import hash_password, verify_password
from src.config.database import get_supabase_client
from src.services.email_service import email_service

# Configuración de logging
logger = logging.getLogger(__name__)

class UserService:
    """
    Servicio para gestionar todas las operaciones relacionadas con usuarios.
    """
    
    def __init__(self):
        """Inicializa el servicio con las dependencias necesarias."""
        self.repository = UserRepository()
    
    # ==================== OPERACIONES CRUD ====================
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Crea un nuevo usuario en el sistema.
        
        Args:
            user_data: Datos del usuario a crear
            
        Returns:
            User: El usuario creado
            
        Raises:
            ValueError: Si el username ya existe
        """
        try:
            # Validar que el username no exista
            existing_user = self.repository.get_by_username(user_data.username)
            if existing_user:
                raise ValueError("El nombre de usuario ya está en uso")
            
            # Validar que el email no exista
            if user_data.email:
                existing_email = self.repository.get_by_email(user_data.email)
                if existing_email:
                    raise ValueError("El email ya está registrado")
            
            # Crear usuario (el hash de contraseña se hace en el repositorio)
            user = self.repository.create_user(user_data)
            
            # Enviar email de verificación si hay email
            if user.email:
                try:
                    verification_token = str(uuid.uuid4())
                    verification_expires = datetime.now(UTC) + timedelta(hours=24)
                    
                    # Guardar token de verificación
                    self.repository.update(user, {
                        "verification_token": verification_token,
                        "verification_token_expires": verification_expires.isoformat()
                    })
                    
                    # Enviar email
                    email_service.send_verification_email(
                        to_email=user.email,
                        username=user.username,
                        verification_token=verification_token
                    )
                except Exception as e:
                    logger.error(f"Error enviando email de verificación: {str(e)}")
                    # No fallar la creación del usuario por el email
            
            return user
            
        except Exception as e:
            logger.error(f"Error al crear usuario: {str(e)}")
            raise
    
    def get_user(self, user_id: int) -> Optional[User]:
        """
        Obtiene un usuario por su ID.
        
        Args:
            user_id: ID del usuario a obtener
            
        Returns:
            Optional[User]: El usuario encontrado o None
        """
        try:
            return self.repository.get(user_id)
        except Exception as e:
            logger.error(f"Error al obtener usuario {user_id}: {str(e)}")
            return None
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Obtiene un usuario por su ID (síncrono - NO usar await).
        
        Args:
            user_id: ID del usuario a obtener
            
        Returns:
            Optional[User]: El usuario encontrado o None
        """
        try:
            logger.info(f"=== UserService.get_by_id ===")
            logger.info(f"Buscando usuario con ID: {user_id}")
            
            user = self.repository.get(user_id)
            
            if user:
                logger.info(f"✅ Usuario encontrado: ID={user_id}, username={user.username}")
            else:
                logger.warning(f"❌ Usuario no encontrado: ID={user_id}")
                
            return user
        except Exception as e:
            logger.error(f"Error al obtener usuario {user_id}: {str(e)}")
            logger.error(f"Tipo de excepción: {type(e).__name__}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Obtiene un usuario por su nombre de usuario.
        
        Args:
            username: Nombre de usuario a buscar
            
        Returns:
            Optional[User]: El usuario encontrado o None
        """
        try:
            return self.repository.get_by_username(username)
        except Exception as e:
            logger.error(f"Error al obtener usuario por username {username}: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Obtiene un usuario por su email.
        
        Args:
            email: Email del usuario
            
        Returns:
            Optional[User]: El usuario encontrado o None
        """
        try:
            return self.repository.get_by_email(email)
        except Exception as e:
            logger.error(f"Error al obtener usuario por email: {str(e)}")
            return None
    
    def update_user(self, user_id: int, user_data: Dict[str, Any], current_user: User) -> Optional[User]:
        """
        Actualiza un usuario existente con validación de permisos.
        
        Args:
            user_id: ID del usuario a actualizar
            user_data: Diccionario con los campos a actualizar
            current_user: Usuario que está realizando la actualización
            
        Returns:
            Optional[User]: El usuario actualizado o None si no existe
        """
        try:
            # 1. VALIDAR PERMISOS
            if not current_user.is_admin and current_user.id != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="No tienes permisos para actualizar este usuario"
                )
            
            # 2. Obtener usuario actual (sin await porque no es async)
            user = self.repository.get(user_id)
            if not user:
                logger.error(f"Usuario {user_id} no encontrado para actualizar")
                return None
            
            # Si se está actualizando el username, verificar que no exista
            if 'username' in user_data and user_data['username'] != user.username:
                existing = self.repository.get_by_username(user_data['username'])
                if existing:
                    raise ValueError("El nombre de usuario ya está en uso")
            
            # Si se está actualizando el email, verificar que no exista
            if 'email' in user_data and user_data['email'] != user.email:
                existing = self.repository.get_by_email(user_data['email'])
                if existing:
                    raise ValueError("El email ya está registrado")
            
            # Actualizar usuario
            success = self.repository.update(user, user_data)
            
            if success:
                # 3. AGREGAR AUDITORÍA
                logger.info(f"Usuario {current_user.username} (ID: {current_user.id}) actualizó al usuario {user_id}")
                
                # Obtener usuario actualizado
                return self.repository.get(user_id)
            else:
                logger.error(f"No se pudo actualizar el usuario {user_id}")
                return None
                
        except HTTPException:
            raise  # Re-lanzar excepciones HTTP tal cual
        except Exception as e:
            logger.error(f"Error al actualizar usuario {user_id}: {str(e)}")
            raise
    def delete_user(self, user_id: int) -> bool:
        """
        Elimina un usuario del sistema.
        
        Args:
            user_id: ID del usuario a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            return self.repository.delete(user_id)
        except Exception as e:
            logger.error(f"Error al eliminar usuario {user_id}: {str(e)}")
            return False
    
    def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """
        Lista todos los usuarios del sistema.
        
        Args:
            limit: Límite de usuarios a retornar
            offset: Desplazamiento para paginación
            
        Returns:
            List[User]: Lista de usuarios
        """
        try:
            return self.repository.list_all(limit=limit, offset=offset)
        except Exception as e:
            logger.error(f"Error al listar usuarios: {str(e)}")
            return []
    
    # ==================== AUTENTICACIÓN ====================
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Autentica un usuario con username y contraseña.
        
        Args:
            username: Nombre de usuario
            password: Contraseña en texto plano
            
        Returns:
            Optional[User]: El usuario autenticado o None si las credenciales son inválidas
        """
        try:
            # Buscar usuario
            user = self.repository.get_by_username(username)
            if not user:
                logger.warning(f"Intento de login con usuario inexistente: {username}")
                return None
            
            # Verificar contraseña
            if not verify_password(password, user.password_hash):
                logger.warning(f"Contraseña incorrecta para usuario: {username}")
                return None
            
            # Actualizar último login
            try:
                self.repository.update_last_login(user.id)
            except Exception as e:
                logger.error(f"Error actualizando último login: {str(e)}")
                # No fallar el login por esto
            
            logger.info(f"Usuario autenticado exitosamente: {username}")
            return user
            
        except Exception as e:
            logger.error(f"Error en autenticación: {str(e)}")
            return None
    
    # ==================== GESTIÓN DE ROLES ====================
    
    def update_user_role(self, user_id: int, is_admin: bool) -> bool:
        """
        Actualiza el rol de un usuario (admin o no admin).
        
        Args:
            user_id: ID del usuario
            is_admin: True si debe ser administrador, False si no
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            return self.repository.update_role(user_id, is_admin)
        except Exception as e:
            logger.error(f"Error al actualizar rol de usuario {user_id}: {str(e)}")
            return False
    
    def is_admin(self, user_id: int) -> bool:
        """
        Verifica si un usuario es administrador.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            bool: True si es administrador
        """
        try:
            user = self.repository.get(user_id)
            return user.is_admin if user else False
        except Exception as e:
            logger.error(f"Error al verificar si usuario {user_id} es admin: {str(e)}")
            return False
    
    # ==================== BÚSQUEDA ====================
    
    def search_users(self, query: str, limit: int = 100) -> List[User]:
        """
        Busca usuarios por username o email.
        
        Args:
            query: Texto a buscar
            limit: Límite de resultados
            
        Returns:
            List[User]: Lista de usuarios que coinciden
        """
        try:
            # Buscar por username
            users_by_username = self.repository.search_by_username(query, limit=limit)
            
            # Buscar por email
            users_by_email = self.repository.search_by_email(query, limit=limit)
            
            # Combinar resultados y eliminar duplicados
            all_users = users_by_username + users_by_email
            unique_users = {user.id: user for user in all_users}
            
            return list(unique_users.values())[:limit]
            
        except Exception as e:
            logger.error(f"Error al buscar usuarios con query '{query}': {str(e)}")
            return []
    
    # ==================== GESTIÓN DE CONTRASEÑAS ====================
    
    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Cambia la contraseña de un usuario.
        
        Args:
            user_id: ID del usuario
            current_password: Contraseña actual
            new_password: Nueva contraseña
            
        Returns:
            bool: True si el cambio fue exitoso
        """
        try:
            # Obtener usuario
            user = self.repository.get(user_id)
            if not user:
                return False
            
            # Verificar contraseña actual
            if not verify_password(current_password, user.password_hash):
                return False
            
            # Actualizar contraseña
            new_hash = hash_password(new_password)
            return self.repository.update_password(user_id, new_hash)
            
        except Exception as e:
            logger.error(f"Error al cambiar contraseña para usuario {user_id}: {str(e)}")
            return False
    
    def request_password_reset(self, email: str) -> bool:
        """
        Solicita un restablecimiento de contraseña.
        
        Args:
            email: Email del usuario
            
        Returns:
            bool: True si se procesó la solicitud (siempre True por seguridad)
        """
        try:
            user = self.repository.get_by_email(email)
            if not user:
                # Por seguridad, no revelar si el email existe
                logger.info(f"Solicitud de reset para email inexistente: {email}")
                return True
            
            # Generar token único
            reset_token = secrets.token_urlsafe(32)
            reset_expires = datetime.now(UTC) + timedelta(hours=1)
            
            # Hash del token para almacenar
            token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
            
            # Guardar token hasheado
            success = self.repository.store_reset_token(user.id, token_hash, reset_expires)
            
            if success:
                # Enviar email con el token sin hashear
                try:
                    email_service.send_password_reset_email(
                        to_email=email,
                        username=user.username,
                        reset_token=reset_token
                    )
                except Exception as e:
                    logger.error(f"Error enviando email de reset: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error en request_password_reset: {str(e)}")
            return True  # Siempre devolver True por seguridad
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """
        Restablece la contraseña usando un token.
        
        Args:
            token: Token de restablecimiento
            new_password: Nueva contraseña
            
        Returns:
            bool: True si el reset fue exitoso
        """
        try:
            logger.info(f"🔐 Iniciando reset de contraseña con token: {token[:10]}...")
            
            # Hash del token para buscar
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            logger.info(f"Token hasheado: {token_hash[:20]}...")
            
            # Buscar usuario por token
            user = self.repository.get_by_reset_token(token_hash)
            if not user:
                logger.warning("❌ Token de reset inválido o expirado")
                return False
            
            logger.info(f"✅ Usuario encontrado: {user.username} (ID: {user.id})")
            
            # Actualizar contraseña
            new_hash = hash_password(new_password)
            logger.info(f"🔒 Nuevo hash generado: {new_hash[:20]}...")
            
            # Verificar contraseña actual antes del cambio
            logger.info(f"Contraseña actual hash: {user.password_hash[:20] if user.password_hash else 'None'}...")
            
            success = self.repository.update_password(user.id, new_hash)
            
            if success:
                logger.info(f"✅ Contraseña actualizada en la base de datos")
                
                # Verificar que el cambio se guardó
                from src.config.database import get_supabase_client
                supabase = get_supabase_client(use_service_role=True)
                verify_response = supabase.table("users").select("password_hash").eq("id", user.id).execute()
                
                if verify_response.data and len(verify_response.data) > 0:
                    saved_hash = verify_response.data[0]['password_hash']
                    if saved_hash == new_hash:
                        logger.info(f"✅ VERIFICACIÓN: Contraseña guardada correctamente en Supabase")
                    else:
                        logger.error(f"❌ ERROR: La contraseña NO coincide después de guardar!")
                        logger.error(f"  - Esperado: {new_hash[:20]}...")
                        logger.error(f"  - Guardado: {saved_hash[:20] if saved_hash else 'None'}...")
                        return False
                
                # Limpiar token
                token_cleared = self.repository.clear_reset_token(user.id)
                if token_cleared:
                    logger.info(f"🧹 Token de reset limpiado exitosamente")
                    
                    # Verificar que realmente se limpió
                    supabase = get_supabase_client(use_service_role=True)
                    verify_token = supabase.table("users").select("reset_token, reset_token_expires").eq("id", user.id).execute()
                    if verify_token.data and len(verify_token.data) > 0:
                        token_data = verify_token.data[0]
                        if token_data['reset_token'] is None:
                            logger.info(f"✅ VERIFICACIÓN: Token limpiado correctamente")
                        else:
                            logger.error(f"❌ ERROR: Token NO se limpió correctamente!")
                            logger.error(f"  - Token aún presente: {token_data['reset_token'][:20] if token_data['reset_token'] else 'None'}...")
                else:
                    logger.error(f"❌ Error al limpiar token de reset")
                
                # Enviar email de confirmación
                try:
                    if user.email:
                        email_service.send_password_changed_email(
                            to_email=user.email,
                            username=user.username
                        )
                        logger.info(f"📧 Email de confirmación enviado a {user.email}")
                except Exception as e:
                    logger.error(f"Error enviando email de confirmación: {str(e)}")
            else:
                logger.error(f"❌ Error al actualizar contraseña en el repositorio")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error en reset_password: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    # ==================== VERIFICACIÓN DE EMAIL ====================
    
    def verify_email(self, token: str) -> bool:
        """
        Verifica el email de un usuario usando un token.
        
        Args:
            token: Token de verificación
            
        Returns:
            bool: True si la verificación fue exitosa
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Buscar usuario por token
            response = supabase.table("users")\
                .select("*")\
                .eq("verification_token", token)\
                .execute()
            
            if not response.data:
                logger.warning("Token de verificación inválido")
                return False
            
            user_data = response.data[0]
            
            # Verificar que no esté expirado
            if user_data.get('verification_token_expires'):
                expires = datetime.fromisoformat(
                    user_data['verification_token_expires'].replace('Z', '+00:00')
                )
                if datetime.now(UTC) > expires:
                    logger.warning("Token de verificación expirado")
                    return False
            
            # Marcar como verificado
            success = self.repository.update_email_verified(user_data['id'], True)
            
            if success:
                # Limpiar token
                self.repository.update(
                    self.repository.get(user_data['id']),
                    {
                        "verification_token": None,
                        "verification_token_expires": None
                    }
                )
                
                # Enviar email de bienvenida
                try:
                    if user_data.get('email'):
                        email_service.send_welcome_email(
                            to_email=user_data['email'],
                            username=user_data['username']
                        )
                except Exception as e:
                    logger.error(f"Error enviando email de bienvenida: {str(e)}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error en verify_email: {str(e)}")
            return False
    
    def resend_verification_email(self, email: str) -> bool:
        """
        Reenvía el email de verificación.
        
        Args:
            email: Email del usuario
            
        Returns:
            bool: True si se procesó la solicitud
        """
        try:
            user = self.repository.get_by_email(email)
            if not user:
                # No revelar si existe
                return True
            
            # Si ya está verificado, no hacer nada
            if getattr(user, 'email_verified', False):
                logger.info(f"Email ya verificado para: {email}")
                return True
            
            # Generar nuevo token
            verification_token = str(uuid.uuid4())
            verification_expires = datetime.now(UTC) + timedelta(hours=24)
            
            # Guardar token
            success = self.repository.update(user, {
                "verification_token": verification_token,
                "verification_token_expires": verification_expires.isoformat()
            })
            
            if success:
                # Enviar email
                try:
                    email_service.send_verification_email(
                        to_email=email,
                        username=user.username,
                        verification_token=verification_token
                    )
                except Exception as e:
                    logger.error(f"Error enviando email de verificación: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error en resend_verification_email: {str(e)}")
            return True
    
    # ==================== UTILIDADES ====================
    
    def get_user_statistics(self) -> Dict[str, int]:
        """
        Obtiene estadísticas de usuarios.
        
        Returns:
            Dict[str, int]: Diccionario con estadísticas
        """
        try:
            all_users = self.repository.list_all(limit=10000)  # Obtener todos
            
            total_users = len(all_users)
            admin_users = sum(1 for user in all_users if user.is_admin)
            regular_users = total_users - admin_users
            
            # Contar usuarios verificados
            verified_users = sum(
                1 for user in all_users 
                if getattr(user, 'email_verified', False)
            )
            
            return {
                "total_users": total_users,
                "admin_users": admin_users,
                "regular_users": regular_users,
                "verified_users": verified_users
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de usuarios: {str(e)}")
            return {
                "total_users": 0,
                "admin_users": 0,
                "regular_users": 0,
                "verified_users": 0
            }
    
    def validate_user_ids(self, user_ids: List[int]) -> Dict[str, List[int]]:
        """
        Valida una lista de IDs de usuarios.
        
        Args:
            user_ids: Lista de IDs a validar
            
        Returns:
            Dict con 'valid' e 'invalid' IDs
        """
        try:
            valid_ids = []
            invalid_ids = []
            
            for user_id in user_ids:
                user = self.repository.get(user_id)
                if user:
                    valid_ids.append(user_id)
                else:
                    invalid_ids.append(user_id)
            
            return {
                "valid": valid_ids,
                "invalid": invalid_ids
            }
            
        except Exception as e:
            logger.error(f"Error validando IDs de usuarios: {str(e)}")
            return {
                "valid": [],
                "invalid": user_ids
            }
