from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Union
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr
    
    @field_validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('El nombre de usuario debe contener solo caracteres alfanuméricos')
        return v

class UserCreate(UserBase):
    password: str
    auth_id: Optional[UUID] = None
    
    @field_validator('password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_admin: Optional[bool] = None
    
    @field_validator('username')
    def username_alphanumeric(cls, v):
        if v is not None and not v.isalnum():
            raise ValueError('El nombre de usuario debe contener solo caracteres alfanuméricos')
        return v

class UserResponse(BaseModel):
    """Respuesta completa de usuario"""
    id: int
    username: str
    email: str
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    auth_id: Optional[str] = None
    email_verified: Optional[bool] = False
    avatar_url: Optional[str] = None
    
    @field_validator('auth_id', mode='before')
    def convert_uuid_to_str(cls, v):
        """Convierte UUID a string si es necesario"""
        if isinstance(v, UUID):
            return str(v)
        return v
    
    model_config = {
        "from_attributes": True
    }

class UserInDB(UserResponse):
    password_hash: str
    
    model_config = {
        "from_attributes": True
    }

# ==================== ESQUEMAS ADICIONALES ====================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    
    @field_validator('new_password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('La nueva contraseña debe tener al menos 8 caracteres')
        return v

class ResetPasswordSecureRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str
    
    @field_validator('new_password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('La nueva contraseña debe tener al menos 8 caracteres')
        return v
    
    @field_validator('code')
    def code_format(cls, v):
        if not v.isalnum():
            raise ValueError('El código debe contener solo letras y números')
        return v.upper()

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('La nueva contraseña debe tener al menos 8 caracteres')
        return v

class RefreshTokenRequest(BaseModel):
    """Solicitud para renovar token"""
    refresh_token: str

class TokenResponse(BaseModel):
    """Respuesta con tokens de autenticación"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None

class EmailVerificationRequest(BaseModel):
    """Solicitud para verificar email"""
    token: str

class ResendVerificationRequest(BaseModel):
    """Solicitud para reenviar verificación"""
    email: EmailStr

class MessageResponse(BaseModel):
    message: str
    success: bool = True

class UserSearchResponse(BaseModel):
    """Respuesta de búsqueda de usuarios"""
    users: List[UserResponse]
    total: int

class UserSearchResponseSingle(UserResponse):
    """Respuesta extendida para búsquedas de usuario individual"""
    last_login: Optional[datetime] = None
    email_verified: bool = False
