"""
API Endpoints para estadísticas globales del sistema - VERSION REFACTORIZADA
Endpoints simples que delegan lógica compleja a servicios y helpers.
"""
from fastapi import APIRouter, Depends, status
from typing import Dict, Any
import logging

from src.models.domain import User
from src.services.statistics_service import StatisticsService
from src.services.statistics_validation_service import StatisticsValidationService
from src.api.helpers.statistics_helpers import StatisticsHelpers
from src.api.dependencies import (
    get_current_user, 
    get_statistics_service, 
    get_statistics_validation_service,
    get_statistics_helpers
)
from src.core.exceptions import DatabaseException

logger = logging.getLogger(__name__)

# Crear router con prefijo y tags para la documentación automática
router = APIRouter(prefix="/statistics", tags=["statistics"])

@router.get("/public", response_model=Dict[str, int])
async def get_public_statistics(
    stats_service: StatisticsService = Depends(get_statistics_service)
):
    """
    Obtiene estadísticas globales del sistema (endpoint público).
    Lógica delegada completamente al servicio.
    """
    try:
        return stats_service.get_global_statistics()
    except Exception as e:
        logger.error(f"Error al obtener estadísticas públicas: {str(e)}", exc_info=True)
        # Retornar valores por defecto en caso de error
        return {
            "total_users": 0,
            "total_documents": 0,
            "active_chats": 0
        }

@router.get("/global", response_model=Dict[str, int])
async def get_global_statistics(
    current_user: User = Depends(get_current_user),
    stats_service: StatisticsService = Depends(get_statistics_service),
    validation_service: StatisticsValidationService = Depends(get_statistics_validation_service)
):
    """
    Obtiene estadísticas globales del sistema.
    Endpoint simple que valida permisos y delega al servicio.
    """
    try:
        # Validar acceso
        validation_service.validate_statistics_access(current_user, "global")
        
        # Delegar al servicio
        return stats_service.get_global_statistics()
        
    except Exception as e:
        logger.error(f"Error al obtener estadísticas globales: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al obtener estadísticas: {str(e)}")

@router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    stats_service: StatisticsService = Depends(get_statistics_service),
    stats_helpers: StatisticsHelpers = Depends(get_statistics_helpers)
) -> Dict[str, Any]:
    """
    Obtiene todos los datos necesarios para el dashboard.
    Lógica compleja delegada completamente a helpers.
    """
    try:
        # Validar acceso al dashboard
        stats_helpers.validate_dashboard_request(current_user)
        
        # Delegar construcción completa del dashboard al helper
        # Los servicios se crean automáticamente dentro del helper para evitar importaciones circulares
        return await stats_helpers.build_dashboard_response(
            user=current_user,
            stats_service=stats_service
        )
        
    except Exception as e:
        logger.error(f"Error al obtener datos del dashboard: {str(e)}", exc_info=True)
        # El helper ya maneja fallbacks, pero por seguridad adicional:
        return {
            "statistics": {
                "total_users": 0,
                "total_documents": 0,
                "active_chats": 0
            },
            "recent_documents": [],
            "recent_chats": []
        }

@router.get("/user/{user_id}")
async def get_user_statistics(
    user_id: int,
    current_user: User = Depends(get_current_user),
    stats_service: StatisticsService = Depends(get_statistics_service),
    validation_service: StatisticsValidationService = Depends(get_statistics_validation_service)
) -> Dict[str, int]:
    """
    Obtiene estadísticas específicas de un usuario.
    Solo accesible por admins o el propio usuario.
    """
    try:
        # Validar que puede acceder a las estadísticas del usuario
        if not current_user.is_admin and current_user.id != user_id:
            validation_service.validate_statistics_access(current_user, "admin_only")
        
        # Delegar al servicio
        return stats_service.get_user_statistics(user_id)
        
    except Exception as e:
        logger.error(f"Error al obtener estadísticas de usuario: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al obtener estadísticas de usuario: {str(e)}")

@router.get("/health")
async def get_system_health(
    current_user: User = Depends(get_current_user),
    stats_service: StatisticsService = Depends(get_statistics_service),
    validation_service: StatisticsValidationService = Depends(get_statistics_validation_service)
) -> Dict[str, Any]:
    """
    Obtiene métricas de salud del sistema.
    Solo accesible por administradores.
    """
    try:
        # Validar permisos de administrador
        validation_service.validate_statistics_access(current_user, "admin_only")
        
        # Delegar al servicio
        return stats_service.calculate_system_health_metrics()
        
    except Exception as e:
        logger.error(f"Error al obtener salud del sistema: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al obtener métricas de salud: {str(e)}")

@router.get("/summary")
async def get_statistics_summary(
    current_user: User = Depends(get_current_user),
    stats_service: StatisticsService = Depends(get_statistics_service),
    stats_helpers: StatisticsHelpers = Depends(get_statistics_helpers)
) -> Dict[str, Any]:
    """
    Obtiene un resumen interpretado de las estadísticas.
    Combina estadísticas con análisis interpretativo.
    """
    try:
        # Obtener estadísticas base
        base_stats = stats_service.get_global_statistics()
        
        # Generar resumen interpretado
        summary = stats_helpers.get_statistics_summary(base_stats)
        
        return {
            "raw_statistics": base_stats,
            "summary": summary,
            "generated_for": current_user.username
        }
        
    except Exception as e:
        logger.error(f"Error al obtener resumen de estadísticas: {str(e)}", exc_info=True)
        raise DatabaseException(f"Error al obtener resumen: {str(e)}")
