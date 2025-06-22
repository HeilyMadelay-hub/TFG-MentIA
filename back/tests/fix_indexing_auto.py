#!/usr/bin/env python3
"""
Script de solución rápida para problemas de indexación en ChromaDB
Ejecuta automáticamente el diagnóstico y re-indexación si es necesario
"""

import sys
import os
import subprocess
import time

# Colores para la consola
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def run_script(script_name, description):
    """Ejecuta un script y captura su salida"""
    print_info(f"Ejecutando: {description}")
    
    try:
        # Asegurarse de que estamos en el directorio correcto
        back_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(back_dir)
        
        # Ejecutar el script
        result = subprocess.run(
            [sys.executable, f"tests/{script_name}"],
            capture_output=True,
            text=True
        )
        
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_docker_service(service_name):
    """Verifica si un servicio Docker está corriendo"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={service_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        return service_name in result.stdout
    except:
        return False

def main():
    print_header("🚀 SOLUCIONADOR AUTOMÁTICO DE PROBLEMAS DE INDEXACIÓN")
    
    # 1. Verificar que Docker esté corriendo
    print_info("Verificando servicios Docker...")
    if not check_docker_service("chromadb"):
        print_error("ChromaDB no está corriendo en Docker")
        print_info("Intentando iniciar servicios...")
        subprocess.run(["docker-compose", "up", "-d", "chromadb"])
        time.sleep(10)  # Esperar a que inicie
    else:
        print_success("ChromaDB está corriendo")
    
    # 2. Verificar estado de ChromaDB
    print_header("PASO 1: VERIFICANDO CHROMADB")
    success, stdout, stderr = run_script("check_chromadb.py", "Verificación de ChromaDB")
    
    if "410" in stdout:
        print_warning("ChromaDB usa API v2 (normal)")
    elif not success:
        print_error("ChromaDB no responde correctamente")
        print(stdout)
        return
    
    # 3. Ejecutar diagnóstico
    print_header("PASO 2: DIAGNÓSTICO COMPLETO")
    success, stdout, stderr = run_script("debug_chromadb.py", "Diagnóstico de indexación")
    
    # Analizar resultado
    needs_reindex = False
    if "Total de chunks: 0" in stdout:
        print_error("No hay documentos indexados")
        needs_reindex = True
    elif "Error" in stdout or not success:
        print_error("Errores encontrados en el diagnóstico")
        needs_reindex = True
    else:
        # Buscar información de chunks
        import re
        chunks_match = re.search(r"Total de chunks: (\d+)", stdout)
        if chunks_match:
            total_chunks = int(chunks_match.group(1))
            if total_chunks > 0:
                print_success(f"Encontrados {total_chunks} chunks indexados")
            else:
                needs_reindex = True
    
    # 4. Re-indexar si es necesario
    if needs_reindex:
        print_header("PASO 3: RE-INDEXANDO DOCUMENTOS")
        print_warning("Se detectaron problemas de indexación. Re-indexando...")
        
        success, stdout, stderr = run_script("reindex_documents.py", "Re-indexación de documentos")
        
        if success and "re-indexado exitosamente" in stdout:
            print_success("Documentos re-indexados correctamente")
            
            # Contar chunks creados
            chunks_created = stdout.count("✅ Documento")
            print_success(f"Se re-indexaron {chunks_created} documentos")
        else:
            print_error("Error durante la re-indexación")
            print(stdout)
            print(stderr)
    else:
        print_success("La indexación está correcta. No se requiere acción.")
    
    # 5. Verificación final
    print_header("VERIFICACIÓN FINAL")
    success, stdout, stderr = run_script("debug_chromadb.py", "Verificación post-indexación")
    
    if "Total de chunks: 0" in stdout:
        print_error("La re-indexación falló. Por favor, revisa los logs.")
    else:
        chunks_match = re.search(r"Total de chunks: (\d+)", stdout)
        if chunks_match:
            total_chunks = int(chunks_match.group(1))
            if total_chunks > 0:
                print_success(f"✨ Sistema funcionando correctamente con {total_chunks} chunks indexados")
            else:
                print_error("No se encontraron chunks después de la re-indexación")
    
    print_header("PROCESO COMPLETADO")
    print_info("Si el problema persiste, revisa:")
    print_info("  1. Los logs del backend al subir documentos")
    print_info("  2. Que los documentos tengan contenido válido")
    print_info("  3. Los logs de Docker: docker logs chromadb")

if __name__ == "__main__":
    main()
