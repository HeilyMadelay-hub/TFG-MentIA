#!/usr/bin/env python3
"""
✅ VERIFICACIÓN RÁPIDA DE IMPORTS SOLAMENTE
Script simple que solo verifica que los imports funcionen
"""
import sys
import os

# Agregar el directorio del proyecto al path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def main():
    print("🔍 VERIFICACIÓN RÁPIDA DE IMPORTS")
    print("=" * 40)
    
    imports_to_test = [
        ("src.api.endpoints.users", "router", "Users router"),
        ("src.services.authentication_service", "AuthenticationService", "Auth Service"),
        ("src.services.user_registration_service", "UserRegistrationService", "Registration Service"),
        ("src.api.helpers.user_helpers", "UserEndpointHelpers", "User Helpers"),
        ("src.api.dependencies", "get_current_user", "get_current_user dependency"),
        ("src.services.auth_service", "AuthService", "Base Auth Service"),
        ("src.main", "app", "FastAPI App"),
    ]
    
    failed = 0
    
    for module_name, import_name, description in imports_to_test:
        try:
            module = __import__(module_name, fromlist=[import_name])
            getattr(module, import_name)
            print(f"✅ {description}")
        except Exception as e:
            print(f"❌ {description}: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 40)
    if failed == 0:
        print("🎉 ¡TODOS LOS IMPORTS FUNCIONAN!")
        print("✅ La refactorización está lista")
        return 0
    else:
        print(f"❌ {failed} imports fallaron")
        return 1

if __name__ == "__main__":
    sys.exit(main())
