"""
Funciones helper para endpoints de documentos (versión compatible Windows)
Contiene lógica específica de operaciones complejas separada de los endpoints
"""
import logging
import time
from typing import Tuple, Dict, Any, List

logger = logging.getLogger(__name__)

class DocumentEndpointHelpers:
    """Helpers para endpoints de documentos"""
    
    def __init__(self):
        # Lazy loading para evitar imports circulares
        self.validator = None
        self.file_processor = None
        self.background_processor = None
    
    def _get_validator(self):
        """Lazy loading del validator"""
        if self.validator is None:
            from src.services.document_validation_service import DocumentValidationService
            self.validator = DocumentValidationService()
        return self.validator
    
    def _get_file_processor(self):
        """Lazy loading del file processor"""
        if self.file_processor is None:
            from src.services.file_processing_service import FileProcessingService
            self.file_processor = FileProcessingService()
        return self.file_processor
    
    def _get_background_processor(self):
        """Lazy loading del background processor"""
        if self.background_processor is None:
            from src.services.document_background_processor_win import DocumentBackgroundProcessor
            self.background_processor = DocumentBackgroundProcessor()
        return self.background_processor
    
    async def handle_document_upload(
        self,
        file,  # UploadFile
        title: str,
        current_user,  # User
        document_service,  # DocumentService
        background_tasks  # BackgroundTasks
    ):
        """
        Maneja la subida completa de un documento
        
        Args:
            file: Archivo subido
            title: Título del documento
            current_user: Usuario actual
            document_service: Servicio de documentos
            background_tasks: Tareas en segundo plano
            
        Returns:
            Documento procesado o placeholder
        """
        start_time = time.time()
        
        try:
            # 1. Validaciones iniciales
            validator = self._get_validator()
            content_type = validator.validate_file_type(file)
            validated_title = validator.validate_document_title(title)
            
            # 2. Leer y validar contenido
            file_content = await file.read()
            file_size = validator.validate_file_size(file_content, file.filename)
            
            read_time = time.time() - start_time
            logger.info(f"Lectura y validacion completada en {read_time:.3f} segundos")
            
            # 3. Crear placeholder en BD
            placeholder_doc = document_service.create_document_placeholder(
                uploaded_by=current_user.id,
                title=validated_title,
                content_type=content_type,
                file_size=file_size,
                filename=file.filename
            )
            
            document_id = placeholder_doc.id
            placeholder_time = time.time() - start_time
            logger.info(f"Placeholder creado en {placeholder_time:.3f} segundos")
            
            # 4. Determinar tipo de procesamiento
            should_sync = validator.should_process_synchronously(file_size, content_type)
            
            if should_sync:
                return await self._process_document_synchronously(
                    file_content, file.filename, document_id, content_type,
                    document_service, current_user.id, start_time
                )
            else:
                return await self._process_document_asynchronously(
                    file_content, file.filename, document_id, content_type,
                    document_service, current_user.id, background_tasks
                )
                
        except Exception as e:
            logger.error(f"Error inesperado en upload: {str(e)}", exc_info=True)
            raise Exception(f"Error al procesar el documento: {str(e)}")
    
    async def _process_document_synchronously(
        self,
        file_content: bytes,
        filename: str,
        document_id: int,
        content_type: str,
        document_service,
        user_id: int,
        start_time: float
    ):
        """Procesa un documento de forma síncrona"""
        
        logger.info(f"Procesando archivo pequeno ({len(file_content)/1024:.1f}KB) sincronicamente")
        
        try:
            # 1. Actualizar estado
            document_service.update_document_status(document_id, "processing", "Extrayendo texto...")
            
            # 2. Extraer texto
            file_processor = self._get_file_processor()
            extracted_text = file_processor.extract_text_from_content(
                file_content, content_type, filename
            )
            
            # 3. Validar contenido extraído
            validator = self._get_validator()
            validated_text = validator.validate_content_extraction(
                extracted_text, content_type, filename
            )
            
            extraction_time = time.time() - start_time
            logger.info(f"Extraccion de texto completada en {extraction_time:.3f} segundos")
            
            # 4. Almacenar archivo original
            file_url = document_service.store_original_file(
                file_content=file_content,
                filename=filename,
                document_id=document_id,
                user_id=user_id
            )
            
            storage_time = time.time() - start_time
            logger.info(f"Almacenamiento completado en {storage_time:.3f} segundos")
            
            # 5. Actualizar documento con contenido y generar vectores
            document_service.update_document_status(document_id, "processing", "Generando vectores...")
            document = document_service.update_document(
                document_id=document_id,
                content=validated_text,
                file_url=file_url
            )
            
            vectorization_time = time.time() - start_time
            logger.info(f"Vectorizacion completada en {vectorization_time:.3f} segundos")
            
            # 6. Finalizar
            document_service.update_document_status(document_id, "completed", "Procesamiento completado")
            
            total_time = time.time() - start_time
            logger.info(f"Procesamiento sincrono completado en {total_time:.3f} segundos")
            
            return document_service.get_document(document_id)
            
        except Exception as e:
            logger.error(f"Error en procesamiento sincrono: {str(e)}")
            document_service.update_document_status(document_id, "error", f"Error: {str(e)}")
            raise Exception(f"Error procesando documento: {str(e)}")
    
    async def _process_document_asynchronously(
        self,
        file_content: bytes,
        filename: str,
        document_id: int,
        content_type: str,
        document_service,
        user_id: int,
        background_tasks
    ):
        """Procesa un documento de forma asíncrona"""
        
        logger.info(f"Procesando archivo grande ({len(file_content)/1024/1024:.2f}MB) asincronicamente")
        
        # Agregar tarea en segundo plano
        background_processor = self._get_background_processor()
        background_tasks.add_task(
            background_processor.process_document_background,
            file_content=file_content,
            filename=filename,
            document_id=document_id,
            document_service=document_service,
            user_id=user_id,
            content_type=content_type
        )
        
        # Devolver placeholder para seguimiento
        return document_service.get_document(document_id)
    
    def handle_document_sharing(
        self,
        document_id: int,
        user_ids: List[int],
        current_user,
        document_service
    ) -> Dict[str, Any]:
        """
        Maneja la lógica de compartir documentos
        """
        try:
            # 1. Verificar que el documento existe
            document = document_service.get_document(document_id)
            if not document:
                raise Exception(f"El documento {document_id} no existe")
            
            # 2. Verificar permisos
            validator = self._get_validator()
            validator.validate_user_access(
                document.uploaded_by, current_user, "compartir"
            )
            
            # 3. Validar usuarios a compartir
            valid_users, errors = validator.validate_share_users(user_ids, current_user)
            
            if errors:
                raise Exception("; ".join(errors))
            
            # 4. Realizar el compartir
            logger.info(f"Compartiendo documento {document_id} con usuarios: {valid_users}")
            
            success = document_service.share_document(
                document_id=document_id,
                user_ids=valid_users,
                requester_id=current_user.id
            )
            
            if not success:
                raise Exception("No se pudo compartir el documento")
            
            return {
                "message": f"Documento compartido exitosamente con {len(valid_users)} usuario(s)",
                "shared_with": valid_users,
                "document_id": document_id
            }
            
        except Exception as e:
            logger.error(f"Error compartiendo documento: {str(e)}", exc_info=True)
            raise Exception("Error al compartir el documento")
    
    def handle_document_access_revocation(
        self,
        document_id: int,
        user_id: int,
        current_user,
        document_service
    ) -> Dict[str, str]:
        """
        Maneja la revocación de acceso a documentos
        """
        try:
            # 1. Verificar documento
            document = document_service.get_document(document_id)
            if not document:
                raise Exception(f"El documento {document_id} no existe")
            
            # 2. Verificar permisos
            validator = self._get_validator()
            validator.validate_user_access(
                document.uploaded_by, current_user, "revocar acceso de"
            )
            
            # 3. Revocar acceso
            success = document_service.remove_user_access(
                document_id=document_id,
                user_id=user_id,
                requester_id=current_user.id
            )
            
            if not success:
                raise Exception("No se pudo revocar el acceso")
            
            logger.info(f"Acceso revocado para usuario {user_id} en documento {document_id}")
            
            return {"message": "Acceso revocado exitosamente"}
            
        except Exception as e:
            logger.error(f"Error revocando acceso: {str(e)}", exc_info=True)
            raise Exception("Error al revocar acceso")
    
    def get_processing_summary(self, file_size: int, content_type: str) -> Dict[str, Any]:
        """
        Obtiene un resumen del procesamiento estimado
        
        Args:
            file_size: Tamaño del archivo
            content_type: Tipo de contenido
            
        Returns:
            Dict con información del procesamiento
        """
        background_processor = self._get_background_processor()
        estimation = background_processor.estimate_processing_time(file_size, content_type)
        thresholds = background_processor.get_processing_thresholds()
        
        return {
            "file_info": {
                "size_mb": round(file_size / (1024 * 1024), 2),
                "content_type": content_type
            },
            "processing": estimation,
            "thresholds": thresholds
        }
