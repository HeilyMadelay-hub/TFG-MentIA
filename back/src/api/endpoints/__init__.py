# El archivo __init__.py en el directorio endpoints esté configurado correctamente para importar y exportar todos los routers
# src/api/endpoints/__init__.py

from src.services.auth_service import AuthService
from src.services.user_service import UserService
from src.services.authentication_service import AuthenticationService
from src.services.user_registration_service import UserRegistrationService
from src.services.user_validation_service import UserValidationService
from src.repositories.user_repository import UserRepository

def get_auth_service() -> AuthService:
    """
    Retorna una instancia del servicio de autenticación base.
    """
    user_repository = UserRepository()
    return AuthService(repository=user_repository)

def get_user_service() -> UserService:
    """
    Retorna una instancia del servicio de usuarios.
    """
    return UserService()

def get_authentication_service() -> AuthenticationService:
    """
    Retorna una instancia del servicio de autenticación mejorado.
    """
    return AuthenticationService()

def get_user_registration_service() -> UserRegistrationService:
    """
    Retorna una instancia del servicio de registro de usuarios.
    """
    return UserRegistrationService()

def get_user_validation_service() -> UserValidationService:
    """
    Retorna una instancia del servicio de validación de usuarios.
    """
    return UserValidationService()
