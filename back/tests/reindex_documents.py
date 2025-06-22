#!/usr/bin/env python3
"""
Script para re-indexar documentos específicos en ChromaDB
"""

import sys
import os
import logging
from pprint import pprint

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.document_service import DocumentService
from src.utils.chromadb_connector import ChromaDBConnector
from src.repositories.document_repository import DocumentRepository

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reindex_documents():
    """
    Re-indexa documentos específicos que están teniendo problemas
    """
    print("\n" + "="*60)
    print("🔄 RE-INDEXANDO DOCUMENTOS EN CHROMADB")
    print("="*60)
    
    # IDs de documentos problemáticos (de los logs)
    document_ids = [54, 56]
    
    try:
        # Inicializar servicios
        doc_service = DocumentService()
        doc_repo = DocumentRepository()
        chromadb = ChromaDBConnector()
        
        for doc_id in document_ids:
            print(f"\n📄 Procesando documento {doc_id}...")
            
            try:
                # 1. Obtener documento de Supabase
                document = doc_repo.get(doc_id)
                print(f"   ✅ Documento encontrado: {document.title}")
                print(f"   - Content type: {document.content_type}")
                print(f"   - Content length: {len(document.content) if document.content else 0} chars")
                print(f"   - ChromaDB ID: {getattr(document, 'chromadb_id', 'N/A')}")
                
                if not document.content or len(document.content.strip()) < 10:
                    print(f"   ❌ Documento sin contenido válido")
                    continue
                
                # 2. Eliminar chunks existentes de ChromaDB
                print(f"   🗑️  Eliminando chunks existentes...")
                doc_service._delete_document_chunks(doc_id)
                
                # 3. Re-indexar el documento
                print(f"   🔄 Re-indexando documento...")
                
                # Dividir en chunks
                chunks = doc_service._split_text_into_chunks(
                    document.content, 
                    content_type=document.content_type
                )
                print(f"   📊 Generados {len(chunks)} chunks")
                
                if not chunks:
                    print(f"   ❌ No se pudieron generar chunks")
                    continue
                
                # Preparar datos para ChromaDB
                document_chunks = []
                chunk_ids = []
                metadatas = []
                
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{doc_id}_{i}"
                    document_chunks.append(chunk)
                    chunk_ids.append(chunk_id)
                    metadatas.append({
                        "document_id": str(doc_id),
                        "title": document.title,
                        "chunk_index": i,
                        "content_type": document.content_type,
                        "user_id": str(document.uploaded_by),
                        "tags": ""
                    })
                
                # Mostrar metadata del primer chunk para verificar
                print(f"   📋 Metadata del primer chunk:")
                pprint(metadatas[0], indent=8)
                
                # 4. Añadir a ChromaDB
                success = chromadb.add_documents(
                    collection_name="documents",
                    document_ids=chunk_ids,
                    chunks=document_chunks,
                    metadatas=metadatas
                )
                
                if success:
                    print(f"   ✅ Documento {doc_id} re-indexado exitosamente")
                    
                    # 5. Verificar que se puede buscar
                    print(f"   🔍 Verificando búsqueda...")
                    results = chromadb.search_relevant_chunks(
                        query="temario documento",
                        document_ids=[doc_id],
                        n_results=3
                    )
                    print(f"   📊 Chunks encontrados en búsqueda de prueba: {len(results)}")
                    
                    if results:
                        print(f"   📝 Primer resultado (100 chars): {results[0].get('content', '')[:100]}...")
                else:
                    print(f"   ❌ Error re-indexando documento {doc_id}")
                    
            except Exception as e:
                print(f"   ❌ Error procesando documento {doc_id}: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reindex_documents()
