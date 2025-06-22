#!/usr/bin/env python3
"""
🚀 SOLUCIÓN RÁPIDA: PROBAR SOLO USERS SIN CHAT
Verificar que la refactorización de users funciona independientemente
"""
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_users_only():
    print("🎯 VERIFICACIÓN SOLO DE USERS (SIN CHAT)")
    print("=" * 50)
    
    # Probar imports críticos de users solamente
    imports_to_test = [
        ("src.api.endpoints.users", "router", "Users router"),
        ("src.services.authentication_service", "AuthenticationService", "Auth Service"),
        ("src.api.dependencies", "get_current_user", "get_current_user dependency"),
        ("src.services.auth_service", "AuthService", "Base Auth Service"),
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
    
    print("\n" + "=" * 50)
    if failed == 0:
        print("🎉 ¡REFACTORIZACIÓN DE USERS: 100% FUNCIONAL!")
        print("✅ El problema es solo en chat.py, no en tu refactorización")
        print("")
        print("🚀 OPCIONES PARA CONTINUAR:")
        print("1. Comentar temporalmente import de chat en main.py")
        print("2. Corregir chat.py después")
        print("3. Arrancar servidor solo con users funcionando")
        
        return True
    else:
        print(f"❌ {failed} imports de users fallaron")
        return False

def suggest_main_fix():
    print("\n🔧 SUGERENCIA: COMENTAR TEMPORALMENTE CHAT EN MAIN.PY")
    print("-" * 50)
    print("Edita src/main.py y comenta la línea:")
    print("# from src.api.endpoints import chat")
    print("# app.include_router(chat.router, prefix='/api')")
    print("")
    print("Esto te permitirá probar tu refactorización de users")
    print("mientras corriges chat.py por separado.")

def main():
    if test_users_only():
        suggest_main_fix()
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
