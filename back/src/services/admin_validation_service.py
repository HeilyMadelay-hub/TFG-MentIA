"""
Servicio de validación para operaciones administrativas
Centraliza todas las validaciones de permisos y parámetros para administradores
"""
import logging
from typing import Optional, Dict, Any
from src.models.domain import User
from src.core.exceptions import ForbiddenException, ValidationException

logger = logging.getLogger(__name__)

class AdminValidationService:
    """Servicio para validaciones administrativas"""
    
    # Límites de paginación
    MIN_SKIP = 0
    MAX_LIMIT = 500
    DEFAULT_LIMIT = 100
    
    # Campos válidos para ordenamiento
    VALID_SORT_FIELDS = ['created_at', 'updated_at', 'title', 'username', 'email', 'status']
    VALID_ORDER_DIRECTIONS = ['asc', 'desc']
    
    def validate_admin_access(self, user: User, operation: str = "acceder") -> bool:
        """
        Valida si un usuario tiene permisos de administrador
        
        Args:
            user: Usuario a validar
            operation: Operación que se quiere realizar (para logs)
            
        Returns:
            bool: True si tiene acceso
            
        Raises:
            ForbiddenException: Si no es administrador
        """
        if not user.is_admin:
            logger.warning(f"❌ Usuario {user.id} ({user.username}) intentó {operation} sin permisos de admin")
            raise ForbiddenException(
                f"Solo los administradores pueden {operation} a este recurso"
            )
        
        logger.info(f"✅ Acceso administrativo validado para {operation} - Usuario: {user.username}")
        return True
    
    def validate_pagination_params(
        self, 
        skip: int, 
        limit: int
    ) -> tuple[int, int]:
        """
        Valida y normaliza parámetros de paginación
        
        Args:
            skip: Número de registros a saltar
            limit: Número máximo de registros a retornar
            
        Returns:
            tuple[int, int]: (skip_normalizado, limit_normalizado)
            
        Raises:
            ValidationException: Si los parámetros son inválidos
        """
        # Validar skip
        if skip < self.MIN_SKIP:
            raise ValidationException(f"El parámetro 'skip' debe ser >= {self.MIN_SKIP}")
        
        # Validar y normalizar limit
        if limit < 1:
            raise ValidationException("El parámetro 'limit' debe ser >= 1")
        
        if limit > self.MAX_LIMIT:
            logger.warning(f"⚠️ Limit {limit} excede el máximo, ajustando a {self.MAX_LIMIT}")
            limit = self.MAX_LIMIT
        
        logger.debug(f"📄 Paginación validada: skip={skip}, limit={limit}")
        return skip, limit
    
    def validate_sort_params(
        self,
        sort_by: Optional[str],
        order: Optional[str],
        resource_type: str = "genérico"
    ) -> tuple[str, str]:
        """
        Valida y normaliza parámetros de ordenamiento
        
        Args:
            sort_by: Campo por el cual ordenar
            order: Dirección del ordenamiento
            resource_type: Tipo de recurso (para determinar defaults)
            
        Returns:
            tuple[str, str]: (sort_by_normalizado, order_normalizado)
        """
        # Defaults según tipo de recurso
        default_sort = 'created_at'
        default_order = 'desc'
        
        # Normalizar sort_by
        if not sort_by:
            sort_by = default_sort
        elif sort_by not in self.VALID_SORT_FIELDS:
            logger.warning(f"⚠️ Campo de ordenamiento inválido: {sort_by}, usando {default_sort}")
            sort_by = default_sort
        
        # Normalizar order
        if not order:
            order = default_order
        else:
            order = order.lower()
            if order not in self.VALID_ORDER_DIRECTIONS:
                logger.warning(f"⚠️ Dirección de ordenamiento inválida: {order}, usando {default_order}")
                order = default_order
        
        logger.debug(f"🔤 Ordenamiento validado: sort_by={sort_by}, order={order}")
        return sort_by, order
    
    def validate_resource_access(
        self,
        resource_type: str,
        resource_id: Optional[int] = None,
        user: Optional[User] = None
    ) -> bool:
        """
        Valida acceso a un recurso específico
        
        Args:
            resource_type: Tipo de recurso (documents, chats, users)
            resource_id: ID del recurso (opcional)
            user: Usuario solicitante (opcional)
            
        Returns:
            bool: True si tiene acceso
            
        Raises:
            ValidationException: Si los parámetros son inválidos
        """
        valid_resources = ['documents', 'chats', 'users', 'stats', 'logs']
        
        if resource_type not in valid_resources:
            raise ValidationException(
                f"Tipo de recurso inválido: {resource_type}. "
                f"Recursos válidos: {', '.join(valid_resources)}"
            )
        
        if resource_id and resource_id < 1:
            raise ValidationException(f"ID de recurso inválido: {resource_id}")
        
        log_msg = f"✅ Acceso validado a recurso: {resource_type}"
        if resource_id:
            log_msg += f" (ID: {resource_id})"
        if user:
            log_msg += f" por usuario: {user.username}"
        
        logger.info(log_msg)
        return True
    
    def validate_stats_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida parámetros para consultas de estadísticas
        
        Args:
            params: Diccionario con parámetros
            
        Returns:
            Dict[str, Any]: Parámetros validados y normalizados
        """
        validated = {}
        
        # Validar período de tiempo
        if 'time_period' in params:
            valid_periods = ['day', 'week', 'month', 'year', 'all']
            period = params['time_period'].lower()
            if period not in valid_periods:
                logger.warning(f"⚠️ Período inválido: {period}, usando 'all'")
                period = 'all'
            validated['time_period'] = period
        
        # Validar agrupación
        if 'group_by' in params:
            valid_groups = ['user', 'type', 'date', 'status']
            group = params['group_by'].lower()
            if group not in valid_groups:
                logger.warning(f"⚠️ Agrupación inválida: {group}, ignorando")
            else:
                validated['group_by'] = group
        
        # Validar límites
        if 'top_n' in params:
            try:
                top_n = int(params['top_n'])
                if top_n < 1:
                    top_n = 10
                elif top_n > 100:
                    top_n = 100
                validated['top_n'] = top_n
            except (ValueError, TypeError):
                validated['top_n'] = 10
        
        logger.info(f"📊 Parámetros de estadísticas validados: {validated}")
        return validated
    
    def validate_bulk_operation(
        self,
        operation: str,
        resource_ids: list[int],
        max_items: int = 100
    ) -> list[int]:
        """
        Valida operaciones en lote
        
        Args:
            operation: Tipo de operación (delete, update, etc.)
            resource_ids: Lista de IDs a procesar
            max_items: Número máximo de items permitidos
            
        Returns:
            list[int]: Lista de IDs validados
            
        Raises:
            ValidationException: Si la operación no es válida
        """
        valid_operations = ['delete', 'update', 'export', 'archive']
        
        if operation not in valid_operations:
            raise ValidationException(
                f"Operación inválida: {operation}. "
                f"Operaciones válidas: {', '.join(valid_operations)}"
            )
        
        if not resource_ids:
            raise ValidationException("No se especificaron recursos para la operación")
        
        # Eliminar duplicados y validar IDs
        unique_ids = []
        for rid in resource_ids:
            if isinstance(rid, int) and rid > 0 and rid not in unique_ids:
                unique_ids.append(rid)
        
        if not unique_ids:
            raise ValidationException("No se encontraron IDs válidos en la lista")
        
        if len(unique_ids) > max_items:
            logger.warning(
                f"⚠️ Operación {operation} limitada a {max_items} items, "
                f"se recibieron {len(unique_ids)}"
            )
            unique_ids = unique_ids[:max_items]
        
        logger.info(
            f"✅ Operación {operation} validada para {len(unique_ids)} recursos"
        )
        return unique_ids
