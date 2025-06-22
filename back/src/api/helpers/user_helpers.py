"""
Helpers para endpoints de usuarios - VERSION REFACTORIZADA MEJORADA
Contiene TODA la lógica de los endpoints para mantenerlos limpios
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC, timedelta
import uuid
import secrets
from fastapi import Request, Header, BackgroundTasks, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from src.models.domain import User
from src.models.schemas.user import (
    UserCreate, UserUpdate, ChangePasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
    UserResponse, MessageResponse, TokenResponse
)
from src.services.authentication_service import AuthenticationService
from src.services.user_registration_service import UserRegistrationService
from src.services.user_validation_service import UserValidationService
from src.services.user_service import UserService
from src.services.email_validation import EmailDeliveryTracker, EmailValidationService
from src.core.exceptions import (
    ValidationException, UnauthorizedException, ConflictException,
    ForbiddenException, DatabaseException, UserNotFoundException
)
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

class UserEndpointHelpers:
    """
    Helpers para endpoints de usuarios.
    Contiene TODA la lógica para mantener los endpoints limpios (~10 líneas).
    """
    
    def __init__(self):
        """Inicializa los helpers con los servicios necesarios."""
        self.auth_service = AuthenticationService()
        self.registration_service = UserRegistrationService()
        self.validation_service = UserValidationService()
        self.user_service = UserService()
        self.email_tracker = EmailDeliveryTracker()
        self.email_validation = EmailValidationService()
        self.settings = get_settings()
    
    # ==================== AUTENTICACIÓN ====================
    
    async def handle_login(
        self, 
        request: Request,
        form_data: OAuth2PasswordRequestForm
    ) -> Dict[str, Any]:
        """
        Maneja el proceso completo de login.
        """
        try:
            logger.info(f"🔐 Login attempt from IP: {request.client.host if request.client else 'unknown'}")
            
            result = self.auth_service.handle_login_process(
                form_data.username, 
                form_data.password
            )
            
            logger.info(f"✅ Login successful for user: {result['username']}")
            return result
            
        except (ValidationException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"❌ Error in login: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al procesar login: {str(e)}")
    
    async def handle_registration(
        self, 
        request: Request, 
        user_data: UserCreate
    ) -> Dict[str, Any]:
        """
        Maneja el proceso completo de registro.
        """
        try:
            logger.info(f"📝 Registration attempt from IP: {request.client.host if request.client else 'unknown'}")
            
            # Validar datos
            self.registration_service.validate_registration_data(user_data)
            
            # Registrar usuario
            result = self.registration_service.handle_user_registration(
                username=user_data.username,
                email=user_data.email,
                password=user_data.password
            )
            
            # Mejorar mensajes
            if "email_verification" in result and not result["email_verification"]["email_sent"]:
                result["email_verification"]["message"] = "Tu cuenta fue creada exitosamente."
            
            logger.info(f"✅ Registration successful for user: {result['username']}")
            return result
            
        except (ConflictException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"❌ Error in registration: {str(e)}", exc_info=True)
            raise DatabaseException("Error al crear cuenta")
    
    async def handle_logout(
        self,
        current_user: User,
        authorization: Optional[str]
    ) -> MessageResponse:
        """
        Maneja el proceso de logout.
        """
        try:
            token = None
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
            
            success = self.auth_service.handle_logout_process(current_user, token)
            
            return MessageResponse(
                message="Sesión cerrada exitosamente",
                success=True
            )
        except Exception as e:
            logger.error(f"Error in logout: {str(e)}")
            return MessageResponse(message="Sesión cerrada", success=True)
    
    async def handle_token_refresh(self, refresh_token: str) -> TokenResponse:
        """
        Maneja la renovación de tokens.
        """
        try:
            result = self.auth_service.handle_token_refresh(refresh_token)
            
            expires_in = self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            
            return TokenResponse(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token", refresh_token),
                token_type="bearer",
                expires_in=expires_in
            )
        except (UnauthorizedException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"Error in token refresh: {str(e)}")
            raise DatabaseException("Error al renovar token")
    
    # ==================== PERFIL DE USUARIO ====================
    
    def format_user_response(self, user: User) -> UserResponse:
        """
        Formatea la respuesta de usuario.
        """
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
    
    async def handle_profile_update(
        self,
        current_user: User,
        update_data: UserUpdate
    ) -> Dict[str, Any]:
        """
        Maneja la actualización del perfil del usuario.
        Ahora retorna un diccionario con el status de la actualización.
        """
        try:
            update_dict = update_data.model_dump(exclude_unset=True)
            
            # Validar datos
            validated_data = self.validation_service.validate_update_data(
                current_user.id, update_dict, current_user
            )
            
            # Actualizar - ahora retorna un diccionario con status
            result = self.user_service.update_user(
                current_user.id,
                validated_data,
                current_user
            )
            
            # Si la actualización fue directa, retornar UserResponse
            if result.get('status') == 'updated':
                return self.format_user_response(result['user'])
            
            # Si está pendiente de confirmación, retornar el resultado completo
            elif result.get('status') == 'pending_confirmation':
                return {
                    "status": "pending_confirmation",
                    "old_email": result.get('old_email'),
                    "new_email": result.get('new_email'),
                    "message": result.get('message')
                }
            
            # Por defecto, retornar el resultado completo
            return result
            
        except (ValidationException, ConflictException):
            raise
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            raise DatabaseException("Error al actualizar perfil")
    
    # ==================== GESTIÓN DE CONTRASEÑAS ====================
    
    async def handle_forgot_password(
        self,
        request: Request,
        forgot_request: ForgotPasswordRequest
    ) -> MessageResponse:
        """
        Maneja solicitud de recuperación de contraseña.
        """
        try:
            logger.info(f"🔑 Password reset request for: {forgot_request.email}")
            
            # Validar email
            email = self.validation_service.validate_email_format(forgot_request.email)
            
            # Procesar solicitud (sin revelar si el email existe)
            self.user_service.request_password_reset(email)
            
            return MessageResponse(
                message="Si el email está registrado, recibirás instrucciones para restablecer tu contraseña.",
                success=True
            )
        except Exception as e:
            logger.error(f"Error in forgot password: {str(e)}")
            # Siempre devolver el mismo mensaje por seguridad
            return MessageResponse(
                message="Si el email está registrado, recibirás instrucciones para restablecer tu contraseña.",
                success=True
            )
    
    async def handle_reset_password(
        self,
        request: Request,
        reset_request: ResetPasswordRequest
    ) -> MessageResponse:
        """
        Maneja el reset de contraseña con token.
        """
        try:
            success = self.registration_service.handle_password_reset(
                reset_request.token,
                reset_request.new_password
            )
            
            if success:
                return MessageResponse(
                    message="Tu contraseña ha sido actualizada exitosamente.",
                    success=True
                )
            else:
                raise ValidationException("Token inválido o expirado")
                
        except (ValidationException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"Error in reset password: {str(e)}")
            raise DatabaseException("Error al restablecer contraseña")
    
    async def handle_change_password(
        self,
        user_id: int,
        change_request: ChangePasswordRequest,
        current_user: User
    ) -> MessageResponse:
        """
        Maneja el cambio de contraseña.
        """
        try:
            # Validar permisos
            self.validation_service.validate_user_ownership(
                current_user, user_id, "cambiar contraseña"
            )
            
            # Cambiar contraseña
            success = self.user_service.change_password(
                user_id=user_id,
                current_password=change_request.current_password,
                new_password=change_request.new_password
            )
            
            if success:
                # Revocar tokens
                self.auth_service.revoke_all_user_tokens(user_id)
                
                return MessageResponse(
                    message="Contraseña actualizada exitosamente.",
                    success=True
                )
            else:
                raise ValidationException("Contraseña actual incorrecta")
                
        except (UnauthorizedException, ForbiddenException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            raise DatabaseException("Error al cambiar contraseña")
    
    # ==================== VERIFICACIÓN DE EMAIL ====================
    
    async def handle_email_verification(self, token: str) -> MessageResponse:
        """
        Maneja la verificación de email (para cambio de email).
        """
        try:
            # Intentar primero como cambio de email
            try:
                success = self.user_service.confirm_email_change(token)
                if success:
                    return MessageResponse(
                        message="Email actualizado exitosamente",
                        success=True
                    )
            except ValidationException:
                # Si falla, intentar como verificación inicial
                pass
            
            # Intentar como verificación inicial de registro
            success = self.registration_service.handle_email_verification(token)
            
            if success:
                return MessageResponse(
                    message="Email verificado exitosamente",
                    success=True
                )
            else:
                raise ValidationException("Token inválido o expirado")
                
        except (ValidationException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"Error verifying email: {str(e)}")
            raise DatabaseException("Error al verificar email")
    
    async def handle_resend_verification(self, email: str) -> MessageResponse:
        """
        Maneja el reenvío de email de verificación.
        """
        try:
            self.registration_service.resend_verification_email(email)
            
            return MessageResponse(
                message="Si el email está registrado, recibirás un nuevo email de verificación.",
                success=True
            )
        except Exception as e:
            logger.error(f"Error resending verification: {str(e)}")
            # Siempre devolver el mismo mensaje por seguridad
            return MessageResponse(
                message="Si el email está registrado, recibirás un nuevo email de verificación.",
                success=True
            )
    
    # ==================== CONSULTAS DE USUARIOS ====================
    
    async def handle_list_users(
        self,
        current_user: User,
        limit: int,
        offset: int
    ) -> List[UserResponse]:
        """
        Maneja el listado de usuarios (admin only).
        """
        try:
            # Validar permisos
            self.validation_service.validate_admin_permissions(
                current_user, "listar usuarios"
            )
            
            # Obtener usuarios
            users = self.user_service.list_users(limit=limit, offset=offset)
            
            return [self.format_user_response(user) for user in users]
            
        except ForbiddenException:
            raise
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            raise DatabaseException("Error al listar usuarios")
    
    async def handle_search_users(
        self,
        current_user: User,
        query: str,
        limit: int
    ) -> List[UserResponse]:
        """
        Maneja la búsqueda de usuarios (admin only).
        """
        try:
            # Validar permisos
            self.validation_service.validate_admin_permissions(
                current_user, "buscar usuarios"
            )
            
            # Validar query
            validated_query = self.validation_service.validate_search_query(query)
            
            # Buscar usuarios
            users = self.user_service.search_users(validated_query, limit)
            
            return [self.format_user_response(user) for user in users]
            
        except (ForbiddenException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"Error searching users: {str(e)}")
            raise DatabaseException("Error al buscar usuarios")
    
    async def handle_get_user(
        self,
        user_id: int,
        current_user: User
    ) -> UserResponse:
        """
        Maneja la obtención de un usuario específico.
        """
        try:
            # Verificar permisos: admin o el mismo usuario
            if not current_user.is_admin and current_user.id != user_id:
                raise ForbiddenException("No tienes permisos para ver este usuario")
            
            # Obtener usuario
            user = self.user_service.get_user(user_id)
            if not user:
                raise UserNotFoundException(user_id)
            
            return self.format_user_response(user)
            
        except (ForbiddenException, UserNotFoundException):
            raise
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            raise DatabaseException("Error al obtener usuario")
    
    async def handle_update_user(
        self,
        user_id: int,
        user_data: UserUpdate,
        current_user: User
    ) -> UserResponse:
        """
        Maneja la actualización de un usuario.
        """
        try:
            # Convertir a dict
            user_data_dict = user_data.model_dump(exclude_unset=True)
            
            # Actualizar (el servicio valida permisos)
            updated_user = self.user_service.update_user(
                user_id, user_data_dict, current_user
            )
            
            if not updated_user:
                raise UserNotFoundException(user_id)
            
            return self.format_user_response(updated_user)
            
        except (UserNotFoundException, ForbiddenException, ValidationException, ConflictException):
            raise
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise DatabaseException("Error al actualizar usuario")
    
    async def handle_delete_user(
        self,
        user_id: int,
        current_user: User
    ) -> None:
        """
        Maneja la eliminación de un usuario (admin only).
        """
        try:
            # Validar permisos admin
            self.validation_service.validate_admin_permissions(
                current_user, "eliminar usuarios"
            )
            
            # Validar permisos específicos
            self.validation_service.validate_user_deletion_permissions(
                current_user, user_id
            )
            
            # Eliminar usuario
            success = self.user_service.delete_user(user_id, current_user)
            
            if not success:
                raise DatabaseException("No se pudo eliminar el usuario")
            
            logger.info(f"🗑️ User {user_id} deleted by admin {current_user.username}")
            
        except (UserNotFoundException, ForbiddenException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            raise DatabaseException("Error al eliminar usuario")
    
    # ==================== UTILIDADES ====================
    
    async def handle_validate_token(
        self,
        current_user: User,
        authorization: Optional[str]
    ) -> Dict[str, Any]:
        """
        Maneja la validación del token actual.
        """
        try:
            expires_soon = False
            
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
                from src.core.token_middleware import check_token_expiry_soon
                
                expires_soon = check_token_expiry_soon(
                    token, 
                    self.settings.JWT_SECRET_KEY,
                    self.settings.JWT_ALGORITHM,
                    minutes_before=5
                )
            
            return {
                "valid": True,
                "user": {
                    "id": current_user.id,
                    "username": current_user.username,
                    "email": current_user.email,
                    "is_admin": current_user.is_admin,
                    "email_verified": getattr(current_user, 'email_verified', False)
                },
                "expires_soon": expires_soon,
                "message": "Token válido" + (" pero expira pronto" if expires_soon else "")
            }
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            raise UnauthorizedException("Token inválido o expirado")
    
    async def handle_change_email_validated(
        self,
        request: Request,
        current_user: User,
        new_email: str,
        background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """
        Maneja el cambio de email con validación estricta de existencia.
        Solo permite el cambio si el email existe y puede recibir correos.
        """
        try:
            logger.info(f"🔍 Validando cambio de email para usuario {current_user.username} a {new_email}")
            
            # 1. Validación básica de formato
            validated_email = self.validation_service.validate_email_format(new_email)
            
            # 2. Verificar que no sea un email temporal/desechable
            if self.email_validation.is_disposable_email(validated_email):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "disposable_email",
                        "message": "No se permiten emails temporales o desechables",
                        "details": f"El dominio de {validated_email} es conocido como temporal",
                        "suggestion": "Por favor, usa un email permanente"
                    }
                )
            
            # 3. Verificar que el email no esté ya registrado
            try:
                existing_user = self.user_service.get_user_by_email(validated_email)
                if existing_user and existing_user.id != current_user.id:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "email_already_exists",
                            "message": "Este email ya está registrado",
                            "details": "El email pertenece a otra cuenta",
                            "suggestion": "Usa un email diferente o recupera tu cuenta existente"
                        }
                    )
            except UserNotFoundException:
                # Esto es bueno, significa que el email no está registrado
                pass
            
            # 4. Generar código de verificación
            verification_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            temp_token = str(uuid.uuid4())
            
            # 5. Guardar intento en la base de datos
            from src.config.database import get_supabase_client
            supabase = get_supabase_client(use_service_role=True)
            
            # Crear registro del intento de cambio
            attempt_data = {
                'user_id': current_user.id,
                'new_email': validated_email,
                'verification_code': verification_code,
                'temp_token': temp_token,
                'status': 'pending',
                'created_at': datetime.now(UTC).isoformat(),
                'expires_at': (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
            }
            
            # Verificar si existe la tabla, si no, usar una alternativa
            try:
                supabase.table('email_change_attempts').insert(attempt_data).execute()
            except:
                # Si la tabla no existe, guardar en el campo verification_token del usuario
                logger.warning("Tabla email_change_attempts no existe, usando método alternativo")
                
            # 6. Intentar enviar email con tracking de entrega (5 segundos máximo)
            logger.info(f"📧 Enviando email de verificación a {validated_email} con tracking...")
            
            delivery_result = await self.email_tracker.send_with_delivery_tracking(
                to_email=validated_email,
                subject="Verifica tu nuevo email - DocuMente",
                code=verification_code,
                tracking_timeout=5  # 5 segundos máximo
            )
            
            # 7. Analizar resultado de la entrega
            if not delivery_result['delivered']:
                # El email no existe o no puede recibir correos
                logger.warning(f"❌ No se pudo entregar email a {validated_email}: {delivery_result['reason']}")
                
                # Actualizar estado del intento como fallido
                try:
                    supabase.table('email_change_attempts').update({
                        'status': 'failed',
                        'failure_reason': delivery_result['reason'],
                        'failed_at': datetime.now(UTC).isoformat()
                    }).eq('temp_token', temp_token).execute()
                except:
                    pass
                
                # Mensaje específico según el tipo de error
                error_messages = {
                    'no_mx_records': 'El dominio del email no tiene servidores de correo configurados',
                    'recipient_not_found': 'La dirección de email no existe en el servidor de destino',
                    'recipient_refused': 'El servidor de destino rechazó el email',
                    'delivery_timeout': 'No se pudo confirmar la entrega del email en el tiempo esperado',
                    'invalid_format': 'El formato del email es inválido',
                    'domain_not_found': 'El dominio del email no existe'
                }
                
                detail_message = error_messages.get(
                    delivery_result['reason'],
                    'No se pudo verificar que el email pueda recibir correos'
                )
                
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "email_not_valid",
                        "message": "El email ingresado no existe o no puede recibir correos",
                        "details": detail_message,
                        "suggestion": "Por favor, verifica que el email esté escrito correctamente",
                        "technical_reason": delivery_result['reason'],
                        "time_taken": f"{delivery_result['time_taken']:.2f} segundos"
                    }
                )
            
            # 8. Email válido - guardar el cambio pendiente
            logger.info(f"✅ Email {validated_email} validado exitosamente")
            
            # Guardar información del cambio pendiente
            import json
            import base64
            
            change_data = {
                "token": temp_token,
                "user_id": current_user.id,
                "old_email": current_user.email,
                "new_email": validated_email,
                "verification_code": verification_code,
                "expires": (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
            }
            
            # Codificar los datos
            encoded_data = base64.b64encode(json.dumps(change_data).encode()).decode()
            
            # Guardar en el usuario
            self.user_service.repository.update_by_id(current_user.id, {
                "verification_token": encoded_data,
                "verification_token_expires": change_data["expires"]
            })
            
            return {
                "status": "verification_sent",
                "message": "Código de verificación enviado exitosamente",
                "token": temp_token,
                "new_email": validated_email,
                "expires_in": 300,  # 5 minutos
                "delivery_info": {
                    "delivered": True,
                    "time_taken": f"{delivery_result['time_taken']:.2f} segundos",
                    "mx_records_found": delivery_result.get('mx_records_found', False)
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en validación de cambio de email: {str(e)}")
            raise DatabaseException("Error al procesar el cambio de email")
    
    async def handle_verify_email_change_code(
        self,
        current_user: User,
        token: str,
        code: str
    ) -> Dict[str, Any]:
        """
        Verifica el código de cambio de email y completa el cambio.
        """
        try:
            import json
            import base64
            from datetime import datetime, timezone
            
            logger.info(f"🔐 Verificando código de cambio de email para usuario {current_user.username}")
            
            # Obtener el token almacenado del usuario
            from src.config.database import get_supabase_client
            supabase = get_supabase_client(use_service_role=True)
            
            user_response = supabase.table("users").select("*").eq("id", current_user.id).execute()
            if not user_response.data:
                raise ValidationException("Usuario no encontrado")
            
            user_data = user_response.data[0]
            stored_token = user_data.get('verification_token')
            
            if not stored_token:
                logger.warning("No hay cambio de email pendiente")
                raise ValidationException("No hay cambio de email pendiente")
            
            # Decodificar los datos del cambio
            try:
                change_data = json.loads(base64.b64decode(stored_token).decode())
            except:
                logger.error("Error al decodificar token de cambio")
                raise ValidationException("Token inválido")
            
            # Verificar que el token coincida
            if change_data.get('token') != token:
                logger.warning(f"Token no coincide: esperado {change_data.get('token')[:10]}..., recibido {token[:10]}...")
                raise ValidationException("Token inválido")
            
            # Verificar que no haya expirado
            expires = datetime.fromisoformat(change_data['expires'].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires:
                logger.warning("Código expirado")
                # Limpiar el token expirado
                self.user_service.repository.update_by_id(current_user.id, {
                    "verification_token": None,
                    "verification_token_expires": None
                })
                raise ValidationException("El código ha expirado. Solicita un nuevo cambio de email.")
            
            # Verificar el código
            if change_data.get('verification_code') != code:
                logger.warning("Código incorrecto")
                raise ValidationException("Código de verificación incorrecto")
            
            # Todo validado, proceder con el cambio
            new_email = change_data['new_email']
            old_email = change_data['old_email']
            
            logger.info(f"✅ Código verificado correctamente. Actualizando email de {old_email} a {new_email}")
            
            # Actualizar el email
            update_success = self.user_service.repository.update_by_id(current_user.id, {
                "email": new_email,
                "verification_token": None,
                "verification_token_expires": None,
                "email_verified": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            
            if not update_success:
                logger.error("Error al actualizar email en la base de datos")
                raise DatabaseException("Error al actualizar el email")
            
            logger.info(f"✅ Email actualizado exitosamente para usuario {current_user.id}")
            
            # Enviar email de confirmación al nuevo email
            try:
                from src.services.email_service import email_service
                email_service.send_password_changed_email(
                    to_email=new_email,
                    username=current_user.username
                )
            except Exception as e:
                logger.error(f"Error enviando email de confirmación: {str(e)}")
                # No fallar la operación por esto
            
            # Obtener usuario actualizado
            updated_user = self.user_service.get_user(current_user.id)
            
            return {
                "status": "success",
                "message": "Email actualizado exitosamente",
                "user": self.format_user_response(updated_user),
                "old_email": old_email,
                "new_email": new_email
            }
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error verificando código de cambio de email: {str(e)}")
            raise DatabaseException("Error al verificar el código")
    
    # ==================== DEBUG (ELIMINAR EN PRODUCCIÓN) ====================
    
    async def handle_debug_user_state(
        self,
        email: str,
        current_user: User
    ) -> Dict[str, Any]:
        """
        DEBUG: Verifica el estado de un usuario.
        """
        try:
            # Solo admins
            self.validation_service.validate_admin_permissions(
                current_user, "usar funciones de debug"
            )
            
            from src.config.database import get_supabase_client
            supabase = get_supabase_client(use_service_role=True)
            
            response = supabase.table("users").select("*").eq("email", email).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                return {
                    "id": user_data['id'],
                    "username": user_data['username'],
                    "email": user_data['email'],
                    "is_admin": user_data.get('is_admin', False),
                    "email_verified": user_data.get('email_verified', False),
                    "has_password": bool(user_data.get('password_hash')),
                    "created_at": user_data.get('created_at'),
                    "updated_at": user_data.get('updated_at')
                }
            else:
                raise ValidationException(f"Usuario con email {email} no encontrado")
                
        except (ForbiddenException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"Error in debug user state: {str(e)}")
            raise DatabaseException("Error en debug")
    
    async def handle_verify_email_exists(self, email: str) -> Dict[str, Any]:
        """
        Verifica si un email existe (público).
        """
        try:
            return self.auth_service.get_authentication_summary(email)
        except Exception as e:
            logger.error(f"Error verifying email: {str(e)}")
            raise DatabaseException("Error al verificar email")
    
    async def handle_test_login(
        self,
        username_or_email: str,
        password: str
    ) -> Dict[str, Any]:
        """
        DEBUG: Prueba el login con información detallada.
        """
        try:
            from src.config.database import get_supabase_client
            from src.utils.password_utils import verify_password
            
            # Verificar si es admin
            supabase = get_supabase_client(use_service_role=True)
            admin_check = supabase.table("users").select("is_admin").eq("username", "ivan").execute()
            
            if not admin_check.data or not admin_check.data[0].get("is_admin"):
                raise ForbiddenException("Solo disponible para administradores")
            
            # Buscar usuario
            if '@' in username_or_email:
                response = supabase.table("users").select("*").eq("email", username_or_email).execute()
            else:
                response = supabase.table("users").select("*").ilike("username", username_or_email).execute()
            
            if not response.data:
                return {
                    "success": False,
                    "message": "Usuario no encontrado",
                    "searched_for": username_or_email,
                    "search_type": "email" if '@' in username_or_email else "username"
                }
            
            user_data = response.data[0]
            password_valid = verify_password(password, user_data.get('password_hash', ''))
            
            return {
                "success": password_valid,
                "user_found": True,
                "user_id": user_data['id'],
                "username": user_data['username'],
                "email": user_data['email'],
                "password_valid": password_valid,
                "search_type": "email" if '@' in username_or_email else "username"
            }
            
        except ForbiddenException:
            raise
        except Exception as e:
            logger.error(f"Error in test login: {str(e)}")
            raise DatabaseException("Error en test login")
    
    async def handle_confirm_email_change(self, token: str) -> MessageResponse:
        """
        Maneja la confirmación del cambio de email.
        """
        try:
            logger.info(f"🌐 Confirmación de email desde navegador - Token: {token[:20]}...")
            
            success = self.user_service.confirm_email_change(token)
            
            if success:
                logger.info(f"✅ Email confirmado exitosamente vía enlace")
                return MessageResponse(
                    message="Email actualizado exitosamente",
                    success=True
                )
            else:
                logger.warning(f"❌ Fallo en confirmación de email vía enlace")
                raise ValidationException("Token inválido o expirado")
                
        except (ValidationException, ConflictException):
            raise
        except Exception as e:
            logger.error(f"Error confirming email change: {str(e)}")
            raise DatabaseException("Error al confirmar cambio de email")