"""
Helpers para endpoints de estadísticas.
Contiene lógica específica de operaciones complejas separada de los endpoints.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from src.models.domain import User
from src.services.statistics_service import StatisticsService
from src.services.statistics_validation_service import StatisticsValidationService
from src.services.document_service import DocumentService
from src.services.chat_service import ChatService
from src.core.exceptions import ValidationException, DatabaseException

logger = logging.getLogger(__name__)

class StatisticsHelpers:
    """Helpers para endpoints de estadísticas"""
    
    def __init__(self):
        self.validator = StatisticsValidationService()
    
    async def build_dashboard_response(
        self,
        user: User,
        stats_service: StatisticsService,
        document_service: Optional[DocumentService] = None,
        chat_service: Optional[ChatService] = None
    ) -> Dict[str, Any]:
        """
        Construye respuesta completa del dashboard delegando la lógica compleja.
        
        Este método centraliza toda la lógica que antes estaba en el endpoint,
        incluyendo determinación de permisos, obtención de recursos y formateo.
        
        Args:
            user: Usuario actual
            stats_service: Servicio de estadísticas
            document_service: Servicio de documentos (opcional)
            chat_service: Servicio de chats (opcional)
            
        Returns:
            Dict[str, Any]: Respuesta completa del dashboard
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔧 Construyendo dashboard para usuario {user.id} (admin: {user.is_admin})")
            
            # 1. Obtener estadísticas del USUARIO, no globales
            logger.info(f"📊 Obteniendo estadísticas del usuario {user.id}...")
            
            # TODOS los usuarios (incluyendo admins) ven SOLO SUS estadísticas
            user_stats = stats_service.get_user_statistics(user.id)
            stats = {
                "total_users": 1,  # Solo el usuario actual
                "total_documents": user_stats.get("user_documents", 0),
                "active_chats": user_stats.get("user_chats", 0),
                "shared_documents": user_stats.get("shared_documents", 0)
            }
            
            stats_time = time.time() - start_time
            logger.info(f"📊 Estadísticas obtenidas en {stats_time:.3f}s: {stats}")
            
            # 2. Determinar permisos y configuración
            permissions = self.handle_admin_vs_user_permissions(user)
            logger.info(f"🔐 Permisos determinados: {permissions}")
            
            # 3. Obtener documentos recientes según permisos
            logger.info("📄 Obteniendo documentos recientes...")
            recent_docs = await self._get_recent_documents_with_permissions(
                user, permissions, document_service
            )
            docs_time = time.time() - start_time
            logger.info(f"📄 Documentos obtenidos en {docs_time:.3f}s: {len(recent_docs)} documentos")
            
            # 4. Obtener chats recientes según permisos
            logger.info("💬 Obteniendo chats recientes...")
            recent_chats = await self._get_recent_chats_with_permissions(
                user, permissions, chat_service
            )
            chats_time = time.time() - start_time
            logger.info(f"💬 Chats obtenidos en {chats_time:.3f}s: {len(recent_chats)} chats")
            
            # 5. Formatear recursos para respuesta API
            formatted_docs = self.format_resource_data(recent_docs, "documents")
            formatted_chats = self.format_resource_data(recent_chats, "chats")
            
            # 6. Construir respuesta final
            dashboard_response = {
                "statistics": stats,
                "recent_documents": formatted_docs,
                "recent_chats": formatted_chats,
                "meta": {
                    "user_permissions": permissions,
                    "generated_at": datetime.now().isoformat(),
                    "processing_time_seconds": round(time.time() - start_time, 3)
                }
            }
            
            total_time = time.time() - start_time
            logger.info(f"🎉 Dashboard construido exitosamente en {total_time:.3f}s")
            
            return dashboard_response
            
        except Exception as e:
            logger.error(f"❌ Error construyendo dashboard: {str(e)}", exc_info=True)
            # Retornar estructura segura en caso de error
            return self._get_fallback_dashboard_response(e)
    
    def format_resource_data(self, resources: List, resource_type: str) -> List[Dict]:
        """
        Formatea datos de recursos para respuesta API.
        
        Args:
            resources: Lista de recursos raw
            resource_type: Tipo de recurso ('documents' o 'chats')
            
        Returns:
            List[Dict]: Recursos formateados
        """
        try:
            logger.info(f"🎨 Formateando {len(resources)} recursos de tipo {resource_type}")
            
            formatted_resources = []
            
            for resource in resources:
                if resource_type == "documents":
                    formatted = self._format_document_data(resource)
                elif resource_type == "chats":
                    formatted = self._format_chat_data(resource)
                else:
                    logger.warning(f"⚠️ Tipo de recurso no soportado: {resource_type}")
                    continue
                
                if formatted:
                    formatted_resources.append(formatted)
            
            logger.info(f"✅ {len(formatted_resources)} recursos formateados exitosamente")
            return formatted_resources
            
        except Exception as e:
            logger.error(f"❌ Error formateando recursos: {e}")
            return []
    
    def handle_admin_vs_user_permissions(self, user: User) -> Dict[str, bool]:
        """
        Determina permisos según rol de usuario.
        
        Args:
            user: Usuario para evaluar permisos
            
        Returns:
            Dict[str, bool]: Mapa de permisos
        """
        # En el dashboard personal, TODOS ven SOLO sus propios datos
        permissions = {
            "is_admin": user.is_admin,
            "can_view_all_documents": False,  # Nadie ve documentos de otros en el dashboard
            "can_view_all_chats": False,  # Nadie ve chats de otros en el dashboard
            "can_view_user_stats": user.is_admin,
            "can_view_system_health": user.is_admin,
            "can_access_admin_features": user.is_admin
        }
        
        logger.info(f"🔐 Permisos para {user.username}: {permissions}")
        return permissions
    
    async def apply_statistics_caching(self, cache_key: str, data_fetcher: callable) -> Any:
        """
        Aplica cacheo a resultados de estadísticas.
        
        Args:
            cache_key: Clave para el cache
            data_fetcher: Función que obtiene los datos
            
        Returns:
            Any: Datos obtenidos (con cache)
        """
        # TODO: Implementar cacheo real con Redis o memoria
        # Por ahora, simplemente ejecuta la función
        logger.info(f"💾 Aplicando cache (placeholder) para clave: {cache_key}")
        
        start_time = time.time()
        result = await data_fetcher() if callable(data_fetcher) else data_fetcher
        execution_time = time.time() - start_time
        
        logger.info(f"💾 Datos obtenidos en {execution_time:.3f}s (sin cache real aún)")
        return result
    
    def get_statistics_summary(self, stats: Dict[str, int]) -> Dict[str, Any]:
        """
        Genera un resumen interpretado de las estadísticas.
        
        Args:
            stats: Estadísticas raw
            
        Returns:
            Dict[str, Any]: Resumen interpretado
        """
        try:
            total_content = stats.get("total_documents", 0) + stats.get("active_chats", 0)
            
            # Interpretación básica
            if total_content == 0:
                activity_level = "sin_actividad"
            elif total_content < 10:
                activity_level = "baja"
            elif total_content < 50:
                activity_level = "moderada"
            else:
                activity_level = "alta"
            
            summary = {
                "total_content_items": total_content,
                "activity_level": activity_level,
                "users_per_document_ratio": round(
                    stats.get("total_users", 1) / max(stats.get("total_documents", 1), 1), 2
                ),
                "chats_per_user_ratio": round(
                    stats.get("active_chats", 0) / max(stats.get("total_users", 1), 1), 2
                ),
                "system_status": "activo" if total_content > 0 else "inactivo"
            }
            
            logger.info(f"📈 Resumen de estadísticas generado: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generando resumen: {e}")
            return {
                "total_content_items": 0,
                "activity_level": "desconocido",
                "system_status": "error"
            }
    
    async def _get_recent_documents_with_permissions(
        self, 
        user: User, 
        permissions: Dict[str, bool],
        document_service: Optional[DocumentService] = None
    ) -> List[Dict]:
        """Obtiene documentos recientes del usuario."""
        try:
            # Si no se proporciona document_service, crear una instancia
            if document_service is None:
                document_service = DocumentService()
            
            # TODOS los usuarios (incluyendo admin) ven SOLO SUS documentos
            logger.info(f"📄 Obteniendo documentos del usuario {user.id}...")
            recent_docs = document_service.list_user_documents(
                user.id,
                skip=0,
                limit=3,
                sort_by="created_at",
                order="desc"
            )
            
            return recent_docs
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo documentos: {e}")
            return []
    
    async def _get_recent_chats_with_permissions(
        self, 
        user: User, 
        permissions: Dict[str, bool],
        chat_service: Optional[ChatService] = None
    ) -> List[Dict]:
        """Obtiene chats recientes del usuario."""
        try:
            # Si no se proporciona chat_service, crear una instancia
            if chat_service is None:
                chat_service = ChatService()
            
            # TODOS los usuarios (incluyendo admin) ven SOLO SUS chats
            logger.info(f"💬 Obteniendo chats del usuario {user.id}...")
            recent_chats_list = chat_service.get_user_chats(
                user.id,
                skip=0,
                limit=3,
                sort_by="created_at",
                order="desc"
            )
            
            return recent_chats_list
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo chats: {e}")
            return []
    
    def _format_document_data(self, doc) -> Optional[Dict]:
        """Formatea datos de un documento individual."""
        try:
            # ✅ MEJORADO: asegurar timezone UTC consistente
            created_at = None
            if doc.created_at:
                # Convertir a UTC si no lo está ya
                created_at = doc.created_at.replace(tzinfo=None).isoformat() + 'Z'
            
            return {
                "id": doc.id,
                "title": doc.title,
                "content_type": doc.content_type,
                "created_at": created_at,
                "is_shared": getattr(doc, 'is_shared', False)
            }
        except Exception as e:
            logger.error(f"❌ Error formateando documento: {e}")
            return None
    
    def _format_chat_data(self, chat) -> Optional[Dict]:
        """Formatea datos de un chat individual."""
        try:
            # ✅ CORREGIDO: usar updated_at real, no created_at
            updated_at = getattr(chat, 'updated_at', None) or getattr(chat, 'created_at', None)
            
            # ✅ MEJORADO: asegurar timezone UTC consistente
            created_at = None
            updated_at_formatted = None
            
            if chat.created_at:
                created_at = chat.created_at.replace(tzinfo=None).isoformat() + 'Z'
            
            if updated_at:
                updated_at_formatted = updated_at.replace(tzinfo=None).isoformat() + 'Z'
            
            return {
                "id": chat.id,
                "title": chat.name_chat or f"Chat {chat.id}",
                "name_chat": chat.name_chat or f"Chat {chat.id}",
                "id_user": chat.id_user,
                "created_at": created_at,
                "updated_at": updated_at_formatted  # ✅ CORREGIDO
            }
        except Exception as e:
            logger.error(f"❌ Error formateando chat: {e}")
            return None
    
    def _get_fallback_dashboard_response(self, error: Exception) -> Dict[str, Any]:
        """Respuesta de fallback en caso de error."""
        logger.error(f"🚨 Generando respuesta de fallback por error: {error}")
        
        return {
            "statistics": {
                "total_users": 0,
                "total_documents": 0,
                "active_chats": 0,
                "shared_documents": 0
            },
            "recent_documents": [],
            "recent_chats": [],
            "meta": {
                "error": "Error obteniendo datos del dashboard",
                "generated_at": datetime.now().isoformat(),
                "fallback": True
            }
        }
    
    def validate_dashboard_request(self, user: User) -> bool:
        """
        Valida que el usuario pueda acceder al dashboard.
        
        Args:
            user: Usuario solicitante
            
        Returns:
            bool: True si puede acceder
            
        Raises:
            ValidationException: Si no puede acceder
        """
        try:
            # Validar que el usuario esté activo
            if not user:
                raise ValidationException("Usuario no válido")
            
            # Validar acceso a estadísticas globales
            self.validator.validate_statistics_access(user, "global")
            
            logger.info(f"✅ Validación de dashboard exitosa para usuario {user.id}")
            return True
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"❌ Error validando acceso al dashboard: {e}")
            raise ValidationException("Error validando acceso al dashboard")
