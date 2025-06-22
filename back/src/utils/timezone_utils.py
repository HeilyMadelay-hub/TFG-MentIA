"""
Configuración de timezone para asegurar que todas las fechas se manejen en UTC
"""
import os
import time
from datetime import datetime, timezone
from typing import Union

# Forzar UTC en el proceso Python (solo funciona en sistemas Unix-like)
try:
    os.environ['TZ'] = 'UTC'
    time.tzset()
except AttributeError:
    # Windows no tiene time.tzset()
    pass

def get_utc_now() -> datetime:
    """
    Obtiene la fecha y hora actual en UTC con timezone awareness.
    
    Returns:
        datetime: Fecha y hora actual en UTC
    """
    return datetime.now(timezone.utc)

def ensure_utc(dt: Union[datetime, str, None]) -> Union[datetime, None]:
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

def format_for_db(dt: Union[datetime, None]) -> Union[str, None]:
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

# Configuración global para logging
import logging
logger = logging.getLogger(__name__)
logger.info(f"Timezone configurado. Hora UTC actual: {get_utc_now()}")
