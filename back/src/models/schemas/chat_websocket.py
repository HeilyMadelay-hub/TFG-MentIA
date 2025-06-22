"""
Schemas para WebSocket de chat
"""
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class MessageType(str, Enum):
    """Tipos de mensajes WebSocket"""
    # Cliente -> Servidor
    MESSAGE = "message"
    PING = "ping"
    TYPING_INDICATOR = "typing_indicator"
    
    # Servidor -> Cliente
    CONNECTION_SUCCESS = "connection_success"
    STREAM_START = "stream_start"
    STREAM_CHUNK = "stream_chunk"
    STREAM_END = "stream_end"
    MESSAGE_SAVED = "message_saved"
    ERROR = "error"
    PONG = "pong"
    RATE_LIMIT_WARNING = "rate_limit_warning"
    STATUS_UPDATE = "status_update"

class StreamStatus(str, Enum):
    """Estados del streaming"""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"

class BaseWebSocketMessage(BaseModel):
    """Mensaje base de WebSocket"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class UserMessageData(BaseModel):
    """Datos de un mensaje de usuario"""
    content: str
    document_ids: Optional[List[int]] = []
    stream: bool = True

class ConnectionSuccessMessage(BaseWebSocketMessage):
    """Mensaje de conexión exitosa"""
    type: MessageType = MessageType.CONNECTION_SUCCESS
    data: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, chat_id: int, user_id: int, **data):
        super().__init__(
            data={
                "chat_id": chat_id,
                "user_id": user_id,
                "message": "Conexión establecida exitosamente",
                **data
            }
        )

class ErrorMessage(BaseWebSocketMessage):
    """Mensaje de error"""
    type: MessageType = MessageType.ERROR
    
    def __init__(self, error: str, error_code: str, details: Optional[Dict[str, Any]] = None, **data):
        super().__init__(
            data={
                "error": error,
                "error_code": error_code,
                "details": details or {},
                **data
            }
        )

class StreamStartMessage(BaseWebSocketMessage):
    """Mensaje de inicio de stream"""
    type: MessageType = MessageType.STREAM_START
    
    def __init__(self, stream_id: str, question: str, **data):
        super().__init__(
            data={
                "stream_id": stream_id,
                "question": question,
                **data
            }
        )

class StreamChunkMessage(BaseWebSocketMessage):
    """Mensaje de chunk de stream"""
    type: MessageType = MessageType.STREAM_CHUNK
    
    def __init__(self, stream_id: str, content: str, chunk_index: int, **data):
        super().__init__(
            data={
                "stream_id": stream_id,
                "content": content,
                "chunk_index": chunk_index,
                **data
            }
        )

class StreamEndMessage(BaseWebSocketMessage):
    """Mensaje de fin de stream"""
    type: MessageType = MessageType.STREAM_END
    
    def __init__(self, stream_id: str, total_chunks: int, total_tokens: int, 
                 processing_time: float, content_length: int, **data):
        super().__init__(
            data={
                "stream_id": stream_id,
                "total_chunks": total_chunks,
                "total_tokens": total_tokens,
                "processing_time": processing_time,
                "content_length": content_length,
                **data
            }
        )

class StatusUpdateMessage(BaseWebSocketMessage):
    """Mensaje de actualización de estado"""
    type: MessageType = MessageType.STATUS_UPDATE
    
    def __init__(self, status: str, message: str, **data):
        super().__init__(
            data={
                "status": status,
                "message": message,
                **data
            }
        )

class MessageFactory:
    """Factory para crear mensajes WebSocket"""
    
    @staticmethod
    def create_connection_success(chat_id: int, user_id: int) -> Dict[str, Any]:
        """Crea mensaje de conexión exitosa"""
        return ConnectionSuccessMessage(chat_id=chat_id, user_id=user_id).dict()
    
    @staticmethod
    def create_error(error: str, error_code: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Crea mensaje de error"""
        return ErrorMessage(error=error, error_code=error_code, details=details).dict()
    
    @staticmethod
    def create_stream_start(stream_id: str, question: str) -> Dict[str, Any]:
        """Crea mensaje de inicio de stream"""
        return StreamStartMessage(stream_id=stream_id, question=question).dict()
    
    @staticmethod
    def create_stream_chunk(stream_id: str, content: str, chunk_index: int) -> Dict[str, Any]:
        """Crea mensaje de chunk de stream"""
        return StreamChunkMessage(stream_id=stream_id, content=content, chunk_index=chunk_index).dict()
    
    @staticmethod
    def create_stream_end(stream_id: str, total_chunks: int, total_tokens: int,
                         processing_time: float, content_length: int) -> Dict[str, Any]:
        """Crea mensaje de fin de stream"""
        return StreamEndMessage(
            stream_id=stream_id,
            total_chunks=total_chunks,
            total_tokens=total_tokens,
            processing_time=processing_time,
            content_length=content_length
        ).dict()
    
    @staticmethod
    def create_status_update(status: str, message: str) -> Dict[str, Any]:
        """Crea mensaje de actualización de estado"""
        return StatusUpdateMessage(status=status, message=message).dict()

class WebSocketConnectionInfo(BaseModel):
    """Información de conexión WebSocket"""
    connection_id: str
    user_id: int
    chat_id: int
    connected_at: datetime
    last_activity: datetime
    messages_sent: int = 0
    messages_received: int = 0
    is_active: bool = True

class WebSocketStats(BaseModel):
    """Estadísticas de WebSocket"""
    total_connections: int
    active_connections: int
    messages_sent: int
    messages_received: int
    average_response_time: float
    uptime_seconds: int

# Schemas adicionales que estaban en la versión original
class WebSocketMessage(BaseModel):
    """Mensaje base de WebSocket (alias para compatibilidad)"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MessageData(BaseModel):
    """Datos de un mensaje de chat (alias para compatibilidad)"""
    content: str
    document_ids: Optional[List[int]] = []
    stream: bool = True

class StreamStartData(BaseModel):
    """Datos de inicio de stream"""
    stream_id: str
    question: str
    timestamp: datetime

class StreamChunkData(BaseModel):
    """Datos de chunk de stream"""
    stream_id: str
    content: str
    chunk_index: int
    timestamp: datetime

class StreamEndData(BaseModel):
    """Datos de fin de stream"""
    stream_id: str
    total_chunks: int
    total_tokens: int
    processing_time: float
    content_length: int
    timestamp: datetime
