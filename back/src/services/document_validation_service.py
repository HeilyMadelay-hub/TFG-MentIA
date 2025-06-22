"""
Servicio de validación para documentos
Centraliza todas las validaciones relacionadas con documentos
"""
import logging
from typing import List, Optional, Tuple
from fastapi import UploadFile
from src.core.exceptions import ValidationException, ForbiddenException
from src.models.domain import User

logger = logging.getLogger(__name__)

class DocumentValidationService:
    """Servicio para validaciones de documentos"""
    
    # Configuración de tipos de archivo y límites
    VALID_CONTENT_TYPES = [
        "application/pdf", 
        "text/plain", 
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]
    
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    # Umbrales para procesamiento síncrono/asíncrono
    TEXT_THRESHOLD = 500 * 1024      # 500KB para texto plano
    PDF_THRESHOLD = 1 * 1024 * 1024  # 1MB para PDFs
    GENERAL_THRESHOLD = 3 * 1024 * 1024  # 3MB para otros formatos

    def validate_file_type(self, file: UploadFile) -> str:
        """
        Valida el tipo de archivo
        
        Args:
            file: Archivo subido
            
        Returns:
            str: Content type validado
            
        Raises:
            ValidationException: Si el tipo no está soportado
        """
        content_type = file.content_type
        
        if content_type not in self.VALID_CONTENT_TYPES:
            raise ValidationException(
                f"Tipo de archivo no soportado: {content_type}. "
                f"Tipos permitidos: {', '.join(self.VALID_CONTENT_TYPES)}"
            )
        
        logger.info(f"✅ Tipo de archivo validado: {content_type}")
        return content_type

    def validate_file_size(self, file_content: bytes, filename: str) -> int:
        """
        Valida el tamaño del archivo
        
        Args:
            file_content: Contenido del archivo
            filename: Nombre del archivo
            
        Returns:
            int: Tamaño del archivo en bytes
            
        Raises:
            ValidationException: Si excede el tamaño máximo
        """
        file_size = len(file_content)
        
        if file_size > self.MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            raise ValidationException(
                f"El archivo '{filename}' ({size_mb:.1f}MB) excede el tamaño máximo "
                f"permitido de {max_mb}MB"
            )
        
        logger.info(f"✅ Tamaño de archivo validado: {file_size / 1024:.1f}KB")
        return file_size

    def should_process_synchronously(self, file_size: int, content_type: str) -> bool:
        """
        Determina si un archivo debe procesarse sincrónicamente
        
        Args:
            file_size: Tamaño del archivo en bytes
            content_type: Tipo de contenido
            
        Returns:
            bool: True si debe procesarse sincrónicamente
        """
        is_small_file = (
            (content_type == "application/pdf" and file_size < self.PDF_THRESHOLD) or
            (content_type == "text/plain" and file_size < self.TEXT_THRESHOLD) or
            (content_type not in ["application/pdf", "text/plain"] and file_size < self.GENERAL_THRESHOLD)
        )
        
        process_type = "síncrono" if is_small_file else "asíncrono"
        logger.info(f"📊 Archivo será procesado {process_type} ({file_size/1024:.1f}KB)")
        
        return is_small_file

    def validate_user_access(self, document_uploaded_by: int, current_user: User, 
                           action: str = "acceder") -> bool:
        """
        Valida si un usuario tiene acceso a realizar una acción sobre un documento
        
        Args:
            document_uploaded_by: ID del usuario que subió el documento
            current_user: Usuario actual
            action: Acción que se quiere realizar (para logs)
            
        Returns:
            bool: True si tiene acceso
            
        Raises:
            ForbiddenException: Si no tiene permisos
        """
        is_owner = document_uploaded_by == current_user.id
        is_admin = getattr(current_user, 'is_admin', False)
        
        if not is_owner and not is_admin:
            raise ForbiddenException(
                f"No tienes permisos para {action} este documento"
            )
        
        access_type = "propietario" if is_owner else "administrador"
        logger.info(f"✅ Acceso validado para {action} como {access_type}")
        return True

    def validate_share_users(self, user_ids: List[int], current_user: User) -> Tuple[List[int], List[str]]:
        """
        Valida una lista de IDs de usuarios para compartir documento
        
        Args:
            user_ids: Lista de IDs de usuarios
            current_user: Usuario actual
            
        Returns:
            Tuple[List[int], List[str]]: (usuarios_válidos, errores)
        """
        if not user_ids:
            return [], ["No se especificaron usuarios para compartir"]
        
        # Eliminar duplicados manteniendo orden
        unique_ids = list(dict.fromkeys(user_ids))
        
        # Filtrar auto-compartir
        valid_ids = [uid for uid in unique_ids if uid != current_user.id]
        
        errors = []
        if len(valid_ids) != len(unique_ids):
            errors.append("No puedes compartir un documento contigo mismo")
        
        if not valid_ids:
            errors.append("No se especificaron usuarios válidos para compartir")
        
        logger.info(f"📤 Validación de compartir: {len(valid_ids)} usuarios válidos")
        return valid_ids, errors

    def validate_content_extraction(self, extracted_text: str, content_type: str, 
                                  filename: str) -> str:
        """
        Valida el texto extraído de un archivo
        
        Args:
            extracted_text: Texto extraído del archivo
            content_type: Tipo de contenido del archivo
            filename: Nombre del archivo
            
        Returns:
            str: Texto validado
            
        Raises:
            ValidationException: Si el contenido no es válido
        """
        if not extracted_text or len(extracted_text.strip()) < 10:
            if content_type == "application/pdf":
                raise ValidationException(
                    f"El PDF '{filename}' no contiene texto extraíble o está vacío"
                )
            else:
                raise ValidationException(
                    f"El archivo '{filename}' no contiene contenido válido"
                )
        
        char_count = len(extracted_text)
        logger.info(f"✅ Contenido validado: {char_count} caracteres extraídos")
        return extracted_text.strip()

    def validate_document_title(self, title: str) -> str:
        """
        Valida y normaliza el título de un documento
        
        Args:
            title: Título a validar
            
        Returns:
            str: Título validado y normalizado
            
        Raises:
            ValidationException: Si el título no es válido
        """
        if not title or not title.strip():
            raise ValidationException("El título del documento es obligatorio")
        
        normalized_title = title.strip()
        
        if len(normalized_title) > 200:
            raise ValidationException("El título no puede exceder 200 caracteres")
        
        if len(normalized_title) < 3:
            raise ValidationException("El título debe tener al menos 3 caracteres")
        
        logger.info(f"✅ Título validado: '{normalized_title}'")
        return normalized_title
