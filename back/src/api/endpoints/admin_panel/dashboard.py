"""
Endpoint mejorado para Panel de Administración.
Resuelve todos los problemas de conteo, tiempos y filtrado.
"""
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_current_user
from src.models.domain import User
from src.config.database import get_supabase_client
from src.utils.timezone_utils import get_utc_now, ensure_utc

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin-panel",
    tags=["🛡️ Admin Panel"]
)

@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtiene todos los datos necesarios para el panel de administración de forma optimizada.
    Solo accesible para administradores.
    """
    # Verificar que el usuario es admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo los administradores pueden acceder a este recurso"
        )
    
    try:
        logger.info(f"🛡️ Admin {current_user.username} (ID: {current_user.id}) solicitando dashboard")
        
        # Usar cliente con permisos de servicio para bypasear RLS
        service_client = get_supabase_client(use_service_role=True)
        
        # 1. OBTENER TODOS LOS USUARIOS
        users_response = service_client.table('users').select('*').execute()
        all_users = users_response.data if users_response.data else []
        
        # Crear diccionario de usuarios para búsquedas rápidas
        users_dict = {user['id']: user for user in all_users}
        
        # Log de usuarios encontrados
        logger.info(f"👥 Total usuarios en el sistema: {len(all_users)}")
        usernames = [u.get('username', 'Unknown') for u in all_users]
        logger.info(f"👥 Usuarios: {usernames}")
        
        # 2. OBTENER TODOS LOS DOCUMENTOS
        docs_response = service_client.table('documents').select('*').order('created_at', desc=True).execute()
        all_documents = docs_response.data if docs_response.data else []
        logger.info(f"📄 Total documentos en el sistema: {len(all_documents)}")
        
        # 3. OBTENER TODOS LOS CHATS
        chats_response = service_client.table('chats').select('*').order('created_at', desc=True).execute()
        all_chats = chats_response.data if chats_response.data else []
        logger.info(f"💬 Total chats en el sistema: {len(all_chats)}")
        
        # 4. FILTRAR DATOS EXCLUYENDO AL ADMIN ACTUAL
        # Documentos que no son del admin actual
        other_users_documents = [
            doc for doc in all_documents 
            if doc.get('uploaded_by') != current_user.id
        ]
        
        # Chats que no son del admin actual  
        other_users_chats = [
            chat for chat in all_chats 
            if chat.get('id_user') != current_user.id
        ]
        
        # Usuarios excluyendo al admin actual
        other_users = [
            user for user in all_users
            if user.get('id') != current_user.id
        ]
        
        logger.info(f"📊 Datos filtrados (excluyendo admin {current_user.username}):")
        logger.info(f"   - Usuarios: {len(other_users)}")
        logger.info(f"   - Documentos: {len(other_users_documents)}")
        logger.info(f"   - Chats: {len(other_users_chats)}")
        
        # 5. CALCULAR ESTADÍSTICAS
        statistics = {
            "total_users": len(other_users),  # Usuarios sin incluir al admin actual
            "total_documents": len(other_users_documents),  # Documentos de otros usuarios
            "active_chats": len(other_users_chats),  # Chats de otros usuarios
            "total_system_users": len(all_users),  # Total real del sistema
            "total_system_documents": len(all_documents),  # Total real del sistema
            "total_system_chats": len(all_chats)  # Total real del sistema
        }
        
        # 6. PREPARAR ACTIVIDAD RECIENTE
        recent_activities = []
        
        # Agregar documentos recientes (máximo 3)
        for doc in other_users_documents[:3]:
            owner_id = doc.get('uploaded_by')
            owner = users_dict.get(owner_id, {})
            
            recent_activities.append({
                "type": "document",
                "action": "Documento subido",
                "title": doc.get('title', 'Sin título'),
                "user": owner.get('username', 'Usuario desconocido'),
                "user_id": owner_id,
                "timestamp": doc.get('created_at'),
                "formatted_time": _format_relative_time(doc.get('created_at'))
            })
        
        # Agregar chats recientes (máximo 3)
        for chat in other_users_chats[:3]:
            user_id = chat.get('id_user')
            user = users_dict.get(user_id, {})
            
            recent_activities.append({
                "type": "chat",
                "action": "Chat actualizado",
                "title": chat.get('name_chat', f"Chat {chat.get('id')}"),
                "user": user.get('username', 'Usuario desconocido'),
                "user_id": user_id,
                "timestamp": chat.get('created_at'),
                "formatted_time": _format_relative_time(chat.get('created_at'))
            })
        
        # Ordenar actividades por timestamp
        recent_activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        recent_activities = recent_activities[:5]  # Limitar a 5 actividades más recientes
        
        # 7. PREPARAR LISTA DE USUARIOS CON INFORMACIÓN COMPLETA
        users_list = []
        for user in other_users:
            created_at = user.get('created_at')
            logger.info(f"🕒 Usuario {user.get('username')} - created_at: {created_at}")
            formatted_time = _format_relative_time(created_at)
            logger.info(f"🕒 Usuario {user.get('username')} - tiempo formateado: {formatted_time}")
            
            users_list.append({
                "id": user.get('id'),
                "username": user.get('username'),
                "email": user.get('email'),
                "created_at": user.get('created_at'),
                "formatted_created": formatted_time,
                "is_admin": user.get('is_admin', False),
                "documents_count": len([d for d in all_documents if d.get('uploaded_by') == user.get('id')]),
                "chats_count": len([c for c in all_chats if c.get('id_user') == user.get('id')])
            })
        
        # 8. PREPARAR LISTA DE DOCUMENTOS CON INFORMACIÓN DEL PROPIETARIO
        documents_list = []
        for doc in other_users_documents[:20]:  # Limitar a 20 documentos más recientes
            owner_id = doc.get('uploaded_by')
            owner = users_dict.get(owner_id, {})
            
            documents_list.append({
                "id": doc.get('id'),
                "title": doc.get('title'),
                "content_type": doc.get('content_type'),
                "status": doc.get('status'),
                "created_at": doc.get('created_at'),
                "formatted_created": _format_relative_time(doc.get('created_at')),
                "owner": {
                    "id": owner_id,
                    "username": owner.get('username', 'Usuario desconocido'),
                    "email": owner.get('email', '')
                },
                "file_url": doc.get('file_url'),
                "file_size": doc.get('file_size'),
                "is_shared": doc.get('is_shared', False)
            })
        
        # 9. PREPARAR LISTA DE CHATS CON INFORMACIÓN DEL USUARIO
        chats_list = []
        for chat in other_users_chats[:20]:  # Limitar a 20 chats más recientes
            user_id = chat.get('id_user')
            user = users_dict.get(user_id, {})
            
            chats_list.append({
                "id": chat.get('id'),
                "title": chat.get('name_chat', f"Chat {chat.get('id')}"),
                "created_at": chat.get('created_at'),
                "formatted_created": _format_relative_time(chat.get('created_at')),
                "owner": {
                    "id": user_id,
                    "username": user.get('username', 'Usuario desconocido'),
                    "email": user.get('email', '')
                }
            })
        
        # 10. CONSTRUIR RESPUESTA COMPLETA
        response = {
            "statistics": statistics,
            "recent_activities": recent_activities,
            "users": users_list,
            "documents": documents_list,
            "chats": chats_list,
            "meta": {
                "current_admin": {
                    "id": current_user.id,
                    "username": current_user.username
                },
                "generated_at": get_utc_now().isoformat(),
                "filters_applied": f"Excluyendo datos del admin {current_user.username}"
            }
        }
        
        logger.info(f"✅ Dashboard generado exitosamente para admin {current_user.username}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error generando dashboard admin: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generando dashboard: {str(e)}"
        )


def _format_relative_time(timestamp: str) -> str:
    """
    Formatea un timestamp a tiempo relativo de forma correcta.
    Corrige el problema de las zonas horarias.
    """
    if not timestamp:
        return "Fecha desconocida"
    
    try:
        # Parsear el timestamp
        if isinstance(timestamp, str):
            # Remover la 'Z' si existe y parsear
            if timestamp.endswith('Z'):
                timestamp = timestamp[:-1] + '+00:00'
            
            # Intentar parsear con diferentes formatos
            try:
                dt = datetime.fromisoformat(timestamp)
            except:
                # Intentar formato alternativo
                dt = datetime.strptime(timestamp.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                # Asumir UTC si no tiene timezone
                dt = ensure_utc(dt)
        else:
            dt = timestamp
        
        # Obtener el tiempo actual UTC
        now = get_utc_now()
        
        # Si dt no tiene timezone, asumir UTC
        if dt.tzinfo is None:
            dt = ensure_utc(dt)
        
        # Calcular diferencia
        diff = now - dt
        
        # Formatear según la diferencia
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "Hace un momento"
        elif seconds < 3600:  # Menos de 1 hora
            minutes = int(seconds / 60)
            return f"Hace {minutes} min"
        elif seconds < 86400:  # Menos de 1 día
            hours = int(seconds / 3600)
            return f"Hace {hours}h"
        elif seconds < 172800:  # Menos de 2 días
            return "Ayer"
        elif seconds < 604800:  # Menos de 1 semana
            days = int(seconds / 86400)
            return f"Hace {days} días"
        elif seconds < 2592000:  # Menos de 30 días
            weeks = int(seconds / 604800)
            return f"Hace {weeks} semana{'s' if weeks > 1 else ''}"
        else:
            # Mostrar fecha completa
            return dt.strftime("%d/%m/%Y")
            
    except Exception as e:
        logger.error(f"Error formateando tiempo: {e}")
        return "Fecha inválida"
