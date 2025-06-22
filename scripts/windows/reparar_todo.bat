@echo off
echo ========================================
echo    REPARAR SISTEMA COMPLETO
echo ========================================
echo.

REM Verificar Docker
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker no está ejecutándose.
    echo Abre Docker Desktop primero.
    pause
    exit /b 1
)

echo Deteniendo servicios...
docker-compose down

echo.
echo Eliminando volúmenes antiguos...
docker-compose down -v

echo.
echo Reconstruyendo servicios...
docker-compose build --no-cache

echo.
echo Iniciando servicios...
docker-compose up -d

echo.
echo ========================================
echo REPARACIÓN COMPLETADA
echo.
echo Servicios en:
echo - http://localhost
echo - http://localhost:2690/docs
echo.
echo NOTA: Los documentos se han eliminado.
echo Deberás subirlos nuevamente.
echo ========================================
echo.
pause