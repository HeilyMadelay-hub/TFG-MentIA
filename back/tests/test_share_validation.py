# back/tests/test_share_validation.py

import requests
import json
from typing import Dict, List, Optional
import time

class DocumentShareTester:
    def __init__(self, base_url: str = "http://localhost:2690", token: Optional[str] = None):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Content-Type": "application/json"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def login(self, username: str, password: str) -> str:
        """Obtiene token de autenticación"""
        response = requests.post(
            f"{self.base_url}/api/users/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers["Authorization"] = f"Bearer {self.token}"
            print(f"✅ Login exitoso para {username}")
            return self.token
        else:
            print(f"❌ Error en login: {response.text}")
            return None
    
    def validate_share(self, document_id: int, user_ids: List[int]) -> Dict:
        """Valida antes de compartir"""
        print(f"\n🔍 Validando compartir documento {document_id} con usuarios {user_ids}")
        
        response = requests.post(
            f"{self.base_url}/api/documents/{document_id}/validate-share",
            headers=self.headers,
            json={"user_ids": user_ids}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Validación exitosa:")
            print(f"   - Puede compartir: {data['can_share']}")
            print(f"   - Usuarios que ya tienen acceso: {len(data['validation']['already_shared'])}")
            print(f"   - Nuevos usuarios: {len(data['validation']['new_users'])}")
            
            if data['validation']['already_shared']:
                print("\n   Usuarios con acceso existente:")
                for user in data['validation']['already_shared']:
                    print(f"     - {user['username']} (ID: {user['id']}) - Desde: {user['shared_at']}")
            
            return data
        else:
            print(f"❌ Error en validación: {response.text}")
            return None
    
    def share_document(self, document_id: int, user_ids: List[int]) -> Dict:
        """Comparte documento con usuarios"""
        print(f"\n📤 Compartiendo documento {document_id} con usuarios {user_ids}")
        
        response = requests.post(
            f"{self.base_url}/api/documents/{document_id}/share",
            headers=self.headers,
            json={"user_ids": user_ids}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Resultado:")
            print(f"   - Éxito: {data['success']}")
            print(f"   - Mensaje: {data['message']}")
            print(f"\n   Resumen:")
            summary = data['share_summary']
            print(f"     - Solicitados: {summary['total_requested']}")
            print(f"     - Ya compartidos: {summary['already_shared']}")
            print(f"     - Nuevos compartidos: {summary['new_shares']}")
            print(f"     - Fallidos: {summary['failed']}")
            
            if data['already_shared']:
                print("\n   Usuarios que ya tenían acceso:")
                for user in data['already_shared']:
                    print(f"     - {user['username']} (ID: {user['id']})")
            
            return data
        else:
            print(f"❌ Error al compartir: {response.text}")
            return None
    
    def get_shared_count(self) -> int:
        """Obtiene el conteo de documentos compartidos del dashboard"""
        response = requests.get(
            f"{self.base_url}/api/statistics/dashboard",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return data['statistics']['shared_documents']
        return 0
    
    def run_test_scenarios(self, document_id: int):
        """Ejecuta varios escenarios de prueba"""
        print("\n" + "="*60)
        print("🧪 EJECUTANDO ESCENARIOS DE PRUEBA")
        print("="*60)
        
        # Obtener conteo inicial
        initial_count = self.get_shared_count()
        print(f"\n📊 Documentos compartidos iniciales: {initial_count}")
        
        # Escenario 1: Primera vez compartiendo
        print("\n### ESCENARIO 1: Primera vez compartiendo")
        self.validate_share(document_id, [46, 47, 48])
        result1 = self.share_document(document_id, [46, 47, 48])
        time.sleep(1)
        
        # Escenario 2: Intentar compartir de nuevo (algunos ya tienen acceso)
        print("\n### ESCENARIO 2: Algunos ya tienen acceso")
        self.validate_share(document_id, [46, 47, 48, 49])
        result2 = self.share_document(document_id, [46, 47, 48, 49])
        time.sleep(1)
        
        # Escenario 3: Todos ya tienen acceso
        print("\n### ESCENARIO 3: Todos ya tienen acceso")
        self.validate_share(document_id, [46, 47, 48])
        result3 = self.share_document(document_id, [46, 47, 48])
        
        # Verificar conteo final
        final_count = self.get_shared_count()
        print(f"\n📊 Documentos compartidos finales: {final_count}")
        print(f"📈 Diferencia: {final_count - initial_count}")

def main():
    """Función principal de prueba"""
    # Configuración
    BASE_URL = "http://localhost:2690"  # Cambiar según tu servidor
    USERNAME = "Ivan"  # Usuario de prueba
    PASSWORD = "12345"  # Contraseña
    DOCUMENT_ID = 56  # ID del documento a probar (Tarea2)
    
    # Crear tester
    tester = DocumentShareTester(BASE_URL)
    
    # Login
    token = tester.login(USERNAME, PASSWORD)
    if not token:
        print("❌ No se pudo obtener token. Abortando pruebas.")
        return
    
    # Ejecutar pruebas
    tester.run_test_scenarios(DOCUMENT_ID)
    
    print("\n✅ Pruebas completadas")

if __name__ == "__main__":
    main()

# Ejemplo de uso manual:
# 
# tester = DocumentShareTester("http://localhost:2690")
# tester.login("Ivan", "12345")
# 
# # Validar antes de compartir
# result = tester.validate_share(56, [46, 47])
# 
# # Compartir si se puede
# if result and result['can_share']:
#     tester.share_document(56, result['validation']['new_users'])
