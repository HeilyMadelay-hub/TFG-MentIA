"""
Helpers para WebSocket de chat
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import WebSocket
from src.models.schemas.chat_websocket import MessageType, MessageFactory

class ChatWebSocketHelpers:
    """Helpers para facilitar operaciones WebSocket"""
    
    async def send_welcome_message(
        self, 
        websocket: WebSocket, 
        chat_id: int, 
        user_id: int
    ) -> None:
        """Envía mensaje de bienvenida al conectarse"""
        await websocket.send_json({
            "type": MessageType.CONNECTION_SUCCESS,
            "data": {
                "chat_id": chat_id,
                "user_id": user_id,
                "message": "Conexión establecida exitosamente",
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
    async def send_error(
        self,
        websocket: WebSocket,
        error: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Envía mensaje de error"""
        await websocket.send_json({
            "type": MessageType.ERROR,
            "data": {
                "error": error,
                "error_code": error_code,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
    async def send_rate_limit_warning(
        self,
        websocket: WebSocket,
        remaining_messages: int,
        reset_time: datetime
    ) -> None:
        """Envía advertencia de rate limit"""
        await websocket.send_json({
            "type": MessageType.RATE_LIMIT_WARNING,
            "data": {
                "remaining_messages": remaining_messages,
                "reset_time": reset_time.isoformat(),
                "message": f"Has alcanzado el límite de mensajes. Te quedan {remaining_messages} mensajes."
            }
        })
        
    async def start_stream(
        self,
        websocket: WebSocket,
        question: str
    ) -> str:
        """Inicia un stream de respuesta"""
        stream_id = str(uuid.uuid4())
        await websocket.send_json({
            "type": MessageType.STREAM_START,
            "data": {
                "stream_id": stream_id,
                "question": question,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        return stream_id
        
    async def send_stream_chunk(
        self,
        websocket: WebSocket,
        stream_id: str,
        content: str,
        chunk_index: int
    ) -> None:
        """Envía un chunk del stream"""
        await websocket.send_json({
            "type": MessageType.STREAM_CHUNK,
            "data": {
                "stream_id": stream_id,
                "content": content,
                "chunk_index": chunk_index,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
    async def end_stream(
        self,
        websocket: WebSocket,
        stream_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Finaliza un stream"""
        await websocket.send_json({
            "type": MessageType.STREAM_END,
            "data": {
                "stream_id": stream_id,
                **metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
    async def send_message_saved(
        self,
        websocket: WebSocket,
        message_id: int,
        question: str,
        answer: str
    ) -> None:
        """Confirma que un mensaje fue guardado"""
        await websocket.send_json({
            "type": MessageType.MESSAGE_SAVED,
            "data": {
                "message_id": message_id,
                "question": question,
                "answer": answer,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
    async def send_typing_indicator(
        self,
        websocket: WebSocket,
        user_id: int,
        is_typing: bool
    ) -> None:
        """Envía indicador de escritura"""
        await websocket.send_json({
            "type": MessageType.TYPING_INDICATOR,
            "data": {
                "user_id": user_id,
                "is_typing": is_typing,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
