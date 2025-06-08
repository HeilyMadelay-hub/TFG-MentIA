"""
Script de prueba completa del sistema de reset de contraseña

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from datetime import datetime
from src.services.user_service import UserService
from src.services.email_service import email_service
from src.models.schemas.user import UserCreate
from src.config.database import get_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_complete_reset_flow():
  
    Prueba el flujo completo de reset de contraseña
  
    user_service = UserService()
    test_email = "test_reset@example.com"
    test_username = "testresetuser"  # Sin guiones bajos
    
    logger.info("=== INICIANDO PRUEBA COMPLETA DE RESET DE CONTRASEÑA ===\n")
    
    try:
        # 1. Crear usuario de prueba o usar existente
        logger.info("1️⃣ Buscando o creando usuario de prueba...")
        user = user_service.get_user_by_email(test_email)
        
        if not user:
            logger.info("   Usuario no existe, creando...")
            user_data = UserCreate(
                username=test_username,
                email=test_email,
                password="password123"
            )
            user = user_service.create_user(user_data)
            logger.info(f"   ✅ Usuario creado: {user.username} ({user.email})")
        else:
            logger.info(f"   ✅ Usuario existente encontrado: {user.username}")
        
        # 2. Solicitar reset de contraseña
        logger.info("\n2️⃣ Solicitando reset de contraseña...")
        success = user_service.request_password_reset(test_email)
        
        if success:
            logger.info("   ✅ Solicitud de reset procesada")
            
            # Verificar que se guardó el token
            supabase = get_supabase_client(use_service_role=True)
            response = supabase.table("users")\
                .select("reset_token, reset_token_expires")\
                .eq("id", user.id)\
                .execute()
            
            if response.data and response.data[0]['reset_token']:
                logger.info(f"   ✅ Token guardado en BD")
                logger.info(f"   Token hash: {response.data[0]['reset_token'][:20]}...")
                logger.info(f"   Expira: {response.data[0]['reset_token_expires']}")
            else:
                logger.error("   ❌ Token NO se guardó en la base de datos")
        else:
            logger.error("   ❌ Error en solicitud de reset")
            
        # 3. Probar envío de email manualmente
        logger.info("\n3️⃣ Probando envío de email...")
        email_sent = email_service.send_password_reset_email(
            to_email=test_email,
            username=user.username,
            reset_token="test_token_123"
        )
        
        if email_sent:
            logger.info("   ✅ Email enviado (o simulado si SMTP no está configurado)")
        else:
            logger.error("   ❌ Error enviando email")
            
        # 4. Simular reset de contraseña
        logger.info("\n4️⃣ Simulando reset de contraseña...")
        
        # Obtener el token real de la BD
        response = supabase.table("users")\
            .select("reset_token")\
            .eq("id", user.id)\
            .execute()
            
        if response.data and response.data[0]['reset_token']:
            # Para la prueba, necesitamos el token sin hashear
            # Como no lo tenemos, vamos a generar uno nuevo para la prueba
            import secrets
            test_token = secrets.token_urlsafe(32)
            
            # Guardar el hash del token de prueba
            import hashlib
            token_hash = hashlib.sha256(test_token.encode()).hexdigest()
            
            update_response = supabase.table("users")\
                .update({"reset_token": token_hash})\
                .eq("id", user.id)\
                .execute()
                
            if update_response.data:
                logger.info("   Token de prueba guardado")
                
                # Intentar reset
                new_password = "nueva_password_123"
                reset_success = user_service.reset_password(test_token, new_password)
                
                if reset_success:
                    logger.info("   ✅ Contraseña actualizada exitosamente")
                    
                    # Verificar que se puede hacer login con nueva contraseña
                    authenticated = user_service.authenticate_user(user.username, new_password)
                    if authenticated:
                        logger.info("   ✅ Login exitoso con nueva contraseña")
                    else:
                        logger.error("   ❌ No se puede hacer login con nueva contraseña")
                else:
                    logger.error("   ❌ Error al actualizar contraseña")
        
        # 5. Limpiar usuario de prueba (opcional)
        logger.info("\n5️⃣ Limpieza...")
        # user_service.delete_user(user.id)
        logger.info("   ℹ️  Usuario de prueba mantenido para futuras pruebas")
        
    except Exception as e:
        logger.error(f"❌ Error en prueba: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("\n=== PRUEBA COMPLETADA ===")

def test_email_config():
    
    Prueba la configuración de email
 
    logger.info("\n=== VERIFICANDO CONFIGURACIÓN DE EMAIL ===")
    logger.info(f"SMTP Host: {email_service.smtp_host}")
    logger.info(f"SMTP Port: {email_service.smtp_port}")
    logger.info(f"SMTP User: {email_service.smtp_user[:5]}..." if email_service.smtp_user else "SMTP User: No configurado")
    logger.info(f"From Email: {email_service.from_email}")
    
    if not email_service.smtp_user or not email_service.smtp_password:
        logger.warning("⚠️  SMTP no está completamente configurado - los emails serán simulados")
    else:
        logger.info("✅ SMTP configurado correctamente")

if __name__ == "__main__":
    # Primero verificar configuración
    test_email_config()
    
    # Luego ejecutar prueba completa
    asyncio.run(test_complete_reset_flow())
"""