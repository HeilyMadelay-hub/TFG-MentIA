"""
ACTUALIZAR el WebSocketManager existente para usar los nuevos servicios
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
from src.services.chat import ChatWebSocketService, ChatStreamingService
from src.api.helpers import ChatWebSocketHelpers
from src.models.schemas.chat_websocket import MessageType, StreamStatus

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        # Diccionario de conexiones activas: {chat_id: {user_id: websocket}}
        self._connections: Dict[int, Dict[int, WebSocket]] = {}
        # Servicios
        self.chat_service = ChatWebSocketService()
        self.streaming_service = ChatStreamingService()
        self.helpers = ChatWebSocketHelpers()
        # Métricas
        self.total_connections = 0
        self.messages_sent = 0
        self.messages_received = 0
        # Rate limiting: {user_id: [timestamps]}
        self._user_message_timestamps: Dict[int, List[datetime]] = {}
        self.rate_limit_per_minute = 20
        
    async def connect(self, websocket: WebSocket, chat_id: int, user_id: int):
        """Acepta nueva conexión WebSocket"""
        await websocket.accept()
        
        # Verificar acceso al chat
        if not self.chat_service.verify_chat_access(chat_id, user_id):
            await self.helpers.send_error(
                websocket, 
                "No tienes acceso a este chat",
                "ACCESS_DENIED"
            )
            await websocket.close()
            return False
            
        # Registrar conexión
        if chat_id not in self._connections:
            self._connections[chat_id] = {}
        self._connections[chat_id][user_id] = websocket
        self.total_connections += 1
        
        # Enviar mensaje de bienvenida
        await self.helpers.send_welcome_message(websocket, chat_id, user_id)
        
        # Registrar evento
        self.chat_service.handle_connection_event(
            chat_id, user_id, "connect", 
            {"total_connections": len(self._connections[chat_id])}
        )
        
        logger.info(f"Usuario {user_id} conectado a chat {chat_id}")
        return True
        
    async def disconnect(self, chat_id: int, user_id: int):
        """Desconecta usuario del chat"""
        if chat_id in self._connections and user_id in self._connections[chat_id]:
            del self._connections[chat_id][user_id]
            if not self._connections[chat_id]:
                del self._connections[chat_id]
                
        # Registrar evento
        self.chat_service.handle_connection_event(
            chat_id, user_id, "disconnect",
            {"remaining_connections": len(self._connections.get(chat_id, {}))}
        )
        
        logger.info(f"Usuario {user_id} desconectado de chat {chat_id}")
        
    async def handle_message(self, websocket: WebSocket, chat_id: int, user_id: int, message: dict):
        """Procesa mensaje entrante"""
        try:
            msg_type = message.get("type")
            data = message.get("data", {})
            
            # Rate limiting
            if not await self._check_rate_limit(user_id):
                await self.helpers.send_rate_limit_warning(
                    websocket, 
                    self._get_remaining_messages(user_id),
                    self._get_rate_limit_reset_time(user_id)
                )
                return
                
            if msg_type == MessageType.MESSAGE:
                await self._handle_chat_message(websocket, chat_id, user_id, data)
            elif msg_type == MessageType.PING:
                await self._handle_ping(websocket)
            elif msg_type == MessageType.TYPING_INDICATOR:
                await self._handle_typing_indicator(chat_id, user_id, data)
            else:
                await self.helpers.send_error(
                    websocket,
                    f"Tipo de mensaje no soportado: {msg_type}",
                    "UNSUPPORTED_MESSAGE_TYPE"
                )
                
            self.messages_received += 1
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            await self.helpers.send_error(
                websocket,
                "Error procesando mensaje",
                "PROCESSING_ERROR",
                {"detail": str(e)}
            )
            
    async def _handle_chat_message(self, websocket: WebSocket, chat_id: int, user_id: int, data: dict):
        """Procesa mensaje de chat con streaming"""
        content = data.get("content", "").strip()
        document_ids = data.get("document_ids", [])
        stream = data.get("stream", True)
        
        if not content:
            await self.helpers.send_error(websocket, "Mensaje vacío", "EMPTY_MESSAGE")
            return
            
        try:
            if stream:
                # Streaming habilitado
                stream_id = await self.helpers.start_stream(websocket, content)
                
                # Generar respuesta en streaming
                chunk_index = 0
                full_response = ""
                start_time = datetime.utcnow()
                
                async for chunk in self.streaming_service.stream_ai_response(
                    question=content,
                    chat_id=chat_id,
                    user_id=user_id,
                    document_ids=document_ids
                ):
                    # Enviar chunk
                    await self.helpers.send_stream_chunk(
                        websocket, stream_id, chunk, chunk_index
                    )
                    full_response += chunk
                    chunk_index += 1
                    self.messages_sent += 1
                    
                # Finalizar stream
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                
                await self.helpers.end_stream(websocket, stream_id, {
                    "total_chunks": chunk_index,
                    "total_tokens": self.streaming_service.estimate_tokens(full_response),
                    "processing_time": processing_time,
                    "content_length": len(full_response)
                })
                
                # Guardar mensaje en DB
                message_id = self.chat_service.save_message(
                    chat_id=chat_id,
                    question=content,
                    answer=full_response,
                    user_id=user_id,
                    processing_time=processing_time
                )
                
                # Confirmar guardado
                await self.helpers.send_message_saved(
                    websocket, message_id, content, full_response
                )
                
            else:
                # Sin streaming - respuesta completa
                result = self.chat_service.process_message(
                    chat_id=chat_id,
                    user_id=user_id,
                    content=content,
                    document_ids=document_ids
                )
                
                await websocket.send_json({
                    "type": MessageType.MESSAGE,
                    "data": result
                })
                self.messages_sent += 1
                
        except Exception as e:
            logger.error(f"Error generando respuesta: {str(e)}")
            await self.helpers.send_error(
                websocket,
                "Error generando respuesta",
                "GENERATION_ERROR",
                {"detail": str(e)}
            )
            
    async def _handle_ping(self, websocket: WebSocket):
        """Responde a ping con pong"""
        await websocket.send_json({
            "type": MessageType.PONG,
            "data": {"timestamp": datetime.utcnow().isoformat()}
        })
        
    async def _handle_typing_indicator(self, chat_id: int, user_id: int, data: dict):
        """Broadcast indicador de escritura a otros usuarios"""
        is_typing = data.get("is_typing", False)
        
        # Enviar a todos los demás usuarios en el chat
        if chat_id in self._connections:
            for other_user_id, ws in self._connections[chat_id].items():
                if other_user_id != user_id:
                    try:
                        await self.helpers.send_typing_indicator(ws, user_id, is_typing)
                    except:
                        pass  # Ignorar errores de broadcast
                        
    async def _check_rate_limit(self, user_id: int) -> bool:
        """Verifica rate limit del usuario"""
        now = datetime.utcnow()
        if user_id not in self._user_message_timestamps:
            self._user_message_timestamps[user_id] = []
            
        # Limpiar timestamps antiguos (más de 1 minuto)
        self._user_message_timestamps[user_id] = [
            ts for ts in self._user_message_timestamps[user_id]
            if (now - ts).total_seconds() < 60
        ]
        
        # Verificar límite
        if len(self._user_message_timestamps[user_id]) >= self.rate_limit_per_minute:
            return False
            
        # Agregar timestamp actual
        self._user_message_timestamps[user_id].append(now)
        return True
        
    def _get_remaining_messages(self, user_id: int) -> int:
        """Obtiene mensajes restantes para el usuario"""
        if user_id not in self._user_message_timestamps:
            return self.rate_limit_per_minute
        return self.rate_limit_per_minute - len(self._user_message_timestamps[user_id])
        
    def _get_rate_limit_reset_time(self, user_id: int) -> datetime:
        """Obtiene tiempo de reset del rate limit"""
        if user_id not in self._user_message_timestamps or not self._user_message_timestamps[user_id]:
            return datetime.utcnow()
        oldest_timestamp = min(self._user_message_timestamps[user_id])
        return oldest_timestamp + timedelta(minutes=1)
        
    def get_stats(self) -> dict:
        """Obtiene estadísticas del WebSocket"""
        return {
            "total_connections": self.total_connections,
            "active_connections": sum(len(users) for users in self._connections.values()),
            "active_chats": len(self._connections),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "connections_by_chat": {
                chat_id: len(users) for chat_id, users in self._connections.items()
            }
        }

# Instancia global
websocket_manager = WebSocketManager()
