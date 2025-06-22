#!/usr/bin/env python3
"""
Script de prueba rápida para verificar endpoints de usuarios refactorizados
"""
import requests
import json
import sys
import time
import random
import string

BASE_URL = "http://localhost:8000/api"

def test_endpoints():
    """Prueba básica de endpoints principales"""
    print("🧪 PRUEBA DE ENDPOINTS REFACTORIZADOS")
    print("=" * 50)
    
    tests = [
        {
            "name": "Verificar salud del servidor",
            "method": "GET",
            "url": f"{BASE_URL}/health",
        },
        {
            "name": "Registro nuevo usuario",
            "method": "POST",
            "url": f"{BASE_URL}/users/register",
            "json": {
                "username": f"testuser{''.join(random.choices(string.digits, k=6))}",
                "email": f"test{int(time.time())}@gmail.com",
                "password": "SecurePass123!"
            }
        },
        {
            "name": "Login con credenciales conocidas (ivan)",
            "method": "POST",
            "url": f"{BASE_URL}/users/login",
            "data": {"username": "ivan", "password": "ivan1234"},
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Login con Ivan (case-sensitive original)",
            "method": "POST", 
            "url": f"{BASE_URL}/users/login",
            "data": {"username": "Ivan", "password": "ivan1234"},
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Login con variaciones de Ivan (IvAn)",
            "method": "POST", 
            "url": f"{BASE_URL}/users/login",
            "data": {"username": "IvAn", "password": "ivan1234"},
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Login con variaciones de Ivan (IVAN)",
            "method": "POST", 
            "url": f"{BASE_URL}/users/login",
            "data": {"username": "IVAN", "password": "ivan1234"},
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Login con email de Ivan (@documente.es)",
            "method": "POST", 
            "url": f"{BASE_URL}/users/login",
            "data": {"username": "ivan@documente.es", "password": "ivan1234"},
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"\n🔍 {test['name']}...")
            
            if test['method'] == 'GET':
                response = requests.get(test['url'])
            elif test['method'] == 'POST':
                if 'json' in test:
                    response = requests.post(test['url'], json=test['json'])
                else:
                    response = requests.post(test['url'], data=test['data'], headers=test.get('headers', {}))
            
            if response.status_code in [200, 201]:
                print(f"✅ PASS - Status: {response.status_code}")
                if test['name'].startswith('Registro'):
                    data = response.json()
                    print(f"   Usuario creado: {data.get('username', 'N/A')}")
                passed += 1
            else:
                print(f"❌ FAIL - Status: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                failed += 1
                
        except requests.exceptions.ConnectionError:
            print("❌ Error: No se puede conectar al servidor")
            print("   Asegúrate de que el servidor esté corriendo:")
            print("   uvicorn src.main:app --reload")
            return
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Resultados: {passed} pasaron, {failed} fallaron")
    
    if failed == 0:
        print("🎉 ¡Todos los tests pasaron!")
    else:
        print("⚠️ Algunos tests fallaron. Revisa los logs del servidor.")
    
    return passed, failed

def test_authenticated_endpoints(token):
    """Prueba endpoints que requieren autenticación"""
    print("\n🔐 PRUEBA DE ENDPOINTS AUTENTICADOS")
    print("=" * 50)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    auth_tests = [
        {
            "name": "Obtener perfil actual",
            "method": "GET",
            "url": f"{BASE_URL}/users/me"
        },
        {
            "name": "Validar token",
            "method": "GET",
            "url": f"{BASE_URL}/users/token/validate"
        }
    ]
    
    for test in auth_tests:
        try:
            print(f"\n🔍 {test['name']}...")
            response = requests.get(test['url'], headers=headers)
            
            if response.status_code == 200:
                print(f"✅ PASS - Status: {response.status_code}")
                data = response.json()
                if 'user' in data:
                    print(f"   Usuario: {data['user'].get('username', 'N/A')}")
            else:
                print(f"❌ FAIL - Status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    # Primero probar endpoints básicos
    passed, failed = test_endpoints()
    
    # Intentar login para obtener token
    print("\n🔑 Intentando obtener token de autenticación...")
    login_response = requests.post(
        f"{BASE_URL}/users/login",
        data={"username": "ivan", "password": "ivan1234"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if login_response.status_code == 200:
        token = login_response.json().get('access_token')
        if token:
            print("✅ Token obtenido exitosamente")
            test_authenticated_endpoints(token)
    else:
        print("❌ No se pudo obtener token de autenticación")
        print(f"   Status: {login_response.status_code}")
        print(f"   Response: {login_response.text[:200]}...")
