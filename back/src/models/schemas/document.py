from pydantic import BaseModel, Field, field_validator, validator
from typing import Optional, List
from datetime import datetime

class DocumentBase(BaseModel):
    """Base para documento - campos comunes"""
    title: str
    content_type: Optional[str] = Field(None, description="Tipo de documento (pdf, txt, etc.)")
    
    @field_validator('title')
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('el título no puede estar vacío')
        return v

class DocumentCreate(DocumentBase):
    """Crear nuevo documento"""
    # Campos opcionales durante la creación
    content: Optional[str] = None
    original_filename: Optional[str] = None
    file_size: Optional[int] = None

class DocumentUpdate(BaseModel):
    """Actualizar documento"""
    title: Optional[str] = None
    content: Optional[str] = None  # Para actualizar el contenido del documento
    content_type: Optional[str] = None
    tags: Optional[List[str]] = None  # Para actualizar las etiquetas
    status: Optional[str] = None
    status_message: Optional[str] = None
    chromadb_id: Optional[str] = None
    file_url: Optional[str] = None

class DocumentResponse(DocumentBase):
    """Respuesta completa del documento - coincide con tabla documents"""
    id: int
    chromadb_id: Optional[str] = None
    uploaded_by: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    file_url: Optional[str] = None
    status: str = 'pending'
    status_message: Optional[str] = None
    file_size: Optional[int] = None
    original_filename: Optional[str] = None
    
    model_config = {
        "from_attributes": True
    }

class DocumentShare(BaseModel):
    """Compartir documento con usuarios"""
    document_id: int
    user_ids: List[int]

class ShareDocumentRequest(BaseModel):
    """Request para compartir documento con validación"""
    user_ids: List[int]
    
    @validator('user_ids')
    def validate_user_ids(cls, v):
        if not v:
            raise ValueError("Debe especificar al menos un ID de usuario")
        # Eliminar duplicados
        return list(set(v))

class DocumentUserLink(BaseModel):
    """Vincular usuarios a documentos"""
    user_ids: List[int]

class DocumentAccess(BaseModel):
    """Acceso a documentos - coincide con tabla acceso_documentos_usuario"""
    id_document: int
    id_user: int
    linked_time: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }

class DocumentUploadResponse(BaseModel):
    """Respuesta inmediata al subir documento"""
    document_id: int
    title: str
    status: str
    message: str

# Alias para compatibilidad
DocumentResponseHybrid = DocumentResponse
