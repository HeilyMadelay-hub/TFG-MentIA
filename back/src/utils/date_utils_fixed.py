"""
Utilidades para manejo de fechas en la aplicación.
Actualizado para usar UTC correctamente y manejar particiones dinámicamente.
"""
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

def get_safe_timestamp() -> str:
    """
    Devuelve una marca de tiempo en UTC para insertar en la base de datos.
    
    Returns:
        str: Timestamp en formato ISO UTC
    """
    # Siempre usar UTC
    now = datetime.now(timezone.utc)
    return now.isoformat()

def get_utc_now() -> datetime:
    """
    Obtiene la fecha y hora actual en UTC con timezone awareness.
    
    Returns:
        datetime: Fecha y hora actual en UTC
    """
    return datetime.now(timezone.utc)

def ensure_utc(dt):
    """
    Asegura que una fecha esté en UTC con timezone awareness.
    
    Args:
        dt: Fecha a convertir (datetime, string ISO o None)
        
    Returns:
        datetime: Fecha en UTC o None si la entrada es None
    """
    if dt is None:
        return None
    
    # Si es string, parsear
    if isinstance(dt, str):
        from dateutil import parser
        dt = parser.parse(dt)
    
    # Si no tiene timezone, asumir UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Si tiene timezone diferente, convertir a UTC
    elif dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)
    
    return dt

def format_for_db(dt):
    """
    Formatea una fecha para guardar en la base de datos.
    Siempre retorna en formato ISO con UTC.
    
    Args:
        dt: Fecha a formatear
        
    Returns:
        str: Fecha en formato ISO UTC o None
    """
    if dt is None:
        return None
    
    # Asegurar que esté en UTC
    dt_utc = ensure_utc(dt)
    
    # Retornar en formato ISO
    return dt_utc.isoformat()

# Funciones para compatibilidad con el código existente
def get_partition_name(date=None):
    """
    Obtiene el nombre de la partición para una fecha dada.
    
    Args:
        date: Fecha para la cual obtener la partición (por defecto, ahora)
        
    Returns:
        str: Nombre de la partición (ej: 'messages_y2025m06')
    """
    if date is None:
        date = datetime.now(timezone.utc)
    elif isinstance(date, str):
        from dateutil import parser
        date = parser.parse(date)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
    
    year = date.year
    month = date.month
    
    return f"messages_y{year}m{month:02d}"

def check_partition_exists(partition_name):
    """
    Verifica si una partición existe (placeholder para implementación real).
    
    Args:
        partition_name: Nombre de la partición
        
    Returns:
        bool: True si existe (asumimos que sí por ahora)
    """
    # En una implementación real, esto debería verificar en la BD
    logger.info(f"Verificando partición: {partition_name}")
    return True
