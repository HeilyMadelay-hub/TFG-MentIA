# Script de emergencia para problemas de indexación en PowerShell
# Ejecuta la solución automática con manejo de errores

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   SOLUCIONADOR DE EMERGENCIA - CHROMADB   " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Guardar directorio actual
$originalLocation = Get-Location

try {
    # Cambiar al directorio del script
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location $scriptPath
    
    Write-Host "Verificando Python..." -ForegroundColor Yellow
    python --version
    
    Write-Host ""
    Write-Host "Ejecutando solucion automatica..." -ForegroundColor Green
    Write-Host ""
    
    # Ejecutar el script de solución
    python tests\fix_indexing_auto.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Proceso completado exitosamente!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ Hubo un error durante la ejecución" -ForegroundColor Red
        Write-Host ""
        Write-Host "Intentando solución alternativa..." -ForegroundColor Yellow
        python tests\reindex_documents.py
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Posibles soluciones:" -ForegroundColor Yellow
    Write-Host "1. Verifica que Python esté instalado"
    Write-Host "2. Verifica que estés en el directorio correcto"
    Write-Host "3. Reinicia Docker Desktop"
} finally {
    # Restaurar directorio original
    Set-Location $originalLocation
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Si el problema persiste:" -ForegroundColor Yellow
Write-Host "1. Reinicia Docker Desktop"
Write-Host "2. Ejecuta: docker-compose restart chromadb"
Write-Host "3. Vuelve a ejecutar este script"
Write-Host ""
Write-Host "Presiona cualquier tecla para salir..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
