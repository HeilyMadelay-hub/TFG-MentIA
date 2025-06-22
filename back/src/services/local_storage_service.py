import os
import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class LocalStorageService:
    """Servicio para almacenar archivos localmente"""
    
    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path)
        self.documents_path = self.base_path / "documents"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Asegura que los directorios necesarios existan"""
        self.documents_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Directorio de documentos: {self.documents_path}")
    
    def store_file(self, file_content: bytes, filename: str, user_id: int) -> Optional[str]:
        """
        Almacena un archivo localmente
        
        Args:
            file_content: Contenido del archivo
            filename: Nombre del archivo
            user_id: ID del usuario que sube el archivo
            
        Returns:
            Path relativo del archivo almacenado o None si falla
        """
        try:
            # Crear directorio para el usuario si no existe
            user_dir = self.documents_path / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            # Generar nombre único para evitar colisiones
            from uuid import uuid4
            unique_filename = f"{uuid4()}_{filename}"
            file_path = user_dir / unique_filename
            
            # Escribir el archivo
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Retornar path relativo
            relative_path = f"documents/{user_id}/{unique_filename}"
            logger.info(f"✅ Archivo almacenado: {relative_path}")
            return relative_path
            
        except Exception as e:
            logger.error(f"❌ Error almacenando archivo: {e}")
            return None
    
    def get_file_path(self, relative_path: str) -> Optional[Path]:
        """Obtiene el path completo de un archivo"""
        try:
            full_path = self.base_path / relative_path
            if full_path.exists():
                return full_path
            return None
        except Exception as e:
            logger.error(f"❌ Error obteniendo path: {e}")
            return None
    
    def delete_file(self, relative_path: str) -> bool:
        """Elimina un archivo del almacenamiento local"""
        try:
            full_path = self.base_path / relative_path
            if full_path.exists():
                full_path.unlink()
                logger.info(f"🗑️ Archivo eliminado: {relative_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Error eliminando archivo: {e}")
            return False
    
    def get_file_url(self, relative_path: str, base_url: str) -> str:
        """Genera la URL para acceder al archivo"""
        return f"{base_url}/api/files/{relative_path}"

# Instancia global
local_storage = LocalStorageService()
