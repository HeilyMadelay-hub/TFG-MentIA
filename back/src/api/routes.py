# src/api/routes.py
from fastapi import APIRouter
from src.api.endpoints import documents, users, health, statistics, admin, files, chat, chat_websocket
from src.api.endpoints.admin_panel import dashboard as admin_panel_dashboard

api_router = APIRouter()

# Incluir los routers de endpoints
# ORDEN IMPORTANTE: admin ANTES que documents para evitar conflictos
api_router.include_router(health.router)      # Health checks
api_router.include_router(users.router)       # Autenticación y usuarios
api_router.include_router(admin.router)       # Endpoints administrativos (ANTES que documents)
api_router.include_router(documents.router)   # Gestión de documentos
api_router.include_router(files.router)       # Servir archivos almacenados
api_router.include_router(chat.router)        # Chat con RAG integrado
api_router.include_router(statistics.router)  # Estadísticas globales
api_router.include_router(admin_panel_dashboard.router)  # Panel de administración mejorado

# Importar el router de WebSocket
from .endpoints.chat_websocket import router as websocket_router

# Agregar a la función que incluye todos los routers:
api_router.include_router(
    websocket_router,
    tags=["websocket"],
    prefix=""  # Sin prefijo porque ya incluye /ws en las rutas
)