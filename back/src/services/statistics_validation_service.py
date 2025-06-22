"""
Servicio para validaciones específicas de estadísticas.
Centraliza todas las validaciones relacionadas con operaciones estadísticas.
"""
import logging
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from src.models.domain import User
from src.core.exceptions import ValidationException

logger = logging.getLogger(__name__)

class StatisticsValidationService:
    """Servicio para validaciones específicas de estadísticas"""
    
    def validate_time_period(self, period: str) -> str:
        """
        Valida y normaliza períodos de tiempo para estadísticas.
        
        Args:
            period: Período a validar (7d, 30d, 1y, etc.)
            
        Returns:
            str: Período normalizado
            
        Raises:
            ValidationException: Si el período no es válido
        """
        valid_periods = {
            "7d": "7 días",
            "30d": "30 días", 
            "90d": "90 días",
            "1y": "1 año",
            "all": "Todo el tiempo"
        }
        
        if period not in valid_periods:
            raise ValidationException(
                f"Período inválido: {period}. "
                f"Períodos válidos: {list(valid_periods.keys())}"
            )
        
        logger.info(f"✅ Período validado: {period} -> {valid_periods[period]}")
        return period
    
    def validate_group_by_field(self, field: str, resource_type: str) -> str:
        """
        Valida campos de agrupación según tipo de recurso.
        
        Args:
            field: Campo por el cual agrupar
            resource_type: Tipo de recurso (documents, chats, users)
            
        Returns:
            str: Campo validado
            
        Raises:
            ValidationException: Si el campo no es válido para el tipo de recurso
        """
        valid_fields = {
            "documents": ["content_type", "created_at", "user_id", "is_shared"],
            "chats": ["created_at", "user_id", "status"],
            "users": ["created_at", "is_admin", "is_active"]
        }
        
        if resource_type not in valid_fields:
            raise ValidationException(f"Tipo de recurso inválido: {resource_type}")
        
        if field not in valid_fields[resource_type]:
            raise ValidationException(
                f"Campo inválido '{field}' para {resource_type}. "
                f"Campos válidos: {valid_fields[resource_type]}"
            )
        
        logger.info(f"✅ Campo de agrupación validado: {field} para {resource_type}")
        return field
    
    def validate_statistics_access(self, user: User, operation: str) -> bool:
        """
        Valida permisos de acceso a estadísticas según el usuario y operación.
        
        Args:
            user: Usuario que solicita la operación
            operation: Tipo de operación (global, user_specific, admin_only)
            
        Returns:
            bool: True si tiene acceso
            
        Raises:
            ValidationException: Si no tiene permisos
        """
        logger.info(f"🔐 Validando acceso de {user.username} para operación: {operation}")
        
        # Operaciones públicas (cualquier usuario autenticado)
        public_operations = ["global", "user_specific"]
        
        # Operaciones solo para administradores
        admin_operations = ["admin_only", "system_health", "all_users_stats"]
        
        if operation in public_operations:
            logger.info(f"✅ Operación {operation} permitida para usuario autenticado")
            return True
        
        if operation in admin_operations:
            if not user.is_admin:
                logger.warning(f"❌ Usuario {user.username} sin permisos de admin para {operation}")
                raise ValidationException(
                    f"No tienes permisos para la operación: {operation}"
                )
            logger.info(f"✅ Operación {operation} permitida para admin {user.username}")
            return True
        
        # Operación no reconocida
        logger.error(f"❌ Operación no reconocida: {operation}")
        raise ValidationException(f"Operación no válida: {operation}")
    
    def validate_limit_and_skip(self, limit: Optional[int], skip: Optional[int]) -> Tuple[int, int]:
        """
        Valida y normaliza parámetros de paginación.
        
        Args:
            limit: Límite de resultados
            skip: Número de resultados a saltar
            
        Returns:
            Tuple[int, int]: (limit, skip) validados
            
        Raises:
            ValidationException: Si los parámetros no son válidos
        """
        # Límites por defecto
        default_limit = 10
        max_limit = 100
        
        # Validar limit
        if limit is None:
            limit = default_limit
        elif limit < 1:
            raise ValidationException("El límite debe ser mayor a 0")
        elif limit > max_limit:
            raise ValidationException(f"El límite no puede ser mayor a {max_limit}")
        
        # Validar skip
        if skip is None:
            skip = 0
        elif skip < 0:
            raise ValidationException("El skip no puede ser negativo")
        
        logger.info(f"✅ Paginación validada: limit={limit}, skip={skip}")
        return limit, skip
    
    def validate_date_range(self, start_date: Optional[str], end_date: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Valida un rango de fechas para filtros estadísticos.
        
        Args:
            start_date: Fecha de inicio (formato ISO)
            end_date: Fecha de fin (formato ISO)
            
        Returns:
            Tuple[Optional[datetime], Optional[datetime]]: Fechas parseadas
            
        Raises:
            ValidationException: Si las fechas no son válidas
        """
        parsed_start = None
        parsed_end = None
        
        try:
            if start_date:
                parsed_start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            
            if end_date:
                parsed_end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            # Validar que start_date sea anterior a end_date
            if parsed_start and parsed_end and parsed_start >= parsed_end:
                raise ValidationException("La fecha de inicio debe ser anterior a la fecha de fin")
            
            # Validar que las fechas no sean futuras
            now = datetime.now()
            if parsed_start and parsed_start > now:
                raise ValidationException("La fecha de inicio no puede ser futura")
            
            if parsed_end and parsed_end > now:
                raise ValidationException("La fecha de fin no puede ser futura")
            
            logger.info(f"✅ Rango de fechas validado: {parsed_start} -> {parsed_end}")
            return parsed_start, parsed_end
            
        except ValueError as e:
            raise ValidationException(f"Formato de fecha inválido: {str(e)}")
    
    def validate_resource_type(self, resource_type: str) -> str:
        """
        Valida que el tipo de recurso sea válido.
        
        Args:
            resource_type: Tipo de recurso a validar
            
        Returns:
            str: Tipo de recurso validado
            
        Raises:
            ValidationException: Si el tipo de recurso no es válido
        """
        valid_types = ["documents", "chats", "users", "all"]
        
        if resource_type not in valid_types:
            raise ValidationException(
                f"Tipo de recurso inválido: {resource_type}. "
                f"Tipos válidos: {valid_types}"
            )
        
        logger.info(f"✅ Tipo de recurso validado: {resource_type}")
        return resource_type
