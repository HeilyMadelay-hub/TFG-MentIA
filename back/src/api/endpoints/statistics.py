"""
API Endpoints para estadísticas globales del sistema.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import logging
from datetime import datetime, timedelta

from src.models.domain import User
from src.services.statistics_service import StatisticsService
from src.services.document_service import DocumentService
from src.services.chat_service import ChatService
from src.api.dependencies import get_current_user, get_statistics_service, get_document_service
from src.api.dependencies import document_service, chat_service  # Usar las instancias directas

logger = logging.getLogger(__name__)

# Crear router con prefijo y tags para la documentación automática
router = APIRouter(prefix="/statistics", tags=["statistics"])

@router.get("/public", response_model=Dict[str, int])
async def get_public_statistics(
    statistics_service: StatisticsService = Depends(get_statistics_service)
):
    """
    Obtiene estadísticas globales del sistema (endpoint público).
    
    Retorna:
    - total_users: Número total de usuarios registrados
    - total_documents: Número total de documentos en el sistema
    - active_chats: Número de chats activos
    
    Este endpoint es público y no requiere autenticación.
    """
    try:
        stats = statistics_service.get_global_statistics()
        return stats
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
    statistics_service: StatisticsService = Depends(get_statistics_service)
):
    """
    Obtiene estadísticas globales del sistema.
    
    Retorna:
    - total_users: Número total de usuarios registrados
    - total_documents: Número total de documentos en el sistema
    - active_chats: Número de chats activos en los últimos 7 días
    
    Este endpoint está disponible para todos los usuarios autenticados.
    """
    try:
        stats = statistics_service.get_global_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error al obtener estadísticas globales: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )

@router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    statistics_service: StatisticsService = Depends(get_statistics_service)
) -> Dict[str, Any]:
    """
    Obtiene todos los datos necesarios para el dashboard en una sola llamada.
    
    Retorna:
    - statistics: Estadísticas globales del sistema
    - recent_documents: Últimos 3 documentos (del usuario o todos si es admin)
    - recent_chats: Últimos 3 chats (del usuario o todos si es admin)
    
    Este endpoint optimiza el rendimiento al combinar múltiples llamadas en una sola.
    """
    try:
        # Obtener estadísticas globales actualizadas
        logger.info("🔍 Obteniendo estadísticas para dashboard...")
        stats = statistics_service.get_global_statistics()
        logger.info(f"📊 Estadísticas obtenidas: {stats}")
        
        # Determinar si es administrador
        is_admin = current_user.is_admin
        logger.info(f"👤 Usuario {current_user.id} es admin: {is_admin}")
        
        # Obtener documentos recientes
        logger.info(f"📄 Obteniendo documentos recientes...")
        if is_admin:
            # Si es admin, obtener los últimos documentos del sistema
            recent_docs = document_service.list_all_documents(
                skip=0,
                limit=3,
                sort_by="created_at",
                order="desc"
            )
        else:
            # Si es usuario normal, obtener solo sus documentos
            recent_docs = document_service.list_user_documents(
                current_user.id,
                skip=0,
                limit=3,
                sort_by="created_at",
                order="desc"
            )
        logger.info(f"📄 Documentos obtenidos: {len(recent_docs)}")        
        
        # Obtener chats recientes
        try:
            if is_admin:
                # Si es admin, obtener los últimos chats del sistema
                recent_chats_list = chat_service.get_all_chats(
                    skip=0,
                    limit=3,
                    sort_by="created_at",
                    order="desc"
                )
            else:
                # Si es usuario normal, obtener solo sus chats
                recent_chats_list = chat_service.get_user_chats(
                    current_user.id,
                    skip=0,
                    limit=3,
                    sort_by="created_at",  # Cambiar a created_at ya que chats no tiene updated_at
                    order="desc"
                )
            
            logger.info(f"🔍 Chats obtenidos: {len(recent_chats_list)}")
            
            recent_chats = []
            for chat in recent_chats_list:
                # Los chats vienen como ChatResponse que tiene name_chat, no title
                chat_dict = {
                    "id": chat.id,
                    "title": chat.name_chat or f"Chat {chat.id}",  # Usar name_chat
                    "name_chat": chat.name_chat or f"Chat {chat.id}",
                    "id_user": chat.id_user,
                    "created_at": chat.created_at.isoformat() if chat.created_at else None,
                    "updated_at": chat.created_at.isoformat() if chat.created_at else None  # Usar created_at ya que no hay updated_at
                }
                recent_chats.append(chat_dict)
                logger.info(f"✅ Chat procesado: {chat_dict['title']}")
        except Exception as e:
            logger.warning(f"Error obteniendo chats recientes: {e}")
            import traceback
            logger.error(traceback.format_exc())
            recent_chats = []
        
        # Convertir documentos a dict
        docs_data = [
            {
                "id": doc.id,
                "title": doc.title,
                "content_type": doc.content_type,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "is_shared": getattr(doc, 'is_shared', False)
            }
            for doc in recent_docs
        ]
        
        logger.info(f"Dashboard data: stats={stats}, docs_count={len(docs_data)}, chats_count={len(recent_chats)}")
        if len(recent_chats) > 0:
            logger.info(f"Recent chats sample: {recent_chats[0]}")
        else:
            logger.info("No recent chats found")
        
        return {
            "statistics": stats,
            "recent_documents": docs_data,
            "recent_chats": recent_chats
        }
        
    except Exception as e:
        logger.error(f"Error al obtener datos del dashboard: {str(e)}", exc_info=True)
        # Retornar estructura con valores vacíos en caso de error
        return {
            "statistics": {
                "total_users": 0,
                "total_documents": 0,
                "active_chats": 0
            },
            "recent_documents": [],
            "recent_chats": []
        }
