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

# Importar excepciones personalizadas
from src.core.exceptions import (
    UserNotFoundException,
    ValidationException,
    ConflictException,
    ForbiddenException,
    DatabaseException,
    UnauthorizedException
)

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
            ValidationException: Si los datos son inválidos
            ConflictException: Si el username o email ya existen
            DatabaseException: Si hay error en la base de datos
        """
        try:
            
            # El repositorio se encarga de todas las validaciones y lanza las excepciones apropiadas
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
    
    def get_user(self, user_id: int) -> User:
        """
        Obtiene un usuario por su ID.
        
        Args:
            user_id: ID del usuario a obtener
            
        Returns:
            User: El usuario encontrado
            
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error en la base de datos
        """
        return self.repository.get(user_id)
    
    def get_by_id(self, user_id: int) -> User:
        """
        Obtiene un usuario por su ID (síncrono - NO usar await).
        
        Args:
            user_id: ID del usuario a obtener
            
        Returns:
            User: El usuario encontrado
            
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error en la base de datos
        """
        logger.info(f"=== UserService.get_by_id ===")
        logger.info(f"Buscando usuario con ID: {user_id}")
        
        user = self.repository.get(user_id)
        logger.info(f"✅ Usuario encontrado: ID={user_id}, username={user.username}")
        return user
    
    def get_user_by_username(self, username: str) -> User:
        """
        Obtiene un usuario por su nombre de usuario.
        
        Args:
            username: Nombre de usuario a buscar
            
        Returns:
            User: El usuario encontrado
            
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error en la base de datos
        """
        return self.repository.get_by_username_strict(username)
    
    def get_user_by_email(self, email: str) -> User:
        """
        Obtiene un usuario por su email.
        
        Args:
            email: Email del usuario
            
        Returns:
            User: El usuario encontrado
            
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error en la base de datos
        """
        return self.repository.get_by_email_strict(email)
    
    def update_user(self, user_id: int, user_data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
        """
        Actualiza un usuario existente con validación de permisos.
        Si se cambia el email, requiere confirmación (excepto para admin).
        
        Args:
            user_id: ID del usuario a actualizar
            user_data: Diccionario con los campos a actualizar
            current_user: Usuario que está realizando la actualización
            
        Returns:
            Dict[str, Any]: Resultado de la actualización con status
            
        Raises:
            ForbiddenException: Si no tiene permisos
            UserNotFoundException: Si el usuario no existe
            ConflictException: Si el username o email ya existen
            DatabaseException: Si hay error en la base de datos
        """
        try:
            # 1. VALIDAR PERMISOS
            if not current_user.is_admin and current_user.id != user_id:
                raise ForbiddenException("No tienes permisos para actualizar este usuario")
            
            # 2. Obtener usuario actual - lanzará UserNotFoundException si no existe
            user = self.repository.get(user_id)
            
            # Guardar email anterior para comparación
            old_email = user.email
            email_is_changing = 'email' in user_data and user_data['email'] != old_email
            
            # Si se está actualizando el username, verificar que no exista
            if 'username' in user_data and user_data['username'] != user.username:
                existing = self.repository.get_by_username(user_data['username'])
                if existing:
                    raise ConflictException(f"El nombre de usuario '{user_data['username']}' ya está en uso")
            
            # Si se está actualizando el email, verificar que no exista
            if email_is_changing:
                existing = self.repository.get_by_email(user_data['email'])
                if existing:
                    raise ConflictException(f"El email '{user_data['email']}' ya está registrado")
            
            # Si es admin o no hay cambio de email, actualizar directamente
            if current_user.is_admin or not email_is_changing:
                # Actualizar usuario - lanzará DatabaseException si falla
                self.repository.update(user, user_data)
                
                # 3. AGREGAR AUDITORÍA
                logger.info(f"Usuario {current_user.username} (ID: {current_user.id}) actualizó al usuario {user_id}")
                
                # Obtener usuario actualizado
                updated_user = self.repository.get(user_id)
                return {
                    "status": "updated",
                    "user": updated_user,
                    "message": "Perfil actualizado exitosamente"
                }
            
            # Si hay cambio de email y NO es admin, requerir confirmación
            else:
                new_email = user_data['email']
                
                # Generar token de confirmación
                confirmation_token = str(uuid.uuid4())
                confirmation_expires = datetime.now(UTC) + timedelta(hours=24)
                
                # Guardar temporalmente los datos del cambio pendiente
                # Usaremos los campos de verification_token para esto
                pending_data = {
                    "verification_token": confirmation_token,
                    "verification_token_expires": confirmation_expires.isoformat()
                }
                
                # Guardar el nuevo email en un campo temporal o en memoria
                # Por ahora lo incluiremos en el token de forma segura
                import json
                import base64
                
                token_data = {
                    "token": confirmation_token,
                    "user_id": user_id,
                    "old_email": old_email,
                    "new_email": new_email,
                    "expires": confirmation_expires.isoformat()
                }
                
                # Codificar los datos del token
                encoded_data = base64.b64encode(json.dumps(token_data).encode()).decode()
                
                # Guardar el token en la BD
                self.repository.update(user, {
                    "verification_token": encoded_data,
                    "verification_token_expires": confirmation_expires.isoformat()
                })
                
                # Actualizar otros campos que no son el email
                other_updates = {k: v for k, v in user_data.items() if k != 'email'}
                if other_updates:
                    self.repository.update(user, other_updates)
                
                # Enviar email de confirmación al email ANTERIOR
                try:
                    email_service.send_email_change_notification(
                        old_email=old_email,
                        new_email=new_email,
                        username=user.username,
                        confirmation_token=confirmation_token
                    )
                    logger.info(f"Email de confirmación enviado a {old_email} para cambio a {new_email}")
                except Exception as e:
                    logger.error(f"Error enviando email de confirmación: {str(e)}")
                    # Limpiar el token si falla el envío
                    self.repository.update(user, {
                        "verification_token": None,
                        "verification_token_expires": None
                    })
                    raise DatabaseException("Error al enviar email de confirmación")
                
                return {
                    "status": "pending_confirmation",
                    "old_email": old_email,
                    "new_email": new_email,
                    "verification_token": confirmation_token,  # Incluir el token UUID
                    "message": f"Se ha enviado un email de confirmación a {old_email}. Por favor, revisa tu correo."
                }
                
        except (ForbiddenException, UserNotFoundException, ConflictException, DatabaseException):
            raise  # Re-lanzar excepciones conocidas
        except Exception as e:
            logger.error(f"Error inesperado al actualizar usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al actualizar usuario", original_error=e)
    
    def confirm_email_change(self, token: str) -> bool:
        """
        Confirma el cambio de email usando el token de confirmación.
        
        Args:
            token: Token de confirmación
            
        Returns:
            bool: True si el cambio fue exitoso
            
        Raises:
            ValidationException: Si el token es inválido o expiró
            DatabaseException: Si hay error en la base de datos
        """
        try:
            import json
            import base64
            from datetime import datetime, timezone
            
            logger.info(f"🔍 Token recibido para verificación: {token[:20]}...")
            
            # Buscar usuarios con tokens activos
            supabase = get_supabase_client(use_service_role=True)
            # Obtener todos los usuarios y filtrar en Python los que tienen token
            response = supabase.table("users").select("*").execute()
            
            # Filtrar usuarios con tokens no nulos
            users_with_tokens = [user for user in response.data if user.get('verification_token')]
            
            if not users_with_tokens:
                logger.warning("❌ No se encontraron usuarios con tokens activos")
                raise ValidationException("Token inválido o expirado")
            
            logger.info(f"📋 Encontrados {len(users_with_tokens)} usuarios con tokens de verificación")
            
            # Buscar el token que coincida
            user_data = None
            token_data = None
            
            for user in users_with_tokens:
                try:
                    # Decodificar el token almacenado
                    stored_token = user.get('verification_token')
                    if not stored_token:
                        continue
                        
                    decoded = json.loads(base64.b64decode(stored_token).decode())
                    stored_uuid = decoded.get('token')
                    
                    logger.debug(f"Comparando token almacenado: {stored_uuid[:20]}... con {token[:20]}...")
                    
                    # Verificar si el token coincide
                    if stored_uuid == token:
                        logger.info(f"✅ Token encontrado para usuario {user.get('username')} (ID: {user.get('id')})")
                        user_data = user
                        token_data = decoded
                        break
                except Exception as e:
                    logger.warning(f"Error procesando token para usuario {user.get('id')}: {e}")
                    continue
            
            # Si no se encontró por UUID, intentar búsqueda directa (por si el token está codificado)
            if not user_data:
                try:
                    direct_response = supabase.table("users").select("*").eq("verification_token", token).execute()
                    if direct_response.data and len(direct_response.data) > 0:
                        logger.info(f"✅ Usuario encontrado por búsqueda directa")
                        user_data = direct_response.data[0]
                        # Si llegamos aquí, el token ya está codificado, decodificarlo
                        decoded = json.loads(base64.b64decode(user_data['verification_token']).decode())
                        token_data = decoded
                except Exception as e:
                    logger.debug(f"Búsqueda directa falló: {e}")
            
            if not user_data or not token_data:
                logger.warning("❌ Token no encontrado en ninguna búsqueda")
                raise ValidationException("Token inválido o expirado")
            
            # Verificar que no haya expirado
            expires = datetime.fromisoformat(token_data['expires'].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires:
                logger.warning(f"❌ Token expirado para usuario {user_data['id']}")
                # Limpiar el token expirado
                self.repository.update_by_id(user_data['id'], {
                    "verification_token": None,
                    "verification_token_expires": None
                })
                raise ValidationException("El token ha expirado")
            
            # Verificar que el email nuevo siga disponible
            new_email = token_data['new_email']
            old_email = token_data.get('old_email', user_data['email'])
            
            existing = self.repository.get_by_email(new_email)
            if existing and existing.id != user_data['id']:
                raise ConflictException(f"El email '{new_email}' ya está registrado")
            
            logger.info(f"✅ Token válido para usuario: {user_data['username']} (ID: {user_data['id']})")
            logger.info(f"📧 Actualizando email de {old_email} a {new_email}")
            
            # Actualizar el email
            update_success = self.repository.update_by_id(user_data['id'], {
                "email": new_email,
                "verification_token": None,
                "verification_token_expires": None,
                "email_verified": True,  # Marcar como verificado
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            
            if update_success:
                logger.info(f"✅ Email actualizado exitosamente para usuario {user_data['id']}")
                
                # Enviar email de confirmación al NUEVO email
                try:
                    if new_email:
                        # Nota: Cambiar este método si quieres un email específico para cambio de email
                        email_service.send_password_changed_email(
                            to_email=new_email,
                            username=user_data['username']
                        )
                        logger.info(f"📧 Email de confirmación enviado a {new_email}")
                except Exception as e:
                    logger.error(f"Error enviando email de confirmación: {str(e)}")
                    # No fallar la operación por esto
            else:
                logger.error(f"❌ Error al actualizar el email en la base de datos")
            
            return update_success
            
        except (ValidationException, ConflictException):
            raise
        except Exception as e:
            logger.error(f"❌ Error no controlado en confirm_email_change: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise DatabaseException("Error al confirmar cambio de email", original_error=e)
    
    def delete_user(self, user_id: int, current_user: User) -> bool:
        """
        Elimina un usuario del sistema. Solo administradores pueden eliminar usuarios.
        
        Args:
            user_id: ID del usuario a eliminar
            current_user: Usuario que está realizando la eliminación
            
        Returns:
            bool: True si se eliminó correctamente
            
        Raises:
            ForbiddenException: Si no tiene permisos
            UserNotFoundException: Si el usuario no existe
            ValidationException: Si intenta eliminarse a sí mismo
            DatabaseException: Si hay error en la base de datos
        """
        try:
            # Validar permisos - solo administradores pueden eliminar usuarios
            if not current_user.is_admin:
                raise ForbiddenException("Solo los administradores pueden eliminar usuarios")
                
            # Verificar que el usuario existe - lanzará UserNotFoundException si no existe
            user_to_delete = self.repository.get(user_id)
                
            # No permitir que un usuario se elimine a sí mismo
            if current_user.id == user_id:
                raise ValidationException("No puedes eliminarte a ti mismo")
                
            # Realizar la eliminación - lanzará DatabaseException si falla
            self.repository.delete(user_id)
            
            logger.info(f"Usuario {current_user.username} (ID: {current_user.id}) eliminó al usuario ID: {user_id}")
            return True
            
        except (ForbiddenException, UserNotFoundException, ValidationException, DatabaseException):
            raise  # Re-lanzar excepciones conocidas
        except Exception as e:
            logger.error(f"Error inesperado al eliminar usuario {user_id}: {str(e)}")
            raise DatabaseException("Error interno al eliminar usuario", original_error=e)
    
    def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """
        Lista todos los usuarios del sistema.
        
        Args:
            limit: Límite de usuarios a retornar
            offset: Desplazamiento para paginación
            
        Returns:
            List[User]: Lista de usuarios
            
        Raises:
            DatabaseException: Si hay error en la base de datos
        """
        return self.repository.list_all(limit=limit, offset=offset)
    
    # ==================== AUTENTICACIÓN ====================
    
    def authenticate_user(self, username: str, password: str) -> User:
        """
        Autentica un usuario con username y contraseña.
        
        Args:
            username: Nombre de usuario
            password: Contraseña en texto plano
            
        Returns:
            User: El usuario autenticado
            
        Raises:
            UnauthorizedException: Si las credenciales son inválidas
            DatabaseException: Si hay error en la base de datos
        """
        try:
            # Buscar usuario
            user = self.repository.get_by_username(username)
            if not user:
                logger.warning(f"Intento de login con usuario inexistente: {username}")
                raise UnauthorizedException("Credenciales inválidas")
            
            # Verificar contraseña
            if not verify_password(password, user.password_hash):
                logger.warning(f"Contraseña incorrecta para usuario: {username}")
                raise UnauthorizedException("Credenciales inválidas")
            
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
            
        Raises:
            UserNotFoundException: Si el usuario no existe
            DatabaseException: Si hay error en la base de datos
        """
        return self.repository.update_role(user_id, is_admin)
    
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
            return user.is_admin
        except UserNotFoundException:
            return False
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
            
        Raises:
            DatabaseException: Si hay error en la base de datos
        """
        # Buscar por username
        users_by_username = self.repository.search_by_username(query, limit=limit)
        
        # Buscar por email
        users_by_email = self.repository.search_by_email(query, limit=limit)
        
        # Combinar resultados y eliminar duplicados
        all_users = users_by_username + users_by_email
        unique_users = {user.id: user for user in all_users}
        
        return list(unique_users.values())[:limit]
    
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
            
        Raises:
            UserNotFoundException: Si el usuario no existe
            UnauthorizedException: Si la contraseña actual es incorrecta
            DatabaseException: Si hay error en la base de datos
        """
        try:
            # Obtener usuario - lanzará UserNotFoundException si no existe
            user = self.repository.get(user_id)
            
            # Verificar contraseña actual
            if not verify_password(current_password, user.password_hash):
                raise UnauthorizedException("Contraseña actual incorrecta")
            
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
            logger.info(f"📧 Actualizando email_verified=TRUE para usuario ID: {user_data['id']}")
            success = self.repository.update_email_verified(user_data['id'], True)
            
            if success:
                logger.info(f"✅ Campo email_verified actualizado exitosamente para usuario {user_data['username']}")
                
                # Verificar que realmente se actualizó
                supabase = get_supabase_client(use_service_role=True)
                verify = supabase.table("users").select("email_verified").eq("id", user_data['id']).execute()
                if verify.data and len(verify.data) > 0:
                    actual_value = verify.data[0]['email_verified']
                    logger.info(f"🔍 VERIFICACIÓN: email_verified = {actual_value}")
                    if not actual_value:
                        logger.error(f"❌ ERROR: email_verified NO se actualizó correctamente!")
                # Limpiar token
                self.repository.update(
                    self.repository.get(user_data['id']),
                    {
                        "verification_token": None,
                        "verification_token_expires": None
                    }
                )
                
                # Email de bienvenida removido - ya no se envia automaticamente
                logger.info(f"Email verificado exitosamente para {user_data['username']} - No se envia email adicional")
            
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
            
        except DatabaseException as e:
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
                if self.repository.exists(user_id):
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
