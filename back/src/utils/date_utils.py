"""
Utilidades para manejo de fechas en la aplicación.
Específicamente para evitar problemas con particionamiento de tablas.
"""
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

def get_safe_timestamp() -> str:
    """
    Devuelve una marca de tiempo segura para insertar en la base de datos.
    
    NOTA: La tabla messages está particionada por fecha y solo tiene particiones
    hasta mayo 2025. Esta función devuelve una fecha dentro del rango seguro.
    
    Returns:
        str: Timestamp en formato ISO que es seguro para insertar
    """
    # SOLUCIÓN TEMPORAL: Usar una fecha que sabemos tiene partición
    # En producción, esto debería manejarse agregando particiones dinámicamente
    # o usando una estrategia diferente de particionamiento
    
    # Obtener fecha actual
    now = datetime.now(timezone.utc)
    
    # Si estamos en junio 2025 o después, usar el último día de mayo 2025
    if now.year >= 2025 and now.month >= 6:
        # Usar mayo 31, 2025 con la hora actual
        safe_date = datetime(2025, 5, 31, now.hour, now.minute, now.second, 
                           now.microsecond, tzinfo=timezone.utc)
        logger.warning(f"Fecha actual {now} está fuera del rango de particiones. Usando {safe_date}")
    else:
        safe_date = now
    
    return safe_date.isoformat()
