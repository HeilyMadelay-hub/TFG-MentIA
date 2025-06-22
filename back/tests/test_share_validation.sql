-- ===============================================
-- PRUEBAS DE VALIDACIÓN DE COMPARTIR DOCUMENTOS
-- ===============================================

-- 1. Crear usuarios de prueba si no existen
INSERT INTO users (username, email, password_hash, auth_id, is_admin)
VALUES 
    ('test_owner', 'owner@test.com', '$2b$12$dummy_hash', gen_random_uuid(), false),
    ('test_user1', 'user1@test.com', '$2b$12$dummy_hash', gen_random_uuid(), false),
    ('test_user2', 'user2@test.com', '$2b$12$dummy_hash', gen_random_uuid(), false),
    ('test_user3', 'user3@test.com', '$2b$12$dummy_hash', gen_random_uuid(), false)
ON CONFLICT (username) DO NOTHING;

-- 2. Obtener IDs de usuarios
SELECT id, username FROM users 
WHERE username IN ('test_owner', 'test_user1', 'test_user2', 'test_user3');

-- 3. Crear documento de prueba (ajustar uploaded_by con el ID del test_owner)
INSERT INTO documents (title, uploaded_by, content_type, content, status)
SELECT 
    'Documento de Prueba Compartir ' || NOW()::TEXT,
    id,
    'text/plain',
    'Este es un documento de prueba para validar la funcionalidad de compartir.',
    'completed'
FROM users 
WHERE username = 'test_owner'
RETURNING id, title;

-- 4. Obtener el ID del documento recién creado
-- NOTA: Guardar este ID para las siguientes pruebas
WITH last_doc AS (
    SELECT id, title 
    FROM documents 
    WHERE title LIKE 'Documento de Prueba Compartir%' 
    ORDER BY created_at DESC 
    LIMIT 1
)
SELECT * FROM last_doc;

-- ===============================================
-- PRUEBA 1: Primera vez compartiendo
-- ===============================================

-- Verificar estado inicial (nadie tiene acceso)
SELECT 
    d.id,
    d.title,
    d.is_shared,
    COUNT(adu.id_user) as usuarios_con_acceso
FROM documents d
LEFT JOIN acceso_documentos_usuario adu ON d.id = adu.id_document
WHERE d.title LIKE 'Documento de Prueba Compartir%'
GROUP BY d.id, d.title, d.is_shared
ORDER BY d.created_at DESC
LIMIT 1;

-- Compartir con test_user1 y test_user2
-- NOTA: Reemplazar los IDs con los valores reales
INSERT INTO acceso_documentos_usuario (id_document, id_user)
SELECT 
    (SELECT id FROM documents WHERE title LIKE 'Documento de Prueba Compartir%' ORDER BY created_at DESC LIMIT 1),
    u.id
FROM users u
WHERE u.username IN ('test_user1', 'test_user2');

-- Verificar que se compartió correctamente
SELECT 
    adu.id_document,
    d.title,
    u.username,
    adu.created_at as compartido_desde
FROM acceso_documentos_usuario adu
JOIN documents d ON adu.id_document = d.id
JOIN users u ON adu.id_user = u.id
WHERE d.title LIKE 'Documento de Prueba Compartir%'
ORDER BY adu.created_at DESC;

-- ===============================================
-- PRUEBA 2: Intentar compartir de nuevo (duplicados)
-- ===============================================

-- Intentar insertar duplicado (debería fallar o ser ignorado)
DO $$
DECLARE
    doc_id INTEGER;
    user_id INTEGER;
BEGIN
    -- Obtener IDs
    SELECT id INTO doc_id FROM documents 
    WHERE title LIKE 'Documento de Prueba Compartir%' 
    ORDER BY created_at DESC LIMIT 1;
    
    SELECT id INTO user_id FROM users WHERE username = 'test_user1';
    
    -- Intentar insertar duplicado
    BEGIN
        INSERT INTO acceso_documentos_usuario (id_document, id_user)
        VALUES (doc_id, user_id);
        RAISE NOTICE 'ERROR: Se permitió insertar duplicado!';
    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE 'OK: Constraint único funcionando correctamente';
    END;
END $$;

-- ===============================================
-- PRUEBA 3: Validar usuarios con acceso existente
-- ===============================================

-- Consulta que simula get_existing_shares
WITH test_doc AS (
    SELECT id FROM documents 
    WHERE title LIKE 'Documento de Prueba Compartir%' 
    ORDER BY created_at DESC LIMIT 1
),
test_users AS (
    SELECT id FROM users 
    WHERE username IN ('test_user1', 'test_user2', 'test_user3')
)
SELECT 
    u.id,
    u.username,
    u.email,
    CASE 
        WHEN adu.id_user IS NOT NULL THEN 'Ya tiene acceso'
        ELSE 'No tiene acceso'
    END as estado,
    adu.created_at as compartido_desde
FROM test_users tu
JOIN users u ON tu.id = u.id
LEFT JOIN acceso_documentos_usuario adu 
    ON adu.id_user = u.id 
    AND adu.id_document = (SELECT id FROM test_doc);

-- ===============================================
-- PRUEBA 4: Verificar actualización de is_shared
-- ===============================================

-- Verificar que is_shared está en TRUE
SELECT 
    id,
    title,
    is_shared,
    (SELECT COUNT(*) FROM acceso_documentos_usuario WHERE id_document = d.id) as accesos
FROM documents d
WHERE title LIKE 'Documento de Prueba Compartir%'
ORDER BY created_at DESC
LIMIT 1;

-- ===============================================
-- PRUEBA 5: Revocar acceso y verificar is_shared
-- ===============================================

-- Eliminar todos los accesos
DELETE FROM acceso_documentos_usuario
WHERE id_document = (
    SELECT id FROM documents 
    WHERE title LIKE 'Documento de Prueba Compartir%' 
    ORDER BY created_at DESC LIMIT 1
);

-- Verificar que is_shared se actualizó a FALSE (si el trigger está activo)
SELECT 
    id,
    title,
    is_shared,
    (SELECT COUNT(*) FROM acceso_documentos_usuario WHERE id_document = d.id) as accesos
FROM documents d
WHERE title LIKE 'Documento de Prueba Compartir%'
ORDER BY created_at DESC
LIMIT 1;

-- ===============================================
-- LIMPIEZA (OPCIONAL)
-- ===============================================

-- Eliminar documento de prueba
/*
DELETE FROM documents 
WHERE title LIKE 'Documento de Prueba Compartir%';

-- Eliminar usuarios de prueba
DELETE FROM users 
WHERE username IN ('test_owner', 'test_user1', 'test_user2', 'test_user3');
*/

-- ===============================================
-- CONSULTAS ÚTILES PARA DEBUGGING
-- ===============================================

-- Ver todos los accesos compartidos
SELECT 
    d.id as doc_id,
    d.title,
    d.uploaded_by,
    u1.username as owner,
    d.is_shared,
    array_agg(u2.username) as shared_with
FROM documents d
JOIN users u1 ON d.uploaded_by = u1.id
LEFT JOIN acceso_documentos_usuario adu ON d.id = adu.id_document
LEFT JOIN users u2 ON adu.id_user = u2.id
GROUP BY d.id, d.title, d.uploaded_by, u1.username, d.is_shared
ORDER BY d.created_at DESC
LIMIT 10;

-- Verificar constraint único
SELECT 
    tc.constraint_name,
    tc.table_name,
    array_agg(kcu.column_name) as columns
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'acceso_documentos_usuario'
    AND tc.constraint_type = 'UNIQUE'
GROUP BY tc.constraint_name, tc.table_name;
