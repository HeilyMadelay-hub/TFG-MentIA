@echo off
REM Script para solucionar problemas de indexación en ChromaDB
REM Ejecutar desde el directorio chabot\back

echo ===============================================
echo   SOLUCIONADOR DE PROBLEMAS DE INDEXACION
echo ===============================================
echo.

REM Verificar que estamos en el directorio correcto
if not exist "tests\reindex_documents.py" (
    echo ERROR: Este script debe ejecutarse desde el directorio 'back'
    echo Por favor, navegue a: chabot\back
    pause
    exit /b 1
)

echo Seleccione una opcion:
echo.
echo 1. Ver estado del sistema
echo 2. Diagnosticar problemas de indexacion
echo 3. Re-indexar documentos especificos (54, 56)
echo 4. Re-indexar TODOS los documentos
echo 5. Solucion automatica completa
echo 6. Salir
echo.

set /p opcion="Ingrese el numero de opcion: "

if "%opcion%"=="1" (
    echo.
    echo Verificando estado del sistema...
    python tests\system_status.py
    pause
    goto :eof
)

if "%opcion%"=="2" (
    echo.
    echo Ejecutando diagnostico...
    python tests\debug_chromadb.py
    pause
    goto :eof
)

if "%opcion%"=="3" (
    echo.
    echo Re-indexando documentos 54 y 56...
    python tests\reindex_documents.py
    pause
    goto :eof
)

if "%opcion%"=="4" (
    echo.
    echo Re-indexando TODOS los documentos...
    python tests\reindex_all_documents.py
    pause
    goto :eof
)

if "%opcion%"=="5" (
    echo.
    echo Ejecutando solucion automatica...
    python tests\fix_indexing_auto.py
    pause
    goto :eof
)

if "%opcion%"=="6" (
    exit /b 0
)

echo.
echo Opcion invalida. Por favor, seleccione 1-6.
pause
