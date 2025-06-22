# Scripts de Testing y Diagnóstico

Este directorio contiene scripts de utilidad para diagnosticar y solucionar problemas comunes del sistema.

## 🔧 Scripts de ChromaDB y Indexación

### `check_chromadb.py`
**Propósito:** Verificar si ChromaDB está funcionando correctamente  
**Uso:** `python tests/check_chromadb.py`  
**Cuándo usarlo:** Cuando sospechas que ChromaDB no está respondiendo

### `debug_chromadb.py`
**Propósito:** Diagnóstico completo del estado de indexación  
**Uso:** `python tests/debug_chromadb.py`  
**Cuándo usarlo:** Para ver cuántos documentos están indexados y su estado

### `reindex_documents.py`
**Propósito:** Re-indexar documentos específicos en ChromaDB  
**Uso:** `python tests/reindex_documents.py`  
**Cuándo usarlo:** Cuando los documentos no devuelven resultados en las búsquedas

### `fix_indexing_auto.py` 🆕
**Propósito:** Solución automática de problemas de indexación  
**Uso:** `python tests/fix_indexing_auto.py`  
**Cuándo usarlo:** Para diagnosticar y solucionar automáticamente problemas de indexación

### `verify_refactorization.py`
**Propósito:** Verificar que toda la refactorización esté funcionando  
**Uso:** `python tests/verify_refactorization.py`  
**Cuándo usarlo:** Después de cambios importantes en el código

## 📋 Orden de Ejecución para Solucionar Problemas

### Método Manual:
1. `check_chromadb.py` - Verificar conexión
2. `debug_chromadb.py` - Diagnosticar estado
3. `reindex_documents.py` - Re-indexar si es necesario
4. `verify_refactorization.py` - Verificación final

### Método Automático:
```bash
python tests/fix_indexing_auto.py
```

## ⚠️ IMPORTANTE

**SIEMPRE ejecutar desde el directorio `back`:**
```bash
cd C:\Users\heily\Desktop\chabot\back
python tests/nombre_del_script.py
```

**NO ejecutar desde el directorio `tests`:**
```bash
# ❌ INCORRECTO
cd tests
python nombre_del_script.py
```

## 🚨 Problemas Comunes y Soluciones

### Error: "No module named 'src'"
**Causa:** Ejecutando desde el directorio incorrecto  
**Solución:** Ejecutar desde el directorio `back`

### Error: "ChromaDB código 410"
**Causa:** API v1 deprecated  
**Solución:** Normal en versiones nuevas, el sistema funciona con v2

### Error: "No se encontraron documentos relevantes"
**Causa:** Documentos no indexados en ChromaDB  
**Solución:** Ejecutar `reindex_documents.py` o `fix_indexing_auto.py`

## 🛠️ Otros Scripts de Testing

### Base de Datos
- `test_supabase.py` - Pruebas de conexión con Supabase
- `conftest.py` - Configuración de pytest

### Autenticación
- `test_auth.py` - Pruebas del sistema de autenticación

### Documentos
- `test_documents.py` - Pruebas de gestión de documentos
- `debug_shared_count.py` - Debug de conteo de documentos compartidos
- `test_imports_simple.py` - Verificación de imports

### Chat
- `test_chat.py` - Pruebas del sistema de chat
- `test_websocket_integration.py` - Pruebas de WebSocket

### Seguridad
- `test_security_config.py` - Verificación de configuración de seguridad

### Utilidades
- `test_ai_connector.py` - Pruebas del conector de IA
- `test_endpoints_quick.py` - Verificación rápida de endpoints
- `test_simple.py` - Pruebas simples del sistema
- `test_solo_users.py` - Pruebas aisladas de usuarios
- `test_ultra_simple.py` - Pruebas ultra simplificadas

## 📊 Métricas de Éxito

Después de ejecutar los scripts de solución:
- ChromaDB debe responder (aunque sea con código 410)
- Debe haber chunks > 0 en la colección
- Las búsquedas deben devolver resultados
- El chat debe responder preguntas sobre documentos

## 🐛 Debugging Avanzado

Para más información detallada, revisa:
- Logs de Docker: `docker logs chromadb`
- Logs del backend: `docker logs backend`
- Archivo de troubleshooting: `docs/GUIA_TROUBLESHOOTING_CHROMADB.md`
