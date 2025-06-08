# Modelos del dominio
from .domain import (
    User,
    Document,
    AccesoDocumentosUsuario,
    DocumentAccess,  # Alias
    Chat,
    Message,
    Base
)

# Schemas
from .schemas import (
    # User
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserInDB,
    
    # Document
    DocumentBase,
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentShare,
    DocumentUserLink,
    DocumentAccess as DocumentAccessSchema,
    DocumentUploadResponse,
    DocumentResponseHybrid,
    
    # Chat
    ChatBase,
    ChatCreate,
    ChatUpdate,
    ChatResponse,
    ChatSimpleResponse,
    MessageBase,
    MessageCreate,
    MessageResponse,
    ChatMessage
)

__all__ = [
    # Domain models
    "User",
    "Document", 
    "AccesoDocumentosUsuario",
    "DocumentAccess",
    "Chat",
    "Message",
    "Base",
    
    # User schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    
    # Document schemas
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "DocumentShare",
    "DocumentUserLink",
    "DocumentAccessSchema",
    "DocumentUploadResponse",
    "DocumentResponseHybrid",
    
    # Chat schemas
    "ChatBase",
    "ChatCreate",
    "ChatUpdate",
    "ChatResponse",
    "ChatSimpleResponse",
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "ChatMessage"
]
