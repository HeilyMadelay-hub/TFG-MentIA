-- ===============================================
-- VERIFICACIÓN SIMPLE - FUNCIONES YA EXISTENTES
-- ===============================================

-- 1. Verificar qué funciones existen
SELECT 
    routine_name as function_name,
    routine_type as type
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND (routine_name LIKE '%shared%' OR routine_name LIKE '%user_sharing%')
ORDER BY routine_name;

-- ===============================================
-- 2. PROBAR FUNCIÓN PRINCIPAL CON IVAN (ID: 19)
-- ===============================================

-- Probar get_user_sharing_stats para Ivan
SELECT 'Estadísticas de Ivan (ID: 19):' as test;
SELECT * FROM get_user_sharing_stats(19);

-- ===============================================
-- 3. VER DATOS ACTUALES DE IVAN
-- ===============================================

-- Ver documentos de Ivan
SELECT 
    'Documentos de Ivan:' as info,
    COUNT(*) as total_documentos
FROM documents 
WHERE uploaded_by = 19;

-- Ver documentos de Ivan que están compartidos
SELECT 
    'Documentos de Ivan compartidos:' as info,
    COUNT(DISTINCT d.id) as documentos_compartidos
FROM documents d
INNER JOIN acceso_documentos_usuario adu ON d.id = adu.id_document
WHERE d.uploaded_by = 19;

-- Ver detalles de compartición de Ivan
SELECT 
    d.id as doc_id,
    d.title,
    COUNT(adu.id_user) as compartido_con_usuarios,
    STRING_AGG(u.username, ', ') as usuarios
FROM documents d
JOIN acceso_documentos_usuario adu ON d.id = adu.id_document
JOIN users u ON adu.id_user = u.id
WHERE d.uploaded_by = 19
GROUP BY d.id, d.title
ORDER BY d.id;

-- ===============================================
-- 4. VERIFICAR CONTEO CORRECTO
-- ===============================================

-- Conteo manual para comparar
SELECT 
    'Verificación manual:' as tipo,
    (SELECT COUNT(DISTINCT d.id)
     FROM documents d
     INNER JOIN acceso_documentos_usuario adu ON d.id = adu.id_document
     WHERE d.uploaded_by = 19) as conteo_manual,
    get_documents_shared_by_user(19) as funcion_resultado
;

-- ===============================================
-- 5. SI LAS FUNCIONES NO EXISTEN, EJECUTAR ESTO:
-- ===============================================

-- Solo ejecutar si las funciones no aparecen arriba

/* 
CREATE OR REPLACE FUNCTION get_documents_shared_by_user(user_id INTEGER)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    shared_count INTEGER;
BEGIN
    -- Contar documentos del usuario que tienen accesos compartidos
    SELECT COUNT(DISTINCT d.id)
    INTO shared_count
    FROM documents d
    INNER JOIN acceso_documentos_usuario adu ON d.id = adu.id_document
    WHERE d.uploaded_by = user_id;
    
    RETURN COALESCE(shared_count, 0);
END;
$$;

CREATE OR REPLACE FUNCTION get_user_sharing_stats(user_id INTEGER)
RETURNS TABLE(
    documents_shared_by_me INTEGER,
    documents_shared_with_me INTEGER,
    total_users_i_shared_with INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        -- Documentos que YO he compartido
        (SELECT COUNT(DISTINCT d.id)
         FROM documents d
         INNER JOIN acceso_documentos_usuario adu ON d.id = adu.id_document
         WHERE d.uploaded_by = user_id)::INTEGER as documents_shared_by_me,
        
        -- Documentos compartidos CONMIGO
        (SELECT COUNT(DISTINCT adu.id_document)
         FROM acceso_documentos_usuario adu
         INNER JOIN documents d ON adu.id_document = d.id
         WHERE adu.id_user = user_id 
         AND d.uploaded_by != user_id)::INTEGER as documents_shared_with_me,
        
        -- Número de usuarios únicos con los que he compartido
        (SELECT COUNT(DISTINCT adu.id_user)
         FROM documents d
         INNER JOIN acceso_documentos_usuario adu ON d.id = adu.id_document
         WHERE d.uploaded_by = user_id)::INTEGER as total_users_i_shared_with;
END;
$$;

-- Dar permisos
GRANT EXECUTE ON FUNCTION get_documents_shared_by_user(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION get_documents_shared_by_user(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_sharing_stats(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION get_user_sharing_stats(INTEGER) TO authenticated;
*/