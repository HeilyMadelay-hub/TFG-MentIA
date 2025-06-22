"""
Servicio de procesamiento de archivos
Maneja extracción de texto, almacenamiento y procesamiento de archivos
"""
import logging
import tempfile
import os
from typing import Optional, Tuple
from pathlib import Path as PathLib

logger = logging.getLogger(__name__)

class FileProcessingService:
    """Servicio para procesamiento de archivos"""
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        
    def extract_text_from_content(self, file_content: bytes, content_type: str, 
                                 filename: str) -> str:
        """
        Extrae texto según el tipo de archivo
        
        Args:
            file_content: Contenido del archivo en bytes
            content_type: Tipo MIME del archivo
            filename: Nombre del archivo (para logs)
            
        Returns:
            str: Texto extraído
            
        Raises:
            Exception: Si hay error en la extracción
        """
        logger.info(f"🔄 Iniciando extracción de texto de '{filename}' ({content_type})")
        
        try:
            if content_type == "application/pdf":
                return self._extract_pdf_text(file_content, filename)
            
            elif content_type == "text/plain":
                return self._extract_plain_text(file_content, filename)
            
            elif content_type in ["text/csv", "application/csv"]:
                return self._extract_csv_text(file_content, filename)
            
            elif content_type in [
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ]:
                return self._extract_excel_text(file_content, filename)
            
            else:
                # Fallback para otros tipos: intentar como texto plano
                return self._extract_plain_text(file_content, filename)
                
        except Exception as e:
            logger.error(f"❌ Error extrayendo texto de '{filename}': {str(e)}")
            raise Exception(f"No se pudo extraer texto del archivo: {str(e)}")

    def _extract_pdf_text(self, file_content: bytes, filename: str) -> str:
        """Extrae texto de un PDF"""
        try:
            import PyPDF2
            import io
            
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"⚠️ Error en página {page_num + 1} de '{filename}': {str(e)}")
                    continue
            
            extracted_text = "\n".join(text_parts)
            
            if not extracted_text.strip():
                # Intentar con pdfplumber como fallback
                try:
                    import pdfplumber
                    
                    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                        text_parts = []
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                        
                        extracted_text = "\n".join(text_parts)
                        
                except ImportError:
                    logger.warning("📚 pdfplumber no disponible para fallback")
                except Exception as e:
                    logger.warning(f"⚠️ Error con pdfplumber: {str(e)}")
            
            logger.info(f"📄 PDF procesado: {len(extracted_text)} caracteres extraídos")
            return extracted_text
            
        except ImportError:
            raise Exception("PyPDF2 no está instalado. No se pueden procesar archivos PDF.")
        except Exception as e:
            raise Exception(f"Error procesando PDF: {str(e)}")

    def _extract_plain_text(self, file_content: bytes, filename: str) -> str:
        """Extrae texto de archivo plano"""
        try:
            # Intentar diferentes encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    text = file_content.decode(encoding)
                    logger.info(f"📝 Texto plano decodificado con {encoding}: {len(text)} caracteres")
                    return text
                except UnicodeDecodeError:
                    continue
            
            # Si ningún encoding funciona, usar utf-8 con errores ignorados
            text = file_content.decode('utf-8', errors='ignore')
            logger.warning(f"⚠️ Texto decodificado con errores ignorados: {len(text)} caracteres")
            return text
            
        except Exception as e:
            raise Exception(f"Error procesando archivo de texto: {str(e)}")

    def _extract_csv_text(self, file_content: bytes, filename: str) -> str:
        """Extrae y estructura texto de CSV"""
        try:
            import pandas as pd
            import io
            
            # Intentar diferentes encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    text_data = file_content.decode(encoding)
                    csv_file = io.StringIO(text_data)
                    
                    # Intentar diferentes separadores
                    separators = [',', ';', '\t', '|']
                    
                    for sep in separators:
                        try:
                            csv_file.seek(0)
                            df = pd.read_csv(csv_file, separator=sep, low_memory=False)
                            
                            if len(df.columns) > 1:  # CSV válido si tiene múltiples columnas
                                # Convertir a texto estructurado
                                structured_text = self._dataframe_to_text(df, filename)
                                logger.info(f"📊 CSV procesado: {df.shape[0]} filas, {df.shape[1]} columnas")
                                return structured_text
                                
                        except Exception:
                            continue
                    
                    # Si no se pudo parsear como CSV, devolver como texto plano
                    logger.warning(f"⚠️ '{filename}' no se pudo parsear como CSV, usando como texto plano")
                    return text_data
                    
                except UnicodeDecodeError:
                    continue
            
            raise Exception("No se pudo decodificar el archivo CSV")
            
        except ImportError:
            # Si pandas no está disponible, tratar como texto plano
            return self._extract_plain_text(file_content, filename)
        except Exception as e:
            raise Exception(f"Error procesando CSV: {str(e)}")

    def _extract_excel_text(self, file_content: bytes, filename: str) -> str:
        """Extrae texto de archivos Excel"""
        try:
            import pandas as pd
            import io
            
            # Crear un archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name
            
            try:
                # Leer todas las hojas
                excel_data = pd.read_excel(tmp_path, sheet_name=None, engine='openpyxl')
                
                text_parts = []
                for sheet_name, df in excel_data.items():
                    text_parts.append(f"=== HOJA: {sheet_name} ===\n")
                    text_parts.append(self._dataframe_to_text(df, f"{filename} - {sheet_name}"))
                    text_parts.append("\n")
                
                structured_text = "\n".join(text_parts)
                total_rows = sum(len(df) for df in excel_data.values())
                total_sheets = len(excel_data)
                
                logger.info(f"📈 Excel procesado: {total_sheets} hojas, {total_rows} filas totales")
                return structured_text
                
            finally:
                # Limpiar archivo temporal
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                    
        except ImportError:
            raise Exception("pandas y openpyxl son requeridos para procesar archivos Excel")
        except Exception as e:
            raise Exception(f"Error procesando Excel: {str(e)}")

    def _dataframe_to_text(self, df, source_name: str) -> str:
        """Convierte un DataFrame a texto estructurado para búsqueda"""
        try:
            text_parts = []
            
            # Información del dataset
            text_parts.append(f"Fuente: {source_name}")
            text_parts.append(f"Dimensiones: {df.shape[0]} filas, {df.shape[1]} columnas")
            text_parts.append(f"Columnas: {', '.join(df.columns.astype(str))}")
            text_parts.append("")
            
            # Muestra de datos (primeras filas)
            sample_size = min(10, len(df))
            text_parts.append(f"Muestra de datos (primeras {sample_size} filas):")
            
            for idx, row in df.head(sample_size).iterrows():
                row_text = " | ".join([f"{col}: {str(val)}" for col, val in row.items() if pd.notna(val)])
                text_parts.append(f"Fila {idx + 1}: {row_text}")
            
            # Estadísticas descriptivas para columnas numéricas
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                text_parts.append("\nEstadísticas numéricas:")
                for col in numeric_cols:
                    stats = df[col].describe()
                    text_parts.append(f"{col}: min={stats['min']:.2f}, max={stats['max']:.2f}, media={stats['mean']:.2f}")
            
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.warning(f"⚠️ Error estructurando DataFrame: {str(e)}")
            # Fallback: convertir a string simple
            return df.to_string()

    def create_temp_file(self, file_content: bytes, suffix: str = '') -> str:
        """
        Crea un archivo temporal con el contenido dado
        
        Args:
            file_content: Contenido del archivo
            suffix: Sufijo para el archivo temporal
            
        Returns:
            str: Ruta del archivo temporal creado
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(file_content)
            return tmp_file.name

    def cleanup_temp_file(self, file_path: str) -> bool:
        """
        Elimina un archivo temporal
        
        Args:
            file_path: Ruta del archivo a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"🗑️ Archivo temporal eliminado: {file_path}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ No se pudo eliminar archivo temporal {file_path}: {str(e)}")
        return False

    def get_file_metadata(self, file_content: bytes, filename: str, content_type: str) -> dict:
        """
        Obtiene metadata del archivo
        
        Args:
            file_content: Contenido del archivo
            filename: Nombre del archivo
            content_type: Tipo de contenido
            
        Returns:
            dict: Metadata del archivo
        """
        return {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(file_content),
            "size_kb": len(file_content) / 1024,
            "size_mb": len(file_content) / (1024 * 1024),
            "extension": PathLib(filename).suffix.lower() if filename else None
        }
