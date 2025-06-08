# src/api/routes.py
from fastapi import APIRouter
from src.api.endpoints import documents, chat, users, health, statistics, admin

api_router = APIRouter()

# Incluir los routers de endpoints
api_router.include_router(health.router)      # Health checks
api_router.include_router(users.router)       # Autenticación y usuarios
api_router.include_router(documents.router)   # Gestión de documentos
api_router.include_router(chat.router)        # Chat con RAG integrado
api_router.include_router(statistics.router)  # Estadísticas globales
api_router.include_router(admin.router)       # Endpoints administrativos