@echo off
REM Script de emergencia para problemas de indexación
REM Ejecuta la solución automática directamente

echo.
echo ============================================
echo    SOLUCIONADOR DE EMERGENCIA - CHROMADB
echo ============================================
echo.
echo Ejecutando solucion automatica...
echo.

cd /d "%~dp0"
python tests\fix_indexing_auto.py

echo.
echo ============================================
echo.
echo Si el problema persiste:
echo 1. Reinicia Docker Desktop
echo 2. Ejecuta: docker-compose restart chromadb
echo 3. Vuelve a ejecutar este script
echo.
pause
