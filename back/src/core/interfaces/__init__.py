"""
Core interfaces module
"""
from .connectors import IAIConnector, IVectorDBConnector, IDocumentProcessor

__all__ = ['IAIConnector', 'IVectorDBConnector', 'IDocumentProcessor']
