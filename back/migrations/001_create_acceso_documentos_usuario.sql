-- Crear tabla para gestionar el acceso compartido a documentos
CREATE TABLE IF NOT EXISTS acceso_documentos_usuario (
    id SERIAL PRIMARY KEY,
    id_document INTEGER NOT NULL,
    id_user INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    CONSTRAINT fk_document FOREIGN KEY (id_document) REFERENCES documents(id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY (id_user) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Evitar duplicados
    CONSTRAINT unique_document_user UNIQUE (id_document, id_user)
);

-- Crear índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_acceso_documentos_usuario_document ON acceso_documentos_usuario(id_document);
CREATE INDEX IF NOT EXISTS idx_acceso_documentos_usuario_user ON acceso_documentos_usuario(id_user);

-- Comentarios para documentación
COMMENT ON TABLE acceso_documentos_usuario IS 'Tabla para gestionar qué usuarios tienen acceso a qué documentos compartidos';
COMMENT ON COLUMN acceso_documentos_usuario.id_document IS 'ID del documento compartido';
COMMENT ON COLUMN acceso_documentos_usuario.id_user IS 'ID del usuario que tiene acceso al documento';
COMMENT ON COLUMN acceso_documentos_usuario.created_at IS 'Fecha cuando se compartió el documento';
