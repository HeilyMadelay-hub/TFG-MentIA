# Modelos Pydantic para Supabase - Coinciden exactamente con la BD
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

class User(BaseModel):
    """Modelo de usuario - tabla users"""
    id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    password_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_admin: bool = False
    email_encrypted: Optional[bytes] = None
    auth_id: Optional[UUID] = None
    avatar_url: Optional[str] = None
    email_verified: bool = False
    last_login: Optional[datetime] = None
    reset_token: Optional[str] = None
    reset_token_expires: Optional[datetime] = None
    verification_token: Optional[str] = None
    verification_token_expires: Optional[datetime] = None
    refresh_token: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class Document(BaseModel):
    """Modelo de documento - tabla documents"""
    id: Optional[int] = None
    title: Optional[str] = None
    chromadb_id: Optional[str] = None
    uploaded_by: Optional[int] = None
    content_type: Optional[str] = None  # PDF, texto, etc.
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    file_url: Optional[str] = None
    status: str = Field(default='pending')
    status_message: Optional[str] = None
    file_size: Optional[int] = None
    original_filename: Optional[str] = None
    content: Optional[str] = None  # IMPORTANTE: Campo para el contenido
    
    model_config = ConfigDict(
        from_attributes=True,
        extra='allow'  # Permitir campos adicionales temporalmente
    )

class AccesoDocumentosUsuario(BaseModel):
    """Modelo de acceso a documentos - tabla acceso_documentos_usuario"""
    id_document: int
    id_user: int
    linked_time: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class Chat(BaseModel):
    """Modelo de chat - tabla chats"""
    id: Optional[int] = None
    id_user: Optional[int] = None
    name_chat: Optional[str] = None
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class Message(BaseModel):
    """Modelo de mensaje - tabla messages"""
    id: Optional[int] = None
    id_chat: Optional[int] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Alias para compatibilidad con código existente
DocumentAccess = AccesoDocumentosUsuario

# Para compatibilidad, exportar una clase Base vacía
class Base:
    pass

# Asegurar que todos los modelos estén disponibles para importación
__all__ = [
    'User',
    'Document',
    'AccesoDocumentosUsuario',
    'DocumentAccess',
    'Chat',
    'Message',
    'Base'
]
