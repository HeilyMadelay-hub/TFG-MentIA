"""
Script para verificar y crear las columnas necesarias para el reset de contraseña
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import get_supabase_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_and_fix_database():
    """
    Verifica que la tabla users tenga todas las columnas necesarias
    """
    try:
        supabase = get_supabase_client(use_service_role=True)
        
        logger.info("🔍 Verificando estructura de la tabla users...")
        
        # Obtener un usuario de ejemplo para ver las columnas
        response = supabase.table("users").select("*").limit(1).execute()
        
        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            columns = list(user_data.keys())
            logger.info(f"Columnas actuales: {columns}")
            
            # Verificar columnas necesarias para reset
            required_columns = ['reset_token', 'reset_token_expires']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                logger.warning(f"⚠️ Faltan columnas: {missing_columns}")
                logger.info("Debes agregar estas columnas en Supabase Dashboard:")
                for col in missing_columns:
                    if col == 'reset_token':
                        logger.info(f"  - {col}: tipo TEXT, puede ser NULL")
                    elif col == 'reset_token_expires':
                        logger.info(f"  - {col}: tipo TIMESTAMP WITH TIME ZONE, puede ser NULL")
            else:
                logger.info("✅ Todas las columnas necesarias están presentes")
                
            # Verificar si hay algún usuario con reset token
            test_response = supabase.table("users")\
                .select("id, username, reset_token, reset_token_expires")\
                .not_.is_("reset_token", "null")\
                .execute()
                
            if test_response.data:
                logger.info(f"📊 Usuarios con reset tokens activos: {len(test_response.data)}")
                for user in test_response.data:
                    logger.info(f"  - {user['username']}: token expira en {user.get('reset_token_expires', 'N/A')}")
        else:
            logger.warning("No hay usuarios en la base de datos")
            
    except Exception as e:
        logger.error(f"Error verificando base de datos: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def test_password_update():
    """
    Prueba actualizar una contraseña directamente
    """
    try:
        supabase = get_supabase_client(use_service_role=True)
        
        # Buscar un usuario de prueba
        response = supabase.table("users")\
            .select("id, username, password_hash")\
            .eq("username", "test")\
            .execute()
            
        if response.data and len(response.data) > 0:
            user = response.data[0]
            logger.info(f"🧪 Usuario de prueba encontrado: {user['username']}")
            logger.info(f"   Hash actual: {user['password_hash'][:20]}...")
            
            # Intentar actualizar
            from src.utils.password_utils import hash_password
            new_hash = hash_password("test_password_123")
            
            update_response = supabase.table("users")\
                .update({"password_hash": new_hash})\
                .eq("id", user['id'])\
                .execute()
                
            if update_response.data:
                logger.info("✅ Actualización exitosa")
                
                # Verificar
                verify_response = supabase.table("users")\
                    .select("password_hash")\
                    .eq("id", user['id'])\
                    .execute()
                    
                if verify_response.data:
                    saved_hash = verify_response.data[0]['password_hash']
                    if saved_hash == new_hash:
                        logger.info("✅ Verificación: La contraseña se guardó correctamente")
                    else:
                        logger.error("❌ ERROR: La contraseña NO se guardó correctamente")
        else:
            logger.info("No se encontró usuario 'test'. Puedes crear uno para pruebas.")
            
    except Exception as e:
        logger.error(f"Error en prueba: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("=== VERIFICACIÓN DE BASE DE DATOS ===")
    verify_and_fix_database()
    logger.info("\n=== PRUEBA DE ACTUALIZACIÓN DE CONTRASEÑA ===")
    test_password_update()
    logger.info("\n✅ Verificación completada")
