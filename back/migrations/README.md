# Migraciones de Base de Datos

## Tabla: acceso_documentos_usuario

Esta tabla es necesaria para gestionar los documentos compartidos entre usuarios.

### Cómo ejecutar la migración:

1. **Opción 1: Desde el panel de Supabase**
   - Ve a tu proyecto en https://app.supabase.com
   - Ve a la sección "SQL Editor"
   - Copia y pega el contenido de `001_create_acceso_documentos_usuario.sql`
   - Ejecuta el script

2. **Opción 2: Usando la CLI de Supabase**
   ```bash
   supabase db push migrations/001_create_acceso_documentos_usuario.sql
   ```

### Estructura de la tabla:

- `id`: ID único del registro (auto-incremental)
- `id_document`: ID del documento compartido (foreign key a documents.id)
- `id_user`: ID del usuario que recibe acceso (foreign key a users.id)
- `created_at`: Timestamp de cuando se compartió el documento

### Características:

- Constraint único en (id_document, id_user) para evitar duplicados
- Índices en ambas columnas foreign key para mejorar performance
- Cascada en DELETE para limpiar automáticamente cuando se elimina un documento o usuario

### Verificar que la tabla existe:

```sql
SELECT * FROM information_schema.tables 
WHERE table_name = 'acceso_documentos_usuario';
```

### Ver registros existentes:

```sql
SELECT 
    adu.*,
    d.title as document_title,
    u.username as shared_with_user
FROM acceso_documentos_usuario adu
JOIN documents d ON d.id = adu.id_document
JOIN users u ON u.id = adu.id_user
ORDER BY adu.created_at DESC;
```
