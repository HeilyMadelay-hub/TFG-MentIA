"""
Servicio para la gestión de documentos en la aplicación.
Este módulo implementa la lógica de negocio relacionada con documentos:
- Creación, lectura, actualización y eliminación de documentos
- Procesamiento de documentos (división en chunks)
- Almacenamiento de documentos en ChromaDB
- Búsqueda semántica en documentos
"""
from typing import List, Dict, Any, Optional
import uuid
import logging
import re
import tempfile
import os
from datetime import datetime, UTC, timezone
from src.config.database import get_supabase_client
import concurrent.futures
import string

# Importaciones de tu proyecto
from src.utils.chromadb_connector import ChromaDBConnector
from src.utils.ai_connector import get_openai_connector
from src.repositories.document_repository import DocumentRepository
from src.repositories.user_repository import UserRepository
from src.models.domain import Document
from src.services.local_storage_service import local_storage
from src.services.signed_url_service import signed_url_service

# Importar excepciones personalizadas
from src.core.exceptions import (
    DocumentNotFoundException,
    UserNotFoundException,
    ValidationException,
    ForbiddenException,
    DatabaseException,
    ExternalServiceException
)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentService:
    """
    Servicio para gestionar todas las operaciones relacionadas con documentos.
    Implementa la lógica de negocio para documentos, incluyendo el almacenamiento
    en bases de datos vectoriales y relacionales.
    """
    
    def __init__(self):
        """
        Inicializa el servicio con las dependencias necesarias:
        - ChromaDB para almacenamiento vectorial
        - Repositorio de documentos para almacenamiento relacional
        """
        self.chromadb = ChromaDBConnector()
        self.openai = get_openai_connector()
        self.document_repo = DocumentRepository() 
        self.user_repo = UserRepository()  # Añadir el repositorio de usuarios
        self.collection_name = "documents"  # Colección por defecto en ChromaDB

    def _generate_signed_url_for_document(self, document: Document, expiration_hours: int = 24) -> Optional[str]:
        """
        Genera una URL firmada para un documento si tiene archivo asociado.
        
        Args:
            document: Documento para el cual generar la URL
            expiration_hours: Horas de validez de la URL
            
        Returns:
            str: URL firmada o None si no hay archivo
        """
        try:
            if not document or not hasattr(document, 'file_url') or not document.file_url:
                return None
            
            # Extraer la ruta del archivo de la URL original
            # La URL tiene formato: http://localhost:2690/api/files/{user_id}/{filename}
            parts = document.file_url.split('/api/files/')
            if len(parts) > 1:
                file_path = parts[1]  # user_id/filename
            else:
                # Si no tiene el formato esperado, intentar construir la ruta
                file_path = f"{document.uploaded_by}/{document.id}_{document.original_filename}"
            
            # Generar URL firmada
            signed_url = signed_url_service.generate_signed_url(
                document_id=document.id,
                user_id=document.uploaded_by,
                file_path=file_path,
                expiration_hours=expiration_hours
            )
            
            return signed_url
            
        except Exception as e:
            logger.error(f"Error generando URL firmada para documento {document.id}: {str(e)}")
            return document.file_url  # Fallback a URL original
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extrae texto de un archivo PDF desde bytes.
        
        Args:
            pdf_content: Contenido del PDF en bytes
            
        Returns:
            str: Texto extraído del PDF
            
        Raises:
            ExternalServiceException: Si no hay librerías de PDF disponibles
            ValidationException: Si no se puede extraer texto del PDF
        """
        try:
            import PyPDF2
            import io
            
            # Crear un objeto de archivo desde bytes
            pdf_file = io.BytesIO(pdf_content)
            
            # Crear un objeto PdfReader
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extraer texto de todas las páginas
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            # Limpiar el texto extraído
            text = self._clean_extracted_text(text)
            
            if not text.strip():
                logger.warning("No se pudo extraer texto del PDF")
                return ""
                
            logger.info(f"Texto extraído del PDF: {len(text)} caracteres")
            return text
            
        except ImportError:
            logger.error("PyPDF2 no está instalado. Instálelo con: pip install PyPDF2")
            try:
                # Fallback con pdfplumber
                import pdfplumber
                import io
                
                with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                    text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                
                text = self._clean_extracted_text(text)
                logger.info(f"Texto extraído del PDF con pdfplumber: {len(text)} caracteres")
                return text
                
            except ImportError:
                logger.error("No hay librerías de PDF disponibles. Instale PyPDF2 o pdfplumber")
                raise ExternalServiceException(
                    "PDF Processing",
                    "No se puede procesar archivos PDF. Falta librería PyPDF2 o pdfplumber"
                )
                
        except Exception as e:
            logger.error(f"Error al extraer texto del PDF: {str(e)}")
            raise ValidationException(f"Error al procesar PDF: {str(e)}")

    def _clean_extracted_text(self, text: str) -> str:
        """
        Limpia el texto extraído de archivos PDF.
        """
        if not text:
            return ""
        
        # Eliminar caracteres de control y espacios extra
        text = re.sub(r'\x00', '', text)  # Eliminar caracteres nulos
        text = re.sub(r'\s+', ' ', text)  # Normalizar espacios
        text = text.strip()
        
        return text

    def store_original_file(self, file_content: bytes, filename: str, document_id: int, user_id: int) -> str:
        """
        Almacena el archivo original localmente y retorna la URL.
        
        Args:
            file_content: Contenido del archivo en bytes
            filename: Nombre original del archivo
            document_id: ID del documento
            user_id: ID del usuario que sube el archivo
            
        Returns:
            str: URL del archivo almacenado
            
        Raises:
            ExternalServiceException: Si no se puede almacenar el archivo
        """
        try:
            logger.info(f"Almacenando archivo localmente: {filename}")
            
            # Usar el servicio de almacenamiento local
            relative_path = local_storage.store_file(
                file_content=file_content,
                filename=filename,
                user_id=user_id
            )
            
            if not relative_path:
                raise ExternalServiceException(
                    "Local Storage",
                    "No se pudo almacenar el archivo localmente"
                )
            
            # Generar URL para acceder al archivo
            base_url = os.getenv("API_BASE_URL", "http://localhost:2690")
            # Cambiar formato de URL para usar el nuevo endpoint
            file_url = f"{base_url}/api/files/{user_id}/{os.path.basename(relative_path)}"
            
            logger.info(f"✅ Archivo almacenado exitosamente: {file_url}")
            return file_url
            
        except ExternalServiceException:
            raise
        except Exception as e:
            logger.error(f"❌ Error al almacenar archivo: {str(e)}")
            self.update_document_status(document_id, "error", f"Error al almacenar archivo: {str(e)}")
            raise ExternalServiceException(
                "Local Storage",
                f"Error al almacenar archivo: {str(e)}"
            )

    def _get_content_type_from_extension(self, extension: str) -> str:
        """
        Obtiene el content-type basado en la extensión del archivo.
        """
        content_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel'
        }
        return content_types.get(extension.lower(), 'application/octet-stream')

    def _is_valid_text_content(self, content: str) -> bool:
        """
        Valida si el contenido de texto es válido.
        
        Args:
            content: Contenido a validar
            
        Returns:
            bool: True si el contenido es válido
        """
        if not content or not content.strip():
            return False
        
        # Verificar que tenga al menos 10 caracteres
        if len(content.strip()) < 10:
            return False
        
        # Verificar que no sea solo caracteres especiales
        clean_content = re.sub(r'[^\w\s]', '', content)
        if len(clean_content.strip()) < 5:
            return False
        
        return True

    def create_document(self, uploaded_by: int, title: str, content: str, 
                   content_type: str, tags: Optional[List[str]] = None, file_url: Optional[str] = None) -> Document:
        """
        Crea un nuevo documento y lo almacena tanto en la base de datos relacional
        como en la base de datos vectorial (ChromaDB).
        
        Raises:
            ValidationException: Si los datos no son válidos
            ExternalServiceException: Si hay error con servicios externos
            DatabaseException: Si hay error de base de datos
        """
        supabase_document_id = None
        try:
            # Si hay una URL de archivo y no hay contenido, descargar el archivo
            if file_url and (not content or content.strip() == ""):
                logger.info(f"Descargando contenido del archivo: {file_url}")
                
                try:
                    import requests
                    
                    # Descargar el archivo
                    response = requests.get(file_url, timeout=30)
                    response.raise_for_status()
                    
                    # Extraer contenido según el tipo
                    if content_type == "text/plain":
                        content = response.text
                        logger.info(f"Contenido de texto extraído: {len(content)} caracteres")
                    elif content_type == "application/pdf":
                        content = self.extract_text_from_pdf(response.content)
                        logger.info(f"Contenido de PDF extraído: {len(content)} caracteres")
                    else:
                        logger.warning(f"Tipo de contenido no soportado: {content_type}")
                        content = ""
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error al descargar archivo desde {file_url}: {str(e)}")
                    raise ExternalServiceException(
                        "File Download",
                        f"No se pudo descargar el archivo: {str(e)}"
                    )
            
            # Validar que tenemos contenido para procesar
            if not content or content.strip() == "":
                raise ValidationException("No hay contenido para procesar")
            
            # 1. Procesar el documento
            chunks = self._split_text_into_chunks(content)
            
            document = Document(
                uploaded_by=uploaded_by,  
                title=title,
                content_type=content_type,
                file_url=file_url,  # Añadir la URL del archivo
                content=content,  # IMPORTANTE: Incluir el contenido
                created_at=datetime.now(UTC),  
                updated_at=datetime.now(UTC)
            )
            
            # 3. Guardar en la base de datos relacional
            supabase_document_id = self.document_repo.create(document)
            document.id = supabase_document_id
            
            # 4. Preparar para guardar en ChromaDB
            document_chunks = []
            document_ids = []
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document.id}_{i}"
                document_chunks.append(chunk)
                document_ids.append(chunk_id)
                metadatas.append({
                    "document_id": str(document.id),
                    "title": title,
                    "chunk_index": i,
                    "content_type": content_type,
                    "user_id": str(uploaded_by),  # IMPORTANTE: Guardar user_id
                    "tags": ",".join(tags) if tags else ""
                })
                
            # Log para verificar metadatos
            logger.info(f"\n=== Indexando documento en ChromaDB ===")
            logger.info(f"Document ID: {document.id}")
            logger.info(f"User ID: {uploaded_by}")
            logger.info(f"Número de chunks: {len(document_chunks)}")
            if metadatas:
                logger.info(f"Metadata del primer chunk: {metadatas[0]}")
            
            # 5. Almacenar en ChromaDB
            try:
                self.chromadb.add_documents(
                    collection_name=self.collection_name,
                    document_ids=document_ids,
                    chunks=document_chunks,
                    metadatas=metadatas
                )
            except Exception as chroma_error:
                # Si falla en ChromaDB, eliminar el documento de Supabase para mantener consistencia
                if supabase_document_id:
                    try:
                        self.document_repo.delete(supabase_document_id)
                    except Exception as cleanup_error:
                        # Registrar el error de limpieza pero propagar el error original
                        logger.error(f"Error al eliminar documento {supabase_document_id} durante recuperación: {cleanup_error}")
                
                # Propagar el error como ExternalServiceException
                raise ExternalServiceException("ChromaDB", f"Error al guardar en ChromaDB: {chroma_error}")
            
            # 6. Actualizar el documento con la referencia a ChromaDB
            if document_ids:
                document.chromadb_id = document_ids[0].split("_")[0]  # Usar la parte del ID común
                self.document_repo.update(document)
            else:
                logger.warning("No se pudieron crear IDs de documento para ChromaDB")
            
            logger.info(f"Documento creado con éxito: {document.id}")
            return document
            
        except (ValidationException, ExternalServiceException, DatabaseException):
            # Re-lanzar excepciones conocidas
            raise
        except Exception as e:
            # Si ocurre un error en cualquier punto después de crear el documento en Supabase
            if supabase_document_id and "Error al guardar en ChromaDB" not in str(e):
                try:
                    # Intenta eliminar el documento de Supabase para evitar inconsistencias
                    self.document_repo.delete(supabase_document_id)
                except Exception as cleanup_error:
                    logger.error(f"Error al limpiar documento {supabase_document_id} después de error: {cleanup_error}")
            
            logger.error(f"Error al crear documento: {str(e)}")
            raise DatabaseException("Error al crear documento", original_error=e)
        
    def get_document(self, document_id: int) -> Document:
        """
        Obtiene un documento por su ID desde la base de datos relacional.
        
        Args:
            document_id: ID del documento a recuperar
            
        Returns:
            Document: El documento recuperado
            
        Raises:
            DocumentNotFoundException: Si el documento no existe
            DatabaseException: Si hay error de base de datos
        """
        # El repository ahora lanza DocumentNotFoundException si no existe
        # No necesitamos verificar None
        return self.document_repo.get(document_id)
    
    def update_document(self, document_id: int, title: Optional[str] = None, 
                        content: Optional[str] = None, tags: Optional[List[str]] = None,
                        file_url: Optional[str] = None) -> Document:
        """
        Actualiza un documento existente.
        
        Raises:
            DocumentNotFoundException: Si el documento no existe
            ValidationException: Si los datos no son válidos
            ExternalServiceException: Si hay error con ChromaDB
            DatabaseException: Si hay error de base de datos
        """
        try:
            # 1. Obtener el documento actual (lanza DocumentNotFoundException si no existe)
            document = self.document_repo.get(document_id)
            
            # 2. Actualizar los campos necesarios
            if title is not None:
                document.title = title
            
            # Verificar si hay cambio de contenido
            content_changed = content is not None
            if content_changed:
                document.content = content
            
            if file_url is not None:
                # Garantizar que el atributo existe en el objeto
                if not hasattr(document, 'file_url'):
                    # Agregar dinámicamente el atributo si no existe
                    setattr(document, 'file_url', file_url)
                else:
                    document.file_url = file_url
                    
                # Log detallado para verificar
                logger.info(f"URL del archivo asignada a documento {document_id}: {file_url}")
                
                # Verificación adicional
                logger.info(f"Después de asignar, document.file_url = {getattr(document, 'file_url', 'NO EXISTE')}")
            
            # Actualizar tags solo si se proporcionan y el atributo existe
            if tags is not None and hasattr(document, 'tags'):
                document.tags = tags
            
                
            document.updated_at = datetime.now(UTC)

            # 3. Añadir actualización explícita de file_url
            # Esta es la clave: pasar explícitamente el file_url al repositorio
            update_success = self.document_repo.update_with_url(
                document, 
                file_url=file_url if file_url is not None else getattr(document, 'file_url', None)
            )
            
            if not update_success:
                logger.error(f"Fallo al actualizar documento {document_id} en la base de datos")
                raise DatabaseException(f"No se pudo actualizar el documento {document_id}")
            
            # 4. Si cambió el contenido, actualizar ChromaDB
            if content_changed and content:
                logger.info(f"📝 Actualizando contenido para documento {document_id}")
                logger.info(f"   - Longitud del contenido: {len(content)} caracteres")
                if not content.strip():
                    logger.warning(f"❌ Contenido vacío para documento {document_id}")
                    return document
                if document.content_type == "text/plain" and not self._is_valid_text_content(content):
                    logger.warning(f"Contenido de texto no válido para documento {document_id}")
                    return document
                # Eliminar chunks antiguos
                self._delete_document_chunks(document_id)
                # Crear nuevos chunks
                try:
                    chunks = self._split_text_into_chunks(
                        content, 
                        content_type=document.content_type
                    )
                    logger.info(f"✅ Generados {len(chunks)} chunks para documento {document_id}")
                    for i, chunk in enumerate(chunks[:3]):
                        logger.debug(f"   Chunk {i}: {chunk[:100]}...")
                except Exception as chunk_error:
                    logger.error(f"❌ Error generando chunks: {str(chunk_error)}")
                    raise ValidationException(f"Error generando chunks: {str(chunk_error)}")
                
                if not chunks:
                    logger.warning(f"No se generaron chunks para el documento {document_id}")
                    return document
                
                document_chunks = []
                document_ids = []
                metadatas = []
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{document_id}_{i}"
                    document_chunks.append(chunk)
                    document_ids.append(chunk_id)
                    tags_value = ""
                    if hasattr(document, 'tags') and document.tags:
                        tags_value = ",".join(document.tags)
                    metadatas.append({
                        "document_id": str(document_id),
                        "title": document.title,
                        "chunk_index": i,
                        "content_type": document.content_type,
                        "user_id": str(document.uploaded_by),
                        "tags": tags_value,
                        "default": "true"
                    })
                try:
                    self.chromadb.add_documents(
                        collection_name=self.collection_name,
                        document_ids=document_ids,
                        chunks=document_chunks,
                        metadatas=metadatas
                    )
                    logger.info(f"✅ Documento {document_id} indexado en ChromaDB con {len(document_ids)} chunks")
                except Exception as chromadb_error:
                    logger.error(f"❌ Error al indexar en ChromaDB: {str(chromadb_error)}")
                    raise ExternalServiceException("ChromaDB", f"Error al indexar en ChromaDB: {str(chromadb_error)}")
                
                if document_ids:
                    document.chromadb_id = str(document_id)
                    update_success = self.document_repo.update(document)
                    if not update_success:
                        logger.warning(f"No se pudo actualizar chromadb_id en documento {document_id}")
                else:
                    logger.warning("No se pudieron crear IDs de documento para ChromaDB")
            
            logger.info(f"Documento actualizado con éxito: {document.id}")
            return document
            
        except (DocumentNotFoundException, ValidationException, ExternalServiceException):
            raise
        except Exception as e:
            logger.error(f"Error al actualizar documento {document_id}: {str(e)}")
            raise DatabaseException(f"Error al actualizar documento {document_id}", original_error=e)

    def verify_document_indexed(self, document_id: int) -> bool:
        """
        Verifica si un documento está correctamente indexado en ChromaDB
        """
        try:
            where_filter = {"document_id": str(document_id)}
            results = self.chromadb.search_documents(
                collection_name=self.collection_name,
                query_text="test",  # Query dummy
                n_results=1,
                where=where_filter
            )
            is_indexed = results and 'metadatas' in results and len(results['metadatas'][0]) > 0
            logger.info(f"Documento {document_id} indexado: {is_indexed}")
            return is_indexed
        except Exception as e:
            logger.error(f"Error verificando indexación: {str(e)}")
            return False
    
    def _delete_document_chunks(self, document_id: int):
        """
        Elimina todos los chunks de un documento en ChromaDB según su document_id.
        """
        try:
            # Buscar todos los chunks con el document_id
            where_filter = {"document_id": str(document_id)}
            # Buscar los metadatos para obtener los ids de los chunks
            results = self.chromadb.search_documents(
                collection_name=self.collection_name,
                query_text="test",  # Query dummy
                n_results=1000,
                where=where_filter
            )
            # Extraer los ids de los chunks
            chunk_ids = []
            if results and 'ids' in results:
                for ids_list in results['ids']:
                    chunk_ids.extend(ids_list)
            if chunk_ids:
                self.chromadb.delete_documents(self.collection_name, chunk_ids)
                logger.info(f"Eliminados {len(chunk_ids)} chunks de documento {document_id} en ChromaDB")
            else:
                logger.info(f"No se encontraron chunks para eliminar del documento {document_id} en ChromaDB")
        except Exception as e:
            logger.error(f"Error al eliminar chunks de documento {document_id} en ChromaDB: {str(e)}")
    
    def split_text_into_chunks(self, text: str, content_type: str = None, max_chunk_size: int = 1000, overlap: int = 100) -> list:
        """
        Divide el texto en chunks optimizados para indexación en ChromaDB.
        - max_chunk_size: tamaño máximo de cada chunk (por defecto 1000)
        - overlap: solapamiento entre chunks (por defecto 100)
        - Si el tipo es 'text/plain', usa chunks más grandes y menos solapamiento.
        """
        if content_type == "text/plain":
            max_chunk_size = 2000
            overlap = 50
        if not text:
            return []
        chunks = []
        start = 0
        text_length = len(text)
        while start < text_length:
            end = min(start + max_chunk_size, text_length)
            chunk = text[start:end]
            chunks.append(chunk)
            if end == text_length:
                break
            start += max_chunk_size - overlap
        return chunks
    
    def _split_text_into_chunks(self, text: str, content_type: str = None, max_chunk_size: int = 1000, overlap: int = 100) -> list:
        """
        Divide el texto en chunks optimizados para indexación en ChromaDB (privado, para uso interno).
        - max_chunk_size: tamaño máximo de cada chunk (por defecto 1000)
        - overlap: solapamiento entre chunks (por defecto 100)
        - Si el tipo es 'text/plain', usa chunks más grandes y menos solapamiento.
        """
        if content_type == "text/plain":
            max_chunk_size = 2000
            overlap = 50
        if not text:
            return []
        chunks = []
        start = 0
        text_length = len(text)
        while start < text_length:
            end = min(start + max_chunk_size, text_length)
            chunk = text[start:end]
            chunks.append(chunk)
            if end == text_length:
                break
            start += max_chunk_size - overlap
        return chunks

    def list_user_documents(self, user_id: int, skip: int = 0, limit: int = 100, sort_by: str = 'created_at', order: str = 'desc') -> list:
        """
        Devuelve la lista de documentos subidos por un usuario.
        
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            return self.document_repo.list_by_user(user_id, limit=limit, offset=skip, sort_by=sort_by, order=order)
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Error al listar documentos del usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al listar documentos del usuario {user_id}", original_error=e)

    def get_shared_documents(self, user_id: int, skip: int = 0, limit: int = 100) -> list:
        """
        Devuelve la lista de documentos compartidos con el usuario.
        
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            return self.document_repo.get_shared_documents(user_id, limit=limit, offset=skip)
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Error al listar documentos compartidos para el usuario {user_id}: {str(e)}")
            raise DatabaseException(f"Error al listar documentos compartidos del usuario {user_id}", original_error=e)

    def create_document_placeholder(self, uploaded_by: int, title: str, content_type: str, file_size: int = None, filename: str = None, file_url: str = None) -> Document:
        """
        Crea un documento placeholder (sin contenido, solo metadatos iniciales).
        
        Raises:
            ValidationException: Si los datos no son válidos
            DatabaseException: Si hay error de base de datos
        """
        try:
            document = Document(
                uploaded_by=uploaded_by,
                title=title,
                content_type=content_type,
                file_url=file_url,
                file_size=file_size,
                original_filename=filename,
                content="",
                status="pending",
                status_message="Procesando...",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            document_id = self.document_repo.create_placeholder(document)
            document.id = document_id
            return document
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al crear documento placeholder: {str(e)}")
            raise DatabaseException("Error al crear documento placeholder", original_error=e)

    def get_rag_response(self, query: str, user_id: int = None, n_results: int = 5, document_ids: Optional[List[int]] = None) -> dict:
        """
        Realiza una búsqueda semántica en ChromaDB y retorna la respuesta generada por el modelo AI.

        Args:
            query: Texto de búsqueda
            user_id: ID del usuario (usado para filtrar documentos si no se especifican document_ids)
            n_results: Número de resultados a obtener
            document_ids: Lista opcional de IDs de documentos para filtrar la búsqueda

        Returns:
            dict: Diccionario con contexto, respuesta y documentos usados
        """
        try:
            # Construir filtro where
            where_filter = {}

            # Si se especifican document_ids, filtrar por ellos
            if document_ids:
                # Convertir IDs a string y crear filtro OR
                doc_id_strings = [str(doc_id) for doc_id in document_ids]
                where_filter = {"document_id": {"$in": doc_id_strings}}
                logger.info(f"\n=== BÚSqueda con documentos específicos ===")
                logger.info(f"Document IDs: {document_ids}")
                logger.info(f"Filtro ChromaDB: {where_filter}")
            elif user_id:
                # Si no hay document_ids pero sí user_id, filtrar por documentos del usuario
                where_filter = {"user_id": str(user_id)}
                logger.info(f"\n=== BúSqueda en todos los documentos del usuario ===")
                logger.info(f"User ID: {user_id}")
                logger.info(f"Filtro ChromaDB: {where_filter}")

            # Buscar chunks relevantes en ChromaDB
            results = self.chromadb.search_documents(
                collection_name=self.collection_name,
                query_text=query,
                n_results=n_results,
                where=where_filter if where_filter else None
            )
            
            # Log de resultados encontrados
            logger.info(f"\n=== Resultados de ChromaDB ===")
            if results and 'documents' in results:
                logger.info(f"Chunks encontrados: {len(results.get('documents', [[]])[0])}")
            else:
                logger.info("No se encontraron resultados")

            # Extraer texto y metadatos de los chunks
            chunks = []
            documents_used = []
            seen_docs = set()

            if results and 'documents' in results and 'metadatas' in results:
                for doc_list, meta_list in zip(results['documents'], results['metadatas']):
                    for doc, meta in zip(doc_list, meta_list):
                        chunks.append(doc)

                        # Recopilar información de documentos únicos usados
                        doc_id = meta.get('document_id')
                        if doc_id and doc_id not in seen_docs:
                            seen_docs.add(doc_id)
                            documents_used.append({
                                'document_id': doc_id,
                                'title': meta.get('title', 'Sin título'),
                                'content_type': meta.get('content_type', 'unknown')
                            })

            # Si no hay chunks, devolver respuesta vacía
            if not chunks:
                logger.info(f"No se encontraron documentos relevantes para la consulta: {query}")
                return {
                    "context": "",
                    "response": "No encontré información relevante en los documentos disponibles para responder tu pregunta.",
                    "documents": []
                }

            # Construir contexto
            context = "\n\n".join(chunks)

            # Preparar prompt para el modelo AI
            system_prompt = """Eres un asistente útil que responde preguntas basándose en el contexto proporcionado. \
            Si la información no está en el contexto, indícalo claramente. \
            Responde de manera clara, concisa y profesional."""

            user_prompt = f"""Contexto de los documentos:
        {context}

        Pregunta del usuario: {query}

        Por favor, responde basándote en el contexto proporcionado."""

            # Llamar al modelo AI para generar respuesta
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]

                ai_response = self.openai.generate_chat_completion(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
            except Exception as ai_error:
                logger.error(f"Error al generar respuesta con AI: {str(ai_error)}")
                ai_response = "Lo siento, hubo un error al generar la respuesta. Por favor, intenta de nuevo."

            return {
                "context": context,
                "response": ai_response,
                "documents": documents_used
            }

        except Exception as e:
            logger.error(f"Error en get_rag_response: {str(e)}")
            return {
                "context": "",
                "response": "Error al procesar la consulta. Por favor, intenta de nuevo.",
                "documents": []
            }
    
    def update_document_status(self, document_id: int, status: str, message: Optional[str] = None) -> None:
        """
        Actualiza el estado de un documento en la base de datos.

        Args:
            document_id: ID del documento a actualizar.
            status: Nuevo estado del documento.
            message: Mensaje opcional para describir el estado.
            
        Raises:
            DocumentNotFoundException: Si el documento no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Obtener el documento actual (lanza DocumentNotFoundException si no existe)
            document = self.document_repo.get(document_id)

            # Actualizar el estado y el mensaje
            document.status = status
            if message is not None:
                document.status_message = message
            document.updated_at = datetime.now(UTC)

            # Guardar los cambios en la base de datos
            update_success = self.document_repo.update_status(document)
            if not update_success:
                raise DatabaseException(f"No se pudo actualizar el estado del documento {document_id}")

            logger.info(f"Estado del documento {document_id} actualizado a '{status}' con mensaje: '{message}'")
        except (DocumentNotFoundException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al actualizar el estado del documento {document_id}: {str(e)}")
            raise DatabaseException(f"Error al actualizar estado del documento {document_id}", original_error=e)

    def search_documents(self, query: str, user_id: int, n_results: int = 5, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Busca documentos por contenido usando búsqueda semántica.
        
        Raises:
            ExternalServiceException: Si hay error con ChromaDB
        """
        try:
            # Construir filtro para el usuario
            where_filter = {"user_id": str(user_id)}
            
            # Agregar filtro de tags si se especifica
            if tags:
                where_filter["tags"] = {"$in": tags}
            
            # Buscar en ChromaDB
            results = self.chromadb.search_documents(
                collection_name=self.collection_name,
                query_text=query,
                n_results=n_results,
                where=where_filter
            )
            
            # Procesar resultados
            search_results = []
            if results and 'documents' in results and 'metadatas' in results:
                for i, (docs, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
                    for j, (doc, meta) in enumerate(zip(docs, metadata)):
                        search_results.append({
                            "document_id": meta.get("document_id"),
                            "title": meta.get("title"),
                            "content_snippet": doc[:200] + "..." if len(doc) > 200 else doc,
                            "content_type": meta.get("content_type"),
                            "relevance_score": results.get('distances', [[]])[i][j] if 'distances' in results else 0
                        })
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error en búsqueda de documentos: {str(e)}")
            raise ExternalServiceException("ChromaDB", f"Error en búsqueda: {str(e)}")

    def share_document(self, document_id: int, user_ids: List[int], requester_id: int) -> Dict[str, Any]:
        """
        Comparte un documento con usuarios específicos, validando duplicados.
        
        Args:
            document_id: ID del documento a compartir
            user_ids: Lista de IDs de usuarios con quienes compartir (ya validados)
            requester_id: ID del usuario que solicita compartir
            
        Returns:
            Dict con información sobre el resultado de la operación
            
        Raises:
            DocumentNotFoundException: Si el documento no existe
            ForbiddenException: Si no tiene permisos
            ValidationException: Si hay errores de validación
            DatabaseException: Si hay error de base de datos
        """
        try:
            logger.info(f"=== DocumentService.share_document ===")
            logger.info(f"Document ID: {document_id}")
            logger.info(f"User IDs to share: {user_ids}")
            logger.info(f"Requester ID: {requester_id}")
            
            # get() ahora lanza DocumentNotFoundException si no existe
            document = self.document_repo.get(document_id)
            
            logger.info(f"Documento encontrado: {document.title}, owner: {document.uploaded_by}")
            
            # Verificar permisos (propietario o admin)
            is_owner = document.uploaded_by == requester_id
            is_admin = self.is_admin_user(requester_id)
            
            logger.info(f"Is owner: {is_owner}, Is admin: {is_admin}")
            
            if not is_owner and not is_admin:
                logger.error(f"Usuario {requester_id} no tiene permisos para compartir documento {document_id}")
                raise ForbiddenException("No tienes permisos para compartir este documento")
            
            # Compartir el documento
            logger.info(f"Llamando a repository.share_document_with_users...")
            result = self.document_repo.share_document_with_users(document_id, user_ids)
            
            logger.info(f"✅ Resultado de compartir: {result}")
            
            # Validar resultado
            if result["total_new_shares"] == 0 and result["total_already_shared"] == 0:
                raise DatabaseException("No se pudo compartir el documento con ningún usuario")
                
            return result
            
        except (DocumentNotFoundException, ForbiddenException, ValidationException, DatabaseException):
            # Re-lanzar excepciones conocidas
            raise
        except Exception as e:
            logger.error(f"Error inesperado al compartir documento: {str(e)}")
            raise DatabaseException(f"Error al compartir documento: {str(e)}", original_error=e)
    
    def get_existing_shares(self, document_id: int, user_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Obtiene información sobre usuarios que ya tienen acceso al documento.
        
        Args:
            document_id: ID del documento
            user_ids: Lista de IDs de usuarios a verificar
            
        Returns:
            List[Dict]: Lista con información de usuarios que ya tienen acceso
            
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            return self.document_repo.get_existing_shares(document_id, user_ids)
        except Exception as e:
            logger.error(f"Error al obtener shares existentes: {str(e)}")
            raise DatabaseException(f"Error al verificar accesos existentes", original_error=e)

    def link_users_to_document(self, document_id: int, user_ids: List[int], requester_id: int) -> bool:
        """
        Vincula usuarios a un documento.
        """
        result = self.share_document(document_id, user_ids, requester_id)
        return result["total_new_shares"] > 0 or result["total_already_shared"] > 0

    def check_user_access(self, document_id: int, user_id: int) -> bool:
        """
        Verifica si un usuario tiene acceso a un documento.
        
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            return self.document_repo.check_user_access(document_id, user_id)
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Error al verificar acceso: {str(e)}")
            raise DatabaseException("Error al verificar acceso al documento", original_error=e)

    def list_document_users(self, document_id: int, requester_id: int) -> List[Dict[str, Any]]:
        """
        Lista usuarios con acceso a un documento.
        
        Raises:
            ForbiddenException: Si no tiene permisos
            DocumentNotFoundException: Si el documento no existe
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar permisos
            if not self.check_user_access(document_id, requester_id):
                raise ForbiddenException("No tienes permisos para ver los usuarios de este documento")
            
            user_ids = self.document_repo.list_document_users(document_id)
            users = []
            
            for user_id in user_ids:
                user = self.user_repo.get(user_id)
                if user:
                    users.append({
                        "id": user.id,
                        "username": user.username,
                        "email": user.email
                    })
            
            return users
            
        except (ForbiddenException, DocumentNotFoundException):
            raise
        except Exception as e:
            logger.error(f"Error al listar usuarios del documento: {str(e)}")
            raise DatabaseException("Error al listar usuarios del documento", original_error=e)

    def remove_user_access(self, document_id: int, user_id: int, requester_id: int) -> bool:
        """
        Elimina el acceso de un usuario a un documento.
        
        Raises:
            DocumentNotFoundException: Si el documento no existe
            ForbiddenException: Si no tiene permisos
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar que el documento existe (lanza DocumentNotFoundException si no existe)
            document = self.document_repo.get(document_id)
            
            # Verificar permisos (propietario)
            if document.uploaded_by != requester_id:
                raise ForbiddenException("Solo el propietario puede eliminar acceso a este documento")
            
            return self.document_repo.remove_user_access(document_id, user_id)
            
        except (DocumentNotFoundException, ForbiddenException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al eliminar acceso: {str(e)}")
            raise DatabaseException("Error al eliminar acceso del usuario", original_error=e)

    def delete_document(self, document_id: int, requester_id: int) -> bool:
        """
        Elimina un documento del sistema.
        
        Raises:
            DocumentNotFoundException: Si el documento no existe
            ForbiddenException: Si no tiene permisos
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Verificar que el documento existe (lanza DocumentNotFoundException si no existe)
            document = self.document_repo.get(document_id)
            
            # Verificar permisos (propietario o admin)
            if document.uploaded_by != requester_id and not self.is_admin_user(requester_id):
                raise ForbiddenException("No tienes permisos para eliminar este documento")
            
            # Eliminar chunks de ChromaDB
            self._delete_document_chunks(document_id)
            
            # Eliminar de la base de datos
            return self.document_repo.delete(document_id)
            
        except (DocumentNotFoundException, ForbiddenException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"Error al eliminar documento: {str(e)}")
            raise DatabaseException("Error al eliminar documento", original_error=e)

    def is_admin_user(self, user_id: int) -> bool:
        """
        Verifica si un usuario es administrador.
        """
        try:
            user = self.user_repo.get(user_id)
            return user and getattr(user, 'is_admin', False)
        except Exception as e:
            logger.error(f"Error al verificar si es admin: {str(e)}")
            return False
    
    async def get_shared_with_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Document]:
        """
        Obtiene documentos compartidos con un usuario específico.
        
        Args:
            user_id: ID del usuario
            skip: Número de documentos a saltar
            limit: Número máximo de documentos a retornar
            
        Returns:
            List[Document]: Lista de documentos compartidos
        """
        try:
            # Usar el método existente get_shared_documents
            return self.get_shared_documents(user_id, skip=skip, limit=limit)
        except Exception as e:
            logger.error(f"Error obteniendo documentos compartidos: {e}")
            return []
    
    def get_all_documents_for_admin(self, skip: int = 0, limit: int = 1000) -> List[Document]:
        """
        Obtiene TODOS los documentos del sistema para administradores.
        No filtra por usuario, devuelve todos los documentos.
        
        Args:
            skip: Número de documentos a saltar
            limit: Número máximo de documentos a retornar
            
        Returns:
            List[Document]: Lista de todos los documentos del sistema
            
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            logger.info(f"[ADMIN] Obteniendo todos los documentos del sistema (skip={skip}, limit={limit})")
            
            # Obtener todos los documentos sin filtrar por usuario
            documents = self.document_repo.get_all_documents(skip=skip, limit=limit)
            
            logger.info(f"[ADMIN] Total de documentos encontrados: {len(documents)}")
            
            return documents
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener todos los documentos para admin: {str(e)}")
            raise DatabaseException("Error al obtener todos los documentos", original_error=e)
    
    async def user_has_access(self, document_id: int, user_id: int) -> bool:
        """
        Verifica si un usuario tiene acceso a un documento.
        
        Args:
            document_id: ID del documento
            user_id: ID del usuario
            
        Returns:
            bool: True si el usuario tiene acceso
        """
        try:
            # Usar el método existente check_user_access
            return self.check_user_access(document_id, user_id)
        except Exception as e:
            logger.error(f"Error verificando acceso: {e}")
            return False
    
    def list_all_documents(self, limit: int = 100, skip: int = 0, sort_by: str = 'created_at', order: str = 'desc') -> List[Document]:
        """
        Lista TODOS los documentos del sistema (solo para administradores).
        
        Args:
            limit: Número máximo de documentos a retornar
            skip: Número de documentos a saltar
            sort_by: Campo por el cual ordenar
            order: Orden de clasificación (asc, desc)
            
        Returns:
            List[Document]: Lista de todos los documentos
            
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            # Usar el método correcto del repository
            return self.document_repo.list_all_documents(limit=limit, offset=skip)
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Error al listar todos los documentos: {str(e)}")
            raise DatabaseException("Error al listar todos los documentos", original_error=e)
    
    def count_all_documents(self) -> int:
        """
        Cuenta el total de documentos en el sistema.
        
        Returns:
            int: Número total de documentos
            
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            return self.document_repo.count_all()
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Error al contar documentos: {str(e)}")
            raise DatabaseException("Error al contar documentos", original_error=e)
    
    def get_documents_count_by_user(self) -> Dict[str, int]:
        """
        Obtiene el conteo de documentos por usuario.
        
        Returns:
            Dict[str, int]: Diccionario con username como clave y conteo como valor
            
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            return self.document_repo.count_by_user()
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Error al contar documentos por usuario: {str(e)}")
            raise DatabaseException("Error al contar documentos por usuario", original_error=e)
    
    def get_documents_count_by_type(self) -> Dict[str, int]:
        """
        Obtiene el conteo de documentos por tipo de contenido.
        
        Returns:
            Dict[str, int]: Diccionario con content_type como clave y conteo como valor
            
        Raises:
            DatabaseException: Si hay error de base de datos
        """
        try:
            return self.document_repo.count_by_content_type()
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Error al contar documentos por tipo: {str(e)}")
            raise DatabaseException("Error al contar documentos por tipo", original_error=e)
