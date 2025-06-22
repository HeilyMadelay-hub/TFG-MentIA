"""
Sistema unificado de logging para toda la aplicación.
Proporciona configuración consistente y utilidades de logging.
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from src.config.settings import get_settings

settings = get_settings()


class ColoredFormatter(logging.Formatter):
    """Formatter con colores para la consola"""
    
    # Códigos de color ANSI
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Verde
        'WARNING': '\033[33m',   # Amarillo
        'ERROR': '\033[31m',     # Rojo
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Aplicar color al nivel
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


class AppLogger:
    """Configurador centralizado de logging para la aplicación"""
    
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self._configured_loggers: Dict[str, logging.Logger] = {}
        
        # Configurar logging raíz
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """Configura el logger raíz de la aplicación"""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        
        # Limpiar handlers existentes
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Formatter para consola con colores
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # Handler para archivo
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        
        # Formatter para archivo (sin colores)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Agregar handlers al logger raíz
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Obtiene un logger configurado para un módulo específico.
        
        Args:
            name: Nombre del módulo (usar __name__)
            
        Returns:
            logging.Logger: Logger configurado
        """
        if name in self._configured_loggers:
            return self._configured_loggers[name]
        
        logger = logging.getLogger(name)
        
        # El logger hereda la configuración del logger raíz
        # Solo necesitamos guardarlo en cache
        self._configured_loggers[name] = logger
        
        return logger
    
    def log_request(self, method: str, url: str, status_code: int, 
                   duration: float, user_id: Optional[int] = None):
        """Registra una petición HTTP"""
        logger = self.get_logger("http.requests")
        
        # Determinar nivel basado en código de estado
        if status_code >= 500:
            level = logging.ERROR
        elif status_code >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO
        
        user_info = f" | User: {user_id}" if user_id else ""
        message = f"{method} {url} | {status_code} | {duration:.3f}s{user_info}"
        
        logger.log(level, message)
    
    def log_database_operation(self, operation: str, table: str, 
                              duration: float, affected_rows: int = 0):
        """Registra una operación de base de datos"""
        logger = self.get_logger("database")
        
        message = f"{operation} on {table} | {duration:.3f}s | {affected_rows} rows"
        logger.info(message)
    
    def log_external_service(self, service: str, operation: str, 
                           status: str, duration: float):
        """Registra llamadas a servicios externos"""
        logger = self.get_logger("external_services")
        
        message = f"{service}.{operation} | {status} | {duration:.3f}s"
        
        if status.lower() in ['error', 'failed', 'timeout']:
            logger.error(message)
        elif status.lower() == 'warning':
            logger.warning(message)
        else:
            logger.info(message)
    
    def log_security_event(self, event_type: str, user_id: Optional[int], 
                          ip_address: str, details: str):
        """Registra eventos de seguridad"""
        logger = self.get_logger("security")
        
        user_info = f"User: {user_id}" if user_id else "Anonymous"
        message = f"{event_type} | {user_info} | IP: {ip_address} | {details}"
        
        # Los eventos de seguridad siempre son importantes
        logger.warning(message)


# Instancia global del sistema de logging
app_logger = AppLogger()


def get_logger(name: str) -> logging.Logger:
    """
    Función auxiliar para obtener un logger.
    Usar en los módulos como: logger = get_logger(__name__)
    """
    return app_logger.get_logger(name)


# Decorador para logging automático de funciones
def log_function_call(level: str = 'DEBUG'):
    """
    Decorador para registrar automáticamente llamadas a funciones.
    
    Args:
        level: Nivel de logging ('DEBUG', 'INFO', etc.)
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            log_level = getattr(logging, level.upper())
            
            logger.log(log_level, f"Calling {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                logger.log(log_level, f"Completed {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                raise
        
        return wrapper
    return decorator


# Utilidades de logging específicas
class LogContext:
    """Context manager para logging con información adicional"""
    
    def __init__(self, logger: logging.Logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        context_str = " | ".join(f"{k}: {v}" for k, v in self.context.items())
        self.logger.info(f"Starting {self.operation} | {context_str}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(f"Failed {self.operation} | Duration: {duration:.3f}s | Error: {exc_val}")
        else:
            self.logger.info(f"Completed {self.operation} | Duration: {duration:.3f}s")


# Configuración específica para bibliotecas externas
def configure_third_party_loggers():
    """Configura el nivel de logging para bibliotecas externas"""
    
    # Silenciar logs muy verbosos
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    
    # Configurar otros según necesidad
    if settings.APP_ENVIRONMENT == "production":
        logging.getLogger('uvicorn').setLevel(logging.WARNING)
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING)


# Inicializar configuración de bibliotecas externas
configure_third_party_loggers()
