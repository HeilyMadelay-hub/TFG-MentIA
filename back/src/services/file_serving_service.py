"""
Servicio para servir archivos
Centraliza la lógica de construcción de rutas, determinación de content-type y preparación de respuestas
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi.responses import FileResponse
from src.core.exceptions import ValidationException, NotFoundException

logger = logging.getLogger(__name__)

class FileServingService:
    """Servicio para el servicio de archivos"""
    
    # Mapeo de extensiones a content-types optimizado
    CONTENT_TYPE_MAP = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript'
    }
    
    # Archivos que se muestran inline por defecto
    INLINE_CONTENT_TYPES = {
        'application/pdf',
        'image/png',
        'image/jpeg',
        'image/gif',
        'image/svg+xml',
        'text/plain'
    }

    def construct_file_path(self, user_id: int, filename: str) -> Path:
        """
        Construye la ruta completa del archivo de manera segura
        
        Args:
            user_id: ID del usuario propietario
            filename: Nombre del archivo
            
        Returns:
            Path: Ruta completa del archivo
        """
        # Construir ruta base
        base_path = Path("uploads/documents")
        file_path = base_path / str(user_id) / filename
        
        logger.info(f"📁 Ruta construida: {file_path}")
        return file_path

    def construct_document_file_path(self, file_url: str, document_id: int, 
                                   uploaded_by: int, original_filename: str) -> Path:
        """
        Construye la ruta del archivo basada en la URL del documento
        
        Args:
            file_url: URL del archivo desde el documento
            document_id: ID del documento
            uploaded_by: ID del usuario que subió el documento
            original_filename: Nombre original del archivo
            
        Returns:
            Path: Ruta del archivo
        """
        if file_url:
            # Extraer la ruta del archivo de la URL
            # La URL tiene formato: http://localhost:port/api/files/{user_id}/{filename}
            parts = file_url.split('/api/files/')
            if len(parts) > 1:
                path_info = parts[1]  # user_id/filename
                file_path = Path(f"uploads/documents/{path_info}")
                logger.info(f"📁 Ruta extraída de URL: {file_path}")
                return file_path
        
        # Fallback: construir ruta basada en los datos del documento
        fallback_filename = f"{document_id}_{original_filename}" if original_filename else f"document_{document_id}.pdf"
        file_path = Path(f"uploads/documents/{uploaded_by}/{fallback_filename}")
        
        logger.info(f"📁 Ruta fallback construida: {file_path}")
        return file_path

    def determine_content_type(self, filename: str, document_content_type: Optional[str] = None) -> str:
        """
        Determina el content-type más apropiado para un archivo
        
        Args:
            filename: Nombre del archivo
            document_content_type: Content-type del documento (si disponible)
            
        Returns:
            str: Content-type apropiado
        """
        # Priorizar content-type del documento si está disponible
        if document_content_type and document_content_type != "application/octet-stream":
            logger.info(f"🏷️ Usando content-type del documento: {document_content_type}")
            return document_content_type
        
        # Determinar por extensión
        if filename:
            extension = Path(filename).suffix.lower()
            content_type = self.CONTENT_TYPE_MAP.get(extension, "application/octet-stream")
            logger.info(f"🏷️ Content-type determinado por extensión: {content_type}")
            return content_type
        
        # Fallback
        logger.info("🏷️ Usando content-type fallback: application/octet-stream")
        return "application/octet-stream"

    def prepare_file_response(
        self, 
        file_path: Path, 
        filename: str, 
        content_type: str,
        download: bool = False,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> FileResponse:
        """
        Prepara la respuesta de archivo optimizada
        
        Args:
            file_path: Ruta del archivo
            filename: Nombre del archivo para la respuesta
            content_type: Content-type del archivo
            download: Si forzar descarga en lugar de vista previa
            custom_headers: Headers adicionales
            
        Returns:
            FileResponse: Respuesta preparada
        """
        # Headers por defecto
        headers = custom_headers or {}
        
        # Determinar disposición
        if download or content_type not in self.INLINE_CONTENT_TYPES:
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'
            disposition = "descarga"
        else:
            headers["Content-Disposition"] = f'inline; filename="{filename}"'
            disposition = "vista previa"
        
        # Headers de seguridad para PDFs
        if content_type == "application/pdf":
            headers.update({
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "public, max-age=3600"  # Cache por 1 hora
            })
        
        logger.info(f"📤 Preparando respuesta para {disposition}: {filename} ({content_type})")
        
        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            filename=filename,
            headers=headers
        )

    def handle_secure_file_access(
        self, 
        document_id: int, 
        file_path: str, 
        original_filename: str,
        content_type: str,
        download: bool = False
    ) -> FileResponse:
        """
        Maneja el acceso seguro a archivos con URLs firmadas
        
        Args:
            document_id: ID del documento
            file_path: Ruta relativa del archivo
            original_filename: Nombre original del archivo
            content_type: Content-type del archivo
            download: Si forzar descarga
            
        Returns:
            FileResponse: Respuesta de archivo
        """
        # Construir ruta completa
        full_path = Path(f"uploads/documents/{file_path}")
        
        # Verificar existencia
        if not full_path.exists():
            logger.error(f"💥 Archivo no encontrado en acceso seguro: {full_path}")
            raise NotFoundException("Archivo físico", str(full_path))
        
        # Determinar filename para respuesta
        response_filename = original_filename or f"document_{document_id}.pdf"
        
        # Headers de seguridad adicionales
        security_headers = {
            "X-Robots-Tag": "noindex, nofollow",  # No indexar por buscadores
            "X-Frame-Options": "SAMEORIGIN"      # Prevenir embedding
        }
        
        logger.info(f"🔒 Sirviendo archivo seguro: {response_filename}")
        
        return self.prepare_file_response(
            file_path=full_path,
            filename=response_filename,
            content_type=content_type,
            download=download,
            custom_headers=security_headers
        )

    def log_file_access(
        self, 
        filename: str, 
        user_id: Optional[int], 
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        access_type: str = "direct"
    ):
        """
        Registra el acceso a archivos para auditoría
        
        Args:
            filename: Nombre del archivo accedido
            user_id: ID del usuario (si está autenticado)
            ip_address: Dirección IP del cliente
            user_agent: User agent del cliente
            access_type: Tipo de acceso (direct, document, secure)
        """
        user_info = f"usuario {user_id}" if user_id else "anónimo"
        
        log_data = {
            "archivo": filename,
            "usuario": user_info,
            "tipo_acceso": access_type,
            "ip": ip_address or "desconocida",
            "user_agent": user_agent or "desconocido"
        }
        
        logger.info(f"📊 Acceso a archivo registrado: {log_data}")

    def get_file_stats(self, file_path: Path) -> Dict[str, Any]:
        """
        Obtiene estadísticas del archivo
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            Dict: Estadísticas del archivo
        """
        try:
            if not file_path.exists():
                return {"exists": False}
            
            stat = file_path.stat()
            
            return {
                "exists": True,
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": stat.st_mtime,
                "is_file": file_path.is_file()
            }
            
        except Exception as e:
            logger.error(f"💥 Error obteniendo estadísticas de archivo: {str(e)}")
            return {"exists": False, "error": str(e)}

    def optimize_response_headers(self, content_type: str, file_size: int) -> Dict[str, str]:
        """
        Optimiza headers de respuesta basado en el tipo y tamaño del archivo
        
        Args:
            content_type: Tipo de contenido
            file_size: Tamaño del archivo en bytes
            
        Returns:
            Dict: Headers optimizados
        """
        headers = {}
        
        # Cache headers basados en tipo de archivo
        if content_type.startswith('image/'):
            headers["Cache-Control"] = "public, max-age=86400"  # 24 horas para imágenes
        elif content_type == 'application/pdf':
            headers["Cache-Control"] = "public, max-age=3600"   # 1 hora para PDFs
        else:
            headers["Cache-Control"] = "public, max-age=1800"   # 30 minutos para otros
        
        # Headers de compresión para archivos grandes
        if file_size > 1024 * 1024:  # > 1MB
            headers["Accept-Ranges"] = "bytes"
        
        # Headers de seguridad
        headers.update({
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        })
        
        logger.info(f"⚡ Headers optimizados para {content_type} ({file_size} bytes)")
        return headers
