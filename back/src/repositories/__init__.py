"""
Este módulo proporciona los repositorios para acceso a datos de la aplicación.

Los repositorios implementan el patrón Repository para:
1. Abstraer la capa de persistencia (Supabase)
2. Centralizar la lógica de acceso a datos
3. Facilitar el testing mediante mocks

Repositorios Implementados:

DocumentRepository:
- create(document: Document) -> int
- get(document_id: int) -> Optional[Document]
- update(document: Document) -> bool
- delete(document_id: int) -> bool
- list_by_user(user_id: int, limit: int, offset: int) -> List[Document]
- search_by_title(title_query: str, user_id: Optional[int], limit: int) -> List[Document]
"""
from .document_repository import DocumentRepository
from .user_repository import UserRepository
from src.models.domain import Document, DocumentAccess, User
from typing import List, Optional

# Instancia predeterminada para facilitar el uso del repositorio de documentos.
# Esto crea un objeto de la clase `DocumentRepository` llamado `default_document_repo`.
# Este objeto puede ser utilizado en otras partes del código como una instancia global
# para realizar operaciones CRUD (Crear, Leer, Actualizar, Eliminar) y consultas específicas
# sobre la tabla "documents" en la base de datos de Supabase.
# Claro, aquí tienes una explicación detallada en forma de comentario para la línea seleccionada:

# Este patrón es útil para evitar que cada módulo o función tenga que crear su propia instancia de 
# DocumentRepository. En su lugar, pueden reutilizar esta instancia predeterminada. Esto es especialmente
# práctico si el repositorio no tiene estado (stateless) o si no requiere configuraciones específicas para cada uso.


__all__ = [
    # Clase del repositorio
    "DocumentRepository",
    "UserRepository",
]