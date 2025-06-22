#!/usr/bin/env python3
"""
Script de diagnóstico para ChromaDB
Verifica si los documentos están siendo indexados correctamente
"""

import sys
import os
import logging
from pprint import pprint

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.chromadb_connector import ChromaDBConnector
from src.repositories.document_repository import DocumentRepository

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_chromadb():
    """
    Función principal de diagnóstico
    """
    print("\n" + "="*60)
    print("🔍 DIAGNÓSTICO DE CHROMADB")
    print("="*60)
    
    # 1. Conectar a ChromaDB
    try:
        chromadb = ChromaDBConnector()
        client = chromadb.get_client()
        print("✅ Conexión a ChromaDB establecida")
    except Exception as e:
        print(f"❌ Error conectando a ChromaDB: {e}")
        return
    
    # 2. Verificar colecciones existentes
    try:
        collections = client.list_collections()
        print(f"\n📂 Colecciones encontradas: {len(collections)}")
        for collection in collections:
            print(f"   - {collection.name}")
    except Exception as e:
        print(f"❌ Error listando colecciones: {e}")
        return
    
    # 3. Verificar contenido de la colección 'documents'
    try:
        collection = client.get_collection("documents")
        print(f"\n📄 Analizando colección 'documents'...")
        
        # Obtener todos los documentos
        results = collection.get()
        
        print(f"   - Total de chunks: {len(results.get('ids', []))}")
        
        if results.get('ids'):
            print(f"   - Primeros 5 IDs: {results['ids'][:5]}")
            
            # Mostrar metadatos del primer documento
            if results.get('metadatas'):
                print(f"   - Metadata del primer chunk:")
                pprint(results['metadatas'][0], indent=8)
                
            # Mostrar contenido del primer chunk (primeros 200 caracteres)
            if results.get('documents'):
                first_doc = results['documents'][0]
                print(f"   - Primer chunk (200 chars): {first_doc[:200]}...")
                
            # Agrupar por document_id para ver cuántos chunks hay por documento
            document_counts = {}
            for metadata in results.get('metadatas', []):
                doc_id = metadata.get('document_id', 'unknown')
                document_counts[doc_id] = document_counts.get(doc_id, 0) + 1
            
            print(f"\n📊 Chunks por documento:")
            for doc_id, count in document_counts.items():
                print(f"   - Documento {doc_id}: {count} chunks")
                
    except Exception as e:
        print(f"❌ Error analizando colección documents: {e}")
        return
    
    # 4. Verificar documentos en Supabase
    try:
        print(f"\n🗄️  Verificando documentos en Supabase...")
        doc_repo = DocumentRepository()
        # Obtener algunos documentos de ejemplo
        documents = doc_repo.list_all_documents(limit=5)
        print(f"   - Documentos en Supabase: {len(documents)}")
        
        for doc in documents:
            print(f"   - Doc ID: {doc.id}, Título: {doc.title}, ChromaDB ID: {getattr(doc, 'chromadb_id', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Error verificando Supabase: {e}")
    
    # 5. Probar búsqueda específica
    print(f"\n🔍 Probando búsqueda específica...")
    try:
        # Buscar con documento específico (usar un ID que sabemos que existe)
        test_query = "temario"
        test_doc_ids = [54, 56]  # IDs de los documentos que vemos en los logs
        
        print(f"   - Query: '{test_query}'")
        print(f"   - Document IDs: {test_doc_ids}")
        
        # Usar la función search_relevant_chunks
        results = chromadb.search_relevant_chunks(
            query=test_query,
            document_ids=test_doc_ids,
            n_results=5
        )
        
        print(f"   - Resultados encontrados: {len(results)}")
        for i, result in enumerate(results[:3]):
            print(f"     • Resultado {i+1}:")
            print(f"       - Content (100 chars): {result.get('content', '')[:100]}...")
            print(f"       - Metadata: {result.get('metadata', {})}")
            print(f"       - Distance: {result.get('distance', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Error en búsqueda específica: {e}")
    
    # 6. Probar búsqueda directa en ChromaDB
    print(f"\n🔎 Probando búsqueda directa en ChromaDB...")
    try:
        where_filter = {
            "document_id": {
                "$in": ["54", "56"]
            }
        }
        
        direct_results = chromadb.search_documents(
            collection_name="documents",
            query_text="temario",
            n_results=5,
            where=where_filter
        )
        
        print(f"   - Búsqueda directa encontró: {len(direct_results.get('documents', [[]])[0])} chunks")
        if direct_results.get('metadatas'):
            print(f"   - Primer metadata: {direct_results['metadatas'][0][0] if direct_results['metadatas'][0] else 'None'}")
            
    except Exception as e:
        print(f"❌ Error en búsqueda directa: {e}")

if __name__ == "__main__":
    debug_chromadb()
