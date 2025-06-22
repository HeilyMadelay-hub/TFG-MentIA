#!/usr/bin/env python3
"""
Script de diagnóstico avanzado para el problema de tiempo relativo.
Verifica el estado actual del sistema y proporciona información detallada.
"""

import json
import os
import requests
from datetime import datetime, timezone
from pathlib import Path

def test_backend_response():
    """Prueba la respuesta del backend directamente."""
    print("🔍 PROBANDO RESPUESTA DEL BACKEND...")
    print("=" * 50)
    
    try:
        # Nota: Este test requiere que tengas un token válido
        # En un ambiente real, necesitarías autenticarte primero
        print("⚠️ NOTA: Este test requiere autenticación manual")
        print("   Para probar manualmente:")
        print("   1. Abre las herramientas de desarrollador en Chrome (F12)")
        print("   2. Ve a la tab 'Network'")
        print("   3. Recarga el panel de administración")
        print("   4. Busca la petición a '/api/admin-panel/dashboard'")
        print("   5. Revisa la respuesta JSON")
        print("   6. Verifica que contenga 'formatted_created' para cada usuario")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando backend: {e}")
        return False

def analyze_current_times():
    """Analiza los tiempos actuales vs esperados."""
    print("📅 ANALISIS DE TIEMPOS ACTUALES")
    print("=" * 50)
    
    # Datos reales de la base de datos (según la imagen)
    users_data = [
        {"username": "marcos", "created_at": "2025-06-15T16:47:01.361564", "expected": "Hace 2-3 días"},
        {"username": "testuser832410", "created_at": "2025-06-16T21:01:16.643421", "expected": "Hace 1-2 días"},
        {"username": "heily185", "created_at": "2025-06-14T15:59:22.033419", "expected": "Hace 3-4 días"}
    ]
    
    # Tiempo actual simulado (18 de junio 2025, 12:00 PM como en los logs)
    current_time = datetime(2025, 6, 18, 12, 0, 0, tzinfo=timezone.utc)
    print(f"🕐 Tiempo de referencia: {current_time}")
    print()
    
    for user in users_data:
        try:
            # Parsear fecha de creación
            created_at = datetime.fromisoformat(user["created_at"].replace('Z', '+00:00'))
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            # Calcular diferencia
            diff = current_time - created_at
            days = diff.days
            hours = diff.seconds // 3600
            
            # Determinar tiempo relativo esperado
            if days == 0:
                relative_time = "Hoy"
            elif days == 1:
                relative_time = "Ayer"
            elif days < 7:
                relative_time = f"Hace {days} días"
            else:
                weeks = days // 7
                relative_time = f"Hace {weeks} semana{'s' if weeks > 1 else ''}"
            
            status = "✅" if relative_time in user["expected"] else "⚠️"
            
            print(f"{status} {user['username']:15} | Creado: {user['created_at'][:10]} | Días: {days:2} | Calculado: '{relative_time}' | Esperado: '{user['expected']}'")
            
        except Exception as e:
            print(f"❌ Error procesando {user['username']}: {e}")
    
    print()

def check_files_status():
    """Verifica el estado de los archivos del proyecto."""
    print("📁 VERIFICANDO ARCHIVOS DEL PROYECTO")
    print("=" * 50)
    
    files_to_check = [
        ("Backend Dashboard", "C:/Users/heily/Desktop/chabot/back/src/api/endpoints/admin_panel/dashboard.py"),
        ("Frontend Admin Panel", "C:/Users/heily/Desktop/chabot/front/frontend_flutter/lib/screens/admin_panel_screen.dart"),
        ("Backend Utils", "C:/Users/heily/Desktop/chabot/back/src/utils/timezone_utils.py"),
    ]
    
    for name, path in files_to_check:
        if os.path.exists(path):
            # Obtener información del archivo
            stat = os.stat(path)
            modified = datetime.fromtimestamp(stat.st_mtime)
            size = stat.st_size
            
            print(f"✅ {name}")
            print(f"   📍 Ruta: {path}")
            print(f"   📅 Modificado: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   📏 Tamaño: {size:,} bytes")
            
            # Verificar contenido clave
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if "dashboard.py" in path:
                if '"formatted_created": formatted_time' in content:
                    print("   ✅ Backend enviando 'formatted_created'")
                else:
                    print("   ❌ Backend NO enviando 'formatted_created'")
                    
            elif "admin_panel_screen.dart" in path:
                if "userData['formatted_created']" in content:
                    print("   ✅ Frontend usando 'formatted_created' del backend")
                else:
                    print("   ❌ Frontend NO usando 'formatted_created' del backend")
                    
            print()
        else:
            print(f"❌ {name}: ARCHIVO NO ENCONTRADO")
            print(f"   📍 Ruta esperada: {path}")
            print()

def generate_debug_checklist():
    """Genera una lista de verificación para debugging."""
    print("🔧 LISTA DE VERIFICACIÓN PARA DEBUGGING")
    print("=" * 50)
    
    checklist = [
        "¿El backend está ejecutándose en localhost:2690?",
        "¿Flutter está ejecutándose en localhost:53793?",
        "¿Has limpiado el cache de Flutter (flutter clean)?",
        "¿Has recargado la página sin cache (Ctrl+Shift+R)?",
        "¿Las herramientas de desarrollador muestran la petición a /api/admin-panel/dashboard?",
        "¿La respuesta JSON contiene 'formatted_created' para cada usuario?",
        "¿Los logs del backend muestran 'tiempo formateado: Hace X días'?",
        "¿Los logs del frontend muestran '✅ Usando tiempo del backend para...'?",
        "¿Chrome está usando la versión más reciente del código?",
        "¿Has verificado que no hay errores en la consola del navegador?"
    ]
    
    for i, item in enumerate(checklist, 1):
        print(f"   {i:2d}. ⬜ {item}")
    
    print()
    print("🎯 PASOS RECOMENDADOS:")
    print("   1. Ejecuta: verificar_y_limpiar.bat")
    print("   2. Verifica cada elemento de la lista anterior")
    print("   3. Si el problema persiste, revisa los logs del backend en tiempo real")
    print("   4. Usa las herramientas de desarrollador para inspeccionar las peticiones")

def main():
    """Función principal del diagnóstico."""
    print("🚀 DIAGNÓSTICO AVANZADO - PROBLEMA DE TIEMPO RELATIVO")
    print("=" * 60)
    print("📅 Ejecutado el:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    analyze_current_times()
    check_files_status() 
    test_backend_response()
    generate_debug_checklist()
    
    print("🎉 DIAGNÓSTICO COMPLETADO")
    print("   Si el problema persiste después de ejecutar verificar_y_limpiar.bat,")
    print("   es probable que sea un problema de cache del navegador.")

if __name__ == "__main__":
    main()
