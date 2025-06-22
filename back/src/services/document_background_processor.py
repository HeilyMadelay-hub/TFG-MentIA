"""
Servicio de procesamiento asíncrono de documentos
Maneja el procesamiento en background de documentos grandes
"""
import logging
from typing import Optional
from src.services.document_service import DocumentService
from src.services.file_processing_service import FileProcessingService

logger = logging.getLogger(__name__)

class DocumentBackgroundProcessor:
    """Procesador de documentos en segundo plano"""
    
    def __init__(self):
        self.file_processor = FileProcessingService()
    
    async def process_document_background(
        self,
        file_content: bytes,
        filename: str,
        document_id: int,
        document_service: DocumentService,
        user_id: int,
        content_type: str
    ) -> bool:
        """
        Procesa un documento en segundo plano
        
        Args:
            file_content: Contenido del archivo
            filename: Nombre del archivo
            document_id: ID del documento en la BD
            document_service: Servicio de documentos
            user_id: ID del usuario
            content_type: Tipo de contenido
            
        Returns:
            bool: True si el procesamiento fue exitoso
        """
        try:
            logger.info(f"🔄 Iniciando procesamiento en segundo plano para documento {document_id}")
            
            # 1. Actualizar estado inicial
            self._update_status(document_service, document_id, "processing", "Extrayendo texto...")
            
            # 2. Extraer texto según el tipo de archivo
            try:
                extracted_text = self.file_processor.extract_text_from_content(
                    file_content, content_type, filename
                )
                logger.info(f"✅ Texto extraído: {len(extracted_text)} caracteres")
            except Exception as e:
                logger.error(f"❌ Error extrayendo texto: {str(e)}")
                self._update_status(
                    document_service, document_id, "error", 
                    f"Error extrayendo texto: {str(e)}"
                )
                return False
            
            # 3. Almacenar archivo original
            self._update_status(document_service, document_id, "processing", "Almacenando archivo original...")
            
            try:
                file_url = document_service.store_original_file(
                    file_content=file_content,
                    filename=filename,
                    document_id=document_id,
                    user_id=user_id
                )
                logger.info(f"✅ Archivo almacenado en: {file_url}")
            except Exception as e:
                logger.error(f"❌ Error almacenando archivo: {str(e)}")
                self._update_status(
                    document_service, document_id, "error", 
                    f"Error almacenando archivo: {str(e)}"
                )
                return False
            
            # 4. Generar vectores y guardar en ChromaDB
            self._update_status(
                document_service, document_id, "processing", 
                "Generando vectores y guardando en ChromaDB..."
            )
            
            try:
                updated_doc = document_service.update_document(
                    document_id=document_id,
                    content=extracted_text,
                    file_url=file_url
                )
                logger.info(f"✅ Documento actualizado con contenido y vectores")
            except Exception as e:
                logger.error(f"❌ Error actualizando documento: {str(e)}")
                self._update_status(
                    document_service, document_id, "error", 
                    f"Error generando vectores: {str(e)}"
                )
                return False
            
            # 5. Verificar vectorización exitosa
            if not getattr(updated_doc, 'chromadb_id', None):
                logger.warning(f"⚠️ No se asignó chromadb_id al documento {document_id}")
                self._update_status(
                    document_service, document_id, "warning", 
                    "Documento procesado pero sin vectorización completa. "
                    "Podría no estar disponible para búsquedas."
                )
                return False
            
            # 6. Finalizar con éxito
            self._update_status(document_service, document_id, "completed", "Procesamiento completado")
            
            logger.info(f"🎉 Procesamiento en segundo plano completado exitosamente para documento {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"💥 Error crítico en procesamiento de documento {document_id}: {str(e)}", exc_info=True)
            self._update_status(
                document_service, document_id, "error", 
                f"Error crítico: {str(e)}"
            )
            return False
    
    def _update_status(self, document_service: DocumentService, document_id: int, 
                      status: str, message: str) -> None:
        """
        Actualiza el estado de un documento con manejo de errores
        
        Args:
            document_service: Servicio de documentos
            document_id: ID del documento
            status: Nuevo estado
            message: Mensaje de estado
        """
        try:
            document_service.update_document_status(document_id, status, message)
            logger.debug(f"📊 Estado actualizado para documento {document_id}: {status} - {message}")
        except Exception as e:
            logger.error(f"❌ Error actualizando estado de documento {document_id}: {str(e)}")

    def get_processing_thresholds(self) -> dict:
        """
        Obtiene los umbrales de procesamiento configurados
        
        Returns:
            dict: Umbrales para diferentes tipos de archivo
        """
        return {
            "text_threshold_kb": 500,  # 500KB para texto plano
            "pdf_threshold_mb": 1,     # 1MB para PDFs
            "general_threshold_mb": 3,  # 3MB para otros formatos
            "max_file_size_mb": 100    # 100MB límite máximo
        }

    def estimate_processing_time(self, file_size: int, content_type: str) -> dict:
        """
        Estima el tiempo de procesamiento basado en el tamaño y tipo de archivo
        
        Args:
            file_size: Tamaño del archivo en bytes
            content_type: Tipo de contenido
            
        Returns:
            dict: Estimación de tiempo y tipo de procesamiento
        """
        size_mb = file_size / (1024 * 1024)
        
        if content_type == "application/pdf":
            # PDFs son más lentos de procesar
            estimated_minutes = max(1, size_mb * 2)
            process_type = "síncrono" if size_mb < 1 else "asíncrono"
        elif content_type == "text/plain":
            # Texto plano es rápido
            estimated_minutes = max(0.5, size_mb * 0.5)
            process_type = "síncrono" if size_mb < 0.5 else "asíncrono"
        else:
            # Otros formatos (Excel, CSV)
            estimated_minutes = max(1, size_mb * 1.5)
            process_type = "síncrono" if size_mb < 3 else "asíncrono"
        
        return {
            "estimated_minutes": round(estimated_minutes, 1),
            "process_type": process_type,
            "file_size_mb": round(size_mb, 2),
            "content_type": content_type
        }
