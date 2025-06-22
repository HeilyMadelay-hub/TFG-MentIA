@echo off
echo ========================================
echo     INICIANDO CHATBOT CON DOCKER
echo ========================================
echo.

REM Detener servicios anteriores
echo Deteniendo servicios anteriores...
docker-compose down

REM Limpiar volúmenes si es necesario (comentar si no quieres perder datos)
REM docker-compose down -v

echo.
echo Construyendo imágenes...
docker-compose build --no-cache backend

echo.
echo Iniciando servicios...
docker-compose up -d

echo.
echo Esperando a que los servicios estén listos...
timeout /t 10 /nobreak > nul

echo.
echo Verificando estado de los servicios...
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo ========================================
echo Servicios disponibles en:
echo ========================================
echo   Frontend:  http://localhost
echo   Backend:   http://localhost:2690/docs
echo   ChromaDB:  http://localhost:8050
echo ========================================

echo.
echo Verificando salud del backend...
curl -s http://localhost:2690/health || echo Backend aún no está listo

echo.
echo Para ver los logs del backend:
echo   docker logs -f chabot-backend
echo.
echo Para diagnosticar problemas:
echo   python check_docker_services.py
echo.
pause
