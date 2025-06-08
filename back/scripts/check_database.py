"""
Script para verificar y crear la tabla acceso_documentos_usuario si no existe.
Ejecutar este script antes de iniciar la aplicación.
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from src.config.database import get_supabase_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_and_create_table():
    """Verifica si la tabla existe y la crea si es necesario."""
    try:
        # Obtener cliente con permisos de servicio
        supabase = get_supabase_client(use_service_role=True)
        
        # Verificar si la tabla existe
        logger.info("🔍 Verificando si existe la tabla acceso_documentos_usuario...")
        
        try:
            # Intentar hacer una consulta simple
            response = supabase.table("acceso_documentos_usuario").select("id").limit(1).execute()
            logger.info("✅ La tabla acceso_documentos_usuario ya existe")
            return True
        except Exception as e:
            logger.warning(f"❌ La tabla no existe o hay un error: {str(e)}")
            logger.info("📝 Creando la tabla acceso_documentos_usuario...")
            
            # SQL para crear la tabla
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS acceso_documentos_usuario (
                id SERIAL PRIMARY KEY,
                id_document INTEGER NOT NULL,
                id_user INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                
                CONSTRAINT fk_document FOREIGN KEY (id_document) REFERENCES documents(id) ON DELETE CASCADE,
                CONSTRAINT fk_user FOREIGN KEY (id_user) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT unique_document_user UNIQUE (id_document, id_user)
            );
            
            CREATE INDEX IF NOT EXISTS idx_acceso_documentos_usuario_document ON acceso_documentos_usuario(id_document);
            CREATE INDEX IF NOT EXISTS idx_acceso_documentos_usuario_user ON acceso_documentos_usuario(id_user);
            """
            
            # Nota: Supabase Python client no tiene método directo para ejecutar SQL raw
            # Por lo que necesitarás ejecutar este SQL manualmente en el dashboard de Supabase
            
            logger.error("⚠️  IMPORTANTE: La tabla no existe en Supabase.")
            logger.error("📋 Por favor, ejecuta el siguiente SQL en tu dashboard de Supabase:")
            logger.error("-" * 80)
            print(create_table_sql)
            logger.error("-" * 80)
            logger.error("🔗 Ve a: https://app.supabase.com → SQL Editor → Nueva consulta")
            logger.error("📝 Pega el SQL anterior y ejecuta")
            logger.error("✅ Luego vuelve a ejecutar este script para verificar")
            
            return False
            
    except Exception as e:
        logger.error(f"Error general: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== Verificador de Tabla acceso_documentos_usuario ===")
    
    if check_and_create_table():
        logger.info("✅ Todo listo! La tabla existe y está configurada correctamente.")
    else:
        logger.error("❌ Necesitas crear la tabla manualmente en Supabase antes de continuar.")
        sys.exit(1)
