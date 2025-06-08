"""
Endpoint de health check para monitoreo del sistema
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from datetime import datetime
from src.config.database import get_supabase_client
from src.utils.chromadb_connector import ChromaDBConnector

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)

@router.get("/", response_model=Dict[str, Any])
async def health_check():
    """
    Verifica el estado de salud del sistema
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {}
    }
    
    # Verificar Supabase
    try:
        supabase = get_supabase_client()
        # Hacer una consulta simple
        response = supabase.table("users").select("count").limit(1).execute()
        health_status["services"]["supabase"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["supabase"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}"
        }
    
    # Verificar ChromaDB
    try:
        chromadb = ChromaDBConnector()
        # Verificar que se puede acceder a las colecciones
        collections = chromadb.client.list_collections()
        health_status["services"]["chromadb"] = {
            "status": "healthy",
            "message": f"Vector DB operational, {len(collections)} collections"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["chromadb"] = {
            "status": "unhealthy",
            "message": f"Vector DB error: {str(e)}"
        }
    
    # Determinar código de estado HTTP
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

@router.get("/ready", response_model=Dict[str, str])
async def readiness_check():
    """
    Verifica si el servicio está listo para recibir tráfico
    """
    try:
        # Verificar dependencias críticas
        supabase = get_supabase_client()
        chromadb = ChromaDBConnector()
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.get("/live", response_model=Dict[str, str])
async def liveness_check():
    """
    Verifica si el servicio está vivo
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
