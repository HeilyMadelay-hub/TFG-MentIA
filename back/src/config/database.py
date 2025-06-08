"""
# -*- coding: utf-8 -*-
Configuración de la conexión a Supabase con patrón singleton.
Versión simplificada que solo usa el cliente de Supabase (sin SQLAlchemy).
"""
import os
import sys
import logging
import importlib
from typing import Optional

# Configurar logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Intenta diferentes formas de importar dotenv
try:
    from dotenv import load_dotenv
    logger.info("dotenv importado correctamente")
except ImportError:
    logger.warning("Error importando dotenv. Usando implementación alternativa.")
    def load_dotenv():
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        try:
                            key, value = line.strip().split('=', 1)
                            os.environ[key.strip()] = value.strip()
                        except ValueError:
                            logger.warning(f"Ignorando línea mal formateada en .env: {line.strip()}")

# Verificación detallada de supabase
supabase_import_error = None
try:
    # Primero verificar si el módulo está instalado
    if importlib.util.find_spec("supabase") is None:
        raise ImportError("El módulo 'supabase' no está instalado")
    
    # Intentar importar normalmente
    from supabase import create_client, Client
    logger.info("supabase importado correctamente")
except ImportError as e:
    supabase_import_error = str(e)
    logger.error(f"ERROR DETALLADO DE IMPORTACIÓN: {supabase_import_error}")
    logger.info("Intentando importar supabase-py como alternativa...")
    
    try:
        # Intentar con supabase-py en caso de que ese sea el nombre del paquete
        import supabase
        from supabase import create_client, Client
        print("supabase_py importado correctamente")
    except ImportError:
        print("ADVERTENCIA: No se pudo importar supabase ni supabase-py. Las funciones de base de datos no estarán disponibles.")
        
        # Definir stubs para permitir que el archivo se cargue
        class Client:
            pass
        
        def create_client(url, key):
            print(f"Se llamó a create_client con URL={url} y KEY={key[:4]}***")
            return None

# Cargar variables de entorno
load_dotenv()
logger.info("Variables de entorno cargadas")
logger.debug(f"SUPABASE_URL definida: {'Sí' if os.getenv('SUPABASE_URL') else 'No'}")
logger.debug(f"SUPABASE_KEY definida: {'Sí' if os.getenv('SUPABASE_KEY') else 'No'}")

# Validar variables de entorno requeridas
required_env_vars = ["SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_KEY"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Faltan variables de entorno requeridas: {', '.join(missing_vars)}")
    raise ValueError(f"Faltan variables de entorno requeridas: {', '.join(missing_vars)}")

class SupabaseConnector:
    """
    Implementación del patrón Singleton para la conexión a Supabase.
    Garantiza una única instancia de la conexión en toda la aplicación.
    """
    _instance: Optional['SupabaseConnector'] = None
    _client = None
    _service_client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseConnector, cls).__new__(cls)
            cls._instance._client = None
            cls._instance._service_client = None
        return cls._instance
    
    def get_client(self, use_service_role=False):
        """
        Obtiene el cliente de Supabase, inicializándolo si es necesario.
        
        Args:
            use_service_role: Si es True, usa la clave de servicio para omitir RLS
        """
        # Usar el cliente de servicio si se solicita
        if use_service_role:
            if self._service_client is None:
                # Inicializar cliente con clave de servicio
                supabase_url = os.getenv("SUPABASE_URL")
                service_key = os.getenv("SUPABASE_SERVICE_KEY")
                
                if not supabase_url or not service_key:
                    raise ValueError(
                        "Las variables de entorno SUPABASE_URL y SUPABASE_SERVICE_KEY son requeridas "
                        "para operaciones que requieren permisos elevados."
                    )
                
                print(f"Inicializando cliente de Supabase con clave de servicio en {supabase_url}")
                try:
                    self._service_client = create_client(supabase_url, service_key)
                    print("Cliente de Supabase con permisos de servicio creado exitosamente")
                except Exception as e:
                    print(f"Error al crear cliente de Supabase con permisos de servicio: {str(e)}")
                    raise
            
            return self._service_client
        
        # Usar el cliente normal si no se solicita el de servicio
        if self._client is None:
            # Obtener credenciales desde variables de entorno
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                raise ValueError(
                    "Las variables de entorno SUPABASE_URL y SUPABASE_KEY son requeridas. "
                    "Asegúrate de configurarlas en el archivo .env"
                )
            
            print(f"Inicializando cliente de Supabase en {supabase_url}")
            try:
                self._client = create_client(supabase_url, supabase_key)
                print("Cliente de Supabase creado exitosamente")
            except Exception as e:
                print(f"Error al crear cliente de Supabase: {str(e)}")
                raise
        
        return self._client
        
    def test_connection(self) -> bool:
        """
        Prueba la conexión a Supabase realizando una operación simple.
        """
        try:
            client = self.get_client()
            print("Probando conexión a Supabase...")
            
            # Intenta una operación simple: verificar si existe la tabla users
            response = client.from_('users').select('count').limit(1).execute()
            
            print(f"Conexión exitosa a Supabase. Respuesta: {response}")
            return True
        except Exception as e:
            print(f"Error al conectar con Supabase: {str(e)}")
            return False 

# Funciones auxiliares
def get_supabase_connector() -> SupabaseConnector:
    return SupabaseConnector()

def get_supabase_client(use_service_role=False):
    return get_supabase_connector().get_client(use_service_role)


class Session:
    """Stub para compatibilidad"""
    pass

def get_db():
    """
    Stub para compatibilidad con código que espera SQLAlchemy.
    En lugar de una sesión de base de datos, devuelve el cliente de Supabase.
    """
    client = get_supabase_client()
    yield client

# Variables de compatibilidad
engine = None
SessionLocal = None
