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
CREATE INDEX idx_email_change_attempts_user_id ON email_change_attempts(user_id);
CREATE INDEX idx_email_change_attempts_temp_token ON email_change_attempts(temp_token);
CREATE INDEX idx_email_change_attempts_status ON email_change_attempts(status);
CREATE INDEX idx_email_change_attempts_created_at ON email_change_attempts(created_at);

-- Función para limpiar intentos expirados (ejecutar periódicamente)
CREATE OR REPLACE FUNCTION cleanup_expired_email_change_attempts()
RETURNS void AS $$
BEGIN
    DELETE FROM email_change_attempts 
    WHERE status = 'pending' 
    AND expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Crear un job para limpiar automáticamente (si usas pg_cron)
-- SELECT cron.schedule('cleanup-email-attempts', '0 * * * *', 'SELECT cleanup_expired_email_change_attempts();');

-- Vista para monitorear intentos de cambio de email
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

-- Trigger para prevenir múltiples intentos activos
CREATE OR REPLACE FUNCTION check_active_email_change_attempts()
RETURNS TRIGGER AS $$
BEGIN
    -- Verificar si ya existe un intento activo para este usuario
    IF EXISTS (
        SELECT 1 FROM email_change_attempts 
        WHERE user_id = NEW.user_id 
        AND status = 'pending' 
        AND expires_at > CURRENT_TIMESTAMP
    ) THEN
        RAISE EXCEPTION 'Ya existe un intento de cambio de email activo para este usuario';
    END IF;
    
    -- Verificar límite de intentos fallidos en la última hora
    IF (
        SELECT COUNT(*) 
        FROM email_change_attempts 
        WHERE user_id = NEW.user_id 
        AND status = 'failed' 
        AND created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
    ) >= 5 THEN
        RAISE EXCEPTION 'Demasiados intentos fallidos. Intenta más tarde.';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER before_insert_email_change_attempt
    BEFORE INSERT ON email_change_attempts
    FOR EACH ROW
    EXECUTE FUNCTION check_active_email_change_attempts();

-- Comentarios para documentación
COMMENT ON TABLE email_change_attempts IS 'Registro de intentos de cambio de email con validación de existencia';
COMMENT ON COLUMN email_change_attempts.user_id IS 'ID del usuario que intenta cambiar su email';
COMMENT ON COLUMN email_change_attempts.new_email IS 'El nuevo email que el usuario quiere usar';
COMMENT ON COLUMN email_change_attempts.verification_code IS 'Código de 6 dígitos enviado al nuevo email';
COMMENT ON COLUMN email_change_attempts.temp_token IS 'Token único para identificar el intento';
COMMENT ON COLUMN email_change_attempts.status IS 'Estado del intento: pending, completed, failed';
COMMENT ON COLUMN email_change_attempts.failure_reason IS 'Razón del fallo si status=failed';
