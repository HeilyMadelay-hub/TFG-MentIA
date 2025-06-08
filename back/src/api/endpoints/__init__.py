# El archivo __init__.py en el directorio endpoints esté configurado correctamente para importar y exportar todos los routers
# src/api/endpoints/__init__.py

from src.services.auth_service import AuthService
from src.services.user_service import UserService
from src.repositories.user_repository import UserRepository

def get_auth_service() -> AuthService:
    """
    Retorna una instancia del servicio de autenticación.
    """
    user_repository = UserRepository()
    return AuthService(repository=user_repository)

def get_user_service() -> UserService:
    """
    Retorna una instancia del servicio de usuarios.
    """
    # ✅ ARREGLADO: UserService no acepta parámetros en su constructor
    return UserService()
