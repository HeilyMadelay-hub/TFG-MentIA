@echo off
echo 🔧 SOLUCIONANDO PROBLEMA DE PUERTO OCUPADO
echo =============================================
echo.

echo 🔍 Buscando procesos en el puerto 53793...
netstat -ano | findstr :53793

echo.
echo 🛑 Matando procesos de Flutter/Chrome en el puerto 53793...

REM Buscar y matar procesos que usen el puerto 53793
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :53793') do (
    echo Terminando proceso %%a...
    taskkill /f /pid %%a 2>nul
)

echo.
echo 🌐 Cerrando todas las instancias de Chrome...
taskkill /f /im chrome.exe 2>nul
taskkill /f /im msedge.exe 2>nul

echo.
echo ⏱️ Esperando 3 segundos para que se liberen los puertos...
timeout /t 3 /nobreak >nul

echo.
echo 🚀 Iniciando Flutter en puerto limpio...
cd /d "C:\Users\heily\Desktop\chabot\front\frontend_flutter"

flutter run -d chrome --web-port=53793

echo.
echo ✅ Proceso completado
pause
