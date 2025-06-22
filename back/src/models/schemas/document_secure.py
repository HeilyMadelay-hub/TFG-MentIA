"""
Esquemas extendidos para respuestas de documentos con URLs firmadas.
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from src.models.schemas.document import DocumentResponse

class DocumentWithSignedURL(DocumentResponse):
    """
    Respuesta de documento que incluye URL firmada para acceso seguro.
    """
    signed_url: Optional[str] = Field(
        None, 
        description="URL firmada con token temporal para acceso seguro al archivo"
    )
    signed_url_expires: Optional[datetime] = Field(
        None,
        description="Fecha y hora de expiración de la URL firmada"
    )
    download_url: Optional[str] = Field(
        None,
        description="URL firmada para descarga directa del archivo"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class SecureFileAccessRequest(BaseModel):
    """
    Request para generar URLs firmadas de acceso a archivos.
    """
    document_id: int = Field(..., description="ID del documento")
    access_type: str = Field(
        "preview",
        description="Tipo de acceso: 'preview' (1 hora) o 'download' (24 horas)"
    )
    
class SecureFileAccessResponse(BaseModel):
    """
    Response con URLs firmadas para acceso a archivos.
    """
    document_id: int
    preview_url: str = Field(..., description="URL para vista previa (expira en 1 hora)")
    download_url: str = Field(..., description="URL para descarga (expira en 24 horas)")
    expires_at: datetime = Field(..., description="Fecha y hora de expiración")
