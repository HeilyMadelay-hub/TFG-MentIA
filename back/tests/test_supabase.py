"""
Script para probar la conexión a Supabase.
Este script verifica si se puede importar el módulo supabase
y establecer una conexión a la base de datos.
"""
import sys
import os
import subprocess

def check_supabase_installation():
    """Verificar si el paquete supabase está instalado"""
    print("Verificando instalación de supabase...")
    
    # Verificar qué versión de Python está en uso
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    
    # Listar paquetes instalados
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list"], 
            capture_output=True, 
            text=True
        )
        print("Paquetes instalados:")
        for line in result.stdout.splitlines():
            if "supabase" in line.lower():
                print(f"ENCONTRADO: {line}")
    except Exception as e:
        print(f"Error al listar paquetes: {e}")
    
    # Intentar importar supabase
    try:
        import supabase
        print(f"Supabase encontrado: {supabase.__file__}")
        return True
    except ImportError as e:
        print(f"No se pudo importar supabase: {e}")
        
        # Intentar importar supabase_py
        try:
            import supabase
            print(f"supabase_py encontrado: {supabase.__file__}")
            return True
        except ImportError:
            print("No se pudo importar supabase_py")
            return False

def check_env_file():
    """Verificar si el archivo .env existe y tiene las variables necesarias"""
    print("\nVerificando archivo .env...")
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    
    if os.path.exists(env_path):
        print(f"Archivo .env encontrado: {env_path}")
        with open(env_path, 'r') as f:
            content = f.read()
            print("Variables en .env:")
            for line in content.split('\n'):
                if line.strip() and not line.startswith('#'):
                    key = line.split('=')[0] if '=' in line else line
                    value = "***" if '=' in line else "no value"
                    print(f"  {key}={value}")
    else:
        print(f"No se encontró el archivo .env en: {env_path}")
        return False
    return True

# Añadir el directorio raíz del proyecto al path de Python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
print(f"Directorio raíz añadido al path: {project_root}")

def test_supabase_connection():
    """Prueba la conexión a Supabase"""
    print("\nProbando conexión a Supabase...")
    
    try:
        # Importar el conector
        from src.config.database import SupabaseConnector
        print("Módulo SupabaseConnector importado correctamente")
        
        # Obtener instancia del conector
        connector = SupabaseConnector()
        print("Instancia de SupabaseConnector creada")
        
        # Obtener cliente
        client = connector.get_client()
        if client is None:
            print("Error: el cliente es None")
            return False
        
        print("Cliente obtenido exitosamente")
        
        # Intentar una consulta simple
        print("Intentando ejecutar una consulta simple...")
        try:
            # Primero intentar una operación básica
            response = client.from_('users').select('*').limit(1).execute()
            print(f"Consulta exitosa: {response}")
        except Exception as e:
            print(f"Error en la consulta: {e}")
            # Intentar otra operación si la primera falla
            try:
                # Listar tablas podría funcionar incluso si 'users' no existe
                response = client.table('users').select('count').limit(1).execute()
                print(f"Consulta alternativa exitosa: {response}")
            except Exception as e2:
                print(f"Error en consulta alternativa: {e2}")
                return False
        
        print("Conexión a Supabase exitosa!")
        return True
        
    except Exception as e:
        print(f"Error al probar la conexión: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== DIAGNÓSTICO DE CONEXIÓN A SUPABASE ===")
    
    # Verificar instalación de supabase
    supabase_installed = check_supabase_installation()
    
    # Verificar archivo .env
    env_file_ok = check_env_file()
    
    # Sugerir soluciones si hay problemas
    if not supabase_installed:
        print("\n=== SOLUCIÓN RECOMENDADA ===")
        print("Instalar supabase usando pip:")
        print("pip install supabase")
        print("o")
        print("pip install supabase-py")
    
    if not env_file_ok:
        print("\n=== SOLUCIÓN RECOMENDADA ===")
        print("Crear un archivo .env en la raíz del proyecto con:")
        print("SUPABASE_URL=https://tu-proyecto.supabase.co")
        print("SUPABASE_KEY=tu-clave-supabase")
    
    # Probar conexión solo si los requisitos previos están bien
    if supabase_installed and env_file_ok:
        result = test_supabase_connection()
        if result:
            print("\n=== RESULTADO ===")
            print("✅ Prueba de conexión completada con éxito")
        else:
            print("\n=== RESULTADO ===")
            print("❌ Error en la prueba de conexión")
            print("\n=== SOLUCIONES POSIBLES ===")
            print("1. Verificar que las credenciales en .env sean correctas")
            print("2. Verificar que la URL de Supabase esté accesible")
            print("3. Revisar que existan las tablas que estás consultando")
            print("4. Verificar que el API key tenga suficientes permisos")