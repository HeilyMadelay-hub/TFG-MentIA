"""
API Endpoints para la gestión de usuarios - VERSION REFACTORIZADA MEJORADA
Este módulo implementa endpoints ultra-limpios siguiendo el patrón de documents.py:
- Endpoints de ~10 líneas máximo
- TODA la lógica en helpers y servicios
- Manejo de errores consistente
- Documentación clara y concisa
"""
from fastapi import APIRouter, Depends, status, Query, Path, Header, Body, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any, Optional
import logging

# Schemas
from src.models.schemas.user import (
    UserCreate, UserResponse, UserUpdate,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest,
    RefreshTokenRequest, TokenResponse, EmailVerificationRequest,
    ResendVerificationRequest, MessageResponse
)
from src.models.domain import User

# Helpers y servicios
from src.api.helpers.user_helpers import UserEndpointHelpers
from src.api.dependencies import get_current_user
from src.core.exceptions import ValidationException

# Rate limiting
from src.core.rate_limit import rate_limit_register, rate_limit_login, rate_limit_default
from fastapi import Request

logger = logging.getLogger(__name__)

# ==================== CONFIGURACIÓN DEL ROUTER ====================

router = APIRouter(prefix="/users", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

# Inicializar helpers
user_helpers = UserEndpointHelpers()

# ==================== ENDPOINTS DE AUTENTICACIÓN ====================

@router.post("/login", response_model=Dict[str, Any])
@rate_limit_login
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Autentica a un usuario y genera tokens.
    Soporta login por username o email.
    """
    return await user_helpers.handle_login(request, form_data)

@router.post("/register", response_model=Dict[str, Any], status_code=201)
@rate_limit_register
async def register(
    request: Request,
    user_data: UserCreate
):
    """
    Registra un nuevo usuario en el sistema.
    """
    return await user_helpers.handle_registration(request, user_data)

@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    authorization: str = Header(None)
):
    """
    Cierra la sesión del usuario actual.
    """
    return await user_helpers.handle_logout(current_user, authorization)

@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Renueva el token de acceso usando un refresh token.
    """
    return await user_helpers.handle_token_refresh(request.refresh_token)

# ==================== ENDPOINTS DE PERFIL ====================

@router.get("/me", response_model=UserResponse)
async def get_user_me(current_user: User = Depends(get_current_user)):
    """
    Obtiene los datos del usuario autenticado.
    """
    return user_helpers.format_user_response(current_user)

@router.put("/me", response_model=Dict[str, Any])
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza la información del usuario actual.
    Si se cambia el email, puede requerir confirmación.
    """
    return await user_helpers.handle_profile_update(current_user, user_data)

@router.post("/change-email-validated", response_model=Dict[str, Any])
@rate_limit_default
async def change_email_with_validation(
    request: Request,
    new_email: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Cambia el email del usuario con validación estricta.
    Solo permite el cambio si el email existe y puede recibir correos.
    """
    return await user_helpers.handle_change_email_validated(
        request=request,
        current_user=current_user,
        new_email=new_email,
        background_tasks=background_tasks
    )

@router.post("/verify-email-change-code", response_model=Dict[str, Any])
async def verify_email_change_code(
    token: str = Body(...),
    code: str = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Verifica el código de cambio de email y completa el cambio.
    """
    return await user_helpers.handle_verify_email_change_code(
        current_user=current_user,
        token=token,
        code=code
    )

# ==================== ENDPOINTS DE CONTRASEÑAS ====================

@router.post("/forgot-password", response_model=MessageResponse)
@rate_limit_login
async def forgot_password(
    request: Request,
    forgot_request: ForgotPasswordRequest
):
    """
    Solicita restablecimiento de contraseña.
    """
    return await user_helpers.handle_forgot_password(request, forgot_request)

@router.post("/reset-password", response_model=MessageResponse)
@rate_limit_login
async def reset_password(
    request: Request,
    reset_request: ResetPasswordRequest
):
    """
    Restablece la contraseña usando el token recibido.
    """
    return await user_helpers.handle_reset_password(request, reset_request)

@router.post("/me/change-password", response_model=MessageResponse)
async def change_current_user_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Cambia la contraseña del usuario actual.
    """
    return await user_helpers.handle_change_password(
        user_id=current_user.id,
        change_request=request,
        current_user=current_user
    )

@router.put("/{user_id}/change-password", response_model=MessageResponse)
async def change_password(
    user_id: int = Path(..., description="ID del usuario"),
    request: ChangePasswordRequest = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Cambia la contraseña de un usuario específico (admin only).
    """
    return await user_helpers.handle_change_password(
        user_id=user_id,
        change_request=request,
        current_user=current_user
    )

# ==================== ENDPOINTS DE VERIFICACIÓN ====================

@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(request: EmailVerificationRequest):
    """
    Verifica el email del usuario con el token recibido.
    """
    return await user_helpers.handle_email_verification(request.token)

@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(request: ResendVerificationRequest):
    """
    Reenvía el email de verificación.
    """
    return await user_helpers.handle_resend_verification(request.email)

@router.get("/confirm-email-change/{token}", response_model=MessageResponse)
async def confirm_email_change(
    token: str = Path(..., description="Token de confirmación")
):
    """
    Confirma el cambio de email usando el token recibido.
    """
    return await user_helpers.handle_confirm_email_change(token)

@router.get("/verify-email-change", response_class=HTMLResponse)
async def verify_email_change(
    token: str = Query(..., description="Token de confirmación de cambio de email")
):
    """
    Verifica y confirma el cambio de email usando el token recibido.
    Retorna una página HTML con el resultado.
    """
    try:
        # Intentar confirmar el cambio de email
        result = await user_helpers.handle_confirm_email_change(token)
        
        # Si fue exitoso, mostrar página de éxito
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Actualizado - DocuMente</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #6B4CE6 0%, #8B5CF6 100%);
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                .container {
                    background-color: white;
                    padding: 60px;
                    border-radius: 20px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                    animation: fadeIn 0.5s ease;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .success-icon {
                    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                    color: white;
                    font-size: 60px;
                    width: 100px;
                    height: 100px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 30px;
                    animation: pulse 1s ease infinite;
                }
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                    100% { transform: scale(1); }
                }
                h1 {
                    color: #333;
                    margin-bottom: 20px;
                    font-size: 32px;
                }
                p {
                    color: #666;
                    line-height: 1.6;
                    margin-bottom: 30px;
                    font-size: 18px;
                }
                .button {
                    display: inline-block;
                    padding: 15px 40px;
                    background: linear-gradient(135deg, #6B4CE6 0%, #8B5CF6 100%);
                    color: white;
                    text-decoration: none;
                    border-radius: 50px;
                    font-weight: bold;
                    transition: all 0.3s ease;
                    box-shadow: 0 5px 15px rgba(107, 76, 230, 0.3);
                    font-size: 16px;
                }
                .button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(107, 76, 230, 0.4);
                }
                .email-info {
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                    border-left: 4px solid #28a745;
                }
                .email-info strong {
                    color: #28a745;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✓</div>
                <h1>¡Email Actualizado!</h1>
                <div class="email-info">
                    <p><strong>✓ Confirmado:</strong><br>
                    Tu dirección de email ha sido actualizada exitosamente.</p>
                </div>
                <p>Ya puedes iniciar sesión con tu nuevo email.</p>
                <a href="/" class="button">Ir a la Aplicación</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
        
    except ValidationException:
        # Si hubo error, mostrar página de error
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - DocuMente</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                .container {
                    background-color: white;
                    padding: 60px;
                    border-radius: 20px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                    animation: fadeIn 0.5s ease;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .error-icon {
                    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                    color: white;
                    font-size: 60px;
                    width: 100px;
                    height: 100px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 30px;
                    animation: shake 0.5s ease;
                }
                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    25% { transform: translateX(-10px); }
                    75% { transform: translateX(10px); }
                }
                h1 {
                    color: #333;
                    margin-bottom: 20px;
                    font-size: 32px;
                }
                p {
                    color: #666;
                    line-height: 1.6;
                    margin-bottom: 30px;
                    font-size: 18px;
                }
                .button {
                    display: inline-block;
                    padding: 15px 40px;
                    background: linear-gradient(135deg, #6B4CE6 0%, #8B5CF6 100%);
                    color: white;
                    text-decoration: none;
                    border-radius: 50px;
                    font-weight: bold;
                    transition: all 0.3s ease;
                    box-shadow: 0 5px 15px rgba(107, 76, 230, 0.3);
                    font-size: 16px;
                }
                .button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(107, 76, 230, 0.4);
                }
                .error-info {
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                    border-left: 4px solid #dc3545;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">✖</div>
                <h1>Enlace Inválido</h1>
                <div class="error-info">
                    <p>El enlace de confirmación es inválido o ha expirado.</p>
                </div>
                <p>Por favor, solicita un nuevo cambio de email si es necesario.</p>
                <a href="/" class="button">Ir a la Aplicación</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=400)
    except Exception as e:
        # Error genérico
        logger.error(f"Error en verify_email_change: {str(e)}")
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - DocuMente</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                .container {
                    background-color: white;
                    padding: 60px;
                    border-radius: 20px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                    animation: fadeIn 0.5s ease;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .error-icon {
                    background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
                    color: white;
                    font-size: 60px;
                    width: 100px;
                    height: 100px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 30px;
                }
                h1 {
                    color: #333;
                    margin-bottom: 20px;
                    font-size: 32px;
                }
                p {
                    color: #666;
                    line-height: 1.6;
                    margin-bottom: 30px;
                    font-size: 18px;
                }
                .button {
                    display: inline-block;
                    padding: 15px 40px;
                    background: linear-gradient(135deg, #6B4CE6 0%, #8B5CF6 100%);
                    color: white;
                    text-decoration: none;
                    border-radius: 50px;
                    font-weight: bold;
                    transition: all 0.3s ease;
                    box-shadow: 0 5px 15px rgba(107, 76, 230, 0.3);
                    font-size: 16px;
                }
                .button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(107, 76, 230, 0.4);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">⚠</div>
                <h1>Error al Procesar</h1>
                <p>Ocurrió un error al procesar tu solicitud.</p>
                <p>Por favor, intenta nuevamente más tarde.</p>
                <a href="/" class="button">Ir a la Aplicación</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=500)

# ==================== ENDPOINTS DE CONSULTA ====================

@router.get("/", response_model=List[UserResponse])
async def list_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """
    Lista usuarios del sistema (admin only).
    """
    return await user_helpers.handle_list_users(current_user, limit, offset)

@router.get("/search", response_model=List[UserResponse])
async def search_users(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    Busca usuarios por username o email (admin only).
    """
    return await user_helpers.handle_search_users(current_user, q, limit)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int = Path(..., description="ID del usuario"),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene los detalles de un usuario específico.
    """
    return await user_helpers.handle_get_user(user_id, current_user)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int = Path(..., description="ID del usuario"),
    user_data: UserUpdate = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza un usuario específico.
    """
    return await user_helpers.handle_update_user(user_id, user_data, current_user)

@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int = Path(..., description="ID del usuario"),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un usuario del sistema (admin only).
    """
    await user_helpers.handle_delete_user(user_id, current_user)
    return None

# ==================== ENDPOINTS DE UTILIDAD ====================

@router.get("/token/validate")
async def validate_token(
    current_user: User = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    """
    Valida si el token actual es válido.
    """
    return await user_helpers.handle_validate_token(current_user, authorization)

# ==================== ENDPOINTS DE DEBUG (ELIMINAR EN PRODUCCIÓN) ====================

@router.get("/debug-user/{email}")
async def debug_user_state(
    email: str = Path(..., description="Email del usuario"),
    current_user: User = Depends(get_current_user)
):
    """
    DEBUG: Verifica el estado de un usuario en la base de datos.
    ELIMINAR EN PRODUCCIÓN.
    """
    return await user_helpers.handle_debug_user_state(email, current_user)

@router.get("/verify-email/{email}")
async def verify_email_exists(
    email: str = Path(..., description="Email a verificar")
):
    """
    Verifica si un email existe en el sistema (público).
    """
    return await user_helpers.handle_verify_email_exists(email)

@router.post("/test-login")
async def test_login(
    username_or_email: str = Body(...),
    password: str = Body(...)
):
    """
    DEBUG: Prueba el login con información detallada.
    ELIMINAR EN PRODUCCIÓN.
    """
    return await user_helpers.handle_test_login(username_or_email, password)