"""
Servicio de validación para usuarios - VERSION REFACTORIZADA
Centraliza todas las validaciones relacionadas con usuarios para eliminar duplicación
"""
import re
import logging
from typing import List, Optional, Tuple, Dict, Any
from email_validator import validate_email, EmailNotValidError
from src.models.domain import User
from src.core.exceptions import ValidationException, ConflictException, ForbiddenException
from src.repositories.user_repository import UserRepository
from src.config.database import get_supabase_client

logger = logging.getLogger(__name__)

class UserValidationService:
    """
    Servicio centralizado para todas las validaciones de usuarios.
    Elimina la duplicación de validaciones en endpoints.
    """
    
    def __init__(self, repository: Optional[UserRepository] = None):
        """Inicializa el servicio con el repositorio."""
        self.repository = repository or UserRepository()
        self.reserved_usernames = [
            'admin', 'root', 'system', 'user', 'test', 'demo', 'api',
            'ivan', 'administrator', 'moderator', 'support'
        ]
    
    # ==================== VALIDACIONES DE EMAIL ====================
    
    def validate_email_format(self, email: str, username: Optional[str] = None) -> str:
        """
        Valida el formato básico del email.
        
        Args:
            email: Email a validar
            username: Username del usuario (para caso especial de Ivan)
            
        Returns:
            str: Email normalizado
            
        Raises:
            ValidationException: Si el formato es inválido
        """
        if not email:
            raise ValidationException("El email es obligatorio")
        
        email = email.strip().lower()
        
        # Validación básica con '@'
        if '@' not in email:
            # Detectar casos comunes donde falta @
            if 'gmail.com' in email or 'hotmail.com' in email or 'yahoo.com' in email:
                raise ValidationException("Formato de email inválido. ¿Olvidaste el símbolo @?")
            raise ValidationException("Por favor, ingresa un email válido")
        
        # Caso especial: Ivan puede usar @documente.com o @documente.es
        is_ivan = username and username.lower() == 'ivan'
        if is_ivan and ('documente.com' in email or 'documente.es' in email):
            # Para Ivan con dominio documente, no validar estrictamente
            return email
        
        # Validar formato con email_validator
        try:
            valid = validate_email(email)
            return valid.email
        except EmailNotValidError as e:
            # Si es Ivan, permitir emails con @documente.com aunque el validador los rechace
            if is_ivan and '@documente' in email:
                return email
            raise ValidationException(f"Email inválido: {str(e)}")
    
    def validate_email_availability(self, email: str, exclude_user_id: Optional[int] = None, username: Optional[str] = None) -> None:
        """
        Valida que el email no esté en uso por otro usuario.
        
        Args:
            email: Email a validar
            exclude_user_id: ID de usuario a excluir (para actualizaciones)
            username: Username del usuario (para caso especial de Ivan)
            
        Raises:
            ConflictException: Si el email ya está en uso
            ValidationException: Si no es Ivan y usa @documente.com
        """
        
        # Solo Ivan puede usar @documente.com o @documente.es
        if '@documente' in email.lower():
            # Si el username no es ivan, no puede usar @documente
            if username and username.lower() != 'ivan':
                raise ValidationException("Solo Ivan puede usar emails @documente")
            
            # Si no se pasó username, verificar si el email ya está siendo usado por alguien que no sea Ivan
            if not username:
                existing = self.repository.get_by_email(email)
                if existing and existing.username.lower() != 'ivan':
                    raise ValidationException("Solo Ivan puede usar emails @documente")
        
        existing_user = self.repository.get_by_email(email)
        
        if existing_user and (exclude_user_id is None or existing_user.id != exclude_user_id):
            raise ConflictException(
                f"El email '{email}' ya está registrado. ¿Olvidaste tu contraseña?"
            )
    
    def validate_email_patterns(self, email: str, username: Optional[str] = None) -> None:
        """
        Valida patrones avanzados de email para prevenir duplicados.
        
        Args:
            email: Email a validar
            username: Username del usuario (para caso especial de Ivan)
            
        Raises:
            ConflictException: Si hay conflictos de patrones
        """
        if '@' not in email:
            return
        
        username_part, domain = email.rsplit('@', 1)
        
        # Obtener emails existentes
        supabase = get_supabase_client(use_service_role=True)
        all_users = supabase.table("users").select("email").execute()
        existing_emails = [u['email'] for u in all_users.data if u.get('email')]
        
        # Verificar mismo username en diferentes dominios
        for existing_email in existing_emails:
            if '@' in existing_email:
                existing_username, existing_domain = existing_email.rsplit('@', 1)
                if (username_part.lower() == existing_username.lower() and 
                    domain != existing_domain):
                    raise ConflictException(
                        f"Ya existe una cuenta con el email {existing_email}. "
                        f"No se permite crear múltiples cuentas con el mismo nombre."
                    )
    
    # ==================== VALIDACIONES DE USERNAME ====================
    
    def validate_username_format(self, username: str) -> str:
        """
        Valida el formato del nombre de usuario.
        
        Args:
            username: Username a validar
            
        Returns:
            str: Username normalizado
            
        Raises:
            ValidationException: Si el formato es inválido
        """
        if not username:
            raise ValidationException("El nombre de usuario es obligatorio")
        
        username = username.strip()
        
        # Para el caso especial de Ivan, mantener las mayúsculas originales
        if username.lower() == "ivan":
            # No modificar el caso para Ivan
            pass
        else:
            # Para otros usuarios, convertir a minúsculas
            username = username.lower()
        
        # Validar longitud
        if len(username) < 3:
            raise ValidationException("El nombre de usuario debe tener al menos 3 caracteres")
        
        if len(username) > 20:
            raise ValidationException("El nombre de usuario no puede tener más de 20 caracteres")
        
        # Validar caracteres permitidos
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValidationException(
                "El nombre de usuario solo puede contener letras, números, guiones y guiones bajos"
            )
        
        # No debe empezar con números o caracteres especiales
        if username[0] in '0123456789_-':
            raise ValidationException("El nombre de usuario debe empezar con una letra")
        
        return username
    
    def validate_username_availability(self, username: str, exclude_user_id: Optional[int] = None) -> None:
        """
        Valida que el username no esté en uso.
        
        Args:
            username: Username a validar
            exclude_user_id: ID de usuario a excluir (para actualizaciones)
            
        Raises:
            ConflictException: Si el username ya existe
        """
        existing_user = self.repository.get_by_username(username)
        
        if existing_user and (exclude_user_id is None or existing_user.id != exclude_user_id):
            raise ConflictException(f"El nombre de usuario '{username}' ya está registrado")
    
    def validate_username_restrictions(self, username: str) -> None:
        """
        Valida restricciones especiales de usernames.
        
        Args:
            username: Username a validar
            
        Raises:
            ValidationException: Si el username está restringido
        """
        username_lower = username.lower()
        
        # Verificar nombres reservados
        if username_lower in self.reserved_usernames:
            raise ValidationException(
                f"El nombre '{username}' está reservado. Por favor, elige otro."
            )
        
        # Verificar similitud con "Ivan"
        if username_lower == "ivan" or username_lower.startswith("ivan"):
            raise ValidationException(
                "No se permite registrar usuarios con nombres similares a 'Ivan'"
            )
    
    # ==================== VALIDACIONES DE CONTRASEÑA ====================
    
    def validate_password_strength(self, password: str) -> None:
        """
        Valida la fortaleza de la contraseña.
        
        Args:
            password: Contraseña a validar
            
        Raises:
            ValidationException: Si la contraseña es débil
        """
        if not password:
            raise ValidationException("La contraseña es obligatoria")
        
        if len(password) < 8:
            raise ValidationException("La contraseña debe tener al menos 8 caracteres")
        
        if len(password) > 128:
            raise ValidationException("La contraseña no puede tener más de 128 caracteres")
        
        # Validaciones adicionales de fortaleza (opcional)
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        strength_score = sum([has_upper, has_lower, has_digit])
        
        if len(password) >= 12 and strength_score >= 2:
            # Contraseña fuerte
            return
        elif len(password) >= 8 and strength_score >= 1:
            # Contraseña aceptable
            return
        else:
            raise ValidationException(
                "La contraseña debe tener al menos 8 caracteres y contener letras y números"
            )
    
    def validate_credentials_format(self, username_or_email: str, password: str) -> Tuple[str, str]:
        """
        Valida el formato de credenciales de login.
        
        Args:
            username_or_email: Username o email
            password: Contraseña
            
        Returns:
            Tuple[str, str]: (username_or_email_normalizado, password)
            
        Raises:
            ValidationException: Si el formato es inválido
        """
        if not username_or_email or not password:
            raise ValidationException("Usuario y contraseña son obligatorios")
        
        username_or_email = username_or_email.strip()
        
        # Para Ivan, mantener el caso original; para emails, mantener original; otros a minúsculas
        if username_or_email.lower() == "ivan":
            # Mantener el caso original para Ivan
            pass
        elif '@' in username_or_email:
            # Los emails se convierten a minúsculas
            username_or_email = username_or_email.lower()
        else:
            # Otros usernames a minúsculas
            username_or_email = username_or_email.lower()
        
        # Validar formato si parece email
        if '.' in username_or_email and '@' not in username_or_email:
            if any(domain in username_or_email for domain in ['gmail.com', 'hotmail.com', 'yahoo.com']):
                raise ValidationException("Formato de email inválido. ¿Olvidaste el símbolo @?")
        
        return username_or_email, password
    
    # ==================== VALIDACIONES DE PERMISOS ====================
    
    def validate_admin_permissions(self, current_user: User, action: str = "realizar esta acción") -> None:
        """
        Valida que el usuario tenga permisos de administrador.
        
        Args:
            current_user: Usuario actual
            action: Descripción de la acción (para el mensaje de error)
            
        Raises:
            ForbiddenException: Si no tiene permisos
        """
        if not current_user.is_admin:
            raise ForbiddenException(f"Solo los administradores pueden {action}")
    
    def validate_user_ownership(
        self, 
        current_user: User, 
        target_user_id: int, 
        action: str = "realizar esta acción"
    ) -> None:
        """
        Valida que el usuario tenga permisos sobre otro usuario (admin o mismo usuario).
        
        Args:
            current_user: Usuario actual
            target_user_id: ID del usuario objetivo
            action: Descripción de la acción
            
        Raises:
            ForbiddenException: Si no tiene permisos
        """
        if not current_user.is_admin and current_user.id != target_user_id:
            raise ForbiddenException(f"No tienes permisos para {action}")
    
    def validate_user_deletion_permissions(self, current_user: User, target_user_id: int) -> None:
        """
        Valida permisos específicos para eliminación de usuarios.
        
        Args:
            current_user: Usuario actual
            target_user_id: ID del usuario a eliminar
            
        Raises:
            ForbiddenException: Si no tiene permisos
            ValidationException: Si intenta eliminarse a sí mismo
        """
        # Solo admins pueden eliminar
        if not current_user.is_admin:
            raise ForbiddenException("Solo los administradores pueden eliminar usuarios")
        
        # No puede eliminarse a sí mismo
        if current_user.id == target_user_id:
            raise ValidationException("No puedes eliminarte a ti mismo")
    
    # ==================== VALIDACIONES DE DATOS DE REGISTRO ====================
    
    def validate_registration_data(self, username: str, email: str, password: str) -> Tuple[str, str]:
        """
        Valida todos los datos de registro de un usuario.
        
        Args:
            username: Nombre de usuario
            email: Email
            password: Contraseña
            
        Returns:
            Tuple[str, str]: (username_normalizado, email_normalizado)
            
        Raises:
            ValidationException: Si algún dato es inválido
            ConflictException: Si username o email ya existen
        """
        # Validar formato de username
        normalized_username = self.validate_username_format(username)
        
        # Validar restricciones de username (excepto para Ivan)
        if normalized_username.lower() != 'ivan':
            self.validate_username_restrictions(normalized_username)
        
        # Validar disponibilidad de username
        self.validate_username_availability(normalized_username)
        
        # Validar formato de email (pasar username para caso especial de Ivan)
        normalized_email = self.validate_email_format(email, username=normalized_username)
        
        # Validar patrones de email (excepto para Ivan con @documente)
        if not (normalized_username.lower() == 'ivan' and '@documente' in normalized_email):
            self.validate_email_patterns(normalized_email, username=normalized_username)
        
        # Validar disponibilidad de email
        self.validate_email_availability(normalized_email, username=normalized_username)
        
        # Validar fortaleza de contraseña
        self.validate_password_strength(password)
        
        return normalized_username, normalized_email
    
    # ==================== VALIDACIONES DE ACTUALIZACIÓN ====================
    
    def validate_update_data(
        self, 
        user_id: int, 
        update_data: Dict[str, Any], 
        current_user: User
    ) -> Dict[str, Any]:
        """
        Valida datos de actualización de usuario.
        
        Args:
            user_id: ID del usuario a actualizar
            update_data: Datos a actualizar
            current_user: Usuario que realiza la actualización
            
        Returns:
            Dict[str, Any]: Datos validados y normalizados
            
        Raises:
            ForbiddenException: Si no tiene permisos
            ValidationException: Si los datos son inválidos
            ConflictException: Si hay conflictos
        """
        # Validar permisos
        self.validate_user_ownership(current_user, user_id, "actualizar este usuario")
        
        validated_data = {}
        
        # Validar username si se está actualizando
        if 'username' in update_data:
            new_username = self.validate_username_format(update_data['username'])
            self.validate_username_restrictions(new_username)
            self.validate_username_availability(new_username, exclude_user_id=user_id)
            validated_data['username'] = new_username
        
        # Validar email si se está actualizando
        if 'email' in update_data:
            # Obtener username del usuario actual para caso especial de Ivan
            user = self.repository.get(user_id)
            username = user.username if user else None
            
            new_email = self.validate_email_format(update_data['email'], username=username)
            
            # Validar patrones (excepto para Ivan con @documente)
            if not (username and username.lower() == 'ivan' and '@documente' in new_email):
                self.validate_email_patterns(new_email, username=username)
            
            self.validate_email_availability(new_email, exclude_user_id=user_id, username=username)
            validated_data['email'] = new_email
        
        # Copiar otros campos válidos
        allowed_fields = ['is_admin', 'avatar_url', 'email_verified']
        for field in allowed_fields:
            if field in update_data:
                validated_data[field] = update_data[field]
        
        return validated_data
    
    # ==================== VALIDACIONES DE BÚSQUEDA ====================
    
    def validate_search_permissions(self, current_user: User) -> None:
        """
        Valida permisos para búsqueda de usuarios.
        
        Args:
            current_user: Usuario actual
            
        Raises:
            ForbiddenException: Si no tiene permisos
        """
        if not current_user.is_admin:
            raise ForbiddenException("Solo los administradores pueden buscar usuarios")
    
    def validate_search_query(self, query: str) -> str:
        """
        Valida y normaliza query de búsqueda.
        
        Args:
            query: Query de búsqueda
            
        Returns:
            str: Query normalizado
            
        Raises:
            ValidationException: Si el query es inválido
        """
        if not query or len(query.strip()) == 0:
            raise ValidationException("El término de búsqueda no puede estar vacío")
        
        query = query.strip()
        
        if len(query) < 1:
            raise ValidationException("El término de búsqueda debe tener al menos 1 caracter")
        
        if len(query) > 100:
            raise ValidationException("El término de búsqueda no puede tener más de 100 caracteres")
        
        return query
    
    # ==================== VALIDACIONES ESPECIALES ====================
    
    def validate_ivan_special_case(self, username: str, password: str) -> bool:
        """
        Valida el caso especial de Ivan (hardcodeado por requisitos del sistema).
        Acepta cualquier variación de mayúsculas/minúsculas para el username.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            bool: True si es el caso especial de Ivan
        """
        # Aceptar cualquier variación de mayúsculas/minúsculas para Ivan
        return username.lower() == "ivan" and password == "ivan1234"
    
    def validate_token_format(self, token: str, token_type: str = "token") -> str:
        """
        Valida el formato de un token.
        
        Args:
            token: Token a validar
            token_type: Tipo de token (para mensajes de error)
            
        Returns:
            str: Token validado
            
        Raises:
            ValidationException: Si el token es inválido
        """
        if not token:
            raise ValidationException(f"El {token_type} es obligatorio")
        
        token = token.strip()
        
        if len(token) < 10:
            raise ValidationException(f"El {token_type} es inválido")
        
        return token
    
    # ==================== UTILIDADES DE VALIDACIÓN ====================
    
    def get_validation_summary(self, username: str, email: str) -> Dict[str, Any]:
        """
        Obtiene un resumen de validaciones sin lanzar excepciones.
        
        Args:
            username: Username a validar
            email: Email a validar
            
        Returns:
            Dict con resultados de validaciones
        """
        summary = {
            "username": {"valid": False, "errors": []},
            "email": {"valid": False, "errors": []},
            "overall_valid": False
        }
        
        # Validar username
        try:
            self.validate_username_format(username)
            self.validate_username_restrictions(username)
            self.validate_username_availability(username)
            summary["username"]["valid"] = True
        except (ValidationException, ConflictException) as e:
            summary["username"]["errors"].append(str(e))
        
        # Validar email
        try:
            self.validate_email_format(email)
            self.validate_email_patterns(email)
            self.validate_email_availability(email)
            summary["email"]["valid"] = True
        except (ValidationException, ConflictException) as e:
            summary["email"]["errors"].append(str(e))
        
        summary["overall_valid"] = summary["username"]["valid"] and summary["email"]["valid"]
        
        return summary
