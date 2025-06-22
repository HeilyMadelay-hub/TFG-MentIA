"""
Endpoints WebSocket para chat en tiempo real
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import logging
import json

from src.core.websocket_manager import websocket_manager
from src.core.auth import verify_websocket_token
from src.models.domain import User

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    chat_id: int,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint para chat en tiempo real
    
    Protocolo:
    - Cliente envía token como query parameter
    - Servidor valida token y acepta conexión
    - Cliente puede enviar mensajes tipo:
        - message: Para enviar mensajes de chat
        - ping: Para mantener conexión viva
        - typing_indicator: Para mostrar indicador de escritura
    - Servidor responde con:
        - stream_start/chunk/end: Para respuestas en streaming
        - error: Para errores
        - heartbeat: Para mantener conexión
    """
    user = None
    
    try:
        # Validar token
        if not token:
            await websocket.close(code=4001, reason="Token requerido")
            return
            
        user = verify_websocket_token(token)
        if not user:
            await websocket.close(code=4001, reason="Token inválido")
            return
            
        # Conectar al manager
        connected = await websocket_manager.connect(websocket, chat_id, user.id)
        if not connected:
            return
            
        # Loop principal de mensajes
        while True:
            try:
                # Recibir mensaje
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Procesar mensaje
                await websocket_manager.handle_message(
                    websocket, chat_id, user.id, message
                )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket desconectado: usuario {user.id}, chat {chat_id}")
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": "Mensaje JSON inválido"}
                })
            except Exception as e:
                logger.error(f"Error en WebSocket: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": "Error interno del servidor"}
                })
                
    except Exception as e:
        logger.error(f"Error fatal en WebSocket: {str(e)}")
    finally:
        # Desconectar si hay usuario
        if user:
            await websocket_manager.disconnect(chat_id, user.id)

@router.get("/ws/connections/status")
async def get_websocket_status():
    """Obtiene estado de las conexiones WebSocket"""
    return websocket_manager.get_stats()

@router.get("/ws/chat/{chat_id}/users")
async def get_chat_active_users(chat_id: int):
    """Obtiene usuarios activos en un chat"""
    if chat_id in websocket_manager._connections:
        return {
            "chat_id": chat_id,
            "active_users": list(websocket_manager._connections[chat_id].keys()),
            "count": len(websocket_manager._connections[chat_id])
        }
    return {
        "chat_id": chat_id,
        "active_users": [],
        "count": 0
    }
