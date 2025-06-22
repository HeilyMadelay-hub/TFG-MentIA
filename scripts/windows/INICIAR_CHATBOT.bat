@echo off
echo.
echo ============================
echo   INICIANDO CHATBOT
echo ============================
echo.

echo 1. Levantando servicios Docker...
docker-compose up -d

echo.
echo 2. Esperando 60 segundos para que todo inicie...
timeout /t 60

echo.
echo 3. Abriendo navegador...
start http://localhost:3690

echo.
echo ============================
echo   CHATBOT INICIADO!
echo ============================
echo.
echo Frontend: http://localhost:3690
echo Backend:  http://localhost:2690
echo ChromaDB: http://localhost:8050
echo.
echo Para apagar: docker-compose down
echo.
pause
