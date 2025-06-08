"""
Repositorio para operaciones CRUD de documentos en Supabase.
Maneja el acceso a datos para la entidad Document.
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

# Importar el conector de Supabase
from src.config.database import get_supabase_client
from src.models.domain import Document

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentRepository:
    """
    Repositorio para gestionar documentos en Supabase.
    Implementa operaciones CRUD básicas y consultas específicas.
    """
    
    def __init__(self):
        """Inicializa el repositorio con el cliente de Supabase."""
        self.table_name = "documents"
    
    def create(self, document: Document) -> int:
        """
        Crea un nuevo documento en la base de datos.
        
        Args:
            document: Objeto Document con los datos del documento
            
        Returns:
            int: ID del documento creado
        """
        try:
            # Preparar datos para inserción
            document_data = {
                "title": document.title,
                "chromadb_id": document.chromadb_id if hasattr(document, 'chromadb_id') else None,
                "uploaded_by": document.uploaded_by,
                "content_type": document.content_type,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # IMPORTANTE: Incluir content si existe
            if hasattr(document, 'content') and document.content is not None:
                document_data["content"] = document.content
                logger.info(f"Incluyendo content en creación: {len(document.content)} caracteres")
            
            if hasattr(document, 'file_url') and document.file_url is not None:
                document_data["file_url"] = document.file_url
                logger.info(f"Incluyendo file_url en creación: {document.file_url}")
                
            # Incluir campos adicionales si existen
            if hasattr(document, 'status'):
                document_data["status"] = document.status
            if hasattr(document, 'status_message'):
                document_data["status_message"] = document.status_message
            if hasattr(document, 'file_size') and document.file_size is not None:
                document_data["file_size"] = document.file_size
            if hasattr(document, 'original_filename'):
                document_data["original_filename"] = document.original_filename
                
            # Obtener cliente de Supabase
            # Usar service role para tener permisos completos
            supabase = get_supabase_client(use_service_role=True)
            
            # Insertar en Supabase
            response = supabase.table(self.table_name).insert(document_data).execute()
            
            # Obtener el ID insertado
            if response.data and len(response.data) > 0:
                document_id = response.data[0]['id']
                logger.info(f"Documento creado con ID: {document_id}")
                return document_id
            else:
                raise ValueError("No se pudo obtener el ID del documento creado")
                
        except Exception as e:
            logger.error(f"Error al crear documento: {str(e)}")
            raise
    
    def get(self, document_id: int) -> Optional[Document]:
        """
        Obtiene un documento por su ID.
        
        Args:
            document_id: ID del documento a recuperar
            
        Returns:
            Optional[Document]: El documento recuperado o None si no existe
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Consultar en Supabase
            response = supabase.table(self.table_name).select('*').eq('id', document_id).execute()
            
            if response.data and len(response.data) > 0:
                document_data = response.data[0]
                
                document = Document()
                
                document.id = document_data['id']
                document.title = document_data['title']
                document.uploaded_by = document_data['uploaded_by']
                document.content_type = document_data['content_type']
                document.chromadb_id = document_data.get('chromadb_id')
                document.created_at = document_data['created_at']
                document.updated_at = document_data['updated_at']
                
                # CAMPOS NUEVOS que faltaban
                document.file_url = document_data.get('file_url')
                document.status = document_data.get('status', 'pending')
                document.status_message = document_data.get('status_message')
                document.file_size = document_data.get('file_size')
                document.original_filename = document_data.get('original_filename')
                document.content = document_data.get('content')  # IMPORTANTE: Incluir content

                logger.info(f"Documento recuperado: ID={document.id}, chromadb_id={document.chromadb_id}, file_url={document.file_url}")
                return document
            else:
                logger.info(f"Documento con ID {document_id} no encontrado")
                return None
                
        except Exception as e:
            logger.error(f"Error al obtener documento {document_id}: {str(e)}")
            raise
    
    def update(self, document: Document) -> bool:
        """
        Actualiza un documento existente.
        
        Args:
            document: Objeto Document con los datos actualizados
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            # Preparar datos para actualización
            document_data = {
                "title": document.title,
                "content_type": document.content_type,
                "updated_at": datetime.now().isoformat()
            }
            
            # IMPORTANTE: Incluir content si existe
            if hasattr(document, 'content') and document.content is not None:
                document_data["content"] = document.content
                logger.info(f"Incluyendo content en actualización: {len(document.content)} caracteres")
            
            # Incluir file_url si existe
            if hasattr(document, 'file_url') and document.file_url is not None:
                document_data["file_url"] = document.file_url
                logger.info(f"Incluyendo file_url en actualización: {document.file_url}")
            
            # Si hay un nuevo chromadb_id, actualizarlo
            if hasattr(document, 'chromadb_id') and document.chromadb_id:
                document_data["chromadb_id"] = document.chromadb_id
                
            # Incluir estado si existe
            if hasattr(document, 'status'):
                document_data["status"] = document.status
            if hasattr(document, 'status_message'):
                document_data["status_message"] = document.status_message
            
            supabase = get_supabase_client(use_service_role=True)
            
            # Actualizar en Supabase
            response = supabase.table(self.table_name).update(document_data).eq('id', document.id).execute()
            
            success = response.data is not None and len(response.data) > 0
            if success:
                logger.info(f"Documento {document.id} actualizado con éxito. Datos: {document_data}")
            else:
                logger.warning(f"No se pudo actualizar el documento {document.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al actualizar documento {document.id}: {str(e)}")
            raise
    
    def delete(self, document_id: int) -> bool:
        """
        Elimina un documento por su ID.
        
        Args:
            document_id: ID del documento a eliminar
            
        Returns:
            bool: True si la eliminación fue exitosa
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Eliminar en Supabase
            response = supabase.table(self.table_name).delete().eq('id', document_id).execute()
            
            success = response.data is not None
            if success:
                logger.info(f"Documento {document_id} eliminado con éxito")
            else:
                logger.warning(f"No se pudo eliminar el documento {document_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al eliminar documento {document_id}: {str(e)}")
            raise
    
    def list_by_user(self, user_id: int, limit: int = 100, offset: int = 0, sort_by: str = 'created_at', order: str = 'desc') -> List[Document]:
        """
        Lista documentos de un usuario específico.
        
        Args:
            user_id: ID del usuario
            limit: Límite de documentos a retornar
            offset: Desplazamiento para paginación
            
        Returns:
            List[Document]: Lista de documentos del usuario
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Validar parámetros de ordenamiento
            valid_sort_fields = ['created_at', 'updated_at', 'title']
            if sort_by not in valid_sort_fields:
                sort_by = 'created_at'
            
            # Determinar dirección del orden
            desc_order = order.lower() == 'desc' if order else True
            
            # Consultar en Supabase
            response = supabase.table(self.table_name)\
                .select('*')\
                .eq('uploaded_by', user_id)\
                .order(sort_by, desc=desc_order)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            documents = []
            if response.data:
                for document_data in response.data:
                    # Convertir a objeto Document con todos los campos
                    document = Document(
                        id=document_data['id'],
                        title=document_data['title'],
                        uploaded_by=document_data['uploaded_by'],
                        content_type=document_data['content_type'],
                        chromadb_id=document_data.get('chromadb_id'),
                        created_at=document_data['created_at'],
                        updated_at=document_data['updated_at'],
                        file_url=document_data.get('file_url'),
                        status=document_data.get('status', 'pending'),
                        status_message=document_data.get('status_message'),
                        file_size=document_data.get('file_size'),
                        original_filename=document_data.get('original_filename'),
                        content=document_data.get('content')
                    )
                    documents.append(document)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error al listar documentos del usuario {user_id}: {str(e)}")
            raise
    
    def search_by_title(self, title_query: str, user_id: Optional[int] = None, 
                       limit: int = 100) -> List[Document]:
        """
        Busca documentos por título.
        
        Args:
            title_query: Texto a buscar en el título
            user_id: Opcional, filtrar por usuario
            limit: Límite de resultados
            
        Returns:
            List[Document]: Lista de documentos que coinciden
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Iniciar la consulta
            query = supabase.table(self.table_name).select('*').ilike('title', f'%{title_query}%')
            
            # Filtrar por usuario si se especifica
            if user_id is not None:
                query = query.eq('uploaded_by', user_id)
            
            # Ejecutar consulta
            response = query.limit(limit).execute()
            
            documents = []
            if response.data:
                for document_data in response.data:
                    # Convertir a objeto Document
                    document = Document(
                        id=document_data['id'],
                        title=document_data['title'],
                        uploaded_by=document_data['uploaded_by'],
                        content_type=document_data['content_type'],
                        chromadb_id=document_data.get('chromadb_id'),
                        created_at=document_data['created_at'],
                        updated_at=document_data['updated_at'],
                        content=document_data.get('content')
                    )
                    documents.append(document)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error al buscar documentos por título '{title_query}': {str(e)}")
            raise

    def share_document_with_users(self, document_id: int, user_ids: List[int]) -> bool:
        """
        Comparte un documento con múltiples usuarios.
        
        Args:
            document_id: ID del documento a compartir
            user_ids: Lista de IDs de usuarios con quienes compartir
            
        Returns:
            bool: True si se compartió exitosamente
        """
        try:
            logger.info(f"=== INICIANDO COMPARTIR DOCUMENTO ===")
            logger.info(f"Document ID: {document_id}")
            logger.info(f"User IDs: {user_ids}")
            
            # Usar service role para tener permisos completos
            supabase = get_supabase_client(use_service_role=True)
            
            # Verificar que el documento existe
            doc_check = supabase.table("documents").select("id").eq("id", document_id).execute()
            if not doc_check.data:
                logger.error(f"Documento {document_id} no existe en la base de datos")
                raise ValueError(f"Documento {document_id} no existe")
            
            # Preparar los datos para inserción
            access_records = []
            for user_id in user_ids:
                access_records.append({
                    "id_document": document_id,
                    "id_user": user_id
                })
            
            logger.info(f"Registros a insertar: {access_records}")
            
            # Insertar en la tabla de acceso
            if access_records:
                try:
                    # Primero eliminar registros existentes para evitar duplicados
                    for record in access_records:
                        delete_response = supabase.table("acceso_documentos_usuario")\
                            .delete()\
                            .eq("id_document", record["id_document"])\
                            .eq("id_user", record["id_user"])\
                            .execute()
                        logger.info(f"Eliminados registros previos para user {record['id_user']}: {delete_response.data}")
                    
                    # Ahora insertar los nuevos registros
                    response = supabase.table("acceso_documentos_usuario").insert(access_records).execute()
                    
                    logger.info(f"Respuesta de inserción: {response.data}")
                    
                    success = response.data is not None and len(response.data) > 0
                    if success:
                        logger.info(f"✅ Documento {document_id} compartido con {len(user_ids)} usuarios")
                        # Verificar inserción
                        verify = supabase.table("acceso_documentos_usuario").select("*").eq("id_document", document_id).execute()
                        logger.info(f"Verificación - Registros en BD: {len(verify.data) if verify.data else 0}")
                    else:
                        logger.error(f"❌ No se pudo compartir el documento {document_id}")
                        logger.error(f"Response data: {response.data}")
                    
                    return success
                except Exception as db_error:
                    logger.error(f"Error en operación de BD: {str(db_error)}")
                    logger.error(f"Tipo de error: {type(db_error).__name__}")
                    import traceback
                    logger.error(traceback.format_exc())
                    raise
            return True
        except Exception as e:
            logger.error(f"Error al compartir documento {document_id}: {str(e)}")
            logger.error(f"Tipo de error: {type(e).__name__}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def get_shared_documents(self, user_id: int, limit: int = 100, offset: int = 0) -> List[Document]:
        """
        Obtiene los documentos compartidos con un usuario específico.
        
        Args:
            user_id: ID del usuario
            limit: Límite de documentos a retornar
            offset: Desplazamiento para paginación
            
        Returns:
            List[Document]: Lista de documentos compartidos con el usuario
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Obtener IDs de documentos compartidos con el usuario
            response = supabase.table("acceso_documentos_usuario")\
                .select("id_document")\
                .eq("id_user", user_id)\
                .execute()
            
            if not response.data:
                return []
            
            # Extraer los IDs de documentos
            document_ids = [item["id_document"] for item in response.data]
            
            # Obtener los documentos completos
            documents = []
            for doc_id in document_ids[offset:offset+limit]:
                doc = self.get(doc_id)
                if doc:
                    documents.append(doc)
            
            return documents
        except Exception as e:
            logger.error(f"Error al obtener documentos compartidos para usuario {user_id}: {str(e)}")
            raise

    def get_document_users(self, document_id: int) -> List[int]:
        """
        Obtiene los IDs de usuarios que tienen acceso a un documento.
        
        Args:
            document_id: ID del documento
            
        Returns:
            List[int]: Lista de IDs de usuarios con acceso
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Consultar usuarios con acceso
            response = supabase.table("acceso_documentos_usuario")\
                .select("id_user")\
                .eq("id_document", document_id)\
                .execute()
            
            if not response.data:
                return []
            
            # Extraer los IDs de usuarios
            user_ids = [item["id_user"] for item in response.data]
            return user_ids
        except Exception as e:
            logger.error(f"Error al obtener usuarios con acceso al documento {document_id}: {str(e)}")
            raise

    def check_user_access(self, document_id: int, user_id: int) -> bool:
        """
        Verifica si un usuario tiene acceso a un documento.
        
        Args:
            document_id: ID del documento
            user_id: ID del usuario
            
        Returns:
            bool: True si el usuario tiene acceso al documento
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Comprobar si el usuario es el propietario
            document = self.get(document_id)
            if document and document.uploaded_by == user_id:
                return True
            
            # Comprobar si el documento está compartido con el usuario
            response = supabase.table("acceso_documentos_usuario")\
                .select("*")\
                .eq("id_document", document_id)\
                .eq("id_user", user_id)\
                .execute()
            
            return response.data and len(response.data) > 0
        except Exception as e:
            logger.error(f"Error al verificar acceso de usuario {user_id} a documento {document_id}: {str(e)}")
            raise

    def list_document_users(self, document_id: int) -> List[int]:
        """
        Obtiene los IDs de usuarios que tienen acceso a un documento.
        
        Args:
            document_id: ID del documento
            
        Returns:
            List[int]: Lista de IDs de usuarios con acceso
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Obtener el documento para incluir al propietario
            document = self.get(document_id)
            if not document:
                return []
                
            # Incluir al propietario en la lista
            user_ids = [document.uploaded_by]
            
            # Consultar usuarios con acceso en la tabla de acceso
            response = supabase.table("acceso_documentos_usuario")\
                .select("id_user")\
                .eq("id_document", document_id)\
                .execute()
            
            if response.data:
                # Añadir los IDs de usuarios con acceso compartido
                for item in response.data:
                    if item["id_user"] not in user_ids:  # Evitar duplicados
                        user_ids.append(item["id_user"])
            
            return user_ids
        except Exception as e:
            logger.error(f"Error al listar usuarios del documento {document_id}: {str(e)}")
            raise

    def remove_user_access(self, document_id: int, user_id: int) -> bool:
        """Elimina el acceso de un usuario a un documento específico."""
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Verificar que el registro existe antes de eliminar
            check_response = supabase.table("acceso_documentos_usuario")\
                .select("*")\
                .eq("id_document", document_id)\
                .eq("id_user", user_id)\
                .execute()
                
            logger.info(f"Verificación previa - Registros encontrados: {len(check_response.data) if check_response.data else 0}")
            
            if not check_response.data:
                logger.info(f"No se encontró registro de acceso para documento {document_id}, usuario {user_id}")
                return True  # Ya no existe
                
            # Eliminar el registro
            logger.info(f"Eliminando acceso: documento {document_id}, usuario {user_id}")
            response = supabase.table("acceso_documentos_usuario")\
                .delete()\
                .eq("id_document", document_id)\
                .eq("id_user", user_id)\
                .execute()
                
            logger.info(f"Respuesta de eliminación: {response}")
            
            # Verificar que se eliminó
            verify_response = supabase.table("acceso_documentos_usuario")\
                .select("*")\
                .eq("id_document", document_id)\
                .eq("id_user", user_id)\
                .execute()
                
            if verify_response.data:
                logger.error(f"❌ El registro AÚN EXISTE después de la eliminación: {verify_response.data}")
                return False
            else:
                logger.info(f"✅ Registro eliminado correctamente")
                return True
                
        except Exception as e:
            logger.error(f"Error al eliminar acceso: {str(e)}", exc_info=True)
            return False

    def list_all_documents(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """
        Lista todos los documentos del sistema. Solo para administradores.
        
        Args:
            limit: Límite de documentos a retornar
            offset: Desplazamiento para paginación
            
        Returns:
            List[Document]: Lista de todos los documentos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Consultar en Supabase
            response = supabase.table(self.table_name)\
                .select('*')\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            documents = []
            if response.data:
                for document_data in response.data:
                    # Convertir a objeto Document, incluyendo el campo content
                    document = Document(
                        id=document_data['id'],
                        title=document_data['title'],
                        uploaded_by=document_data['uploaded_by'],
                        content_type=document_data['content_type'],
                        chromadb_id=document_data.get('chromadb_id'),
                        created_at=document_data['created_at'],
                        updated_at=document_data['updated_at'],
                        content=document_data.get('content'),
                        file_url=document_data.get('file_url'),
                        status=document_data.get('status', 'pending')
                    )
                    documents.append(document)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error al listar todos los documentos: {str(e)}")
            raise
            
    def list_all_shared_documents(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """
        Lista todos los documentos compartidos en el sistema. Solo para administradores.
        
        Args:
            limit: Límite de documentos a retornar
            offset: Desplazamiento para paginación
            
        Returns:
            List[Document]: Lista de documentos compartidos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Obtener todas las entradas de la tabla de acceso
            response = supabase.table("acceso_documentos_usuario")\
                .select("id_document")\
                .execute()
            
            if not response.data:
                return []
            
            # Extraer los IDs únicos de documentos
            document_ids = list(set([item["id_document"] for item in response.data]))
            
            # Obtener los documentos completos
            documents = []
            for doc_id in document_ids[offset:offset+limit]:
                doc = self.get(doc_id)
                if doc:
                    documents.append(doc)
            
            return documents
        except Exception as e:
            logger.error(f"Error al listar todos los documentos compartidos: {str(e)}")
            raise

    def update_with_url(self, document: Document, file_url: Optional[str] = None) -> bool:
        """
        Actualiza un documento con énfasis en la URL del archivo.
        
        Args:
            document: Objeto Document con datos actualizados
            file_url: URL del archivo explícitamente para asegurar que se incluya
        """
        try:
            # Preparar datos para actualización
            document_data = {
                "title": document.title,
                "content_type": document.content_type,
                "updated_at": datetime.now().isoformat()
            }
            
            # IMPORTANTE: Incluir content si existe
            if hasattr(document, 'content') and document.content is not None:
                document_data["content"] = document.content
                logger.info(f"Incluyendo content en update_with_url: {len(document.content)} caracteres")
            
            # Incluir file_url explícitamente
            if file_url is not None:
                document_data["file_url"] = file_url
                logger.info(f"⭐ Actualizando file_url explícitamente: {file_url}")
            
            # Otras actualizaciones
            if hasattr(document, 'chromadb_id') and document.chromadb_id:
                document_data["chromadb_id"] = document.chromadb_id
                
            if hasattr(document, 'status'):
                document_data["status"] = document.status
            if hasattr(document, 'status_message'):
                document_data["status_message"] = document.status_message
            
            supabase = get_supabase_client(use_service_role=True)
            
            # Actualizar en Supabase con log detallado
            logger.info(f"Enviando actualización a Supabase: {document_data}")
            response = supabase.table(self.table_name).update(document_data).eq('id', document.id).execute()
            
            # Verificar resultado
            success = response.data is not None and len(response.data) > 0
            if success:
                logger.info(f"✅ Documento {document.id} actualizado exitosamente")
            else:
                logger.warning(f"❌ No se pudo actualizar el documento {document.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error en update_with_url: {str(e)}", exc_info=True)
            return False
        
    def create_placeholder(self, document: Document) -> int:
        """Crea un documento placeholder sin contenido ni vectorización"""
        try:
            # Validar campos antes de enviar a Supabase
            document_data = {
                "title": str(document.title),
                "uploaded_by": int(document.uploaded_by),
                "content_type": str(document.content_type),
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat(),
                "status": str(getattr(document, 'status', 'pending')),
                "status_message": str(getattr(document, 'status_message', ''))
            }
            
            # Agregar campos opcionales si existen
            if hasattr(document, 'file_size') and document.file_size is not None:
                document_data["file_size"] = int(document.file_size)
            if hasattr(document, 'original_filename') and document.original_filename is not None:
                document_data["original_filename"] = str(document.original_filename)
            if hasattr(document, 'file_url') and document.file_url is not None:
                document_data["file_url"] = str(document.file_url)
            
            # Log para debug
            logger.info(f"Datos para Supabase: {document_data}")
            
            # Obtener cliente de Supabase
            supabase = get_supabase_client(use_service_role=True)
            
            # Insertar en Supabase
            response = supabase.table(self.table_name).insert(document_data).execute()
            
            # Obtener el ID insertado
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            else:
                raise ValueError("No se pudo obtener el ID del documento creado")
        except Exception as e:
            logger.error(f"Error al crear documento placeholder: {str(e)}", exc_info=True)
            raise

    def get_all_documents(self, skip: int = 0, limit: int = 1000) -> List[Document]:
        """
        Obtiene todos los documentos del sistema. Alias para list_all_documents.
        """
        return self.list_all_documents(limit=limit, offset=skip)
    
    def update_status(self, document: Document) -> bool:
        """Actualiza solo el estado de un documento"""
        try:
            # Preparar datos para actualización
            document_data = {
                "status": document.status,
                "status_message": document.status_message,
                "updated_at": document.updated_at.isoformat()
            }
            
            # Obtener cliente de Supabase
            supabase = get_supabase_client(use_service_role=True)
            
            # Actualizar en Supabase
            response = supabase.table(self.table_name)\
                .update(document_data)\
                .eq("id", document.id)\
                .execute()
                
            return True if response.data else False
        except Exception as e:
            logger.error(f"Error al actualizar estado del documento: {str(e)}", exc_info=True)
            return False
