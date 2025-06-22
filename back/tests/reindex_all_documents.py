#!/usr/bin/env python3
"""
Quick Fix: Re-indexa TODOS los documentos de la base de datos
Útil cuando hay problemas generalizados de indexación
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.document_service import DocumentService
from src.utils.chromadb_connector import ChromaDBConnector
from src.repositories.document_repository import DocumentRepository
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reindex_all_documents():
    """Re-indexa TODOS los documentos en ChromaDB"""
    print("\n" + "="*60)
    print("🔄 RE-INDEXANDO TODOS LOS DOCUMENTOS")
    print("="*60)
    
    try:
        # Inicializar servicios
        doc_service = DocumentService()
        doc_repo = DocumentRepository()
        chromadb = ChromaDBConnector()
        
        # Obtener TODOS los documentos
        print("\n📋 Obteniendo lista de documentos...")
        all_docs = doc_repo.list_all_documents(limit=1000)  # Limite alto para obtener todos
        print(f"✅ Encontrados {len(all_docs)} documentos en total")
        
        if not all_docs:
            print("❌ No hay documentos para indexar")
            return
        
        # Estadísticas
        success_count = 0
        error_count = 0
        
        # Procesar cada documento
        for doc in all_docs:
            print(f"\n📄 Procesando documento {doc.id}: {doc.title}")
            
            try:
                # Verificar que tenga contenido
                if not doc.content or len(doc.content.strip()) < 10:
                    print(f"   ⚠️  Documento sin contenido válido, saltando...")
                    continue
                
                # Eliminar chunks existentes
                print(f"   🗑️  Eliminando chunks existentes...")
                doc_service._delete_document_chunks(doc.id)
                
                # Dividir en chunks
                chunks = doc_service._split_text_into_chunks(
                    doc.content, 
                    content_type=doc.content_type
                )
                print(f"   📊 Generados {len(chunks)} chunks")
                
                if not chunks:
                    print(f"   ❌ No se pudieron generar chunks")
                    error_count += 1
                    continue
                
                # Preparar datos para ChromaDB
                document_chunks = []
                chunk_ids = []
                metadatas = []
                
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{doc.id}_{i}"
                    document_chunks.append(chunk)
                    chunk_ids.append(chunk_id)
                    metadatas.append({
                        "document_id": str(doc.id),
                        "title": doc.title,
                        "chunk_index": i,
                        "content_type": doc.content_type,
                        "user_id": str(doc.uploaded_by),
                        "tags": ""
                    })
                
                # Añadir a ChromaDB
                success = chromadb.add_documents(
                    collection_name="documents",
                    document_ids=chunk_ids,
                    chunks=document_chunks,
                    metadatas=metadatas
                )
                
                if success:
                    print(f"   ✅ Documento indexado exitosamente")
                    success_count += 1
                else:
                    print(f"   ❌ Error indexando documento")
                    error_count += 1
                    
            except Exception as e:
                print(f"   ❌ Error procesando documento: {e}")
                error_count += 1
                import traceback
                traceback.print_exc()
        
        # Resumen final
        print("\n" + "="*60)
        print("📊 RESUMEN DE RE-INDEXACIÓN")
        print("="*60)
        print(f"✅ Documentos indexados exitosamente: {success_count}")
        print(f"❌ Documentos con errores: {error_count}")
        print(f"📋 Total procesados: {success_count + error_count}")
        
        # Verificar estado final
        collection = chromadb.get_client().get_collection("documents")
        results = collection.get()
        total_chunks = len(results.get('ids', []))
        print(f"\n🎯 Total de chunks en ChromaDB: {total_chunks}")
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    response = input("\n⚠️  Esto re-indexará TODOS los documentos. ¿Continuar? (s/n): ")
    if response.lower() == 's':
        reindex_all_documents()
    else:
        print("Operación cancelada.")
