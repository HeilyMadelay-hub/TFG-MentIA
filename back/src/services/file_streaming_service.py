"""
Servicio optimizado para procesamiento de archivos grandes con streaming
"""
import asyncio
import os
import io
from pathlib import Path
from typing import AsyncIterator, Optional, Tuple
import logging
import aiofiles
from fastapi import UploadFile, status
import PyPDF2
from src.core.exceptions import ValidationException
import pdfplumber
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class FileStreamingService:
    """
    Servicio para manejar archivos grandes de manera eficiente con streaming
    """
    
    def __init__(self):
        self.chunk_size = settings.STREAMING_CHUNK_SIZE
        self.pdf_chunk_size = settings.PDF_PROCESSING_CHUNK_SIZE
        
        # Límites por tipo de archivo en bytes
        self.file_limits = {
            "application/pdf": settings.MAX_PDF_SIZE_MB * 1024 * 1024,
            "text/plain": settings.MAX_TEXT_SIZE_MB * 1024 * 1024,
            "text/csv": settings.MAX_EXCEL_SIZE_MB * 1024 * 1024,
            "application/vnd.ms-excel": settings.MAX_EXCEL_SIZE_MB * 1024 * 1024,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": settings.MAX_EXCEL_SIZE_MB * 1024 * 1024,
        }
        
        # Tamaño máximo por defecto
        self.max_size = settings.MAX_DOCUMENT_SIZE_BYTES
    
    async def validate_file_size(self, file: UploadFile) -> Tuple[bool, str, int]:
        """
        Valida el tamaño del archivo antes de procesarlo
        
        Returns:
            Tuple[bool, str, int]: (es_válido, mensaje_error, tamaño_archivo)
        """
        # Obtener el límite específico para este tipo de archivo
        max_allowed = self.file_limits.get(file.content_type, self.max_size)
        max_allowed_mb = max_allowed / (1024 * 1024)
        
        # Leer el archivo en chunks para obtener el tamaño sin cargar todo en memoria
        file_size = 0
        chunk_size = 8192  # 8KB chunks para validación
        
        # Guardar posición actual
        current_pos = file.file.tell()
        file.file.seek(0)
        
        while chunk := file.file.read(chunk_size):
            file_size += len(chunk)
            if file_size > max_allowed:
                file.file.seek(current_pos)  # Restaurar posición
                return False, f"El archivo excede el tamaño máximo permitido de {max_allowed_mb:.0f}MB para {file.content_type}", file_size
        
        # Restaurar posición original
        file.file.seek(current_pos)
        
        logger.info(f"📏 Archivo validado: {file.filename} - {file_size/1024/1024:.2f}MB (límite: {max_allowed_mb:.0f}MB)")
        return True, "", file_size
    
    async def stream_file_to_disk(self, file: UploadFile, destination: Path) -> int:
        """
        Guarda un archivo grande en disco usando streaming
        
        Returns:
            int: Tamaño del archivo en bytes
        """
        # Crear directorio si no existe
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        file_size = 0
        
        # Usar aiofiles para escritura asíncrona
        async with aiofiles.open(destination, 'wb') as f:
            # Leer y escribir en chunks
            file.file.seek(0)
            while chunk := await file.read(self.chunk_size):
                await f.write(chunk)
                file_size += len(chunk)
                
                # Log de progreso para archivos grandes
                if file_size % (10 * 1024 * 1024) == 0:  # Cada 10MB
                    logger.info(f"📝 Escribiendo {file.filename}: {file_size/1024/1024:.1f}MB...")
        
        logger.info(f"✅ Archivo guardado: {destination} ({file_size/1024/1024:.2f}MB)")
        return file_size
    
    async def extract_text_from_pdf_streaming(self, file_path: Path, max_pages: Optional[int] = None) -> AsyncIterator[str]:
        """
        Extrae texto de un PDF grande usando streaming por páginas
        
        Args:
            file_path: Ruta al archivo PDF
            max_pages: Número máximo de páginas a procesar (None = todas)
            
        Yields:
            str: Texto extraído de cada página
        """
        total_text_length = 0
        pages_processed = 0
        
        try:
            # Primero intentar con pdfplumber (mejor calidad)
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"📄 PDF abierto: {total_pages} páginas")
                
                for i, page in enumerate(pdf.pages):
                    if max_pages and i >= max_pages:
                        logger.info(f"⚠️ Límite de páginas alcanzado ({max_pages})")
                        break
                    
                    try:
                        # Extraer texto de la página
                        page_text = page.extract_text() or ""
                        
                        if page_text:
                            total_text_length += len(page_text)
                            pages_processed += 1
                            
                            # Yield el texto de la página
                            yield f"\n[Página {i+1}]\n{page_text}\n"
                            
                            # Log de progreso
                            if (i + 1) % 10 == 0:
                                logger.info(f"📝 Procesadas {i+1}/{total_pages} páginas, {total_text_length/1000:.1f}K caracteres")
                            
                            # Dar control al event loop para evitar bloqueos
                            await asyncio.sleep(0)
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Error en página {i+1}: {str(e)}")
                        continue
                
                logger.info(f"✅ PDF procesado: {pages_processed} páginas, {total_text_length} caracteres totales")
                
        except Exception as e:
            logger.error(f"❌ Error con pdfplumber, intentando con PyPDF2: {str(e)}")
            
            # Fallback a PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    total_pages = len(pdf_reader.pages)
                    
                    for i in range(total_pages):
                        if max_pages and i >= max_pages:
                            break
                        
                        try:
                            page = pdf_reader.pages[i]
                            page_text = page.extract_text()
                            
                            if page_text:
                                yield f"\n[Página {i+1}]\n{page_text}\n"
                                await asyncio.sleep(0)
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Error en página {i+1} con PyPDF2: {str(e)}")
                            continue
                            
            except Exception as e:
                logger.error(f"❌ Error fatal al procesar PDF: {str(e)}")
                raise
    
    async def process_large_text_file(self, file_path: Path, encoding: str = 'utf-8') -> AsyncIterator[str]:
        """
        Procesa archivos de texto grandes usando streaming
        
        Yields:
            str: Chunks de texto
        """
        chunk_count = 0
        total_size = 0
        
        try:
            async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                while True:
                    chunk = await f.read(self.chunk_size)
                    if not chunk:
                        break
                    
                    chunk_count += 1
                    total_size += len(chunk)
                    
                    yield chunk
                    
                    # Log de progreso cada 10MB
                    if total_size % (10 * 1024 * 1024) == 0:
                        logger.info(f"📝 Procesando texto: {total_size/1024/1024:.1f}MB leídos")
                    
                    await asyncio.sleep(0)
                    
            logger.info(f"✅ Archivo de texto procesado: {chunk_count} chunks, {total_size/1024/1024:.2f}MB total")
            
        except UnicodeDecodeError:
            logger.warning(f"⚠️ Error de encoding con {encoding}, intentando con latin-1")
            # Reintentar con otro encoding
            async for chunk in self.process_large_text_file(file_path, 'latin-1'):
                yield chunk
    
    def get_file_size_limit_message(self, content_type: str) -> str:
        """
        Obtiene un mensaje descriptivo sobre los límites de tamaño
        """
        limit_bytes = self.file_limits.get(content_type, self.max_size)
        limit_mb = limit_bytes / (1024 * 1024)
        
        type_names = {
            "application/pdf": "PDFs",
            "text/plain": "archivos de texto",
            "text/csv": "archivos CSV",
            "application/vnd.ms-excel": "archivos Excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "archivos Excel"
        }
        
        type_name = type_names.get(content_type, "este tipo de archivo")
        
        return f"El límite para {type_name} es {limit_mb:.0f}MB"
    
    async def save_upload_file_streaming(self, upload_file: UploadFile, destination: Path) -> Tuple[int, str]:
        """
        Guarda un archivo subido usando streaming y devuelve info
        
        Returns:
            Tuple[int, str]: (tamaño_bytes, checksum_opcional)
        """
        # Validar tamaño primero
        is_valid, error_msg, file_size = await self.validate_file_size(upload_file)
        
        if not is_valid:
            raise ValidationException(error_msg)
        
        # Guardar archivo
        upload_file.file.seek(0)  # Asegurar que estamos al inicio
        saved_size = await self.stream_file_to_disk(upload_file, destination)
        
        return saved_size, ""

# Instancia global del servicio
file_streaming_service = FileStreamingService()
