#!/usr/bin/env python3
"""
Script de corrección automática para el problema de tiempo relativo.
Este script aplica las correcciones necesarias al código del frontend.
"""

import os
import shutil
from pathlib import Path
import re

def backup_file(file_path):
    """Crear una copia de respaldo del archivo."""
    backup_path = f"{file_path}.backup"
    shutil.copy2(file_path, backup_path)
    print(f"📁 Backup creado: {backup_path}")
    return backup_path

def apply_frontend_fix():
    """Aplica la corrección al archivo del frontend."""
    frontend_file = Path("C:/Users/heily/Desktop/chabot/front/frontend_flutter/lib/screens/admin_panel_screen.dart")
    
    if not frontend_file.exists():
        print(f"❌ Archivo no encontrado: {frontend_file}")
        return False
    
    print(f"🔧 Aplicando corrección a: {frontend_file}")
    
    # Crear backup
    backup_file(str(frontend_file))
    
    # Leer el archivo
    with open(frontend_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar y reemplazar la línea problemática
    old_pattern = r"'Cuenta creada: \$\{_formatDateTime\(user\.createdAt\)\}'"
    
    if re.search(old_pattern, content):
        print("✅ Patrón problemático encontrado, aplicando corrección...")
        
        # Insertar el código de corrección antes del return ListTile
        fix_code = '''
                // 🔧 CORRECCIÓN: Usar el tiempo formateado del backend
                String formattedTime = 'Fecha desconocida';
                
                // Buscar los datos del usuario en el dashboard data del backend
                if (_dashboardData != null && 
                    _dashboardData!['users'] != null && 
                    index < _dashboardData!['users'].length) {
                  final userData = _dashboardData!['users'][index];
                  
                  // ✅ USAR EL TIEMPO YA FORMATEADO DEL BACKEND
                  if (userData['formatted_created'] != null && userData['formatted_created'].toString().isNotEmpty) {
                    formattedTime = userData['formatted_created'];
                    print('✅ Usando tiempo del backend para ${user.username}: $formattedTime');
                  } else {
                    // Fallback: calcular en el frontend solo si no viene del backend
                    formattedTime = _formatDateTime(user.createdAt);
                    print('⚠️ Calculando tiempo en frontend para ${user.username}: $formattedTime');
                  }
                } else {
                  // Fallback: calcular en el frontend
                  formattedTime = _formatDateTime(user.createdAt);
                  print('❌ Sin datos del backend, calculando en frontend para ${user.username}: $formattedTime');
                }
                '''
        
        # Buscar el itemBuilder y agregar el código de corrección
        itembuilder_pattern = r"(itemBuilder: \(context, index\) \{\s+final user = _users\[index\];)"
        replacement = r"\1" + fix_code
        
        content = re.sub(itembuilder_pattern, replacement, content, flags=re.MULTILINE)
        
        # Reemplazar la línea problemática
        content = re.sub(old_pattern, "'Cuenta creada: $formattedTime'", content)
        
        # Escribir el archivo corregido
        with open(frontend_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Corrección aplicada exitosamente")
        return True
    else:
        print("⚠️ Patrón problemático no encontrado, es posible que ya esté corregido")
        return False

def verify_backend_config():
    """Verifica que el backend esté enviando los datos correctos."""
    backend_file = Path("C:/Users/heily/Desktop/chabot/back/src/api/endpoints/admin_panel/dashboard.py")
    
    if not backend_file.exists():
        print(f"❌ Archivo backend no encontrado: {backend_file}")
        return False
    
    with open(backend_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar que el backend incluya formatted_created
    if '"formatted_created": formatted_time' in content:
        print("✅ Backend configurado correctamente - enviando formatted_created")
        return True
    elif 'formatted_created' in content:
        print("⚠️ Backend parcialmente configurado - revisar implementación")
        return True
    else:
        print("❌ Backend no está enviando formatted_created")
        return False

def test_fix():
    """Proporciona instrucciones para probar la corrección."""
    print("\n🧪 INSTRUCCIONES PARA PROBAR LA CORRECCIÓN:")
    print("=" * 50)
    print("1. Abrir terminal en la carpeta del frontend:")
    print("   cd C:/Users/heily/Desktop/chabot/front/frontend_flutter")
    print()
    print("2. Ejecutar Flutter:")
    print("   flutter clean")
    print("   flutter pub get") 
    print("   flutter run -d chrome --web-port=53793")
    print()
    print("3. Ir al panel de administración y verificar:")
    print("   - Los tiempos mostrados deben coincidir con los logs del backend")
    print("   - marcos: debería mostrar 'Hace 2-3 días'")
    print("   - testuser832410: debería mostrar 'Hace 1-2 días'")
    print("   - heily185: debería mostrar 'Hace 3-4 días'")
    print()
    print("4. Verificar logs en la consola del navegador:")
    print("   - Deberías ver mensajes como '✅ Usando tiempo del backend para...'")

def main():
    """Función principal del script de corrección."""
    print("🚀 SCRIPT DE CORRECCIÓN AUTOMÁTICA")
    print("Corrigiendo el problema de tiempo relativo en el panel de administración")
    print("=" * 70)
    
    # Verificar backend
    print("\n1. Verificando configuración del backend...")
    backend_ok = verify_backend_config()
    
    # Aplicar corrección al frontend
    print("\n2. Aplicando corrección al frontend...")
    frontend_ok = apply_frontend_fix()
    
    # Resumen
    print("\n" + "=" * 70)
    print("📋 RESUMEN DE LA CORRECCIÓN:")
    print(f"   Backend: {'✅ OK' if backend_ok else '❌ Necesita revisión'}")
    print(f"   Frontend: {'✅ Corregido' if frontend_ok else '⚠️ Sin cambios'}")
    
    if frontend_ok:
        test_fix()
    
    print("\n🎉 Proceso completado. Reinicia la aplicación Flutter para ver los cambios.")

if __name__ == "__main__":
    main()
