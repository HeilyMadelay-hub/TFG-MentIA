import chromadb
from typing import List, Optional

class ChromaService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    async def search_relevant_chunks(
        self,
        query: str,
        document_ids: List[int],
        n_results: int = 5
    ) -> List[dict]:
        """
        Busca chunks relevantes solo en documentos específicos
        """
        try:
            # Construir filtro para documentos accesibles
            where_filter = {
                "document_id": {"$in": [str(doc_id) for doc_id in document_ids]}
            }
            
            # Realizar búsqueda
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            if not results['documents'][0]:
                return []
            
            # Formatear resultados
            chunks = []
            for i in range(len(results['documents'][0])):
                chunks.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                })
            
            return chunks
            
        except Exception as e:
            print(f"Error buscando en ChromaDB: {e}")
            return []
    
    async def add_document_chunks(
        self,
        document_id: int,
        chunks: List[str],
        metadata: dict
    ):
        """
        Agrega chunks de un documento a ChromaDB
        """
        try:
            ids = [f"doc_{document_id}_chunk_{i}" for i in range(len(chunks))]
            
            metadatas = []
            for i in range(len(chunks)):
                chunk_metadata = metadata.copy()
                chunk_metadata['document_id'] = str(document_id)
                chunk_metadata['chunk_index'] = i
                metadatas.append(chunk_metadata)
            
            self.collection.add(
                documents=chunks,
                ids=ids,
                metadatas=metadatas
            )
            
        except Exception as e:
            print(f"Error agregando chunks a ChromaDB: {e}")
            raise
