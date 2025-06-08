"""
API Endpoints para la gestión de documentos.
Este módulo implementa todos los endpoints relacionados con documentos:
- Creación, lectura, actualización y eliminación de documentos
- Búsqueda y compartición de documentos
- Gestión de permisos de usuarios
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body, Form, UploadFile,BackgroundTasks
from typing import List, Optional, Dict, Any
import logging
import time
from datetime import datetime
from fastapi import BackgroundTasks
from src.models.schemas.document import (
    DocumentBase, DocumentCreate, DocumentResponse, DocumentShare, 
    DocumentUserLink, DocumentUploadResponse, DocumentResponseHybrid,
    ShareDocumentRequest
)


from src.models.schemas.document import (
    DocumentCreate, DocumentResponse, DocumentUpdate, 
    DocumentShare, DocumentUserLink
)
import uuid 
from src.models.domain import User
from src.models.domain import Document
from src.models.schemas.user import UserResponse 
from src.services.document_service import DocumentService
from src.services.user_service import UserService
from src.api.dependencies import get_current_user, get_document_service, get_user_service

logger = logging.getLogger(__name__)
# Crear router con prefijo y tags para la documentación automática
router = APIRouter(prefix="/documents", tags=["documents"])

# POST /api/documents/upload - Subir un nuevo documento
@router.post("/upload", response_model=DocumentResponseHybrid)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Sube un archivo y lo procesa con enfoque híbrido:
    - Archivos pequeños: procesamiento síncrono
    - Archivos grandes: procesamiento asíncrono
    """

    start_time = time.time()
    try:
        # 1. Validación del tipo de archivo
        content_type = file.content_type
        valid_types = ["application/pdf", "text/plain", "text/csv", "application/vnd.ms-excel", 
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]
        
        if content_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no soportado: {content_type}"
            )
        
        # 2. Leer el contenido del archivo
        file_content = await file.read()
        file_size = len(file_content)
        read_time = time.time() - start_time
        logger.info(f"⏱️ Lectura de archivo completada en {read_time:.3f} segundos")
        
        if file_size > 100 * 1024 * 1024:  # 100MB
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo excede el tamaño máximo permitido de 100MB"
            )
      
        placeholder_doc = document_service.create_document_placeholder(
            uploaded_by=current_user.id,
            title=title,
            content_type=content_type,
            file_size=file_size,
            filename=file.filename
        )

        document_id = placeholder_doc.id
        placeholder_time = time.time() - start_time
        logger.info(f"⏱️ Placeholder creado en {placeholder_time:.3f} segundos")
        
        TEXT_THRESHOLD = 500 * 1024  # 500KB para archivos de texto plano
        PDF_THRESHOLD = 1 * 1024 * 1024  # 1MB para PDFs
        GENERAL_THRESHOLD = 3 * 1024 * 1024  # 3MB para otros formatos

        

        
        is_small_file = (content_type == "application/pdf" and file_size < PDF_THRESHOLD) or \
                        (content_type == "text/plain" and file_size < TEXT_THRESHOLD) or \
                        (content_type not in ["application/pdf", "text/plain"] and file_size < GENERAL_THRESHOLD)



        if is_small_file:
            # PROCESO SÍNCRONO para archivos pequeños
            logger.info(f"Procesando archivo pequeño ({file_size/1024:.1f}KB) sincrónicamente")
            
            # Actualizar estado
            document_service.update_document_status(document_id, "processing", "Extrayendo texto...")
            
            # Extraer texto según tipo
            extracted_text = ""
            
               
            if content_type == "application/pdf":
                extracted_text = document_service.extract_text_from_pdf(file_content)
                logger.info(f"📄 PDF procesado: {len(extracted_text)} caracteres extraídos")
                if not extracted_text or len(extracted_text.strip()) < 10:
                    logger.error(f"❌ No se pudo extraer texto del PDF")
                    document_service.update_document_status(
                        document_id, 
                        "error", 
                        "No se pudo extraer texto del PDF"
                    )
                    raise HTTPException(
                        status_code=400, 
                        detail="El PDF no contiene texto extraíble"
                    )
            elif content_type == "text/plain":
                # Para archivos de texto plano, usar procesamiento optimizado
                extracted_text = file_content.decode("utf-8", errors="ignore")
                logger.info(f"Archivo de texto procesado: {len(extracted_text)} caracteres")
                
                # Si el contenido es válido, proceder (validación básica)
                if extracted_text.strip() and len(extracted_text.strip()) > 10:
                    logger.info("Contenido de texto validado correctamente")
                else:
                    document_service.update_document_status(document_id, "error", "Contenido de texto no válido")
                    raise HTTPException(status_code=400, detail="El archivo contiene texto no válido")
            else:
                extracted_text = file_content.decode("utf-8", errors="ignore")

            
            extraction_time = time.time() - start_time
            logger.info(f"⏱️ Extracción de texto completada en {extraction_time:.3f} segundos")
            

            # Almacenar archivo y obtener URL
            file_url = document_service.store_original_file(
                file_content=file_content,
                filename=file.filename,
                document_id=document_id
            )
            
            storage_time = time.time() - start_time
            logger.info(f"⏱️ Almacenamiento del archivo completado en {storage_time:.3f} segundos")
            
            # Actualizar documento con contenido para generar vectores
            document_service.update_document_status(document_id, "processing", "Generando vectores...")
            document = document_service.update_document(
                document_id=document_id,
                content=extracted_text,
                file_url=file_url
            )
            vectorization_time = time.time() - start_time
            logger.info(f"⏱️ Vectorización completada en {vectorization_time:.3f} segundos")
            
            # Finalizar estado
            document_service.update_document_status(document_id, "completed", "Procesamiento completado")
            
            total_time = time.time() - start_time
            logger.info(f"⏱️ TIEMPO TOTAL: Procesamiento síncrono completado en {total_time:.3f} segundos")
            
            # Devolver documento actualizado
            return document_service.get_document(document_id)
        else:
            # PROCESO ASÍNCRONO para archivos grandes
            logger.info(f"Procesando archivo grande ({file_size/1024/1024:.2f}MB) asincrónicamente")
            
            # Agregar a tareas en segundo plano
            background_tasks.add_task(
                process_document_in_background, 
                file_content=file_content,
                filename=file.filename,
                document_id=document_id,
                document_service=document_service,
                user_id=current_user.id,
                content_type=content_type
            )
            
            # Devolver placeholder para seguimiento
            return placeholder_doc
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al subir documento: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el documento: {str(e)}"
        )

# POST /api/documents - Subir un nuevo documento
@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document: DocumentCreate,
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Sube un nuevo documento al sistema.
    
    - **document**: Datos del documento a crear
    - Automáticamente se asocia con el usuario autenticado
    - El contenido se procesa y almacena en ChromaDB para búsqueda semántica
    """
    try:
        result = document_service.create_document(
            uploaded_by=current_user.id,
            title=document.title,
            content=document.content,
            content_type=document.content_type,
            tags=document.tags
        )
        return result
    except Exception as e:
        logger.error(f"Error al crear documento: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear documento: {str(e)}"
        )

# PUT /api/documents/{id} - Actualizar metadata del documento
@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int = Path(..., description="ID del documento a actualizar"),
    document_update: DocumentUpdate = Body(..., description="Datos a actualizar"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Actualiza la metadata de un documento específico.
    
    - **document_id**: ID del documento a actualizar
    - **document_update**: Objeto con campos opcionales a actualizar (title, content_type, etc.)
    - Solo el propietario del documento o un administrador puede actualizarlo
    """
    try:
        # Obtener el documento actual
        document = document_service.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento con ID {document_id} no encontrado"
            )
        
        # Verificar permisos (propietario o admin)
        is_admin = document_service.is_admin_user(current_user.id)
        is_owner = document.uploaded_by == current_user.id
        
        if not is_owner and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para actualizar este documento"
            )
        
        # Preparar los campos a actualizar (excluir None)
        update_data = document_update.model_dump(exclude_unset=True)
        
        # Llamar al servicio para actualizar
        updated_document = document_service.update_document(
            document_id=document_id,
            title=update_data.get('title'),
            content=update_data.get('content'),
            tags=update_data.get('tags') if 'tags' in update_data else None,
            file_url=update_data.get('file_url')
        )
        
        return updated_document
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar documento {document_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar documento: {str(e)}"
        )

# POST /api/documents/{id}/share - Compartir un documento con usuarios específicos
@router.post("/{document_id}/share", status_code=status.HTTP_200_OK)
async def share_document(
    document_id: int = Path(..., description="ID del documento a compartir"),
    request: ShareDocumentRequest = Body(..., description="Request con lista de IDs de usuarios"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Comparte un documento con usuarios específicos.
    
    - **document_id**: ID del documento a compartir (en la URL)
    - **request**: ShareDocumentRequest con lista de user_ids validada
    - Solo el propietario del documento o un administrador puede compartirlo
    """
    try:
        # 1. Verificar que el documento existe y pertenece al usuario
        document = document_service.get_document(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento no encontrado"
            )
        
        if document.uploaded_by != current_user.id and not document_service.is_admin_user(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para compartir este documento"
            )
        
        # 2. Validar IDs de usuarios
        invalid_ids = []
        valid_users = []
        self_share_attempted = False
        
        logger.info(f"=== INICIO VALIDACIÓN DE COMPARTIR ===")
        logger.info(f"Usuario actual: {current_user.id} ({current_user.username})")
        logger.info(f"IDs recibidos: {request.user_ids}")
        
        for user_id in request.user_ids:
            # No permitir compartir consigo mismo
            if user_id == current_user.id:
                logger.info(f"Usuario {user_id} intentó compartir consigo mismo")
                self_share_attempted = True
                continue
                
            # Verificar si el usuario existe
            logger.info(f"Verificando existencia de usuario ID: {user_id}")
            try:
                # NOTA: get_by_id NO es realmente async, no usar await
                user = user_service.get_by_id(user_id)
                logger.info(f"Resultado de búsqueda para ID {user_id}: {user}")
                
                if not user:
                    logger.warning(f"Usuario ID {user_id} no encontrado")
                    invalid_ids.append(user_id)
                else:
                    logger.info(f"Usuario ID {user_id} encontrado: {user.username}")
                    valid_users.append(user_id)
            except Exception as e:
                logger.error(f"Error al buscar usuario ID {user_id}: {str(e)}")
                invalid_ids.append(user_id)
        
        logger.info(f"=== RESULTADOS DE VALIDACIÓN ===")
        logger.info(f"Usuarios válidos: {valid_users}")
        logger.info(f"IDs inválidos: {invalid_ids}")
        logger.info(f"Auto-compartir intentado: {self_share_attempted}")
        
        # 3. Verificar si solo intentó compartir consigo mismo
        if self_share_attempted and not valid_users and not invalid_ids:
            error_msg = "¿Para qué quieres compartir el documento contigo mismo?"
            logger.warning(f"Usuario {current_user.id} intentó compartir solo consigo mismo")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # 4. Si hay IDs inválidos, retornar error descriptivo
        if invalid_ids:
            error_msg = f"Los siguientes IDs de usuario no existen: {', '.join(map(str, invalid_ids))}"
            logger.error(f"Error de validación: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # 5. Si no hay usuarios válidos para compartir
        if not valid_users:
            if self_share_attempted:
                error_msg = "¿Para qué quieres compartir el documento contigo mismo?"
            else:
                error_msg = "No se especificaron usuarios válidos para compartir"
            logger.error(f"Error: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # 6. Compartir el documento
        success = document_service.share_document(
            document_id=document_id,
            user_ids=valid_users,
            requester_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo compartir el documento"
            )
        
        return {
            "message": f"Documento compartido exitosamente con {len(valid_users)} usuario(s)",
            "shared_with": valid_users
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al compartir documento: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al compartir el documento"
        )

# POST /api/documents/share - Compartir un documento con usuarios específicos (DEPRECADO - Mantener por compatibilidad)
@router.post("/share", status_code=status.HTTP_200_OK, deprecated=True)
async def share_document_legacy(
    share_data: DocumentShare,
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    [DEPRECADO] Comparte un documento con usuarios específicos.
    Use POST /api/documents/{document_id}/share en su lugar.
    """
    try:
        success = document_service.share_document(
            document_id=share_data.document_id,
            user_ids=share_data.user_ids,
            requester_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo compartir el documento"
            )
        
        return {"message": "Documento compartido exitosamente"}
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error al compartir documento: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al compartir documento: {str(e)}"
        )

# POST /api/documents/{id}/users - Vincular un documento a usuarios específicos
@router.post("/{document_id}/users", status_code=status.HTTP_200_OK)
async def link_document_to_users(
    user_link: DocumentUserLink,
    document_id: int = Path(..., description="ID del documento"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Vincula un documento a usuarios específicos.
    
    - **document_id**: ID del documento
    - **user_link**: Contiene lista de user_ids para vincular
    - Verifica que el usuario sea el propietario del documento
    """
    try:
        # Verificar que el documento existe
        document = document_service.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento con ID {document_id} no encontrado"
            )
        
        # Verificar propiedad
        if document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el propietario puede vincular este documento"
            )
        
        # Vincular usuarios al documento
        success = document_service.link_users_to_document(
            document_id, 
            user_link.user_ids,
            current_user.id
        )
           
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo vincular los usuarios al documento"
            )
        
        return {"message": "Usuarios vinculados exitosamente al documento"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al vincular usuarios: {str(e)}"
        )
    
# GET /api/documents - Listar documentos del usuario
@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = Query(0, description="Número de documentos a saltar para paginación"),
    limit: int = Query(100, description="Número máximo de documentos a retornar"),
    sort_by: Optional[str] = Query(None, description="Campo por el cual ordenar (created_at, updated_at)"),
    order: Optional[str] = Query(None, description="Orden de clasificación (asc, desc)"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Lista todos los documentos del usuario actual.
    IMPORTANTE: Este endpoint SIEMPRE devuelve los documentos del usuario actual,
    independientemente de si es administrador o no.
    Para obtener todos los documentos del sistema, usar /admin/all.
    """
    try:
        # Validar y establecer valores por defecto para ordenamiento
        if sort_by is None:
            sort_by = 'created_at'
        if order is None:
            order = 'desc'
        
        # SIEMPRE devolver solo los documentos del usuario actual
        # No importa si es admin o no, "Mis Documentos" debe mostrar solo SUS documentos
        documents = document_service.list_user_documents(
            user_id=current_user.id,
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            order=order
        )
        
        return documents
    except Exception as e:
        logger.error(f"Error al listar documentos: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar documentos: {str(e)}"
        )

# GET /api/documents/search - Buscar documentos por texto
@router.get("/search", response_model=List[Dict[str, Any]])
async def search_documents(
    query: str = Query(..., description="Texto a buscar en documentos"),
    tags: Optional[List[str]] = Query(None, description="Filtrar por etiquetas"),
    n_results: int = Query(5, description="Número de resultados a retornar"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Busca documentos por contenido usando búsqueda semántica.
    """
    try:
        results = document_service.search_documents(
            query=query,
            user_id=current_user.id,
            n_results=n_results,
            tags=tags
        )
        return results
    except Exception as e:
        logger.error(f"Error en búsqueda: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en búsqueda: {str(e)}"
        )

# GET /api/documents/shared-with-me - Obtener documentos compartidos conmigo
@router.get("/shared-with-me", response_model=List[DocumentResponse])
async def get_shared_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Obtiene documentos compartidos con el usuario actual
    """
    try:
        documents = document_service.get_shared_documents(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        return documents
    except Exception as e:
        logger.error(f"Error obteniendo documentos compartidos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener documentos compartidos"
        )

# GET /api/documents/{id}/access - Verificar acceso a un documento
@router.get("/{document_id}/access")
async def check_document_access(
    document_id: int = Path(..., description="ID del documento"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Verifica si el usuario tiene acceso a un documento
    """
    has_access = document_service.check_user_access(
        document_id=document_id,
        user_id=current_user.id
    )
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este documento"
        )
    
    return {"has_access": True}

# GET /api/documents/shared - Documentos compartidos (DEPRECADO)
@router.get("/shared", response_model=List[DocumentResponse])
async def list_shared_documents(
    skip: int = Query(0, description="Número de documentos a saltar para paginación"),
    limit: int = Query(100, description="Número máximo de documentos a retornar"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Lista todos los documentos compartidos con el usuario autenticado.
    """
    try:
        documents = document_service.get_shared_documents(
            user_id=current_user.id,
            limit=limit,
            skip=skip
        )
        return documents
    except Exception as e:
        logger.error(f"Error al listar documentos compartidos: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar documentos compartidos: {str(e)}"
        )
    
# GET /api/documents/{id} - Obtener información de un documento específico
@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int = Path(..., description="ID del documento a obtener"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Obtiene la información detallada de un documento específico.
    
    - **document_id**: ID del documento a recuperar
    - Verifica que el usuario tenga acceso al documento
    """
    try:
        document = document_service.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento con ID {document_id} no encontrado"
            )
        
        # Verificar acceso
        if not document_service.check_user_access(document_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a este documento"
            )
            
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener documento: {str(e)}"
        )

# GET /api/documents/{document_id}/status - Obtener estado de un documento
@router.get("/{document_id}/status", response_model=Dict[str, Any])
async def get_document_status(
    document_id: int = Path(..., description="ID del documento a consultar"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Obtiene el estado de procesamiento de un documento.
    Útil para implementar polling desde el frontend.
    """
    try:
        # Verificar acceso
        if not document_service.check_user_access(document_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a este documento"
            )
            
        # Obtener documento
        document = document_service.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento con ID {document_id} no encontrado"
            )
            
        # Devolver estado
        return {
            "document_id": document_id,
            "title": document.title,
            "status": getattr(document, 'status', 'unknown'),
            "message": getattr(document, 'status_message', ''),
            "content_type": document.content_type,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
            "file_url": getattr(document, 'file_url', None),
            "completed": getattr(document, 'status', '') == 'completed'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener estado del documento {document_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estado: {str(e)}"
        )

# GET /api/documents/{id}/users - Listar usuarios con acceso a un documento
@router.get("/{document_id}/users", response_model=List[Dict[str, Any]])
async def list_document_users(
    document_id: int = Path(..., description="ID del documento"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Lista todos los usuarios con acceso a un documento específico.
    
    - **document_id**: ID del documento
    - Verifica que el usuario tenga acceso al documento
    """
    try:
        # Verificar que el documento existe
        document = document_service.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento con ID {document_id} no encontrado"
            )
        
        # Verificar acceso
        if not document_service.check_user_access(document_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver los usuarios de este documento"
            )
        
        try:
            users = document_service.list_document_users(document_id, current_user.id)
            return users
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(ve)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al listar usuarios del documento {document_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al listar usuarios: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar usuarios: {str(e)}"
        )

# POST /api/documents/{document_id}/reindex - Re-indexar un documento
@router.post("/{document_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    document_id: int = Path(..., description="ID del documento a re-indexar"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Re-indexa un documento en ChromaDB.
    Útil para documentos que existen en la BD pero no están indexados.
    """
    try:
        document = document_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        if document.uploaded_by != current_user.id and not document_service.is_admin_user(current_user.id):
            raise HTTPException(status_code=403, detail="Sin permisos")
        if not hasattr(document, 'content') or not document.content:
            if hasattr(document, 'file_url') and document.file_url:
                logger.info(f"Descargando contenido desde: {document.file_url}")
                import requests
                response = requests.get(document.file_url)
                if document.content_type == "application/pdf":
                    content = document_service.extract_text_from_pdf(response.content)
                else:
                    content = response.text
                document = document_service.update_document(
                    document_id=document_id,
                    content=content
                )
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="El documento no tiene contenido ni archivo asociado"
                )
        else:
            document = document_service.update_document(
                document_id=document_id,
                content=document.content
            )
        return document
    except Exception as e:
        logger.error(f"Error re-indexando documento {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_document_in_background(
    file_content: bytes,    # Ahora recibimos directamente el contenido
    filename: str,          # Y el nombre del archivo
    document_id: int,
    document_service: DocumentService,
    user_id: int,
    content_type: str
):
    try:
        logger.info(f"Iniciando procesamiento en segundo plano para documento {document_id}")
        
        # Actualizar estado a "processing"
        document_service.update_document_status(document_id, "processing", "Extrayendo texto...")
        
        # Extraer texto según el tipo de archivo
        extracted_text = ""
        if content_type == "application/pdf":
            logger.info(f"Extrayendo texto de PDF para documento {document_id}")
            extracted_text = document_service.extract_text_from_pdf(file_content)
        else:
            # Para archivos de texto y otros formatos soportados
            extracted_text = file_content.decode("utf-8", errors="ignore")
        
        # Actualizar estado
        document_service.update_document_status(document_id, "processing", "Almacenando archivo original...")
        
        # Almacenar archivo original y obtener URL
        file_url = document_service.store_original_file(
            file_content=file_content,
            filename=filename,
            document_id=document_id
        )
        
        # Actualizar estado
        document_service.update_document_status(document_id, "processing", "Generando vectores y guardando en ChromaDB...")
        
        # IMPORTANTE: Ahora actualizamos el documento con el contenido extraído para generar vectores
        updated_doc = document_service.update_document(
            document_id=document_id,
            content=extracted_text,
            file_url=file_url
        )
        
        # Verificar si se asignó chromadb_id correctamente
        if not getattr(updated_doc, 'chromadb_id', None):
            logger.warning(f"No se asignó chromadb_id al documento {document_id}")
            document_service.update_document_status(
                document_id, 
                "warning", 
                "Documento procesado pero sin vectorización completa. Podría no estar disponible para preguntas."
            )
        else:
            # Actualizar estado final
            document_service.update_document_status(document_id, "completed", "Procesamiento completado")
            
        logger.info(f"Procesamiento en segundo plano completado para documento {document_id}")
        
    except Exception as e:
        logger.error(f"Error en procesamiento en segundo plano del documento {document_id}: {str(e)}", exc_info=True)
        document_service.update_document_status(document_id, "error", f"Error: {str(e)}")

# DELETE /api/documents/{id} - Eliminar un documento específico
@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int = Path(..., description="ID del documento a eliminar"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Elimina un documento del sistema.
    
    - Verifica que el usuario sea el propietario del documento o un administrador (Ivan)
    - Elimina el documento tanto de la base de datos como de ChromaDB
    """
    try:
        try:
            # Usar método con verificación de permisos de admin
            success = document_service.delete_document(document_id, current_user.id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudo eliminar el documento"
                )
            
            return None  # 204 No Content
        except ValueError as ve:
            # Errores de validación o permisos
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(ve)
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar documento: {str(e)}"
        )

# DELETE /api/documents/{document_id}/share/{user_id} - Revocar acceso de un usuario
@router.delete("/{document_id}/share/{user_id}", status_code=status.HTTP_200_OK)
async def revoke_document_access(
    document_id: int = Path(..., description="ID del documento"),
    user_id: int = Path(..., description="ID del usuario"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Revoca el acceso de un usuario a un documento.
    Solo el propietario del documento puede revocar accesos.
    """
    try:
        # Verificar que el documento existe
        document = document_service.get_document(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento no encontrado"
            )
        
        # Verificar permisos
        if document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el propietario puede revocar acceso a este documento"
            )
        
        # Revocar acceso
        success = document_service.remove_user_access(
            document_id=document_id,
            user_id=user_id,
            requester_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo revocar el acceso"
            )
        
        return {"message": "Acceso revocado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al revocar acceso: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al revocar acceso"
        )

# DELETE /api/documents/{document_id}/users/{user_id} - Eliminar acceso de un usuario a un documento
@router.delete("/{document_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_access(
    document_id: int = Path(..., description="ID del documento"),
    user_id: int = Path(..., description="ID del usuario a eliminar acceso"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Elimina el acceso de un usuario a un documento específico.
    """
    try:
        document = document_service.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento con ID {document_id} no encontrado"
            )
        
        if document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el propietario puede eliminar acceso a este documento"
            )
        
        success = document_service.remove_user_access(document_id, user_id,current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo eliminar el acceso del usuario"
            )
        
        return None  # 204 No Content
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error al eliminar acceso: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar acceso: {str(e)}"
        )


    

# ==================== ENDPOINTS ADMINISTRATIVOS ====================

# GET /api/documents/admin/all - Obtener TODOS los documentos del sistema (solo admin)
@router.get("/admin/all", response_model=List[DocumentResponse])
async def list_all_documents_admin(
    skip: int = Query(0, description="Número de documentos a saltar para paginación"),
    limit: int = Query(100, description="Número máximo de documentos a retornar"),
    sort_by: Optional[str] = Query("created_at", description="Campo por el cual ordenar (created_at, updated_at)"),
    order: Optional[str] = Query("desc", description="Orden de clasificación (asc, desc)"),
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Lista TODOS los documentos del sistema.
    Solo disponible para administradores.
    """
    try:
        # Verificar que el usuario es admin
        if not document_service.is_admin_user(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden acceder a este endpoint"
            )
        
        # Obtener TODOS los documentos del sistema
        documents = document_service.list_all_documents(
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            order=order
        )
        
        return documents
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al listar todos los documentos: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar documentos: {str(e)}"
        )

# GET /api/documents/admin/stats - Obtener estadísticas de documentos (solo admin)
@router.get("/admin/stats", response_model=Dict[str, Any])
async def get_documents_stats_admin(
    current_user = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Obtiene estadísticas detalladas de los documentos.
    Solo disponible para administradores.
    """
    try:
        # Verificar que el usuario es admin
        if not document_service.is_admin_user(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden acceder a este endpoint"
            )
        
        # Obtener estadísticas
        total_documents = document_service.count_all_documents()
        documents_by_user = document_service.get_documents_count_by_user()
        documents_by_type = document_service.get_documents_count_by_type()
        
        return {
            "total_documents": total_documents,
            "documents_by_user": documents_by_user,
            "documents_by_type": documents_by_type,
            "last_updated": datetime.now()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )

@router.get("/{document_id}/verify-index", response_model=Dict[str, Any])
async def verify_document_index(
    document_id: int,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Verifica si un documento está correctamente indexado en ChromaDB
    """
    try:
        # Verificar acceso al documento
        document = document_service.get_document(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento no encontrado"
            )
        
        # Verificar que el usuario tenga acceso
        if document.uploaded_by != current_user.id and not current_user.is_admin:
            if not document_service.check_user_access(document_id, current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes acceso a este documento"
                )
        
        # Verificar indexación
        is_indexed = document_service.verify_document_indexed(document_id)
        
        return {
            "document_id": document_id,
            "title": document.title,
            "is_indexed": is_indexed,
            "status": document.status if hasattr(document, 'status') else "unknown",
            "message": "Documento correctamente indexado" if is_indexed else "Documento no encontrado en el índice"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al verificar indexación: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar documento: {str(e)}"
        )