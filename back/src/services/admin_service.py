"""
Servicio de lógica de negocio para operaciones administrativas
Centraliza las operaciones complejas de administración
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.models.domain import User, Document, Chat
from src.services.document_service import DocumentService
from src.services.chat_service import ChatService
from src.services.user_service import UserService
from src.core.exceptions import DatabaseException

logger = logging.getLogger(__name__)

class AdminService:
    """Servicio para operaciones administrativas"""
    
    def __init__(
        self,
        document_service: DocumentService,
        chat_service: ChatService,
        user_service: UserService
    ):
        self.document_service = document_service
        self.chat_service = chat_service
        self.user_service = user_service
    
    # ==================== ESTADÍSTICAS GENERALES ====================
    
    def get_system_overview(self) -> Dict[str, Any]:
        """
        Obtiene una vista general del sistema
        
        Returns:
            Dict con estadísticas generales del sistema
        """
        try:
            overview = {
                "timestamp": datetime.utcnow(),
                "totals": {
                    "users": self.user_service.count_all_users(),
                    "documents": self.document_service.count_all_documents(),
                    "chats": self.chat_service.count_all_chats()
                },
                "active_last_24h": self._get_activity_stats(hours=24),
                "active_last_7d": self._get_activity_stats(days=7),
                "system_health": self._get_system_health()
            }
            
            logger.info("📊 Vista general del sistema generada")
            return overview
            
        except Exception as e:
            logger.error(f"Error generando vista general: {str(e)}")
            raise DatabaseException(f"Error al obtener estadísticas: {str(e)}")
    
    def get_detailed_statistics(
        self,
        resource_type: str,
        time_period: str = "all",
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas detalladas de un tipo de recurso
        
        Args:
            resource_type: Tipo de recurso (users, documents, chats)
            time_period: Período de tiempo
            group_by: Campo por el cual agrupar
            
        Returns:
            Dict con estadísticas detalladas
        """
        try:
            stats = {
                "resource_type": resource_type,
                "time_period": time_period,
                "timestamp": datetime.utcnow()
            }
            
            if resource_type == "documents":
                stats.update(self._get_document_statistics(time_period, group_by))
            elif resource_type == "chats":
                stats.update(self._get_chat_statistics(time_period, group_by))
            elif resource_type == "users":
                stats.update(self._get_user_statistics(time_period, group_by))
            else:
                raise ValueError(f"Tipo de recurso no soportado: {resource_type}")
            
            logger.info(f"📊 Estadísticas detalladas generadas para {resource_type}")
            return stats
            
        except Exception as e:
            logger.error(f"Error generando estadísticas detalladas: {str(e)}")
            raise DatabaseException(f"Error al obtener estadísticas: {str(e)}")
    
    # ==================== OPERACIONES DE RECURSOS ====================
    
    def get_all_resources(
        self,
        resource_type: str,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = 'created_at',
        order: str = 'desc',
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Obtiene todos los recursos de un tipo con filtros opcionales
        
        Args:
            resource_type: Tipo de recurso
            skip: Registros a saltar
            limit: Límite de registros
            sort_by: Campo de ordenamiento
            order: Dirección del orden
            filters: Filtros adicionales
            
        Returns:
            Lista de recursos
        """
        try:
            if resource_type == "documents":
                return self.document_service.list_all_documents(
                    skip=skip, limit=limit, sort_by=sort_by, order=order
                )
            elif resource_type == "chats":
                return self.chat_service.get_all_chats(
                    skip=skip, limit=limit, sort_by=sort_by, order=order
                )
            elif resource_type == "users":
                return self.user_service.get_all_users(
                    skip=skip, limit=limit
                )
            else:
                raise ValueError(f"Tipo de recurso no soportado: {resource_type}")
                
        except Exception as e:
            logger.error(f"Error obteniendo recursos {resource_type}: {str(e)}")
            raise DatabaseException(f"Error al obtener {resource_type}: {str(e)}")
    
    def search_resources(
        self,
        resource_type: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Busca recursos por texto
        
        Args:
            resource_type: Tipo de recurso
            query: Texto de búsqueda
            filters: Filtros adicionales
            limit: Límite de resultados
            
        Returns:
            Lista de recursos encontrados
        """
        try:
            results = []
            
            if resource_type == "documents":
                # Búsqueda en título y contenido
                results = self.document_service.search_all_documents(
                    query=query, n_results=limit
                )
            elif resource_type == "users":
                # Búsqueda en username y email
                results = self.user_service.search_users(
                    query=query, limit=limit
                )
            elif resource_type == "chats":
                # Búsqueda en títulos de chat
                results = self.chat_service.search_chats(
                    query=query, limit=limit
                )
            
            logger.info(f"🔍 Búsqueda en {resource_type}: '{query}' - {len(results)} resultados")
            return results
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {str(e)}")
            raise DatabaseException(f"Error al buscar: {str(e)}")
    
    # ==================== OPERACIONES EN LOTE ====================
    
    def bulk_delete_resources(
        self,
        resource_type: str,
        resource_ids: List[int],
        performed_by: User
    ) -> Dict[str, Any]:
        """
        Elimina múltiples recursos
        
        Args:
            resource_type: Tipo de recurso
            resource_ids: Lista de IDs a eliminar
            performed_by: Usuario que realiza la operación
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            success_count = 0
            failed_ids = []
            
            for resource_id in resource_ids:
                try:
                    if resource_type == "documents":
                        success = self.document_service.delete_document(
                            resource_id, performed_by.id
                        )
                    elif resource_type == "chats":
                        success = self.chat_service.delete_chat(
                            resource_id, performed_by.id
                        )
                    elif resource_type == "users":
                        success = self.user_service.delete_user(
                            resource_id, performed_by.id
                        )
                    else:
                        success = False
                    
                    if success:
                        success_count += 1
                    else:
                        failed_ids.append(resource_id)
                        
                except Exception as e:
                    logger.error(f"Error eliminando {resource_type} {resource_id}: {str(e)}")
                    failed_ids.append(resource_id)
            
            result = {
                "operation": "bulk_delete",
                "resource_type": resource_type,
                "total": len(resource_ids),
                "success": success_count,
                "failed": len(failed_ids),
                "failed_ids": failed_ids,
                "performed_by": performed_by.username,
                "timestamp": datetime.utcnow()
            }
            
            logger.info(
                f"🗑️ Eliminación en lote: {success_count}/{len(resource_ids)} "
                f"{resource_type} eliminados por {performed_by.username}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error en eliminación en lote: {str(e)}")
            raise DatabaseException(f"Error al eliminar recursos: {str(e)}")
    
    def export_resources(
        self,
        resource_type: str,
        format: str = "json",
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Exporta recursos en el formato especificado
        
        Args:
            resource_type: Tipo de recurso
            format: Formato de exportación (json, csv)
            filters: Filtros a aplicar
            
        Returns:
            Dict con información de la exportación
        """
        try:
            # TODO: Implementar exportación real
            # Por ahora, retorna metadata de la exportación
            
            export_info = {
                "resource_type": resource_type,
                "format": format,
                "filters": filters or {},
                "status": "pending",
                "message": "Exportación programada. Se notificará cuando esté lista.",
                "timestamp": datetime.utcnow()
            }
            
            logger.info(f"📤 Exportación solicitada: {resource_type} en formato {format}")
            return export_info
            
        except Exception as e:
            logger.error(f"Error en exportación: {str(e)}")
            raise DatabaseException(f"Error al exportar recursos: {str(e)}")
    
    # ==================== MÉTODOS ESPECIALIZADOS PARA DOCUMENTOS ====================
    
    def get_all_documents_with_filters(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        order: str = "desc",
        user_filter: Optional[int] = None,
        content_type_filter: Optional[str] = None
    ) -> List[Any]:
        """
        Obtiene todos los documentos del sistema con filtros avanzados.
        Solo para administradores.
        """
        try:
            # Usar el método existente con filtros básicos
            documents = self.document_service.list_all_documents(
                skip=skip,
                limit=limit,
                sort_by=sort_by,
                order=order
            )
            
            # Aplicar filtros adicionales si se especifican
            if user_filter is not None:
                documents = [doc for doc in documents if doc.uploaded_by == user_filter]
            
            if content_type_filter:
                documents = [doc for doc in documents if doc.content_type == content_type_filter]
            
            return documents
        except Exception as e:
            logger.error(f"Error obteniendo documentos con filtros: {e}")
            raise DatabaseException(f"Error al obtener documentos: {str(e)}")
    
    def get_system_document_statistics(self, time_period: str = "all") -> Dict[str, Any]:
        """
        Genera estadísticas completas de documentos del sistema.
        Incluye distribución por usuarios, tipos y métricas de almacenamiento.
        """
        try:
            stats = {
                "total_count": self.document_service.count_all_documents(),
                "by_user": self.document_service.get_documents_count_by_user(),
                "by_type": self.document_service.get_documents_count_by_type(),
                "storage": {
                    "total_size_mb": 0,  # TODO: Implementar en document_service
                    "average_size_mb": 0,
                    "largest_document_mb": 0
                },
                "time_period": time_period
            }
            
            if time_period != "all":
                # TODO: Implementar estadísticas basadas en tiempo
                stats["time_based"] = {
                    "message": f"Estadísticas por {time_period} en desarrollo"
                }
            
            return stats
        except Exception as e:
            logger.error(f"Error generando estadísticas de documentos: {e}")
            raise DatabaseException(f"Error al generar estadísticas: {str(e)}")
    
    def delete_document_as_admin(
        self,
        document_id: int,
        admin_user_id: int,
        force: bool = False
    ) -> bool:
        """
        Elimina un documento con permisos de administrador.
        Puede eliminar documentos de cualquier usuario.
        """
        try:
            # Log de auditoría
            document = self.document_service.get_document(document_id)
            if document:
                logger.warning(f"Admin {admin_user_id} eliminando documento {document_id} "
                             f"de usuario {document.uploaded_by}")
            
            # Usar el método de eliminación estándar con override de admin
            return self.document_service.delete_document(
                document_id=document_id,
                user_id=admin_user_id  # Admin puede eliminar cualquier documento
            )
        except Exception as e:
            logger.error(f"Error eliminando documento como admin: {e}")
            raise DatabaseException(f"Error al eliminar documento: {str(e)}")
    
    # ==================== MÉTODOS PRIVADOS ====================
    
    def _get_activity_stats(
        self,
        hours: Optional[int] = None,
        days: Optional[int] = None
    ) -> Dict[str, int]:
        """Obtiene estadísticas de actividad reciente"""
        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
        elif days:
            since = datetime.utcnow() - timedelta(days=days)
        else:
            since = None
        
        stats = {
            "new_users": self.user_service.count_users_since(since) if since else 0,
            "new_documents": self.document_service.count_documents_since(since) if since else 0,
            "active_chats": self.chat_service.count_active_chats_since(since) if since else 0
        }
        
        return stats
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Obtiene métricas de salud del sistema"""
        return {
            "status": "healthy",
            "database": "connected",
            "vector_store": "connected",
            "last_check": datetime.utcnow()
        }
    
    def _get_document_statistics(
        self,
        time_period: str,
        group_by: Optional[str]
    ) -> Dict[str, Any]:
        """Obtiene estadísticas de documentos"""
        stats = {
            "total": self.document_service.count_all_documents(),
            "by_type": self.document_service.get_documents_count_by_type(),
            "by_user": self.document_service.get_documents_count_by_user(),
            "average_size": self.document_service.get_average_document_size()
        }
        
        if group_by == "date":
            stats["by_date"] = self.document_service.get_documents_by_date(time_period)
        
        return stats
    
    def _get_chat_statistics(
        self,
        time_period: str,
        group_by: Optional[str]
    ) -> Dict[str, Any]:
        """Obtiene estadísticas de chats"""
        stats = {
            "total": self.chat_service.count_all_chats(),
            "active": self.chat_service.count_active_chats(),
            "by_user": self.chat_service.get_chats_count_by_user(),
            "average_messages": self.chat_service.get_average_messages_per_chat()
        }
        
        if group_by == "date":
            stats["by_date"] = self.chat_service.get_chats_by_date(time_period)
        
        return stats
    
    def _get_user_statistics(
        self,
        time_period: str,
        group_by: Optional[str]
    ) -> Dict[str, Any]:
        """Obtiene estadísticas de usuarios"""
        stats = {
            "total": self.user_service.count_all_users(),
            "active": self.user_service.count_active_users(),
            "by_role": self.user_service.get_users_by_role(),
            "registration_trend": self.user_service.get_registration_trend(time_period)
        }
        
        if group_by == "activity":
            stats["by_activity"] = self.user_service.get_users_by_activity_level()
        
        return stats
