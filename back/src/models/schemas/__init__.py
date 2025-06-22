# Schemas de Pydantic para validación de datos

# User schemas
from .user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserInDB
)

# Document schemas
from .document import (
    DocumentBase,
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentShare,
    DocumentUserLink,
    DocumentAccess,
    DocumentUploadResponse,
    DocumentResponseHybrid
)

# Chat schemas
from .chat import (
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

# WebSocket schemas
from .chat_websocket import (
    MessageType,
    StreamStatus,
    BaseWebSocketMessage,
    UserMessageData,
    ConnectionSuccessMessage,
    ErrorMessage,
    StreamStartMessage,
    StreamChunkMessage,
    StreamEndMessage,
    StatusUpdateMessage,
    MessageFactory,
    WebSocketConnectionInfo,
    WebSocketStats
)

__all__ = [
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    
    # Document
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "DocumentShare",
    "DocumentUserLink",
    "DocumentAccess",
    "DocumentUploadResponse",
    "DocumentResponseHybrid",
    
    # Chat
    "ChatBase",
    "ChatCreate",
    "ChatUpdate",
    "ChatResponse",
    "ChatSimpleResponse",
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "ChatMessage",
    
    # WebSocket
    "MessageType",
    "StreamStatus",
    "BaseWebSocketMessage",
    "UserMessageData",
    "ConnectionSuccessMessage",
    "ErrorMessage",
    "StreamStartMessage",
    "StreamChunkMessage",
    "StreamEndMessage",
    "StatusUpdateMessage",
    "MessageFactory",
    "WebSocketConnectionInfo",
    "WebSocketStats"
]
