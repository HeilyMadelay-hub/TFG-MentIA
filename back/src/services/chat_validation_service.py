"""
Servicio de validación para operaciones de chat
Centraliza todas las validaciones relacionadas con chats y mensajes
"""
import logging
from typing import List, Optional, Tuple
from src.models.domain import User
from src.core.exceptions import (
    ValidationException, 
    ForbiddenException, 
    NotFoundException
)

logger = logging.getLogger(__name__)

class ChatValidationService:
    """Servicio centralizado para validaciones de chat"""
    
    def validate_chat_ownership(
        self, 
        chat_owner_id: int, 
        current_user: User, 
        operation: str = "acceder a"
    ) -> None:
        """
        Valida que el usuario tiene permisos para operar en el chat
        
        Args:
            chat_owner_id: ID del propietario del chat
            current_user: Usuario actual
            operation: Descripción de la operación (para logs)
            
        Raises:
            ForbiddenException: Si el usuario no tiene permisos
        """
        # Los administradores pueden acceder a cualquier chat
        if current_user.is_admin:
            logger.info(f"Admin {current_user.username} accediendo a chat como administrador")
            return
        
        # Validar que el chat pertenece al usuario
        if chat_owner_id != current_user.id:
            logger.warning(
                f"Usuario {current_user.id} ({current_user.username}) "
                f"intentó {operation} chat del usuario {chat_owner_id}"
            )
            raise ForbiddenException(f"No tienes permisos para {operation} este chat")
    
    def validate_admin_permissions(self, current_user: User, operation: str) -> None:
        """
        Valida que el usuario tiene permisos de administrador
        
        Args:
            current_user: Usuario actual
            operation: Descripción de la operación
            
        Raises:
            ForbiddenException: Si el usuario no es administrador
        """
        if not current_user.is_admin:
            logger.warning(
                f"Usuario no-admin {current_user.id} ({current_user.username}) "
                f"intentó acceder a operación de admin: {operation}"
            )
            raise ForbiddenException("Solo los administradores pueden acceder a este endpoint")
    
    def validate_message_content(self, content: str) -> str:
        """
        Valida y sanitiza el contenido de un mensaje
        
        Args:
            content: Contenido del mensaje
            
        Returns:
            str: Contenido validado y sanitizado
            
        Raises:
            ValidationException: Si el contenido es inválido
        """
        if not content or not content.strip():
            raise ValidationException("El mensaje no puede estar vacío")
        
        # Sanitizar contenido
        sanitized = content.strip()
        
        # Validar longitud máxima
        max_length = 5000  # 5000 caracteres máximo
        if len(sanitized) > max_length:
            raise ValidationException(
                f"El mensaje es demasiado largo. Máximo {max_length} caracteres, "
                f"recibido {len(sanitized)}"
            )
        
        # Validar que no sea solo espacios o caracteres especiales
        if not any(c.isalnum() for c in sanitized):
            raise ValidationException("El mensaje debe contener al menos un carácter alfanumérico")
        
        logger.debug(f"Mensaje validado correctamente: {len(sanitized)} caracteres")
        return sanitized
    
    def validate_chat_name(self, name: Optional[str]) -> str:
        """
        Valida y sanitiza el nombre de un chat
        
        Args:
            name: Nombre propuesto para el chat
            
        Returns:
            str: Nombre validado o nombre por defecto
        """
        from datetime import datetime
        
        # Si no se proporciona nombre, generar uno por defecto
        if not name or not name.strip():
            return f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Sanitizar nombre
        sanitized = name.strip()
        
        # Validar longitud
        max_length = 100
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].strip()
            logger.info(f"Nombre de chat truncado a {max_length} caracteres")
        
        # Validar longitud mínima
        if len(sanitized) < 1:
            return f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        logger.debug(f"Nombre de chat validado: '{sanitized}'")
        return sanitized
    
    def validate_rag_parameters(
        self, 
        document_ids: Optional[List[int]], 
        n_results: int,
        user_id: int
    ) -> Tuple[Optional[List[int]], int]:
        """
        Valida los parámetros para búsqueda RAG
        
        Args:
            document_ids: Lista de IDs de documentos
            n_results: Número de resultados a retornar
            user_id: ID del usuario (para logging)
            
        Returns:
            Tuple[Optional[List[int]], int]: Parámetros validados
            
        Raises:
            ValidationException: Si los parámetros son inválidos
        """
        # Validar n_results
        if n_results < 1:
            logger.warning(f"Usuario {user_id}: n_results inválido {n_results}, usando 5")
            n_results = 5
        elif n_results > 20:
            logger.warning(f"Usuario {user_id}: n_results demasiado alto {n_results}, limitando a 20")
            n_results = 20
        
        # Validar document_ids si se proporcionan
        validated_doc_ids = None
        if document_ids is not None:
            if not isinstance(document_ids, list):
                raise ValidationException("document_ids debe ser una lista")
            
            # Filtrar IDs válidos (enteros positivos)
            validated_doc_ids = []
            for doc_id in document_ids:
                if isinstance(doc_id, int) and doc_id > 0:
                    validated_doc_ids.append(doc_id)
                else:
                    logger.warning(f"ID de documento inválido ignorado: {doc_id}")
            
            # Si todos los IDs eran inválidos, usar None
            if not validated_doc_ids:
                logger.warning(f"Usuario {user_id}: Todos los document_ids eran inválidos")
                validated_doc_ids = None
            else:
                logger.info(f"Usuario {user_id}: Validados {len(validated_doc_ids)} document_ids")
        
        return validated_doc_ids, n_results
    
    def validate_pagination_parameters(
        self, 
        skip: int, 
        limit: int, 
        max_limit: int = 500
    ) -> Tuple[int, int]:
        """
        Valida parámetros de paginación
        
        Args:
            skip: Número de elementos a saltar
            limit: Número máximo de elementos a retornar
            max_limit: Límite máximo permitido
            
        Returns:
            Tuple[int, int]: Parámetros validados (skip, limit)
        """
        # Validar skip
        if skip < 0:
            logger.warning(f"skip negativo {skip}, usando 0")
            skip = 0
        
        # Validar limit
        if limit < 1:
            logger.warning(f"limit inválido {limit}, usando 100")
            limit = 100
        elif limit > max_limit:
            logger.warning(f"limit demasiado alto {limit}, limitando a {max_limit}")
            limit = max_limit
        
        return skip, limit
    
    def validate_sort_parameters(
        self, 
        sort_by: Optional[str], 
        order: Optional[str]
    ) -> Tuple[str, str]:
        """
        Valida parámetros de ordenamiento
        
        Args:
            sort_by: Campo por el cual ordenar
            order: Orden de clasificación
            
        Returns:
            Tuple[str, str]: Parámetros validados (sort_by, order)
        """
        # Campos válidos para ordenamiento
        valid_sort_fields = ['created_at', 'updated_at', 'name_chat', 'id']
        
        # Validar sort_by
        if not sort_by or sort_by not in valid_sort_fields:
            sort_by = 'updated_at'  # Valor por defecto
        
        # Validar order
        if not order or order.lower() not in ['asc', 'desc']:
            order = 'desc'  # Valor por defecto
        else:
            order = order.lower()
        
        return sort_by, order
    
    def validate_admin_operation_permissions(
        self, 
        current_user: User, 
        target_user_id: Optional[int] = None
    ) -> None:
        """
        Valida permisos para operaciones administrativas avanzadas
        
        Args:
            current_user: Usuario actual
            target_user_id: ID del usuario objetivo (opcional)
            
        Raises:
            ForbiddenException: Si no tiene permisos
        """
        # Verificar que es administrador
        self.validate_admin_permissions(current_user, "operación administrativa")
        
        # Si intenta operar sobre otro admin, validar permisos adicionales
        if target_user_id and target_user_id != current_user.id:
            # Aquí podrías añadir lógica adicional si hay diferentes niveles de admin
            logger.info(
                f"Admin {current_user.username} realizando operación sobre usuario {target_user_id}"
            )
    
    def validate_message_creation_context(
        self, 
        chat_id: int, 
        user_id: int, 
        has_documents: bool,
        question_type: str
    ) -> None:
        """
        Valida el contexto para creación de mensajes
        
        Args:
            chat_id: ID del chat
            user_id: ID del usuario
            has_documents: Si el usuario tiene documentos disponibles
            question_type: Tipo de pregunta detectado
            
        Raises:
            ValidationException: Si el contexto es inválido
        """
        # Validar IDs
        if chat_id <= 0:
            raise ValidationException("ID de chat inválido")
        
        if user_id <= 0:
            raise ValidationException("ID de usuario inválido")
        
        # Log del contexto para debugging
        logger.debug(
            f"Validando contexto mensaje: chat={chat_id}, user={user_id}, "
            f"has_docs={has_documents}, type={question_type}"
        )
        
        # Aquí podrías añadir más validaciones específicas según el tipo de pregunta
        if question_type == "document_question" and not has_documents:
            logger.info(f"Usuario {user_id} pregunta sobre documentos pero no tiene ninguno")
        
    def validate_bulk_operation_limits(self, operation_count: int, max_operations: int = 100) -> None:
        """
        Valida límites para operaciones en lote
        
        Args:
            operation_count: Número de operaciones solicitadas
            max_operations: Máximo número de operaciones permitidas
            
        Raises:
            ValidationException: Si excede el límite
        """
        if operation_count > max_operations:
            raise ValidationException(
                f"Demasiadas operaciones solicitadas: {operation_count}. "
                f"Máximo permitido: {max_operations}"
            )
        
        if operation_count <= 0:
            raise ValidationException("Número de operaciones debe ser mayor a 0")
