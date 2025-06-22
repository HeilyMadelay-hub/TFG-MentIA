"""
Helpers para endpoints de API
Versiones compatibles con Windows
"""
try:
    from .document_helpers import DocumentEndpointHelpers
except ImportError:
    # Fallback para Windows
    from .document_helpers_win import DocumentEndpointHelpers

from .chat_websocket_helpers import ChatWebSocketHelpers

__all__ = ['DocumentEndpointHelpers', 'ChatWebSocketHelpers']
