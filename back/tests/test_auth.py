"""
Pruebas para el servicio de autenticación y endpoints.
"""
import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from src.services.auth_service import AuthService
from src.models.domain.usuario import User
from src.core.exceptions import ConflictException, UnauthorizedException

# Constantes para pruebas
TEST_USERNAME = "testuser"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "securepass123"
TEST_AUTH_ID = uuid4()

@pytest.fixture
def mock_user_repository():
    """Fixture que proporciona un mock del repositorio de usuarios."""
    mock_repo = Mock()
    
    # Configurar comportamiento para get_by_username
    mock_repo.get_by_username.return_value = None  # Por defecto, no existe el usuario
    
    # Configurar comportamiento para create
    mock_repo.create.return_value = 1  # ID del usuario creado
    
    # Configurar comportamiento para get
    test_user = User(
        id=1,
        username=TEST_USERNAME,
        email=TEST_EMAIL,
        password_hash="hashed_password",
        is_admin=False,
        auth_id=TEST_AUTH_ID,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat()
    )
    mock_repo.get.return_value = test_user
    
    # Configurar comportamiento para get_by_auth_id
    mock_repo.get_by_auth_id.return_value = test_user
    
    return mock_repo

@pytest.fixture
def auth_service(mock_user_repository):
    """Fixture que proporciona el servicio de autenticación con mocks."""
    service = AuthService()
    service.repository = mock_user_repository
    
    # Mock para funciones de hash de contraseña
    service._get_password_hash = Mock(return_value="hashed_password")
    service._verify_password = Mock(return_value=True)
    
    return service

class TestAuthService:
    """Pruebas para el servicio de autenticación."""
    
    def test_register_user_success(self, auth_service):
        """Prueba el registro exitoso de un usuario."""
        # Ejecutar la función
        result = auth_service.register_user(TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD)
        
        # Verificar llamadas al repositorio
        auth_service.repository.get_by_username.assert_called_once_with(TEST_USERNAME)
        auth_service.repository.create.assert_called_once()
        
        # Verificar el resultado
        assert result["username"] == TEST_USERNAME
        assert result["email"] == TEST_EMAIL
        assert result["is_admin"] == False
        assert "access_token" in result
        assert result["token_type"] == "bearer"
    
    def test_register_user_conflict(self, auth_service):
        """Prueba el registro con un nombre de usuario existente."""
        # Configurar el mock para simular un usuario existente
        existing_user = User(
            id=1, 
            username=TEST_USERNAME, 
            email="existing@example.com",
            password_hash="hashed",
            is_admin=False,
            auth_id=uuid4(),
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        auth_service.repository.get_by_username.return_value = existing_user
        
        # Verificar que se lanza la excepción correcta
        with pytest.raises(ConflictException):
            auth_service.register_user(TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD)
    
    def test_login_user_success(self, auth_service):
        """Prueba el login exitoso de un usuario."""
        # Configurar el mock para simular un usuario existente
        existing_user = User(
            id=1, 
            username=TEST_USERNAME, 
            email=TEST_EMAIL,
            password_hash="hashed_password",
            is_admin=False,
            auth_id=TEST_AUTH_ID,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        auth_service.repository.get_by_username.return_value = existing_user
        
        # Ejecutar la función
        result = auth_service.login_user(TEST_USERNAME, TEST_PASSWORD)
        
        # Verificar el resultado
        assert result["username"] == TEST_USERNAME
        assert result["email"] == TEST_EMAIL
        assert "access_token" in result
        assert result["token_type"] == "bearer"
    
    def test_login_user_invalid_credentials(self, auth_service):
        """Prueba el login con credenciales inválidas."""
        # Configurar el mock para simular verificación fallida
        auth_service._verify_password.return_value = False
        
        # Configurar el mock para simular un usuario existente
        existing_user = User(
            id=1, 
            username=TEST_USERNAME, 
            email=TEST_EMAIL,
            password_hash="hashed_password",
            is_admin=False,
            auth_id=TEST_AUTH_ID,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        auth_service.repository.get_by_username.return_value = existing_user
        
        # Verificar que se lanza la excepción correcta
        with pytest.raises(UnauthorizedException):
            auth_service.login_user(TEST_USERNAME, "wrong_password")
    
    def test_get_current_user_success(self, auth_service):
        """Prueba la obtención del usuario actual con un token válido."""
        # Crear un token manualmente
        payload = {"sub": str(TEST_AUTH_ID), "exp": datetime.utcnow() + timedelta(days=1)}
        token = jwt.encode(payload, "tu_clave_secreta_aqui", algorithm="HS256")
        
        # Ejecutar la función
        with patch('jwt.decode', return_value=payload):
            user = auth_service.get_current_user(token)
        
        # Verificar el resultado
        assert user.id == 1
        assert user.username == TEST_USERNAME
        assert user.email == TEST_EMAIL
    
    def test_get_current_user_invalid_token(self, auth_service):
        """Prueba la obtención del usuario actual con un token inválido."""
        # Simular una excepción de JWT
        with patch('jwt.decode', side_effect=jwt.PyJWTError):
            with pytest.raises(UnauthorizedException):
                auth_service.get_current_user("invalid_token")

# Para ejecutar pruebas de integración con los endpoints, necesitaríamos configurar
# TestClient de FastAPI, pero como no conocemos los detalles específicos de la configuración
# de tu aplicación, solo incluimos pruebas unitarias del servicio.