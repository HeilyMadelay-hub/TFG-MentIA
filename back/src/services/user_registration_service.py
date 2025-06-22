"""
Servicio de registro de usuarios - VERSION REFACTORIZADA
Maneja toda la lógica específica de registro de usuarios
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import uuid4

from src.models.schemas.user import UserCreate
from src.models.domain import User
from src.services.auth_service import AuthService
from src.services.user_validation_service import UserValidationService
from src.services.email_service import email_service
from src.repositories.user_repository import UserRepository
from src.core.exceptions import (
    ValidationException, ConflictException, DatabaseException
)

logger = logging.getLogger(__name__)

class UserRegistrationService:
    """
    Servicio especializado para el registro de usuarios.
    Separa toda la lógica de registro del endpoint principal.
    """
    
    def __init__(
        self, 
        auth_service: Optional[AuthService] = None,
        validation_service: Optional[UserValidationService] = None,
        repository: Optional[UserRepository] = None
    ):
        """Inicializa el servicio con sus dependencias."""
        self.auth_service = auth_service or AuthService()
        self.validation_service = validation_service or UserValidationService()
        self.repository = repository or UserRepository()
    
    def handle_user_registration(
        self, 
        username: str, 
        email: str, 
        password: str
    ) -> Dict[str, Any]:
        """
        Maneja el proceso completo de registro de usuario.
        
        Args:
            username: Nombre de usuario
            email: Email del usuario
            password: Contraseña
            
        Returns:
            Dict[str, Any]: Datos del usuario registrado con tokens
            
        Raises:
            ValidationException: Si los datos son inválidos
            ConflictException: Si el usuario ya existe
            DatabaseException: Si hay error en la base de datos
        """
        try:
            logger.info(f"🚀 Iniciando registro para usuario: {username}")
            
            # 1. Validar todos los datos de registro
            validated_username, validated_email = self.validation_service.validate_registration_data(
                username, email, password
            )
            
            logger.info(f"✅ Validaciones pasadas para: {validated_username}")
            
            # 2. Delegar el registro al AuthService
            registration_result = self.auth_service.register_user(
                username=validated_username,
                email=validated_email,
                password=password
            )
            
            # 3. Generar y manejar verificación de email
            verification_info = self._handle_email_verification(
                user_id=registration_result["user_id"],
                email=validated_email,
                username=validated_username
            )
            
            # 4. Agregar información de verificación al resultado
            registration_result["email_verification"] = verification_info
            
            logger.info(f"🎉 Registro completado exitosamente para: {validated_username}")
            
            return registration_result
            
        except (ValidationException, ConflictException):
            # Re-lanzar excepciones de validación y conflicto
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado en registro: {str(e)}")
            raise DatabaseException("Ocurrió un error al crear tu cuenta. Por favor, intenta de nuevo.")
    
    def _handle_email_verification(
        self, 
        user_id: int, 
        email: str, 
        username: str
    ) -> Dict[str, Any]:
        """
        Maneja la generación y envío de verificación de email.
        
        Args:
            user_id: ID del usuario
            email: Email del usuario
            username: Username del usuario
            
        Returns:
            Dict con información de verificación
        """
        verification_info = {
            "required": False,  # No es obligatorio verificar email
            "token_generated": False,
            "email_sent": False,
            "message": "Email de verificación no configurado"
        }
        
        try:
            # Generar token de verificación
            verification_token = str(uuid4())
            verification_expires = datetime.utcnow() + timedelta(hours=24)
            
            # Guardar token en la base de datos
            self.repository.update_by_id(user_id, {
                "verification_token": verification_token,
                "verification_token_expires": verification_expires.isoformat()
            })
            
            verification_info["token_generated"] = True
            logger.info(f"📧 Token de verificación generado para: {username}")
            
            # Intentar enviar email
            email_result = self._send_verification_email(
                email, username, verification_token
            )
            
            verification_info.update(email_result)
            
        except Exception as e:
            logger.error(f"❌ Error en verificación de email: {str(e)}")
            verification_info["message"] = "Error al procesar verificación de email"
        
        return verification_info
    
    def _send_verification_email(
        self, 
        email: str, 
        username: str, 
        verification_token: str
    ) -> Dict[str, Any]:
        """
        Intenta enviar el email de verificación.
        
        Args:
            email: Email destino
            username: Username del usuario
            verification_token: Token de verificación
            
        Returns:
            Dict con resultado del envío
        """
        import os
        
        # Verificar si SMTP está configurado
        smtp_configured = bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))
        
        if not smtp_configured:
            logger.warning("⚠️ SMTP no configurado")
            return {
                "email_sent": False,
                "message": "El servicio de email no está configurado. Contacta al administrador."
            }
        
        try:
            # Enviar email de verificación
            email_sent = email_service.send_verification_email(
                to_email=email,
                username=username,
                verification_token=verification_token
            )
            
            if email_sent:
                logger.info(f"✅ Email de verificación enviado exitosamente a {email}")
                return {
                    "email_sent": True,
                    "message": "Revisa tu email para verificar tu cuenta"
                }
            else:
                logger.error(f"❌ Error al enviar email de verificación a {email}")
                return {
                    "email_sent": False,
                    "message": "No se pudo enviar el email de verificación"
                }
                
        except Exception as e:
            logger.error(f"❌ Excepción al enviar email: {str(e)}")
            return {
                "email_sent": False,
                "message": "Error al enviar email de verificación"
            }
    
    def validate_registration_data(self, user_data: UserCreate) -> None:
        """
        Valida datos de registro usando el servicio de validación.
        
        Args:
            user_data: Datos del usuario a validar
            
        Raises:
            ValidationException: Si los datos son inválidos
        """
        # Validaciones básicas adicionales antes del registro
        if not user_data.username or len(user_data.username) < 3:
            raise ValidationException("El nombre de usuario debe tener al menos 3 caracteres")
        
        if not user_data.username.replace('_', '').replace('-', '').isalnum():
            raise ValidationException(
                "El nombre de usuario solo puede contener letras, números, guiones y guiones bajos"
            )
        
        if user_data.email and '@' not in user_data.email:
            raise ValidationException("Por favor, ingresa un email válido")
        
        if len(user_data.password) < 8:
            raise ValidationException("La contraseña debe tener al menos 8 caracteres")
    
    def handle_email_verification(self, token: str) -> bool:
        """
        Maneja la verificación de email con token.
        
        Args:
            token: Token de verificación
            
        Returns:
            bool: True si la verificación fue exitosa
        """
        try:
            # Validar formato del token
            validated_token = self.validation_service.validate_token_format(
                token, "token de verificación"
            )
            
            # Delegar al servicio de usuario
            from src.services.user_service import UserService
            user_service = UserService()
            
            success = user_service.verify_email(validated_token)
            
            if success:
                logger.info(f"✅ Email verificado exitosamente con token: {token[:10]}...")
            else:
                logger.warning(f"❌ Token de verificación inválido: {token[:10]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error en verificación de email: {str(e)}")
            return False
    
    def handle_password_reset(self, token: str, new_password: str) -> bool:
        """
        Maneja el restablecimiento de contraseña.
        
        Args:
            token: Token de reset
            new_password: Nueva contraseña
            
        Returns:
            bool: True si el reset fue exitoso
        """
        try:
            # Validar formato del token
            validated_token = self.validation_service.validate_token_format(
                token, "token de reset"
            )
            
            # Validar nueva contraseña
            self.validation_service.validate_password_strength(new_password)
            
            # Delegar al servicio de usuario
            from src.services.user_service import UserService
            user_service = UserService()
            
            success = user_service.reset_password(validated_token, new_password)
            
            if success:
                logger.info(f"✅ Contraseña reseteada exitosamente con token: {token[:10]}...")
            else:
                logger.warning(f"❌ Token de reset inválido: {token[:10]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error en reset de contraseña: {str(e)}")
            return False
    
    def resend_verification_email(self, email: str) -> bool:
        """
        Reenvía el email de verificación.
        
        Args:
            email: Email del usuario
            
        Returns:
            bool: True siempre (por seguridad)
        """
        try:
            # Validar formato del email
            validated_email = self.validation_service.validate_email_format(email)
            
            # Delegar al servicio de usuario
            from src.services.user_service import UserService
            user_service = UserService()
            
            success = user_service.resend_verification_email(validated_email)
            
            logger.info(f"📧 Reenvío de verificación procesado para: {validated_email}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error en reenvío de verificación: {str(e)}")
            return True  # Siempre devolver True por seguridad
    
    def get_registration_requirements(self) -> Dict[str, Any]:
        """
        Obtiene los requisitos de registro del sistema.
        
        Returns:
            Dict con requisitos de registro
        """
        return {
            "username": {
                "min_length": 3,
                "max_length": 20,
                "allowed_chars": "letras, números, guiones y guiones bajos",
                "must_start_with": "letra",
                "restrictions": "No puede ser similar a nombres reservados"
            },
            "email": {
                "required": True,
                "must_be_valid": True,
                "verification_required": False
            },
            "password": {
                "min_length": 8,
                "max_length": 128,
                "requirements": "Al menos 8 caracteres, se recomienda incluir letras y números"
            }
        }
