#Vamos a usar mock que es un objeto simulado que imita el comportamiento
#de objetos reales de manera controlada durante las pruebas.
#Es una técnica fundamental en pruebas unitarias, especialmente 
#cuando necesitas probar componentes que tienen dependencias externas.

import unittest
import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock, patch
from datetime import datetime
from typing import List, Dict, Any, Optional
# Primero importa Base
from src.models.domain.base import Base
# Luego importa los modelos
from src.models.domain.documento import Document
from src.models.schemas.document import DocumentBase, DocumentCreate, DocumentUpdate, DocumentResponse
from src.config.database import get_supabase_client
from src.repositories.document_repository import DocumentRepository
from src.services.document_service import DocumentService
from src.utils.chromadb_connector import ChromaDBConnector


# Pruebas unitarias para los modelos de documentos
# Fae 1 prueba del Modelo SQLAlchemy
# Comenzamos con pruebas unitarias simples para el modelo Document:
class TestDocumentSimple(unittest.TestCase):
    def test_document_creation(self):
        """Prueba simple del modelo Document"""
        print(type(Document))
        print(Document.__bases__)
        print(Document.__dict__.keys())
        
        doc = Document(
            title="Test Document",
            uploaded_by=1,
            content_type="texto"
        )
        self.assertEqual(doc.title, "Test Document")
        self.assertEqual(doc.uploaded_by, 1)  # Changed assertion to match 
        self.assertEqual(doc.content_type, "texto")  # Added assertion for content_type

# Fase 2: Ampliación a Modelos Pydantic
# Expandimos las pruebas para incluir validaciones de los modelos Pydantic:
# Estas pruebas verifican la validación de esquemas utilizados en la API:
# - DocumentBase: Validaciones básicas comunes a todos los modelos
# - DocumentCreate: Para validar datos de creación de documentos
# - DocumentUpdate: Para validar datos de actualización parcial/completa
# - DocumentResponse: Para validar respuestas enviadas al cliente
#   La forma correcta de ejecutar solo una clase específica de prueba con pytest es usar la sintaxis:
#       pytest archivo::ClaseDeTest
#   Para probar solo un metodo :pytest tests/test_documents.py::TestDocumentModels::test_document_create_model -v
class TestDocumentModels(unittest.TestCase):
    def test_document_sqlalchemy_model(self):
        """Prueba el modelo SQLAlchemy Document"""
        doc = Document(
            title="Test Document",
            uploaded_by=1,  # Cambiado de user_id a uploaded_by
            content_type="texto",  # Cambiado de document_type a content_type
            chromadb_id="test_chroma_123"  # Añadido para probar este campo
        )
        self.assertEqual(doc.title, "Test Document")
        self.assertEqual(doc.uploaded_by, 1)  # Cambiado de user_id a uploaded_by
        self.assertEqual(doc.content_type, "texto")  # Asegurando que content_type se guarda correctamente
        self.assertEqual(doc.chromadb_id, "test_chroma_123")  # Verificando chromadb_id
    def test_document_pydantic_validations(self):
        """Prueba las validaciones de los modelos Pydantic"""
        # Caso válido
        doc = DocumentBase(title="Documento válido", content_type="pdf")
        self.assertEqual(doc.title, "Documento válido")
        
        # Título vacío debe fallar
        with self.assertRaises(ValidationError):
            DocumentBase(title="", content_type="pdf")
    
    def test_document_create_model(self):
        """Prueba el modelo de creación"""
        doc = DocumentCreate(
            title="Nuevo documento",
            content_type="pdf",
            content="Contenido del documento",
            tags=["tag1", "tag2"]
        )
        self.assertEqual(doc.content, "Contenido del documento")
        self.assertEqual(doc.tags, ["tag1", "tag2"])
    def test_document_update_model(self):
        """Prueba el modelo de actualización"""
        # Actualización parcial
        doc_update = DocumentUpdate(title="Título actualizado")
        self.assertEqual(doc_update.title, "Título actualizado")
        self.assertIsNone(doc_update.content)
        
        # Actualización completa
        doc_update_full = DocumentUpdate(
            title="Nuevo título",
            content_type="markdown",
            content="Contenido actualizado",
            tags=["nuevo", "actualizado"]
        )
        self.assertEqual(doc_update_full.content, "Contenido actualizado")
        self.assertEqual(doc_update_full.tags, ["nuevo", "actualizado"])
    def test_document_response_model(self):
        """Prueba el modelo de respuesta"""
        now = datetime.now()
        doc_response = DocumentResponse(
            id=1,
            title="Documento de prueba",
            content_type="texto",
            uploaded_by=1,
            chromadb_id="chroma_123",
            created_at=now,
            updated_at=now
        )
        self.assertEqual(doc_response.id, 1)
        self.assertEqual(doc_response.title, "Documento de prueba")
        self.assertEqual(doc_response.chromadb_id, "chroma_123")


#Fase 3: Pruebas del Repositorio con Mocks
#Introducimos pruebas para el repositorio, utilizando mocks para simular Supabase:
class TestDocumentRepository(unittest.TestCase):
    @patch('src.repositories.document_repository.get_supabase_client')
    def test_create_document(self, mock_get_client):
        """Prueba la creación de un documento en el repositorio"""
        # Configurar mock de Supabase
        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response
        mock_get_client.return_value = mock_supabase
        
        # Crear un documento mock con los atributos que espera el repositorio
        document = MagicMock()
        document.title = "Test Document"
        document.user_id = 1  # Añadir el atributo que espera el repositorio
        document.document_type = "texto"  # Añadir el atributo que espera el repositorio
        
        # Probar el repositorio
        repo = DocumentRepository()
        doc_id = repo.create(document)
        
        # Verificaciones
        self.assertEqual(doc_id, 1)
        mock_supabase.table.assert_called_with("documents")
    
    @patch('src.repositories.document_repository.get_supabase_client')
    def test_get_document(self, mock_get_client):
        """Prueba la obtención de un documento"""
        # Configurar mock de Supabase
        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{
            "id": 1,
            "title": "Test Document",
            "uploaded_by": 1,  # Falta este campo
            "content_type": "texto",  # Falta este campo
            "chromadb_id": "chroma_1",  # Falta este campo
            "created_at": datetime.utcnow().isoformat(),  # Falta este campo
            "updated_at": datetime.utcnow().isoformat()  # Falta este campo
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_client.return_value = mock_supabase
      
        # Probar
        repo = DocumentRepository()
        document = repo.get(1)
        
        # Verificar
        self.assertEqual(document.id, 1)
        self.assertEqual(document.title, "Test Document")
        mock_supabase.table().select.assert_called_once()
        mock_supabase.table().select().eq.assert_called_with('id', 1)
    
    @patch('src.repositories.document_repository.get_supabase_client')
    def test_get_document_not_found(self, mock_get_client):
        # Simular documento no encontrado
        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []  # Sin datos
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_client.return_value = mock_supabase
        
        # Probar
        repo = DocumentRepository()
        document = repo.get(999)  # ID que no existe
        
        # Verificar
        self.assertIsNone(document)

#Fase 4: Pruebas del Servicio con Mocks
#Finalmente, probamos el servicio que coordina entre repositorio y ChromaDB:

class TestDocumentService(unittest.TestCase):
    @patch('src.repositories.document_repository.DocumentRepository')
    @patch('src.utils.chromadb_connector.ChromaDBConnector')
    def test_create_document_happy_path(self, mock_chromadb_class, mock_repo_class):
        """Prueba el flujo completo de creación"""
        # Configurar mocks
        mock_repo = MagicMock()
        mock_repo.create.return_value = 1
        mock_repo_class.return_value = mock_repo
        
        mock_chromadb = MagicMock()
        mock_chromadb_class.return_value = mock_chromadb
        
        # Simular documento recuperado después de la creación
        mock_document = MagicMock()
        mock_document.id = 1
        mock_document.title = "Test Document"
        mock_repo.get.return_value = mock_document
        
        # Probar el servicio
        from src.services.document_service import DocumentService
        service = DocumentService()
        service.document_repo = mock_repo
        service.chromadb = mock_chromadb
        
        document = service.create_document(
            uploaded_by=1,  # Cambiado de user_id a uploaded_by
            title="Test Document",
            content="Contenido de prueba",
            content_type="texto"  # Cambiado de document_type a content_type
        )
        
        # Verificar
        mock_repo.create.assert_called_once()
        mock_chromadb.add_documents.assert_called_once()
        self.assertEqual(document.id, 1)

@patch('src.repositories.document_repository.DocumentRepository')
@patch('src.utils.chromadb_connector.ChromaDBConnector')
def test_create_document_error_rollback(self, mock_chromadb_class, mock_repo_class):
    """Prueba que se haga rollback si falla ChromaDB"""
    # Configurar mocks
    mock_repo = MagicMock()
    mock_repo.create.return_value = 1
    mock_repo_class.return_value = mock_repo
    
    mock_chromadb = MagicMock()
    mock_chromadb.add_documents.side_effect = Exception("Error en ChromaDB")
    mock_chromadb_class.return_value = mock_chromadb
    
    # Probar el servicio
    from src.services.document_service import DocumentService
    service = DocumentService()
    service.document_repo = mock_repo
    service.chromadb = mock_chromadb
    
    # Debe lanzar excepción
    with self.assertRaises(Exception):
        document = service.create_document(
            uploaded_by=1,  # Cambiado de user_id a uploaded_by
            title="Test Document",
            content="Contenido de prueba",
            content_type="texto"  # Cambiado de document_type a content_type
        )
    
    # Verificar rollback
    mock_repo.delete.assert_called_once_with(1)

# Fase 5: Pruebas de Integración de Flujo Completo
#Las pruebas finales verifican escenarios completos end-to-end:
class TestDocumentServiceIntegration(unittest.TestCase):
    @patch('src.repositories.document_repository.DocumentRepository')
    @patch('src.utils.chromadb_connector.ChromaDBConnector')
    def test_search_documents(self, mock_chromadb_class, mock_repo_class):
        """Prueba la búsqueda de documentos"""
        # Configurar mocks
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        mock_chromadb = MagicMock()
        mock_chromadb_class.return_value = mock_chromadb
        
        # Simular resultados de búsqueda
        mock_chromadb.search_documents.return_value = {
            'ids': [['1_0', '2_0']],
            'documents': [['Contenido del chunk 1', 'Contenido del chunk 2']],
            'metadatas': [[
                {'document_id': '1', 'title': 'Doc 1', 'document_type': 'texto', 'user_id': '1'},
                {'document_id': '2', 'title': 'Doc 2', 'document_type': 'pdf', 'user_id': '1'}
            ]],
            'distances': [[0.1, 0.2]]
        }
        
        # Simular documentos recuperados
        def get_mock_doc(doc_id):
            if doc_id == 1:
                mock = MagicMock()
                mock.id = 1
                mock.title = "Doc 1"
                return mock
            elif doc_id == 2:
                mock = MagicMock()
                mock.id = 2
                mock.title = "Doc 2"
                return mock
        
        mock_repo.get.side_effect = get_mock_doc
        
        # Probar búsqueda
        from src.services.document_service import DocumentService
        service = DocumentService()
        service.document_repo = mock_repo
        service.chromadb = mock_chromadb
        
        results = service.search_documents("texto de búsqueda")
        
        # Verificar
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["document_id"], 1)
        self.assertEqual(results[0]["title"], "Doc 1")

if __name__ == "__main__":
    unittest.main()