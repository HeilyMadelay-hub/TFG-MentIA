"""
Script para crear la tabla email_change_attempts en Supabase
Esta tabla almacena los intentos de cambio de email con validación
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import sys

# Cargar variables de entorno
load_dotenv()

# Configuración de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Error: SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY no están configurados")
    sys.exit(1)

# Crear cliente con service role key para tener permisos completos
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

print("📊 Creando tabla email_change_attempts...")

# SQL para crear la tabla
create_table_sql = """
-- Tabla para almacenar intentos de cambio de email con validación
CREATE TABLE IF NOT EXISTS email_change_attempts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    new_email VARCHAR(255) NOT NULL,
    verification_code VARCHAR(6) NOT NULL,
    temp_token UUID NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, completed, failed
    failure_reason VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    failed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_email_change_attempts_user_id ON email_change_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_email_change_attempts_temp_token ON email_change_attempts(temp_token);
CREATE INDEX IF NOT EXISTS idx_email_change_attempts_status ON email_change_attempts(status);
CREATE INDEX IF NOT EXISTS idx_email_change_attempts_created_at ON email_change_attempts(created_at);

-- Función para limpiar intentos expirados
CREATE OR REPLACE FUNCTION cleanup_expired_email_change_attempts()
RETURNS void AS $$
BEGIN
    DELETE FROM email_change_attempts 
    WHERE status = 'pending' 
    AND expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Vista para monitorear intentos
CREATE OR REPLACE VIEW email_change_attempts_stats AS
SELECT 
    user_id,
    COUNT(*) as total_attempts,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_attempts,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_attempts,
    MAX(created_at) as last_attempt
FROM email_change_attempts
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY user_id;
"""

try:
    # Ejecutar SQL directamente usando la API de Supabase
    # Nota: Supabase Python Client no tiene método directo para ejecutar SQL crudo
    # Así que verificaremos si la tabla existe primero
    
    # Intentar hacer una consulta simple a la tabla
    try:
        result = supabase.table('email_change_attempts').select("count").execute()
        print("✅ La tabla email_change_attempts ya existe")
    except:
        print("❌ La tabla no existe. Por favor, ejecuta el SQL manualmente en el panel de Supabase:")
        print("\n" + "="*60)
        print(create_table_sql)
        print("="*60 + "\n")
        print("📝 Pasos:")
        print("1. Ve a tu proyecto en https://app.supabase.com")
        print("2. Ve a SQL Editor")
        print("3. Pega el SQL anterior y ejecuta")
        print("4. La tabla se creará con todos los índices necesarios")
        
    # Configurar políticas RLS (Row Level Security)
    print("\n🔒 Configurando políticas RLS...")
    
    rls_policies_sql = """
    -- Habilitar RLS
    ALTER TABLE email_change_attempts ENABLE ROW LEVEL SECURITY;
    
    -- Política: Los usuarios solo pueden ver sus propios intentos
    CREATE POLICY "Users can view own attempts" ON email_change_attempts
        FOR SELECT
        USING (auth.uid()::text = (SELECT email FROM users WHERE id = user_id));
    
    -- Política: Solo el backend (service role) puede insertar
    CREATE POLICY "Service role can insert" ON email_change_attempts
        FOR INSERT
        WITH CHECK (auth.role() = 'service_role');
    
    -- Política: Solo el backend puede actualizar
    CREATE POLICY "Service role can update" ON email_change_attempts
        FOR UPDATE
        USING (auth.role() = 'service_role')
        WITH CHECK (auth.role() = 'service_role');
    
    -- Política: Solo el backend puede eliminar
    CREATE POLICY "Service role can delete" ON email_change_attempts
        FOR DELETE
        USING (auth.role() = 'service_role');
    """
    
    print("\n📝 También ejecuta estas políticas RLS:")
    print("\n" + "="*60)
    print(rls_policies_sql)
    print("="*60 + "\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print("\n✅ Proceso completado")
print("\n📊 Información adicional:")
print("- La tabla almacena intentos de cambio de email con validación")
print("- Los intentos expiran después de 5 minutos")
print("- Se limitan a 5 intentos fallidos por hora por usuario")
print("- Los códigos de verificación son de 6 dígitos")
