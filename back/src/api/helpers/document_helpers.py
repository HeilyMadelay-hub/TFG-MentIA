"""
Funciones helper para endpoints de documentos
Contiene lógica específica de operaciones complejas separada de los endpoints
"""
import logging
import time
from typing import Tuple, Dict, Any, List
from fastapi import UploadFile, BackgroundTasks
from src.models.domain import User
from src.models.schemas.document import DocumentResponseHybrid
from src.services.document_service import DocumentService
from src.services.document_validation_service import DocumentValidationService
from src.services.file_processing_service import FileProcessingService
from src.services.document_background_processor import DocumentBackgroundProcessor
from src.core.exceptions import ValidationException, DatabaseException

logger = logging.getLogger(__name__)

class DocumentEndpointHelpers:
    """Helpers para endpoints de documentos"""
    
    def __init__(self):
        self.validator = DocumentValidationService()
        self.file_processor = FileProcessingService()
        self.background_processor = DocumentBackgroundProcessor()
    
    async def handle_document_upload(
        self,
        file: UploadFile,
        title: str,
        current_user: User,
        document_service: DocumentService,
        background_tasks: BackgroundTasks
    ) -> DocumentResponseHybrid:
        """
        Maneja la subida completa de un documento
        
        Args:
            file: Archivo subido
            title: Título del documento
            current_user: Usuario actual
            document_service: Servicio de documentos
            background_tasks: Tareas en segundo plano
            
        Returns:
            DocumentResponseHybrid: Documento procesado o placeholder
        """
        start_time = time.time()
        
        try:
            # 1. Validaciones iniciales
            content_type = self.validator.validate_file_type(file)
            validated_title = self.validator.validate_document_title(title)
            
            # 2. Leer y validar contenido
            file_content = await file.read()
            file_size = self.validator.validate_file_size(file_content, file.filename)
            
            read_time = time.time() - start_time
            logger.info(f"⏱️ Lectura y validación completada en {read_time:.3f} segundos")
            
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
            logger.info(f"⏱️ Placeholder creado en {placeholder_time:.3f} segundos")
            
            # 4. Determinar tipo de procesamiento
            should_sync = self.validator.should_process_synchronously(file_size, content_type)
            
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
                
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"💥 Error inesperado en upload: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al procesar el documento: {str(e)}")
    
    async def _process_document_synchronously(
        self,
        file_content: bytes,
        filename: str,
        document_id: int,
        content_type: str,
        document_service: DocumentService,
        user_id: int,
        start_time: float
    ) -> DocumentResponseHybrid:
        """Procesa un documento de forma síncrona"""
        
        logger.info(f"🔄 Procesando archivo pequeño ({len(file_content)/1024:.1f}KB) sincrónicamente")
        
        try:
            # 1. Actualizar estado
            document_service.update_document_status(document_id, "processing", "Extrayendo texto...")
            
            # 2. Extraer texto
            extracted_text = self.file_processor.extract_text_from_content(
                file_content, content_type, filename
            )
            
            # 3. Validar contenido extraído
            validated_text = self.validator.validate_content_extraction(
                extracted_text, content_type, filename
            )
            
            extraction_time = time.time() - start_time
            logger.info(f"⏱️ Extracción de texto completada en {extraction_time:.3f} segundos")
            
            # 4. Almacenar archivo original
            file_url = document_service.store_original_file(
                file_content=file_content,
                filename=filename,
                document_id=document_id,
                user_id=user_id
            )
            
            storage_time = time.time() - start_time
            logger.info(f"⏱️ Almacenamiento completado en {storage_time:.3f} segundos")
            
            # 5. Actualizar documento con contenido y generar vectores
            document_service.update_document_status(document_id, "processing", "Generando vectores...")
            document = document_service.update_document(
                document_id=document_id,
                content=validated_text,
                file_url=file_url
            )
            
            vectorization_time = time.time() - start_time
            logger.info(f"⏱️ Vectorización completada en {vectorization_time:.3f} segundos")
            
            # 6. Finalizar
            document_service.update_document_status(document_id, "completed", "Procesamiento completado")
            
            total_time = time.time() - start_time
            logger.info(f"🎉 Procesamiento síncrono completado en {total_time:.3f} segundos")
            
            return document_service.get_document(document_id)
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento síncrono: {str(e)}")
            document_service.update_document_status(document_id, "error", f"Error: {str(e)}")
            raise DatabaseException(f"Error procesando documento: {str(e)}")
    
    async def _process_document_asynchronously(
        self,
        file_content: bytes,
        filename: str,
        document_id: int,
        content_type: str,
        document_service: DocumentService,
        user_id: int,
        background_tasks: BackgroundTasks
    ) -> DocumentResponseHybrid:
        """Procesa un documento de forma asíncrona"""
        
        logger.info(f"🔄 Procesando archivo grande ({len(file_content)/1024/1024:.2f}MB) asincrónicamente")
        
        # Agregar tarea en segundo plano
        background_tasks.add_task(
            self.background_processor.process_document_background,
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
        current_user: User,
        document_service: DocumentService
    ) -> Dict[str, Any]:
        """
        Maneja la lógica de compartir documentos con validación de duplicados
        
        Args:
            document_id: ID del documento
            user_ids: Lista de IDs de usuarios
            current_user: Usuario actual
            document_service: Servicio de documentos
            
        Returns:
            Dict con resultado detallado de la operación
        """
        try:
            # 1. Verificar que el documento existe
            document = document_service.get_document(document_id)
            if not document:
                raise ValidationException(f"El documento {document_id} no existe")
            
            # 2. Verificar permisos
            self.validator.validate_user_access(
                document.uploaded_by, current_user, "compartir"
            )
            
            # 3. Validar usuarios a compartir
            valid_users, errors = self.validator.validate_share_users(user_ids, current_user)
            
            if errors:
                raise ValidationException("; ".join(errors))
            
            # 4. Verificar existencia de usuarios (delegado al servicio)
            logger.info(f"📤 Compartiendo documento {document_id} con usuarios: {valid_users}")
            
            # 5. Realizar el compartir con validación de duplicados
            result = document_service.share_document(
                document_id=document_id,
                user_ids=valid_users,
                requester_id=current_user.id
            )
            
            # 6. Construir mensaje de respuesta basado en el resultado
            if result["total_new_shares"] > 0 and result["total_already_shared"] == 0:
                message = f"Documento compartido exitosamente con {result['total_new_shares']} usuario(s)"
            elif result["total_new_shares"] > 0 and result["total_already_shared"] > 0:
                message = f"Documento compartido con {result['total_new_shares']} nuevo(s) usuario(s). " \
                         f"{result['total_already_shared']} ya tenían acceso"
            elif result["total_new_shares"] == 0 and result["total_already_shared"] > 0:
                message = f"No se realizaron nuevos shares. Todos los usuarios ({result['total_already_shared']}) ya tenían acceso"
            else:
                message = "No se pudo compartir el documento"
                
            # 7. Preparar respuesta completa
            return {
                "success": result["total_new_shares"] > 0 or result["total_already_shared"] > 0,
                "message": message,
                "successful_shares": result["successful_shares"],
                "already_shared": result["already_shared"],
                "failed_shares": result.get("failed_shares", []),
                "share_summary": {
                    "total_requested": result["total_requested"],
                    "already_shared": result["total_already_shared"],
                    "new_shares": result["total_new_shares"],
                    "failed": result["total_failed"]
                },
                "document_id": document_id
            }
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"💥 Error compartiendo documento: {str(e)}", exc_info=True)
            raise DatabaseException("Error al compartir el documento")
    
    def handle_document_access_revocation(
        self,
        document_id: int,
        user_id: int,
        current_user: User,
        document_service: DocumentService
    ) -> Dict[str, str]:
        """
        Maneja la revocación de acceso a documentos
        
        Args:
            document_id: ID del documento
            user_id: ID del usuario al que revocar acceso
            current_user: Usuario actual
            document_service: Servicio de documentos
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # 1. Verificar documento
            document = document_service.get_document(document_id)
            if not document:
                raise ValidationException(f"El documento {document_id} no existe")
            
            # 2. Verificar permisos
            self.validator.validate_user_access(
                document.uploaded_by, current_user, "revocar acceso de"
            )
            
            # 3. Revocar acceso
            success = document_service.remove_user_access(
                document_id=document_id,
                user_id=user_id,
                requester_id=current_user.id
            )
            
            if not success:
                raise DatabaseException("No se pudo revocar el acceso")
            
            logger.info(f"🚫 Acceso revocado para usuario {user_id} en documento {document_id}")
            
            return {"message": "Acceso revocado exitosamente"}
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as e:
            logger.error(f"💥 Error revocando acceso: {str(e)}", exc_info=True)
            raise DatabaseException("Error al revocar acceso")
    
    def get_processing_summary(self, file_size: int, content_type: str) -> Dict[str, Any]:
        """
        Obtiene un resumen del procesamiento estimado
        
        Args:
            file_size: Tamaño del archivo
            content_type: Tipo de contenido
            
        Returns:
            Dict con información del procesamiento
        """
        estimation = self.background_processor.estimate_processing_time(file_size, content_type)
        thresholds = self.background_processor.get_processing_thresholds()
        
        return {
            "file_info": {
                "size_mb": round(file_size / (1024 * 1024), 2),
                "content_type": content_type
            },
            "processing": estimation,
            "thresholds": thresholds
        }
