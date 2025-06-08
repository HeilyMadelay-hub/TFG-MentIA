"""
Este módulo proporciona servicios para la lógica de negocio de la aplicación.

Expone:
1. DocumentService: Para la gestión y búsqueda semántica de documentos
2. ChatService: Para la gestión de conversaciones con el chatbot
3. UserService: Para la gestión de usuarios y autenticación
4. NotificationService: Para la gestión de notificaciones

Los servicios implementan la lógica de negocio y orquestan las interacciones entre:
- Modelos de dominio
- Repositorios de datos
- APIs externas (ChromaDB, OpenAI)
"""

from .document_service import DocumentService
from .chat_service import ChatService

# Comentamos estos imports si los servicios aún no están implementados
# from .user_service import UserService
from .auth_service import AuthService
# from .notification_service import NotificationService

# Instancias predeterminadas para facilitar el uso
default_document_service = DocumentService()
default_chat_service = ChatService()
default_auth_service = AuthService()

__all__ = [
    # Servicios principales
    "DocumentService",
    "ChatService",


    # Comentamos estos si no están implementados
    # "UserService",
    "AuthService",
    # "NotificationService",
    
    # Instancias predeterminadas
    "default_document_service",
    "default_chat_service"
    "default_auth_service"
]