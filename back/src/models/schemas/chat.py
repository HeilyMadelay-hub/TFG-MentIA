from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

class MessageBase(BaseModel):
    """Base para mensajes"""
    question: str
    answer: Optional[str] = None

class MessageCreate(BaseModel):
    """Esquema para crear un nuevo mensaje"""
    question: str = Field(..., min_length=1, max_length=5000)
    document_ids: Optional[List[int]] = Field(None, description="IDs de documentos para usar en RAG")
    n_results: Optional[int] = Field(5, description="Número de resultados para RAG")

class MessageResponse(MessageBase):
    """Respuesta de mensaje - coincide con tabla messages"""
    id: Optional[int] = None
    id_chat: int
    created_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }

class ChatBase(BaseModel):
    """Base para chat - TODOS los campos opcionales para consistencia con BD"""
    name_chat: Optional[str] = None  # CAMBIADO A OPCIONAL
    
    @field_validator('name_chat')
    def name_not_empty(cls, v):
        # Si se proporciona un nombre, no puede ser vacío
        if v is not None and (not v or not v.strip()):
            raise ValueError('Si proporcionas un nombre, no puede estar vacío')
        return v.strip() if v else v

class ChatCreate(BaseModel):
    """Esquema para crear un nuevo chat.
    
    Según la BD: name_chat es OPCIONAL (no tiene NOT NULL en la tabla chats)
    """
    name_chat: Optional[str] = Field(None, description="Nombre del chat - OPCIONAL según BD")
    
    @field_validator('name_chat')
    def name_not_empty(cls, v):
        # Si se proporciona un nombre, no puede ser vacío
        if v is not None and (not v or not v.strip()):
            raise ValueError('Si proporcionas un nombre, no puede estar vacío')
        return v.strip() if v else v

class ChatUpdate(BaseModel):
    """Esquema para actualizar un chat"""
    name_chat: Optional[str] = None
    
    @field_validator('name_chat')
    def name_not_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('el nombre del chat no puede estar vacío')
        return v.strip() if v else v

class ChatResponse(BaseModel):
    """Respuesta de chat - NO hereda de ChatBase para evitar conflictos"""
    id: int
    name_chat: Optional[str] = None  # OPCIONAL como en la BD
    id_user: int
    created_at: datetime
    messages: Optional[List[MessageResponse]] = None
    
    model_config = {
        "from_attributes": True
    }

class ChatSimpleResponse(BaseModel):
    """Respuesta simple de chat sin mensajes"""
    id: int
    name_chat: Optional[str] = None  # OPCIONAL como en la BD
    id_user: int
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }

class ChatRename(BaseModel):
    """Schema específico para renombrar un chat"""
    name: str = Field(..., min_length=1, max_length=100, description="Nuevo nombre para el chat")
    
    @field_validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('El nombre del chat no puede estar vacío')
        return v.strip()

# Alias para compatibilidad
ChatMessage = MessageResponse
