"""
Funciones helper para endpoints administrativos
Simplifica la lógica compleja de los endpoints admin
"""
import logging
from typing import List, Dict, Any, Optional
from src.models.domain import User
from src.services.document_service import DocumentService
from src.services.chat_service import ChatService
from src.services.user_service import UserService
from src.services.admin_service import AdminService
from src.services.admin_validation_service import AdminValidationService
from src.core.exceptions import ValidationException, DatabaseException

logger = logging.getLogger(__name__)

class AdminEndpointHelpers:
    """Helpers para simplificar endpoints administrativos"""
    
    def __init__(self):
        self.validator = AdminValidationService()
    
    async def handle_resource_listing(
        self,
        resource_type: str,
        skip: int,
        limit: int,
        sort_by: Optional[str],
        order: Optional[str],
        admin_user: User,
        admin_service: AdminService
    ) -> List[Any]:
        """
        Maneja el listado de recursos con validaciones
        
        Args:
            resource_type: Tipo de recurso (documents, chats, users)
            skip: Registros a saltar
            limit: Límite de registros
            sort_by: Campo de ordenamiento
            order: Dirección del orden
            admin_user: Usuario administrador
            admin_service: Servicio administrativo
            
        Returns:
            Lista de recursos
        """
        try:
            # 1. Validar acceso de administrador
            self.validator.validate_admin_access(admin_user, f"listar {resource_type}")
            
            # 2. Validar y normalizar parámetros
            skip, limit = self.validator.validate_pagination_params(skip, limit)
            sort_by, order = self.validator.validate_sort_params(sort_by, order, resource_type)
            
            # 3. Validar tipo de recurso
            self.validator.validate_resource_access(resource_type, user=admin_user)
            
            # 4. Obtener recursos
            logger.info(f"📋 Listando {resource_type}: skip={skip}, limit={limit}, sort={sort_by} {order}")
            
            resources = admin_service.get_all_resources(
                resource_type=resource_type,
                skip=skip,
                limit=limit,
                sort_by=sort_by,
                order=order
            )
            
            logger.info(f"✅ {len(resources)} {resource_type} obtenidos")
            return resources
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error listando {resource_type}: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al obtener {resource_type}: {str(e)}")
    
    async def handle_statistics_request(
        self,
        admin_user: User,
        admin_service: AdminService,
        resource_type: Optional[str] = None,
        time_period: Optional[str] = None,
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Maneja solicitudes de estadísticas
        
        Args:
            admin_user: Usuario administrador
            admin_service: Servicio administrativo
            resource_type: Tipo de recurso específico (opcional)
            time_period: Período de tiempo
            group_by: Campo de agrupación
            
        Returns:
            Dict con estadísticas
        """
        try:
            # 1. Validar acceso
            self.validator.validate_admin_access(admin_user, "ver estadísticas")
            
            # 2. Si no se especifica tipo, obtener vista general
            if not resource_type:
                logger.info("📊 Generando vista general del sistema")
                return admin_service.get_system_overview()
            
            # 3. Validar parámetros de estadísticas
            params = {
                'time_period': time_period or 'all',
                'group_by': group_by
            }
            validated_params = self.validator.validate_stats_params(params)
            
            # 4. Obtener estadísticas detalladas
            logger.info(f"📊 Generando estadísticas de {resource_type}")
            
            stats = admin_service.get_detailed_statistics(
                resource_type=resource_type,
                time_period=validated_params.get('time_period', 'all'),
                group_by=validated_params.get('group_by')
            )
            
            return stats
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error generando estadísticas: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al generar estadísticas: {str(e)}")
    
    async def handle_search_request(
        self,
        query: str,
        resource_type: str,
        admin_user: User,
        admin_service: AdminService,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Maneja búsquedas administrativas
        
        Args:
            query: Texto de búsqueda
            resource_type: Tipo de recurso
            admin_user: Usuario administrador
            admin_service: Servicio administrativo
            limit: Límite de resultados
            
        Returns:
            Lista de resultados
        """
        try:
            # 1. Validar acceso
            self.validator.validate_admin_access(admin_user, f"buscar en {resource_type}")
            
            # 2. Validar query
            if not query or len(query.strip()) < 2:
                raise ValidationException("La búsqueda debe tener al menos 2 caracteres")
            
            # 3. Validar tipo de recurso
            self.validator.validate_resource_access(resource_type, user=admin_user)
            
            # 4. Realizar búsqueda
            logger.info(f"🔍 Búsqueda admin en {resource_type}: '{query}'")
            
            results = admin_service.search_resources(
                resource_type=resource_type,
                query=query.strip(),
                limit=min(limit, 100)  # Limitar máximo a 100
            )
            
            logger.info(f"✅ {len(results)} resultados encontrados")
            return results
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error en búsqueda: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al buscar: {str(e)}")
    
    async def handle_bulk_operation(
        self,
        operation: str,
        resource_type: str,
        resource_ids: List[int],
        admin_user: User,
        admin_service: AdminService
    ) -> Dict[str, Any]:
        """
        Maneja operaciones en lote
        
        Args:
            operation: Tipo de operación (delete, export, etc.)
            resource_type: Tipo de recurso
            resource_ids: Lista de IDs
            admin_user: Usuario administrador
            admin_service: Servicio administrativo
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # 1. Validar acceso
            self.validator.validate_admin_access(
                admin_user, 
                f"ejecutar operación {operation} en {resource_type}"
            )
            
            # 2. Validar operación y recursos
            valid_ids = self.validator.validate_bulk_operation(operation, resource_ids)
            
            # 3. Validar tipo de recurso
            self.validator.validate_resource_access(resource_type, user=admin_user)
            
            # 4. Ejecutar operación
            logger.info(
                f"🔄 Ejecutando {operation} en lote para {len(valid_ids)} {resource_type}"
            )
            
            if operation == "delete":
                result = admin_service.bulk_delete_resources(
                    resource_type=resource_type,
                    resource_ids=valid_ids,
                    performed_by=admin_user
                )
            elif operation == "export":
                result = admin_service.export_resources(
                    resource_type=resource_type,
                    format="json"  # TODO: Hacer configurable
                )
            else:
                raise ValidationException(f"Operación no implementada: {operation}")
            
            return result
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error en operación {operation}: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al ejecutar {operation}: {str(e)}")
    
    async def get_resource_summary(
        self,
        resource_type: str,
        resource_id: int,
        admin_user: User,
        document_service: Optional[DocumentService] = None,
        chat_service: Optional[ChatService] = None,
        user_service: Optional[UserService] = None
    ) -> Dict[str, Any]:
        """
        Obtiene un resumen detallado de un recurso específico
        
        Args:
            resource_type: Tipo de recurso
            resource_id: ID del recurso
            admin_user: Usuario administrador
            document_service: Servicio de documentos (opcional)
            chat_service: Servicio de chats (opcional)
            user_service: Servicio de usuarios (opcional)
            
        Returns:
            Dict con información detallada del recurso
        """
        try:
            # 1. Validaciones
            self.validator.validate_admin_access(
                admin_user, 
                f"ver detalles de {resource_type}"
            )
            self.validator.validate_resource_access(
                resource_type, 
                resource_id=resource_id,
                user=admin_user
            )
            
            # 2. Obtener información según tipo
            if resource_type == "documents" and document_service:
                document = document_service.get_document(resource_id)
                if not document:
                    raise ValidationException(f"Documento {resource_id} no encontrado")
                
                summary = {
                    "type": "document",
                    "id": resource_id,
                    "title": document.title,
                    "owner": document.uploaded_by,
                    "created_at": document.created_at,
                    "content_type": document.content_type,
                    "size": getattr(document, 'file_size', 0),
                    "status": getattr(document, 'status', 'unknown'),
                    "shared_with_count": document_service.count_document_shares(resource_id),
                    "is_indexed": document_service.verify_document_indexed(resource_id)
                }
                
            elif resource_type == "chats" and chat_service:
                chat = chat_service.get_chat(resource_id)
                if not chat:
                    raise ValidationException(f"Chat {resource_id} no encontrado")
                
                summary = {
                    "type": "chat",
                    "id": resource_id,
                    "title": chat.title,
                    "user_id": chat.user_id,
                    "created_at": chat.created_at,
                    "message_count": chat_service.count_chat_messages(resource_id),
                    "last_activity": chat.updated_at
                }
                
            elif resource_type == "users" and user_service:
                user = user_service.get_user(resource_id)
                if not user:
                    raise ValidationException(f"Usuario {resource_id} no encontrado")
                
                summary = {
                    "type": "user",
                    "id": resource_id,
                    "username": user.username,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at,
                    "document_count": user_service.count_user_documents(resource_id),
                    "chat_count": user_service.count_user_chats(resource_id)
                }
                
            else:
                raise ValidationException(f"Tipo de recurso no soportado: {resource_type}")
            
            logger.info(f"📋 Resumen generado para {resource_type} {resource_id}")
            return summary
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al obtener resumen: {str(e)}")
