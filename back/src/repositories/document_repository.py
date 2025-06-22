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

# Importar excepciones personalizadas
from src.core.exceptions import (
    DocumentNotFoundException,
    DatabaseException,
    ValidationException,
    ConflictException
)

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
            
        Raises:
            ValidationException: Si los datos no son válidos
            DatabaseException: Si hay un error de base de datos
        """
        try:
            # Validar datos requeridos
            if not document.title or not document.title.strip():
                raise ValidationException(
                    "El título del documento es requerido",
                    field_errors={"title": "Campo requerido"}
                )
            
            if not document.uploaded_by:
                raise ValidationException(
                    "El usuario que sube el documento es requerido",
                    field_errors={"uploaded_by": "Campo requerido"}
                )
            
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
                raise DatabaseException("No se pudo obtener el ID del documento creado")
                
        except (ValidationException, DatabaseException):
            # Re-lanzar excepciones conocidas
            raise
        except Exception as e:
            logger.error(f"Error al crear documento: {str(e)}")
            raise DatabaseException(
                "Error al crear documento en la base de datos",
                original_error=e
            )
    
    def get(self, document_id: int) -> Document:
        """
        Obtiene un documento por su ID.
        
        Args:
            document_id: ID del documento a recuperar
            
        Returns:
            Document: El documento recuperado
            
        Raises:
            DocumentNotFoundException: Si el documento no existe
            DatabaseException: Si hay un error de base de datos
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
                raise DocumentNotFoundException(document_id)
                
        except DocumentNotFoundException:
            # Re-lanzar excepción conocida
            raise
        except Exception as e:
            logger.error(f"Error al obtener documento {document_id}: {str(e)}")
            raise DatabaseException(
                f"Error al obtener documento {document_id} de la base de datos",
                original_error=e
            )
    
    def update(self, document: Document) -> bool:
        """
        Actualiza un documento existente.
        
        Args:
            document: Objeto Document con los datos actualizados
            
        Returns:
            bool: True si la actualización fue exitosa
            
        Raises:
            ValidationException: Si los datos no son válidos
            DocumentNotFoundException: Si el documento no existe
            DatabaseException: Si hay un error de base de datos
        """
        try:
            # Validar que el documento tiene ID
            if not hasattr(document, 'id') or not document.id:
                raise ValidationException(
                    "El ID del documento es requerido para actualizar",
                    field_errors={"id": "Campo requerido"}
                )
            
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
            
            if response.data is not None and len(response.data) > 0:
                logger.info(f"Documento {document.id} actualizado con éxito. Datos: {document_data}")
                return True
            else:
                # Si no se actualizó ningún registro, el documento no existe
                raise DocumentNotFoundException(document.id)
            
        except (ValidationException, DocumentNotFoundException):
            raise
        except Exception as e:
            logger.error(f"Error al actualizar documento {document.id}: {str(e)}")
            raise DatabaseException(
                f"Error al actualizar documento {document.id}",
                original_error=e
            )
    
    def delete(self, document_id: int) -> bool:
        """
        Elimina un documento por su ID.
        
        Args:
            document_id: ID del documento a eliminar
            
        Returns:
            bool: True si la eliminación fue exitosa
            
        Raises:
            DocumentNotFoundException: Si el documento no existe
            DatabaseException: Si hay un error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Primero verificar que existe
            check_response = supabase.table(self.table_name).select('id').eq('id', document_id).execute()
            if not check_response.data:
                raise DocumentNotFoundException(document_id)
            
            # Eliminar en Supabase
            response = supabase.table(self.table_name).delete().eq('id', document_id).execute()
            
            if response.data is not None:
                logger.info(f"Documento {document_id} eliminado con éxito")
                return True
            else:
                return False
            
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error al eliminar documento {document_id}: {str(e)}")
            raise DatabaseException(
                f"Error al eliminar documento {document_id}",
                original_error=e
            )
    
    def list_by_user(self, user_id: int, limit: int = 100, offset: int = 0, sort_by: str = 'created_at', order: str = 'desc') -> List[Document]:
        """
        Lista documentos de un usuario específico.
        
        Args:
            user_id: ID del usuario
            limit: Límite de documentos a retornar
            offset: Desplazamiento para paginación
            
        Returns:
            List[Document]: Lista de documentos del usuario
            
        Raises:
            DatabaseException: Si hay un error de base de datos
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
            raise DatabaseException(
                f"Error al listar documentos del usuario {user_id}",
                original_error=e
            )
    
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
            
        Raises:
            DatabaseException: Si hay un error de base de datos
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
            raise DatabaseException(
                f"Error al buscar documentos por título '{title_query}'",
                original_error=e
            )

    def get_existing_shares(self, document_id: int, user_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Obtiene información sobre usuarios que ya tienen acceso al documento.
        
        Args:
            document_id: ID del documento
            user_ids: Lista de IDs de usuarios a verificar
            
        Returns:
            List[Dict]: Lista con información de usuarios que ya tienen acceso
            
        Raises:
            DatabaseException: Si hay un error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Buscar usuarios que ya tienen acceso
            response = supabase.table("acceso_documentos_usuario")\
                .select("id_user, created_at")\
                .eq("id_document", document_id)\
                .in_("id_user", user_ids)\
                .execute()
            
            existing_shares = []
            if response.data:
                # Obtener información adicional de usuarios
                for share in response.data:
                    user_response = supabase.table("users")\
                        .select("id, username, email")\
                        .eq("id", share["id_user"])\
                        .execute()
                    
                    if user_response.data:
                        user_info = user_response.data[0]
                        existing_shares.append({
                            "id": user_info["id"],
                            "username": user_info["username"],
                            "email": user_info["email"],
                            "shared_at": share["created_at"]
                        })
            
            return existing_shares
            
        except Exception as e:
            logger.error(f"Error al obtener shares existentes: {str(e)}")
            raise DatabaseException(
                f"Error al verificar accesos existentes",
                original_error=e
            )
    
    def share_document_with_users(self, document_id: int, user_ids: List[int]) -> Dict[str, Any]:
        """
        Comparte un documento con múltiples usuarios, validando duplicados.
        
        Args:
            document_id: ID del documento a compartir
            user_ids: Lista de IDs de usuarios con quienes compartir
            
        Returns:
            Dict con información sobre el resultado:
                - successful_shares: Lista de IDs compartidos exitosamente
                - already_shared: Lista de usuarios que ya tenían acceso
                - failed_shares: Lista de IDs que fallaron
            
        Raises:
            DocumentNotFoundException: Si el documento no existe
            DatabaseException: Si hay un error de base de datos
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
                raise DocumentNotFoundException(document_id)
            
            # Obtener usuarios que ya tienen acceso
            existing_shares = self.get_existing_shares(document_id, user_ids)
            existing_user_ids = [share["id"] for share in existing_shares]
            
            # Filtrar solo usuarios nuevos
            new_user_ids = [uid for uid in user_ids if uid not in existing_user_ids]
            
            logger.info(f"Usuarios que ya tienen acceso: {existing_user_ids}")
            logger.info(f"Nuevos usuarios a compartir: {new_user_ids}")
            
            successful_shares = []
            failed_shares = []
            
            # Solo insertar nuevos registros
            if new_user_ids:
                access_records = [{
                    "id_document": document_id,
                    "id_user": user_id
                } for user_id in new_user_ids]
                
                try:
                    response = supabase.table("acceso_documentos_usuario").insert(access_records).execute()
                    
                    if response.data:
                        successful_shares = new_user_ids
                        logger.info(f"✅ Documento {document_id} compartido con {len(successful_shares)} nuevos usuarios")
                        
                        # Actualizar is_shared a TRUE si se compartió con alguien
                        try:
                            update_response = supabase.table("documents")\
                                .update({"is_shared": True})\
                                .eq("id", document_id)\
                                .execute()
                            logger.info(f"✅ Columna is_shared actualizada para documento {document_id}")
                        except Exception as update_error:
                            logger.error(f"❌ Error actualizando is_shared: {update_error}")
                    else:
                        failed_shares = new_user_ids
                        logger.error(f"❌ No se pudieron compartir con usuarios nuevos")
                        
                except Exception as e:
                    logger.error(f"Error al insertar accesos: {str(e)}")
                    failed_shares = new_user_ids
            
            # Preparar resultado
            result = {
                "successful_shares": successful_shares,
                "already_shared": existing_shares,
                "failed_shares": failed_shares,
                "total_requested": len(user_ids),
                "total_already_shared": len(existing_shares),
                "total_new_shares": len(successful_shares),
                "total_failed": len(failed_shares)
            }
            
            logger.info(f"Resultado final: {result}")
            return result
            
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error al compartir documento {document_id}: {str(e)}")
            raise DatabaseException(
                f"Error al compartir documento {document_id}",
                original_error=e
            )

    def get_shared_documents(self, user_id: int, limit: int = 100, offset: int = 0) -> List[Document]:
        """
        Obtiene los documentos compartidos con un usuario específico.
        
        Args:
            user_id: ID del usuario
            limit: Límite de documentos a retornar
            offset: Desplazamiento para paginación
            
        Returns:
            List[Document]: Lista de documentos compartidos con el usuario
            
        Raises:
            DatabaseException: Si hay un error de base de datos
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
                try:
                    doc = self.get(doc_id)
                    documents.append(doc)
                except DocumentNotFoundException:
                    # Si un documento fue eliminado, continuar con los demás
                    logger.warning(f"Documento compartido {doc_id} no encontrado, omitiendo")
                    continue
            
            return documents
        except Exception as e:
            logger.error(f"Error al obtener documentos compartidos para usuario {user_id}: {str(e)}")
            raise DatabaseException(
                f"Error al obtener documentos compartidos para usuario {user_id}",
                original_error=e
            )

    def get_document_users(self, document_id: int) -> List[int]:
        """
        Obtiene los IDs de usuarios que tienen acceso a un documento.
        
        Args:
            document_id: ID del documento
            
        Returns:
            List[int]: Lista de IDs de usuarios con acceso
            
        Raises:
            DatabaseException: Si hay un error de base de datos
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
            raise DatabaseException(
                f"Error al obtener usuarios del documento {document_id}",
                original_error=e
            )

    def check_user_access(self, document_id: int, user_id: int) -> bool:
        """
        Verifica si un usuario tiene acceso a un documento.
        
        Args:
            document_id: ID del documento
            user_id: ID del usuario
            
        Returns:
            bool: True si el usuario tiene acceso al documento
            
        Raises:
            DatabaseException: Si hay un error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Comprobar si el usuario es el propietario
            try:
                document = self.get(document_id)
                if document.uploaded_by == user_id:
                    return True
            except DocumentNotFoundException:
                # Si el documento no existe, no hay acceso
                return False
            
            # Comprobar si el documento está compartido con el usuario
            response = supabase.table("acceso_documentos_usuario")\
                .select("*")\
                .eq("id_document", document_id)\
                .eq("id_user", user_id)\
                .execute()
            
            return response.data and len(response.data) > 0
        except Exception as e:
            logger.error(f"Error al verificar acceso de usuario {user_id} a documento {document_id}: {str(e)}")
            raise DatabaseException(
                f"Error al verificar acceso a documento {document_id}",
                original_error=e
            )

    def list_document_users(self, document_id: int) -> List[int]:
        """
        Obtiene los IDs de usuarios que tienen acceso a un documento.
        
        Args:
            document_id: ID del documento
            
        Returns:
            List[int]: Lista de IDs de usuarios con acceso
            
        Raises:
            DocumentNotFoundException: Si el documento no existe
            DatabaseException: Si hay un error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Obtener el documento para incluir al propietario
            document = self.get(document_id)  # Lanza DocumentNotFoundException si no existe
                
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
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error al listar usuarios del documento {document_id}: {str(e)}")
            raise DatabaseException(
                f"Error al listar usuarios del documento {document_id}",
                original_error=e
            )

    def remove_user_access(self, document_id: int, user_id: int) -> bool:
        """
        Elimina el acceso de un usuario a un documento específico.
        
        Args:
            document_id: ID del documento
            user_id: ID del usuario
            
        Returns:
            bool: True si se eliminó exitosamente
            
        Raises:
            DatabaseException: Si hay un error de base de datos
        """
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
                
                # Verificar si quedan más accesos compartidos para este documento
                remaining_access = supabase.table("acceso_documentos_usuario")\
                    .select("*")\
                    .eq("id_document", document_id)\
                    .execute()
                
                # Si no quedan accesos, actualizar is_shared a FALSE
                if not remaining_access.data:
                    try:
                        update_response = supabase.table("documents")\
                            .update({"is_shared": False})\
                            .eq("id", document_id)\
                            .execute()
                        logger.info(f"✅ Columna is_shared actualizada a FALSE para documento {document_id}")
                    except Exception as update_error:
                        logger.error(f"❌ Error actualizando is_shared a FALSE: {update_error}")
                
                return True
                
        except Exception as e:
            logger.error(f"Error al eliminar acceso: {str(e)}", exc_info=True)
            raise DatabaseException(
                f"Error al eliminar acceso del usuario {user_id} al documento {document_id}",
                original_error=e
            )

    def list_all_documents(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """
        Lista todos los documentos del sistema. Solo para administradores.
        
        Args:
            limit: Límite de documentos a retornar
            offset: Desplazamiento para paginación
            
        Returns:
            List[Document]: Lista de todos los documentos
            
        Raises:
            DatabaseException: Si hay un error de base de datos
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
            raise DatabaseException(
                "Error al listar todos los documentos del sistema",
                original_error=e
            )
            
    def list_all_shared_documents(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """
        Lista todos los documentos compartidos en el sistema. Solo para administradores.
        
        Args:
            limit: Límite de documentos a retornar
            offset: Desplazamiento para paginación
            
        Returns:
            List[Document]: Lista de documentos compartidos
            
        Raises:
            DatabaseException: Si hay un error de base de datos
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
                try:
                    doc = self.get(doc_id)
                    documents.append(doc)
                except DocumentNotFoundException:
                    # Si un documento fue eliminado, continuar
                    logger.warning(f"Documento compartido {doc_id} no encontrado, omitiendo")
                    continue
            
            return documents
        except Exception as e:
            logger.error(f"Error al listar todos los documentos compartidos: {str(e)}")
            raise DatabaseException(
                "Error al listar documentos compartidos del sistema",
                original_error=e
            )

    def update_with_url(self, document: Document, file_url: Optional[str] = None) -> bool:
        """
        Actualiza un documento con énfasis en la URL del archivo.
        
        Args:
            document: Objeto Document con datos actualizados
            file_url: URL del archivo explícitamente para asegurar que se incluya
            
        Returns:
            bool: True si la actualización fue exitosa
            
        Raises:
            DocumentNotFoundException: Si el documento no existe
            DatabaseException: Si hay un error de base de datos
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
            if response.data is not None and len(response.data) > 0:
                logger.info(f"✅ Documento {document.id} actualizado exitosamente")
                return True
            else:
                logger.warning(f"❌ No se pudo actualizar el documento {document.id}")
                raise DocumentNotFoundException(document.id)
            
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error en update_with_url: {str(e)}", exc_info=True)
            raise DatabaseException(
                f"Error al actualizar documento {document.id} con URL",
                original_error=e
            )
        
    def create_placeholder(self, document: Document) -> int:
        """
        Crea un documento placeholder sin contenido ni vectorización.
        
        Args:
            document: Documento con metadatos iniciales
            
        Returns:
            int: ID del documento creado
            
        Raises:
            ValidationException: Si los datos no son válidos
            DatabaseException: Si hay un error de base de datos
        """
        try:
            # Validar campos requeridos
            if not document.title or not document.title.strip():
                raise ValidationException(
                    "El título del documento es requerido",
                    field_errors={"title": "Campo requerido"}
                )
            
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
                raise DatabaseException("No se pudo obtener el ID del documento creado")
                
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error al crear documento placeholder: {str(e)}", exc_info=True)
            raise DatabaseException(
                "Error al crear documento placeholder",
                original_error=e
            )

    def get_all_documents(self, skip: int = 0, limit: int = 1000) -> List[Document]:
        """
        Obtiene todos los documentos del sistema. Alias para list_all_documents.
        
        Raises:
            DatabaseException: Si hay un error de base de datos
        """
        return self.list_all_documents(limit=limit, offset=skip)
    
    def update_status(self, document: Document) -> bool:
        """
        Actualiza solo el estado de un documento.
        
        Args:
            document: Documento con el nuevo estado
            
        Returns:
            bool: True si la actualización fue exitosa
            
        Raises:
            DocumentNotFoundException: Si el documento no existe
            DatabaseException: Si hay un error de base de datos
        """
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
                
            if response.data:
                return True
            else:
                raise DocumentNotFoundException(document.id)
                
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error al actualizar estado del documento: {str(e)}", exc_info=True)
            raise DatabaseException(
                f"Error al actualizar estado del documento {document.id}",
                original_error=e
            )

    # Métodos adicionales que faltaban para completar la funcionalidad
    
    def count_all(self) -> int:
        """
        Cuenta el total de documentos en el sistema.
        
        Returns:
            int: Número total de documentos
            
        Raises:
            DatabaseException: Si hay un error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            response = supabase.table(self.table_name).select("id", count="exact").execute()
            return response.count if response.count is not None else 0
        except Exception as e:
            logger.error(f"Error al contar documentos: {str(e)}")
            raise DatabaseException("Error al contar documentos", original_error=e)
    
    def count_by_user(self) -> Dict[str, int]:
        """
        Obtiene el conteo de documentos por usuario.
        
        Returns:
            Dict[str, int]: Diccionario con username como clave y conteo como valor
            
        Raises:
            DatabaseException: Si hay un error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            # Esta consulta requeriría un JOIN con la tabla de usuarios
            # Por ahora retornamos un diccionario vacío
            # TODO: Implementar cuando se tenga acceso a la tabla de usuarios
            return {}
        except Exception as e:
            logger.error(f"Error al contar documentos por usuario: {str(e)}")
            raise DatabaseException("Error al contar documentos por usuario", original_error=e)
    
    def count_by_content_type(self) -> Dict[str, int]:
        """
        Obtiene el conteo de documentos por tipo de contenido.
        
        Returns:
            Dict[str, int]: Diccionario con content_type como clave y conteo como valor
            
        Raises:
            DatabaseException: Si hay un error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            response = supabase.table(self.table_name).select("content_type").execute()
            
            if not response.data:
                return {}
            
            # Contar manualmente por tipo
            counts = {}
            for doc in response.data:
                content_type = doc.get('content_type', 'unknown')
                counts[content_type] = counts.get(content_type, 0) + 1
            
            return counts
        except Exception as e:
            logger.error(f"Error al contar documentos por tipo: {str(e)}")
            raise DatabaseException("Error al contar documentos por tipo", original_error=e)
    
    def exists(self, document_id: int) -> bool:
        """
        Verifica si un documento existe.
        
        Args:
            document_id: ID del documento
            
        Returns:
            bool: True si existe, False si no
            
        Raises:
            DatabaseException: Si hay un error de base de datos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            response = supabase.table(self.table_name).select("id").eq("id", document_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error al verificar si existe documento {document_id}: {str(e)}")
            raise DatabaseException(
                f"Error al verificar existencia del documento {document_id}",
                original_error=e
            )
