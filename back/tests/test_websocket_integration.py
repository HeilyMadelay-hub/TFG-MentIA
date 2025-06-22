import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from websocket import create_connection, WebSocket
import time

from src.main import app

class TestWebSocketIntegration:
    """Tests de integración para WebSocket"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, client):
        """Login y obtener headers de autenticación"""
        response = client.post("/api/users/login", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def auth_token(self, client):
        """Obtener solo el token"""
        response = client.post("/api/users/login", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def chat_id(self, client, auth_headers):
        """Crear un chat para las pruebas"""
        response = client.post(
            "/api/chats",
            json={"name": "Test Chat"},
            headers=auth_headers
        )
        return response.json()["id"]
    
    def test_websocket_connection_without_token(self, chat_id):
        """Test: conexión sin token debe fallar"""
        with pytest.raises(Exception):
            ws = create_connection(f"ws://localhost:8000/api/ws/chat/{chat_id}")
    
    def test_websocket_connection_with_invalid_token(self, chat_id):
        """Test: conexión con token inválido debe fallar"""
        with pytest.raises(Exception):
            ws = create_connection(f"ws://localhost:8000/api/ws/chat/{chat_id}?token=invalid")
    
    def test_websocket_connection_success(self, chat_id, auth_token):
        """Test: conexión exitosa con token válido"""
        ws = create_connection(f"ws://localhost:8000/api/ws/chat/{chat_id}?token={auth_token}")
        
        # Debe recibir mensaje de bienvenida
        result = ws.recv()
        data = json.loads(result)
        
        assert data["type"] == "connection_success"
        assert "chat_id" in data["data"]
        assert data["data"]["chat_id"] == chat_id
        
        ws.close()
    
    def test_websocket_ping_pong(self, chat_id, auth_token):
        """Test: ping/pong para mantener conexión"""
        ws = create_connection(f"ws://localhost:8000/api/ws/chat/{chat_id}?token={auth_token}")
        
        # Recibir mensaje de bienvenida
        ws.recv()
        
        # Enviar ping
        ws.send(json.dumps({
            "type": "ping",
            "data": {"timestamp": "2024-01-01T00:00:00"}
        }))
        
        # Debe recibir pong
        result = ws.recv()
        data = json.loads(result)
        
        assert data["type"] == "pong"
        assert "timestamp" in data["data"]
        
        ws.close()
    
    def test_websocket_message_streaming(self, chat_id, auth_token):
        """Test: envío de mensaje con streaming"""
        ws = create_connection(f"ws://localhost:8000/api/ws/chat/{chat_id}?token={auth_token}")
        
        # Recibir mensaje de bienvenida
        ws.recv()
        
        # Enviar mensaje
        ws.send(json.dumps({
            "type": "message",
            "data": {
                "content": "Hola, ¿cómo estás?",
                "stream": True
            }
        }))
        
        # Recolectar respuestas
        stream_started = False
        chunks_received = 0
        stream_ended = False
        
        # Timeout de 30 segundos para toda la operación
        start_time = time.time()
        while time.time() - start_time < 30:
            result = ws.recv()
            data = json.loads(result)
            
            if data["type"] == "stream_start":
                stream_started = True
                assert "stream_id" in data["data"]
            elif data["type"] == "stream_chunk":
                chunks_received += 1
                assert "content" in data["data"]
                assert "chunk_index" in data["data"]
            elif data["type"] == "stream_end":
                stream_ended = True
                assert "total_chunks" in data["data"]
                assert data["data"]["total_chunks"] == chunks_received
                break
        
        assert stream_started
        assert chunks_received > 0
        assert stream_ended
        
        ws.close()
    
    def test_websocket_message_without_streaming(self, chat_id, auth_token):
        """Test: envío de mensaje sin streaming"""
        ws = create_connection(f"ws://localhost:8000/api/ws/chat/{chat_id}?token={auth_token}")
        
        # Recibir mensaje de bienvenida
        ws.recv()
        
        # Enviar mensaje sin streaming
        ws.send(json.dumps({
            "type": "message",
            "data": {
                "content": "Dame una respuesta corta",
                "stream": False
            }
        }))
        
        # Debe recibir respuesta completa
        result = ws.recv()
        data = json.loads(result)
        
        assert data["type"] == "message"
        assert "answer" in data["data"]
        assert len(data["data"]["answer"]) > 0
        
        ws.close()
    
    def test_websocket_rate_limiting(self, chat_id, auth_token):
        """Test: rate limiting de mensajes"""
        ws = create_connection(f"ws://localhost:8000/api/ws/chat/{chat_id}?token={auth_token}")
        
        # Recibir mensaje de bienvenida
        ws.recv()
        
        # Enviar muchos mensajes rápidamente
        for i in range(25):  # Más del límite de 20/minuto
            ws.send(json.dumps({
                "type": "message",
                "data": {
                    "content": f"Mensaje {i}",
                    "stream": False
                }
            }))
        
        # Eventualmente debería recibir advertencia de rate limit
        rate_limit_warning_received = False
        for _ in range(30):
            result = ws.recv()
            data = json.loads(result)
            if data["type"] == "rate_limit_warning":
                rate_limit_warning_received = True
                break
        
        assert rate_limit_warning_received
        ws.close()
    
    def test_websocket_typing_indicator(self, chat_id, auth_token):
        """Test: indicador de escritura"""
        ws = create_connection(f"ws://localhost:8000/api/ws/chat/{chat_id}?token={auth_token}")
        
        # Recibir mensaje de bienvenida
        ws.recv()
        
        # Enviar indicador de escritura
        ws.send(json.dumps({
            "type": "typing_indicator",
            "data": {"is_typing": True}
        }))
        
        # No debería recibir error
        time.sleep(0.5)
        
        # Enviar indicador de dejar de escribir
        ws.send(json.dumps({
            "type": "typing_indicator",
            "data": {"is_typing": False}
        }))
        
        ws.close()
    
    @pytest.mark.asyncio
    async def test_websocket_multiple_connections(self, chat_id, auth_token):
        """Test: múltiples conexiones al mismo chat"""
        # Este test requiere conexiones asíncronas
        # Implementar con websockets library en lugar de websocket-client
        pass
    
    def test_websocket_status_endpoint(self, client, auth_headers):
        """Test: endpoint de estado de WebSocket"""
        response = client.get("/api/ws/connections/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_connections" in data
        assert "active_connections" in data
        assert "messages_sent" in data
        assert "messages_received" in data
