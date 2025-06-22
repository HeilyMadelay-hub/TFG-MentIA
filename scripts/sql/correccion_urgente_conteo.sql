-- ===============================================
-- CORRECCIÓN URGENTE: CONTAR TOTAL DE COMPARTICIONES
-- ===============================================

-- La función actual cuenta documentos únicos, necesitamos contar comparticiones totales

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
        -- CAMBIO CRÍTICO: Contar TOTAL de comparticiones, no documentos únicos
        (SELECT COUNT(adu.id)
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
GRANT EXECUTE ON FUNCTION get_user_sharing_stats(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION get_user_sharing_stats(INTEGER) TO authenticated;

-- ===============================================
-- VERIFICACIÓN INMEDIATA
-- ===============================================

-- Probar con Ivan después de la corrección
SELECT * FROM get_user_sharing_stats(19);

-- Ver detalles exactos
SELECT 
    d.id as doc_id,
    d.title,
    COUNT(adu.id_user) as total_comparticiones,
    STRING_AGG(adu.id_user::TEXT, ', ') as usuarios_ids
FROM documents d
JOIN acceso_documentos_usuario adu ON d.id = adu.id_document
WHERE d.uploaded_by = 19
GROUP BY d.id, d.title
ORDER BY d.id;

-- Conteo total manual para verificar
SELECT 
    'Total comparticiones de Ivan:' as descripcion,
    COUNT(adu.id) as total_shares
FROM documents d
INNER JOIN acceso_documentos_usuario adu ON d.id = adu.id_document
WHERE d.uploaded_by = 19;