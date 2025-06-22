"""
Script de debug temporal para verificar conteo de documentos compartidos.
Ejecutar desde el directorio back: python debug_shared_count.py
"""

import os
import sys
import logging
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.database import get_supabase_client
from src.services.statistics_service import StatisticsService

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_shared_documents():
    """Debug del conteo de documentos compartidos."""
    
    print("🔍 DEBUG: Verificando conteo de documentos compartidos")
    print("=" * 60)
    
    try:
        # Obtener cliente de Supabase
        service_client = get_supabase_client(use_service_role=True)
        
        # 1. Verificar todos los usuarios
        print("\n1. USUARIOS EN EL SISTEMA:")
        users_response = service_client.table('users').select('id, username, email').execute()
        if users_response.data:
            for user in users_response.data:
                print(f"   Usuario ID {user['id']}: {user['username']} ({user['email']})")
        
        # 2. Verificar todos los documentos
        print("\n2. DOCUMENTOS EN EL SISTEMA:")
        docs_response = service_client.table('documents').select('id, title, uploaded_by, is_shared').execute()
        if docs_response.data:
            for doc in docs_response.data:
                print(f"   Documento ID {doc['id']}: '{doc['title']}' - Propietario: {doc['uploaded_by']} - Compartido: {doc['is_shared']}")
        
        # 3. Verificar accesos compartidos
        print("\n3. ACCESOS COMPARTIDOS:")
        access_response = service_client.table('acceso_documentos_usuario').select('*').execute()
        if access_response.data:
            for access in access_response.data:
                print(f"   Documento {access['id_document']} compartido con usuario {access['id_user']}")
        else:
            print("   ❌ No hay accesos compartidos registrados")
        
        # 4. Probar función SQL optimizada
        print("\n4. PRUEBA DE FUNCIÓN SQL:")
        try:
            # Probar con cada usuario
            for user in users_response.data:
                user_id = user['id']
                try:
                    response = service_client.rpc('get_shared_documents_count', {'target_user_id': user_id}).execute()
                    count = response.data if response.data is not None else 0
                    print(f"   Usuario {user_id} ({user['username']}): {count} documentos compartidos")
                except Exception as e:
                    print(f"   ❌ Error con usuario {user_id}: {e}")
        except Exception as e:
            print(f"   ❌ Error ejecutando función SQL: {e}")
            print("   ℹ️  La función SQL puede no estar creada aún")
        
        # 5. Probar método fallback
        print("\n5. PRUEBA DE MÉTODO FALLBACK:")
        stats_service = StatisticsService()
        
        for user in users_response.data:
            user_id = user['id']
            try:
                count = stats_service._count_shared_documents_fallback(user_id)
                print(f"   Usuario {user_id} ({user['username']}): {count} documentos compartidos (fallback)")
            except Exception as e:
                print(f"   ❌ Error con método fallback para usuario {user_id}: {e}")
        
        # 6. Probar estadísticas completas
        print("\n6. ESTADÍSTICAS COMPLETAS:")
        for user in users_response.data:
            user_id = user['id']
            try:
                stats = stats_service.get_user_statistics(user_id)
                print(f"   Usuario {user_id} ({user['username']}):")
                print(f"     - Documentos propios: {stats['user_documents']}")
                print(f"     - Chats: {stats['user_chats']}")
                print(f"     - Documentos compartidos: {stats['shared_documents']}")
            except Exception as e:
                print(f"   ❌ Error obteniendo estadísticas para usuario {user_id}: {e}")
        
        print("\n✅ Debug completado")
        
    except Exception as e:
        print(f"❌ Error general en debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_shared_documents()
