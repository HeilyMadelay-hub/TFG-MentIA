"""
Tests para los endpoints de documentos refactorizados
Valida que la refactorización mantenga toda la funcionalidad
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
from io import BytesIO

from src.main import app
from src.services.document_validation_service import DocumentValidationService
from src.services.file_processing_service import FileProcessingService
from src.services.document_background_processor import DocumentBackgroundProcessor
from src.api.helpers.document_helpers import DocumentEndpointHelpers


client = TestClient(app)

class TestDocumentValidationService:
    """Tests para el servicio de validación de documentos"""
    
    def setup_method(self):
        self.validator = DocumentValidationService()
    
    def test_validate_file_type_valid(self):
        """Test validación de tipo de archivo válido"""
        mock_file = Mock()
        mock_file.content_type = "application/pdf"
        
        result = self.validator.validate_file_type(mock_file)
        assert result == "application/pdf"
    
    def test_validate_file_type_invalid(self):
        """Test validación de tipo de archivo inválido"""
        mock_file = Mock()
        mock_file.content_type = "application/exe"
        
        with pytest.raises(Exception) as exc_info:
            self.validator.validate_file_type(mock_file)
        assert "no soportado" in str(exc_info.value).lower()
    
    def test_validate_file_size_valid(self):
        """Test validación de tamaño válido"""
        file_content = b"a" * 1000  # 1KB
        result = self.validator.validate_file_size(file_content, "test.pdf")
        assert result == 1000
    
    def test_validate_file_size_too_large(self):
        """Test validación de archivo muy grande"""
        file_content = b"a" * (101 * 1024 * 1024)  # 101MB
        
        with pytest.raises(Exception) as exc_info:
            self.validator.validate_file_size(file_content, "large_file.pdf")
        assert "excede el tamaño máximo" in str(exc_info.value)
    
    def test_should_process_synchronously(self):
        """Test determinación de procesamiento síncrono vs asíncrono"""
        # Archivo pequeño PDF
        assert self.validator.should_process_synchronously(500 * 1024, "application/pdf") == True
        
        # Archivo grande PDF
        assert self.validator.should_process_synchronously(2 * 1024 * 1024, "application/pdf") == False
        
        # Archivo pequeño texto
        assert self.validator.should_process_synchronously(100 * 1024, "text/plain") == True
        
        # Archivo grande texto
        assert self.validator.should_process_synchronously(600 * 1024, "text/plain") == False
    
    def test_validate_document_title(self):
        """Test validación de título de documento"""
        # Título válido
        result = self.validator.validate_document_title("  Mi Documento  ")
        assert result == "Mi Documento"
        
        # Título vacío
        with pytest.raises(Exception):
            self.validator.validate_document_title("")
        
        # Título muy largo
        with pytest.raises(Exception):
            self.validator.validate_document_title("a" * 250)
        
        # Título muy corto
        with pytest.raises(Exception):
            self.validator.validate_document_title("ab")

class TestFileProcessingService:
    """Tests para el servicio de procesamiento de archivos"""
    
    def setup_method(self):
        self.processor = FileProcessingService()
    
    def test_extract_plain_text(self):
        """Test extracción de texto plano"""
        content = "Hola mundo".encode('utf-8')
        result = self.processor._extract_plain_text(content, "test.txt")
        assert result == "Hola mundo"
    
    def test_extract_plain_text_encoding(self):
        """Test extracción con diferentes encodings"""
        content = "Texto con ñ y acentós".encode('latin-1')
        result = self.processor._extract_plain_text(content, "test.txt")
        assert "Texto" in result  # Debe poder extraer algo
    
    def test_get_file_metadata(self):
        """Test obtención de metadata de archivo"""
        content = b"test content"
        metadata = self.processor.get_file_metadata(content, "test.pdf", "application/pdf")
        
        assert metadata["filename"] == "test.pdf"
        assert metadata["content_type"] == "application/pdf"
        assert metadata["size_bytes"] == len(content)
        assert metadata["extension"] == ".pdf"
    
    @patch('tempfile.NamedTemporaryFile')
    def test_create_temp_file(self, mock_temp):
        """Test creación de archivo temporal"""
        mock_temp.return_value.__enter__.return_value.name = "/tmp/test"
        
        content = b"test content"
        result = self.processor.create_temp_file(content, ".pdf")
        
        mock_temp.assert_called_once()

class TestDocumentBackgroundProcessor:
    """Tests para el procesador de tareas en segundo plano"""
    
    def setup_method(self):
        self.processor = DocumentBackgroundProcessor()
    
    def test_get_processing_thresholds(self):
        """Test obtención de umbrales de procesamiento"""
        thresholds = self.processor.get_processing_thresholds()
        
        assert "text_threshold_kb" in thresholds
        assert "pdf_threshold_mb" in thresholds
        assert "general_threshold_mb" in thresholds
        assert "max_file_size_mb" in thresholds
        
        assert thresholds["text_threshold_kb"] == 500
        assert thresholds["pdf_threshold_mb"] == 1
    
    def test_estimate_processing_time(self):
        """Test estimación de tiempo de procesamiento"""
        # Archivo PDF pequeño
        result = self.processor.estimate_processing_time(500 * 1024, "application/pdf")
        assert result["process_type"] == "síncrono"
        assert result["estimated_minutes"] > 0
        
        # Archivo PDF grande
        result = self.processor.estimate_processing_time(2 * 1024 * 1024, "application/pdf")
        assert result["process_type"] == "asíncrono"
        assert result["estimated_minutes"] > 1

class TestDocumentEndpointHelpers:
    """Tests para los helpers de endpoints"""
    
    def setup_method(self):
        self.helpers = DocumentEndpointHelpers()
    
    def test_get_processing_summary(self):
        """Test obtención de resumen de procesamiento"""
        file_size = 1024 * 1024  # 1MB
        content_type = "application/pdf"
        
        summary = self.helpers.get_processing_summary(file_size, content_type)
        
        assert "file_info" in summary
        assert "processing" in summary
        assert "thresholds" in summary
        
        assert summary["file_info"]["size_mb"] == 1.0
        assert summary["file_info"]["content_type"] == content_type

class TestDocumentEndpointsRefactored:
    """Tests de integración para endpoints refactorizados"""
    
    @pytest.fixture
    def mock_auth(self):
        """Mock del usuario autenticado"""
        with patch('src.api.dependencies.get_current_user') as mock:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.username = "testuser"
            mock_user.is_admin = False
            mock.return_value = mock_user
            yield mock_user
    
    @pytest.fixture
    def mock_document_service(self):
        """Mock del servicio de documentos"""
        with patch('src.api.dependencies.get_document_service') as mock:
            service = Mock()
            mock.return_value = service
            yield service
    
    def test_upload_document_structure(self, mock_auth, mock_document_service):
        """Test que el endpoint de upload mantiene la estructura esperada"""
        # Crear archivo mock
        file_content = b"PDF content"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
        data = {"title": "Test Document"}
        
        # Mock del servicio
        mock_doc = Mock()
        mock_doc.id = 1
        mock_doc.title = "Test Document"
        mock_document_service.create_document_placeholder.return_value = mock_doc
        mock_document_service.get_document.return_value = mock_doc
        
        with patch('src.api.helpers.document_helpers.DocumentEndpointHelpers') as mock_helpers:
            mock_helpers_instance = Mock()
            mock_helpers.return_value = mock_helpers_instance
            mock_helpers_instance.handle_document_upload.return_value = mock_doc
            
            # El endpoint debería delegar al helper
            response = client.post("/api/documents/upload", files=files, data=data)
            
            # Verificar que se llamó al helper (indica que la refactorización funcionó)
            mock_helpers_instance.handle_document_upload.assert_called_once()
    
    def test_create_document_endpoint(self, mock_auth, mock_document_service):
        """Test endpoint de creación de documento"""
        document_data = {
            "title": "Test Document",
            "content": "Test content",
            "content_type": "text/plain"
        }
        
        mock_doc = Mock()
        mock_doc.id = 1
        mock_doc.title = "Test Document"
        mock_document_service.create_document.return_value = mock_doc
        
        response = client.post("/api/documents/", json=document_data)
        
        # Verificar que se llamó al servicio
        mock_document_service.create_document.assert_called_once()
    
    def test_list_documents_endpoint(self, mock_auth, mock_document_service):
        """Test endpoint de listar documentos"""
        mock_documents = [Mock(id=1, title="Doc 1"), Mock(id=2, title="Doc 2")]
        mock_document_service.list_user_documents.return_value = mock_documents
        
        response = client.get("/api/documents/")
        
        # Verificar que se llamó al servicio con parámetros por defecto
        mock_document_service.list_user_documents.assert_called_once_with(
            user_id=1,  # ID del mock_auth
            limit=100,
            skip=0,
            sort_by='created_at',
            order='desc'
        )
    
    def test_share_document_endpoint(self, mock_auth, mock_document_service):
        """Test endpoint de compartir documento"""
        share_data = {"user_ids": [2, 3]}
        
        mock_doc = Mock()
        mock_doc.id = 1
        mock_doc.uploaded_by = 1
        mock_document_service.get_document.return_value = mock_doc
        mock_document_service.is_admin_user.return_value = False
        mock_document_service.share_document.return_value = True
        
        with patch('src.api.helpers.document_helpers.DocumentEndpointHelpers') as mock_helpers:
            mock_helpers_instance = Mock()
            mock_helpers.return_value = mock_helpers_instance
            mock_helpers_instance.handle_document_sharing.return_value = {
                "message": "Documento compartido exitosamente",
                "shared_with": [2, 3]
            }
            
            response = client.post("/api/documents/1/share", json=share_data)
            
            # Verificar que se delegó al helper
            mock_helpers_instance.handle_document_sharing.assert_called_once()

class TestRefactoringIntegrity:
    """Tests para verificar que la refactorización mantiene toda la funcionalidad"""
    
    def test_all_services_importable(self):
        """Test que todos los servicios nuevos se pueden importar"""
        from src.services.document_validation_service import DocumentValidationService
        from src.services.file_processing_service import FileProcessingService
        from src.services.document_background_processor import DocumentBackgroundProcessor
        from src.api.helpers.document_helpers import DocumentEndpointHelpers
        
        # Verificar que se pueden instanciar
        assert DocumentValidationService() is not None
        assert FileProcessingService() is not None
        assert DocumentBackgroundProcessor() is not None
        assert DocumentEndpointHelpers() is not None
    
    def test_service_method_signatures(self):
        """Test que los servicios tienen los métodos esperados"""
        validator = DocumentValidationService()
        processor = FileProcessingService()
        background = DocumentBackgroundProcessor()
        helpers = DocumentEndpointHelpers()
        
        # DocumentValidationService
        assert hasattr(validator, 'validate_file_type')
        assert hasattr(validator, 'validate_file_size')
        assert hasattr(validator, 'should_process_synchronously')
        assert hasattr(validator, 'validate_document_title')
        
        # FileProcessingService
        assert hasattr(processor, 'extract_text_from_content')
        assert hasattr(processor, 'get_file_metadata')
        assert hasattr(processor, 'create_temp_file')
        
        # DocumentBackgroundProcessor
        assert hasattr(background, 'get_processing_thresholds')
        assert hasattr(background, 'estimate_processing_time')
        
        # DocumentEndpointHelpers
        assert hasattr(helpers, 'get_processing_summary')
    
    @patch('src.api.dependencies.get_current_user')
    def test_endpoint_file_size_reduction(self, mock_auth):
        """Test que los endpoints están más limpios (menos líneas)"""
        import inspect
        from src.api.endpoints.documents import upload_document, create_document, share_document
        
        # Verificar que los endpoints son más pequeños
        upload_lines = len(inspect.getsource(upload_document).split('\n'))
        create_lines = len(inspect.getsource(create_document).split('\n'))
        share_lines = len(inspect.getsource(share_document).split('\n'))
        
        # Los endpoints refactorizados deberían ser significativamente más pequeños
        assert upload_lines < 50, f"upload_document tiene {upload_lines} líneas, debería ser < 50"
        assert create_lines < 30, f"create_document tiene {create_lines} líneas, debería ser < 30"
        assert share_lines < 40, f"share_document tiene {share_lines} líneas, debería ser < 40"
    
    def test_backup_file_exists(self):
        """Test que el archivo de respaldo existe"""
        import os
        backup_path = "C:/Users/heily/Desktop/chabot/back/src/api/endpoints/documents_backup_20250616.py"
        assert os.path.exists(backup_path), "El archivo de respaldo no existe"
        
        # Verificar que es más grande que el archivo actual
        current_path = "C:/Users/heily/Desktop/chabot/back/src/api/endpoints/documents.py"
        backup_size = os.path.getsize(backup_path)
        current_size = os.path.getsize(current_path)
        
        assert backup_size > current_size, "El archivo de respaldo debería ser más grande que el actual"
        
        # Verificar que la reducción es significativa (al menos 20%)
        reduction = ((backup_size - current_size) / backup_size) * 100
        assert reduction >= 20, f"La reducción es solo {reduction:.1f}%, debería ser >= 20%"

# Test de funcionalidad end-to-end simplificado
class TestEndToEndRefactored:
    """Test end-to-end simplificado para verificar que todo funciona"""
    
    @patch('src.api.dependencies.get_current_user')
    @patch('src.api.dependencies.get_document_service')
    def test_document_workflow_simplified(self, mock_service, mock_auth):
        """Test simplificado del flujo completo de documento"""
        # Setup mocks
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_auth.return_value = mock_user
        
        mock_doc_service = Mock()
        mock_service.return_value = mock_doc_service
        
        # Mock para create_document_placeholder
        placeholder = Mock()
        placeholder.id = 1
        placeholder.title = "Test Doc"
        mock_doc_service.create_document_placeholder.return_value = placeholder
        
        # Mock para get_document
        mock_doc_service.get_document.return_value = placeholder
        
        # Mock para list_user_documents
        mock_doc_service.list_user_documents.return_value = [placeholder]
        
        with patch('src.api.helpers.document_helpers.DocumentEndpointHelpers') as mock_helpers:
            mock_helpers_instance = Mock()
            mock_helpers.return_value = mock_helpers_instance
            mock_helpers_instance.handle_document_upload.return_value = placeholder
            
            # 1. Upload documento
            file_content = b"test content"
            files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
            data = {"title": "Test Document"}
            
            response = client.post("/api/documents/upload", files=files, data=data)
            assert response.status_code in [200, 201]
            
            # 2. Listar documentos
            response = client.get("/api/documents/")
            assert response.status_code == 200
            
            # El test pasa si no hay errores en los endpoints

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
