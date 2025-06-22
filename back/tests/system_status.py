#!/usr/bin/env python3
"""
Script de estado rápido del sistema
Muestra un resumen del estado de todos los componentes
"""

import sys
import os
import subprocess
import requests
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Colores
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def check_service_docker(service_name):
    """Verifica si un servicio está corriendo en Docker"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={service_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True
        )
        return "Up" in result.stdout
    except:
        return False

def check_http_service(url, service_name):
    """Verifica si un servicio HTTP está respondiendo"""
    try:
        response = requests.get(url, timeout=3)
        return response.status_code < 500
    except:
        return False

def get_chromadb_stats():
    """Obtiene estadísticas de ChromaDB"""
    try:
        from src.utils.chromadb_connector import ChromaDBConnector
        chromadb = ChromaDBConnector()
        client = chromadb.get_client()
        collection = client.get_collection("documents")
        results = collection.get()
        return len(results.get('ids', []))
    except:
        return -1

def get_document_count():
    """Obtiene el número de documentos en Supabase"""
    try:
        from src.repositories.document_repository import DocumentRepository
        doc_repo = DocumentRepository()
        docs = doc_repo.list_all_documents(limit=100)
        return len(docs)
    except:
        return -1

def print_status(service, is_running, extra_info=""):
    """Imprime el estado de un servicio con formato"""
    status = f"{Colors.GREEN}✅ OK{Colors.ENDC}" if is_running else f"{Colors.RED}❌ ERROR{Colors.ENDC}"
    print(f"  {service:<20} {status}  {extra_info}")

def main():
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}📊 ESTADO DEL SISTEMA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    # 1. Servicios Docker
    print(f"{Colors.BOLD}🐳 SERVICIOS DOCKER:{Colors.ENDC}")
    services = {
        "backend": "Backend API",
        "chromadb": "ChromaDB",
        "postgres": "PostgreSQL",
        "redis": "Redis"
    }
    
    for container, name in services.items():
        is_running = check_service_docker(container)
        print_status(name, is_running)
    
    # 2. Endpoints HTTP
    print(f"\n{Colors.BOLD}🌐 ENDPOINTS HTTP:{Colors.ENDC}")
    endpoints = {
        "http://localhost:2690/api/users/me": "API Backend",
        "http://localhost:8050": "ChromaDB HTTP",
        "http://localhost:3690": "Frontend"
    }
    
    for url, name in endpoints.items():
        is_running = check_http_service(url, name)
        print_status(name, is_running)
    
    # 3. Estado de la base de datos
    print(f"\n{Colors.BOLD}💾 ESTADO DE DATOS:{Colors.ENDC}")
    
    # Documentos en Supabase
    doc_count = get_document_count()
    if doc_count >= 0:
        print_status("Documentos en DB", True, f"{Colors.YELLOW}{doc_count} documentos{Colors.ENDC}")
    else:
        print_status("Documentos en DB", False, "No se pudo conectar")
    
    # Chunks en ChromaDB
    chunk_count = get_chromadb_stats()
    if chunk_count >= 0:
        status = chunk_count > 0
        color = Colors.GREEN if status else Colors.YELLOW
        print_status("Chunks indexados", status, f"{color}{chunk_count} chunks{Colors.ENDC}")
        
        if chunk_count == 0 and doc_count > 0:
            print(f"\n  {Colors.YELLOW}⚠️  Hay documentos pero no están indexados!{Colors.ENDC}")
            print(f"  {Colors.YELLOW}    Ejecuta: python tests/reindex_documents.py{Colors.ENDC}")
    else:
        print_status("Chunks indexados", False, "ChromaDB no disponible")
    
    # 4. Resumen y recomendaciones
    print(f"\n{Colors.BOLD}📝 RESUMEN:{Colors.ENDC}")
    
    all_services_ok = all([
        check_service_docker("backend"),
        check_service_docker("chromadb"),
        chunk_count > 0 if chunk_count >= 0 else False
    ])
    
    if all_services_ok:
        print(f"  {Colors.GREEN}✨ Sistema funcionando correctamente{Colors.ENDC}")
    else:
        print(f"  {Colors.YELLOW}⚠️  Hay problemas que requieren atención{Colors.ENDC}")
        
        if not check_service_docker("chromadb"):
            print(f"\n  {Colors.BOLD}Solución sugerida:{Colors.ENDC}")
            print(f"    docker-compose up -d chromadb")
        
        if chunk_count == 0 and doc_count > 0:
            print(f"\n  {Colors.BOLD}Solución sugerida:{Colors.ENDC}")
            print(f"    python tests/fix_indexing_auto.py")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.ENDC}\n")

if __name__ == "__main__":
    # Silenciar warnings de imports
    import warnings
    warnings.filterwarnings("ignore")
    
    main()
