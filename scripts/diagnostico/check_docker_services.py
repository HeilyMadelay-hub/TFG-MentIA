"""
Script para verificar el estado de los servicios Docker
"""
import subprocess
import requests
import time
import sys

def check_docker_services():
    """Verifica que los servicios Docker estén corriendo"""
    print("🔍 Verificando servicios Docker...\n")
    
    try:
        # Verificar contenedores
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'], 
                               capture_output=True, text=True)
        print("📦 Contenedores activos:")
        print(result.stdout)
        
        # Verificar logs del backend si está caído
        backend_running = 'chabot-backend' in result.stdout
        if not backend_running:
            print("\n⚠️  Backend no está corriendo. Verificando logs...")
            logs = subprocess.run(['docker', 'logs', 'chabot-backend', '--tail', '50'], 
                                capture_output=True, text=True)
            print("📋 Últimos logs del backend:")
            print(logs.stdout)
            print(logs.stderr)
            
    except Exception as e:
        print(f"❌ Error verificando Docker: {str(e)}")
        return False
    
    return True

def check_service_health():
    """Verifica la salud de cada servicio"""
    services = [
        ("Frontend", "http://localhost", "/"),
        ("Backend", "http://localhost:2690", "/health"),
        ("Backend Docs", "http://localhost:2690", "/docs"),
        ("ChromaDB", "http://localhost:8050", "/api/v1/heartbeat")
    ]
    
    print("\n🏥 Verificando salud de servicios:")
    for name, base_url, path in services:
        try:
            response = requests.get(f"{base_url}{path}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: OK")
            else:
                print(f"⚠️  {name}: Respuesta {response.status_code}")
        except requests.ConnectionError:
            print(f"❌ {name}: No se puede conectar")
        except Exception as e:
            print(f"❌ {name}: Error - {str(e)}")

def test_chromadb_connection():
    """Prueba específica de ChromaDB"""
    print("\n🔬 Prueba de conexión ChromaDB:")
    try:
        # Desde el host
        response = requests.get("http://localhost:8050/api/v1/heartbeat", timeout=5)
        print(f"✅ ChromaDB desde host: {response.status_code}")
        
        # Desde el contenedor backend
        result = subprocess.run(
            ['docker', 'exec', 'chabot-backend', 'curl', '-s', 'http://chromadb:8000/api/v1/heartbeat'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ ChromaDB desde backend container: OK")
        else:
            print("❌ ChromaDB desde backend container: No accesible")
            
    except Exception as e:
        print(f"❌ Error en prueba ChromaDB: {str(e)}")

def restart_backend():
    """Reinicia el backend si está caído"""
    print("\n🔄 Reiniciando backend...")
    subprocess.run(['docker-compose', 'restart', 'backend'])
    time.sleep(10)
    print("✅ Backend reiniciado")

def main():
    print("="*50)
    print("   🩺 DIAGNÓSTICO DE SERVICIOS DOCKER")
    print("="*50)
    
    # Verificar Docker
    if not check_docker_services():
        print("\n❌ Docker no está disponible")
        return
    
    # Verificar salud
    check_service_health()
    
    # Test específico de ChromaDB
    test_chromadb_connection()
    
    # Preguntar si reiniciar backend
    print("\n" + "="*50)
    backend_status = subprocess.run(['docker', 'ps', '-q', '-f', 'name=chabot-backend'], 
                                   capture_output=True, text=True)
    if not backend_status.stdout.strip():
        response = input("\n⚠️  El backend no está corriendo. ¿Deseas reiniciarlo? (s/n): ")
        if response.lower() == 's':
            restart_backend()
            check_service_health()

if __name__ == "__main__":
    main()
