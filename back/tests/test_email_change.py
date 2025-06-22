"""
Script de prueba para verificar el flujo de cambio de email
"""
import requests
import json
import time

# Configuración
BASE_URL = "http://localhost:2690/api"

def test_email_change_flow():
    print("🔄 Iniciando prueba de cambio de email...")
    
    # 1. Login como usuario normal (heily185)
    print("\n1️⃣ Haciendo login como heily185...")
    login_response = requests.post(f"{BASE_URL}/users/login", data={
        "username": "heily185",
        "password": "heily"  # Asumiendo esta es la contraseña
    })
    
    if login_response.status_code != 200:
        print(f"❌ Error en login: {login_response.status_code}")
        print(login_response.text)
        return
    
    login_data = login_response.json()
    token = login_data.get("access_token")
    print(f"✅ Login exitoso. Token obtenido.")
    
    # 2. Obtener perfil actual
    print("\n2️⃣ Obteniendo perfil actual...")
    headers = {"Authorization": f"Bearer {token}"}
    profile_response = requests.get(f"{BASE_URL}/users/me", headers=headers)
    
    if profile_response.status_code != 200:
        print(f"❌ Error obteniendo perfil: {profile_response.status_code}")
        return
    
    current_profile = profile_response.json()
    current_email = current_profile.get("email")
    print(f"✅ Email actual: {current_email}")
    
    # 3. Intentar cambiar el email
    new_email = "test_change@example.com"  # Email de prueba
    print(f"\n3️⃣ Intentando cambiar email a: {new_email}")
    
    update_response = requests.put(
        f"{BASE_URL}/users/me",
        headers=headers,
        json={"email": new_email}
    )
    
    if update_response.status_code != 200:
        print(f"❌ Error actualizando perfil: {update_response.status_code}")
        print(update_response.text)
        return
    
    update_data = update_response.json()
    print(f"✅ Respuesta: {json.dumps(update_data, indent=2)}")
    
    # Verificar el tipo de respuesta
    if isinstance(update_data, dict) and update_data.get("status") == "pending_confirmation":
        print(f"\n✅ Se requiere confirmación por email!")
        print(f"📧 Email enviado a: {update_data.get('old_email')}")
        print(f"📧 Nuevo email será: {update_data.get('new_email')}")
        print(f"💬 Mensaje: {update_data.get('message')}")
    else:
        print("\n❓ La actualización fue directa (no requirió confirmación)")
    
    # 4. Login como admin (Ivan) para probar cambio directo
    print("\n\n4️⃣ Probando cambio de email como admin (Ivan)...")
    admin_login = requests.post(f"{BASE_URL}/users/login", data={
        "username": "ivan",
        "password": "ivan1234"
    })
    
    if admin_login.status_code == 200:
        admin_token = admin_login.json().get("access_token")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Cambiar email como admin
        admin_update = requests.put(
            f"{BASE_URL}/users/me",
            headers=admin_headers,
            json={"email": "ivan_new@documente.es"}
        )
        
        if admin_update.status_code == 200:
            admin_result = admin_update.json()
            if isinstance(admin_result, dict) and "id" in admin_result:
                print("✅ Como admin, el cambio fue directo (sin confirmación)")
            else:
                print(f"📧 Resultado: {json.dumps(admin_result, indent=2)}")

if __name__ == "__main__":
    test_email_change_flow()
