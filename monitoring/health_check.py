"""
Script de monitoreo de salud del sistema con WebSocket
"""
import asyncio
import aiohttp
import websockets
import json
from datetime import datetime

BACKEND_URL = "http://localhost:2690"
WEBSOCKET_URL = "ws://localhost:2690/api/ws/chat/1"

async def check_backend_health():
    """Verifica salud del backend"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Backend: {data.get('status', 'OK')}")
                    return True
                else:
                    print(f"❌ Backend: Error {resp.status}")
                    return False
    except Exception as e:
        print(f"❌ Backend: {str(e)}")
        return False

async def check_websocket_health(token: str):
    """Verifica salud de WebSocket"""
    try:
        uri = f"{WEBSOCKET_URL}?token={token}"
        async with websockets.connect(uri) as websocket:
            # Esperar mensaje de bienvenida
            welcome = await websocket.recv()
            data = json.loads(welcome)
            
            if data.get("type") == "connection_success":
                print("✅ WebSocket: Conexión exitosa")
                
                # Enviar ping
                await websocket.send(json.dumps({
                    "type": "ping",
                    "data": {"timestamp": datetime.utcnow().isoformat()}
                }))
                
                # Esperar pong
                pong = await websocket.recv()
                pong_data = json.loads(pong)
                
                if pong_data.get("type") == "pong":
                    print("✅ WebSocket: Ping/Pong funcionando")
                    return True
            
            print("❌ WebSocket: Respuesta inesperada")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket: {str(e)}")
        return False

async def get_websocket_stats(token: str):
    """Obtiene estadísticas de WebSocket"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {token}"}
            async with session.get(
                f"{BACKEND_URL}/api/ws/connections/status",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print("\n📊 Estadísticas WebSocket:")
                    print(f"  - Conexiones totales: {data.get('total_connections', 0)}")
                    print(f"  - Conexiones activas: {data.get('active_connections', 0)}")
                    print(f"  - Mensajes enviados: {data.get('messages_sent', 0)}")
                    print(f"  - Mensajes recibidos: {data.get('messages_received', 0)}")
                    return True
    except Exception as e:
        print(f"❌ No se pudieron obtener estadísticas: {str(e)}")
        return False

async def main():
    """Función principal de monitoreo"""
    print("🔍 Iniciando verificación de salud del sistema...")
    print("=" * 50)
    
    # Verificar backend
    backend_ok = await check_backend_health()
    
    if backend_ok:
        # Obtener token de prueba (deberías tener uno válido)
        # Por ahora, saltamos la verificación de WebSocket si no hay token
        print("\n⚠️  Para verificar WebSocket, proporciona un token válido")
        
        # Ejemplo de cómo sería con token:
        # token = "tu_token_aqui"
        # await check_websocket_health(token)
        # await get_websocket_stats(token)
    
    print("\n" + "=" * 50)
    print("✅ Verificación completada")

if __name__ == "__main__":
    asyncio.run(main())
