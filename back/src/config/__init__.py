"""
Inicialización del paquete de configuraciones.
Permite acceder a las configuraciones globales, el conector de Supabase,
y las utilidades de base de datos.
"""

# Importar configuraciones globales
from .settings import Settings, settings, get_settings

# Importar utilidades de base de datos
from .database import (
    SupabaseConnector,
    get_supabase_connector,
    get_supabase_client
)

# Exportar las clases y funciones públicas

# El __all__ en Python es una lista especial que define explícitamente qué nombres (variables, funciones, clases) estarán disponibles cuando otro módulo use la declaración from modulo import *. esto significa que importa todo lo del all ,cualquier otro elemento que este en el modulo
# pero no esté en __all__ no será importado.Sin __all__, un import * importaría todos los nombres que no empiecen con guión bajo (_), lo cual podría causar conflictos de nombres no deseados.
# Pero si pone from src.config import * importará solo lo que esté en __all__.

__all__ = [
    # Configuraciones
    "Settings",
    "settings",
    "get_settings",
    
    # Base de datos
    "SupabaseConnector",
    "get_supabase_connector",
    "get_supabase_client",
]