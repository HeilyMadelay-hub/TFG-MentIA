"""
Test simple de imports - Compatible con Windows
"""
import sys
import os

# Agregar el path actual
sys.path.insert(0, os.getcwd())

def test_basic_imports():
    print("PROBANDO IMPORTS BASICOS")
    print("-" * 40)
    
    errors = []
    
    try:
        print("Importando DocumentValidationService...")
        from src.services.document_validation_service import DocumentValidationService
        validator = DocumentValidationService()
        print("OK DocumentValidationService")
    except Exception as e:
        errors.append(f"DocumentValidationService: {e}")
        print(f"ERROR DocumentValidationService: {e}")
    
    try:
        print("Importando FileProcessingService...")
        from src.services.file_processing_service import FileProcessingService
        processor = FileProcessingService()
        print("OK FileProcessingService")
    except Exception as e:
        errors.append(f"FileProcessingService: {e}")
        print(f"ERROR FileProcessingService: {e}")
    
    try:
        print("Importando DocumentBackgroundProcessor...")
        from src.services.document_background_processor import DocumentBackgroundProcessor
        background = DocumentBackgroundProcessor()
        print("OK DocumentBackgroundProcessor")
    except Exception as e:
        errors.append(f"DocumentBackgroundProcessor: {e}")
        print(f"ERROR DocumentBackgroundProcessor: {e}")
    
    try:
        print("Importando DocumentEndpointHelpers...")
        from src.api.helpers.document_helpers import DocumentEndpointHelpers
        helpers = DocumentEndpointHelpers()
        print("OK DocumentEndpointHelpers")
    except Exception as e:
        errors.append(f"DocumentEndpointHelpers: {e}")
        print(f"ERROR DocumentEndpointHelpers: {e}")
    
    return errors

def test_basic_functionality():
    print("\nPROBANDO FUNCIONALIDAD BASICA")
    print("-" * 40)
    
    errors = []
    
    try:
        from src.services.document_validation_service import DocumentValidationService
        validator = DocumentValidationService()
        
        # Test titulo
        title = validator.validate_document_title("  Test  ")
        assert title == "Test"
        print("OK Validacion de titulo funciona")
        
        # Test procesamiento
        sync = validator.should_process_synchronously(100*1024, "text/plain")
        assert sync == True
        print("OK Determinacion de procesamiento funciona")
        
    except Exception as e:
        errors.append(f"DocumentValidationService functionality: {e}")
        print(f"ERROR DocumentValidationService: {e}")
    
    try:
        from src.services.file_processing_service import FileProcessingService
        processor = FileProcessingService()
        
        # Test metadata
        metadata = processor.get_file_metadata(b"test", "test.pdf", "application/pdf")
        assert metadata["filename"] == "test.pdf"
        print("OK Metadata funciona")
        
    except Exception as e:
        errors.append(f"FileProcessingService functionality: {e}")
        print(f"ERROR FileProcessingService: {e}")
    
    try:
        from src.services.document_background_processor import DocumentBackgroundProcessor
        background = DocumentBackgroundProcessor()
        
        # Test thresholds
        thresholds = background.get_processing_thresholds()
        assert "text_threshold_kb" in thresholds
        print("OK Thresholds funcionan")
        
    except Exception as e:
        errors.append(f"DocumentBackgroundProcessor functionality: {e}")
        print(f"ERROR DocumentBackgroundProcessor: {e}")
    
    return errors

def main():
    print("TEST SIMPLE DE REFACTORIZACION")
    print("=" * 50)
    
    # Test 1: Imports
    import_errors = test_basic_imports()
    
    # Test 2: Funcionalidad (solo si no hay errores de import)
    functionality_errors = []
    if not import_errors:
        functionality_errors = test_basic_functionality()
    else:
        print("\nSALTANDO pruebas de funcionalidad debido a errores de import")
    
    # Resumen
    print("\n" + "=" * 50)
    print("RESUMEN")
    print("=" * 50)
    
    total_errors = len(import_errors) + len(functionality_errors)
    
    if total_errors == 0:
        print("EXITO! Todos los tests pasaron")
        print("\nLa refactorizacion esta funcionando correctamente")
        print("\nBENEFICIOS:")
        print("- Servicios especializados creados")
        print("- Imports funcionando correctamente") 
        print("- Funcionalidad basica operativa")
        print("\nPROXIMO PASO:")
        print("python check_refactoring_win.py")
        return True
    else:
        print(f"ERROR: {total_errors} problemas encontrados")
        print("\nERRORES DE IMPORT:")
        for error in import_errors:
            print(f"- {error}")
        
        print("\nERRORES DE FUNCIONALIDAD:")
        for error in functionality_errors:
            print(f"- {error}")
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
