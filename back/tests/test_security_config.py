"""
Script para probar las configuraciones de seguridad
"""
import requests
import time
import json

BASE_URL = "http://localhost:2690/api"

def test_cors():
    """Prueba la configuración de CORS"""
    print("\n🔍 PROBANDO CONFIGURACIÓN CORS")
    print("="*50)
    
    # Simular petición desde diferentes orígenes
    origins = [
        "http://localhost:3000",
        "http://localhost:53793", 
        "https://example.com",  # Este debería fallar en desarrollo
    ]
    
    for origin in origins:
        headers = {"Origin": origin}
        try:
            response = requests.get(f"{BASE_URL}/health", headers=headers)
            print(f"✅ Origen {origin}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ Origen {origin}: Error {str(e)}")

def test_rate_limiting():
    """Prueba el rate limiting en diferentes endpoints"""
    print("\n🚦 PROBANDO RATE LIMITING")
    print("="*50)
    
    # Test 1: Login endpoint (límite: 10/minuto)
    print("\n1. Probando límite de login (10/minuto):")
    login_data = {
        "username": "test_user",
        "password": "wrong_password"
    }
    
    for i in range(12):
        try:
            response = requests.post(
                f"{BASE_URL}/users/login",
                data=login_data
            )
            if response.status_code == 429:
                print(f"   ⛔ Petición {i+1}: Rate limit alcanzado!")
                print(f"      Mensaje: {response.json().get('detail')}")
                break
            else:
                print(f"   ✅ Petición {i+1}: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Petición {i+1}: Error {str(e)}")
        
        time.sleep(0.5)  # Pequeña pausa entre peticiones
    
    # Test 2: Register endpoint (límite: 5/minuto)
    print("\n2. Probando límite de registro (5/minuto):")
    
    for i in range(7):
        register_data = {
            "username": f"test_user_{int(time.time())}_{i}",
            "email": f"test_{int(time.time())}_{i}@example.com",
            "password": "TestPassword123!"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/users/register",
                json=register_data
            )
            if response.status_code == 429:
                print(f"   ⛔ Petición {i+1}: Rate limit alcanzado!")
                print(f"      Mensaje: {response.json().get('detail')}")
                break
            else:
                print(f"   ✅ Petición {i+1}: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Petición {i+1}: Error {str(e)}")
        
        time.sleep(0.5)

def test_health_endpoint():
    """Verifica el endpoint de health y la configuración"""
    print("\n🏥 PROBANDO HEALTH ENDPOINT")
    print("="*50)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Estado: {data.get('status')}")
            print(f"🌍 Entorno: {data.get('environment')}")
            print(f"🔒 CORS habilitado: {data.get('cors_enabled')}")
            print(f"🚦 Rate limiting: {data.get('rate_limiting_enabled')}")
        else:
            print(f"❌ Error: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    print("\n🔒 PRUEBA DE CONFIGURACIONES DE SEGURIDAD")
    print("="*50)
    print("Asegúrate de que el servidor esté corriendo en http://localhost:2690")
    
    input("\nPresiona ENTER para comenzar las pruebas...")
    
    # Ejecutar pruebas
    test_health_endpoint()
    test_cors()
    test_rate_limiting()
    
    print("\n✅ PRUEBAS COMPLETADAS")
    print("\nRECOMENDACIONES:")
    print("1. Verifica los logs del servidor para más detalles")
    print("2. Ajusta los límites según tus necesidades")
    print("3. En producción, usa dominios específicos para CORS")

if __name__ == "__main__":
    main()
