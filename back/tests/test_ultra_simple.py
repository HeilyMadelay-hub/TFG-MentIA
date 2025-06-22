"""
Test ultra simple - Solo verifica que los archivos existen y se pueden importar
"""
import sys
import os

# Agregar el path actual
sys.path.insert(0, os.getcwd())

def test_files_exist():
    print("VERIFICANDO ARCHIVOS...")
    
    files = [
        "src/services/document_validation_service.py",
        "src/services/file_processing_service.py",
        "src/services/document_background_processor.py",
        "src/api/helpers/document_helpers.py",
        "src/api/endpoints/documents.py",
        "src/api/endpoints/documents_backup_20250616.py"
    ]
    
    all_exist = True
    for file in files:
        if os.path.exists(file):
            print(f"OK {file}")
        else:
            print(f"ERROR {file} - NO ENCONTRADO")
            all_exist = False
    
    return all_exist

def test_imports_simple():
    print("\nVERIFICANDO IMPORTS SIMPLES...")
    
    try:
        # Import más básico posible
        from src.services import document_validation_service
        print("OK document_validation_service module")
        
        from src.services import file_processing_service
        print("OK file_processing_service module")
        
        # Intentar importar las clases
        from src.services.document_validation_service import DocumentValidationService
        print("OK DocumentValidationService class")
        
        from src.services.file_processing_service import FileProcessingService
        print("OK FileProcessingService class")
        
        return True
        
    except Exception as e:
        print(f"ERROR importing: {e}")
        return False

def test_size_reduction():
    print("\nVERIFICANDO REDUCCION DE TAMANO...")
    
    backup_path = "src/api/endpoints/documents_backup_20250616.py"
    current_path = "src/api/endpoints/documents.py"
    
    if os.path.exists(backup_path) and os.path.exists(current_path):
        backup_size = os.path.getsize(backup_path)
        current_size = os.path.getsize(current_path)
        reduction = ((backup_size - current_size) / backup_size) * 100
        
        print(f"Original: {backup_size:,} bytes")
        print(f"Refactorizado: {current_size:,} bytes") 
        print(f"Reduccion: {reduction:.1f}%")
        
        return reduction > 20
    else:
        print("ERROR: No se pueden comparar archivos")
        return False

def main():
    print("TEST ULTRA SIMPLE DE REFACTORIZACION")
    print("=" * 50)
    
    files_ok = test_files_exist()
    imports_ok = test_imports_simple()
    size_ok = test_size_reduction()
    
    print("\n" + "=" * 50)
    print("RESULTADO:")
    
    if files_ok and imports_ok and size_ok:
        print("EXITO! Refactorizacion basica funcionando")
        print("\nBENEFICIOS:")
        print("- Archivos refactorizados creados")
        print("- Imports basicos funcionando")
        print("- Reduccion de tamano lograda")
        print("\nPROXIMO PASO:")
        print("1. python check_refactoring_win.py")
        print("2. Probar funcionalidad en frontend")
        return True
    else:
        print("ERROR: Algunos tests fallaron")
        print(f"Archivos: {'OK' if files_ok else 'ERROR'}")
        print(f"Imports: {'OK' if imports_ok else 'ERROR'}")
        print(f"Tamano: {'OK' if size_ok else 'ERROR'}")
        return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 50)
    sys.exit(0 if success else 1)
