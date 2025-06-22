"""
ChromaDB Connector - Funciones CRUD para la base de datos vectorial

---------------------------------------------------------

PEQUEÑO PARENTENSIS

No se crea a partir del crud_base.py porque:

En SQLAlchemy (crud_base.py):

Trabaja con modelos de bases de datos relacionales
Usa sesiones SQL para las transacciones
Maneja entidades que tienen relaciones entre sí
Opera sobre registros con estructura fija (tablas)

En ChromaDB (chromadb_connector.py):

Trabaja con embeddings vectoriales para búsqueda semántica
Opera con "colecciones" de vectores en lugar de tablas
Está optimizado para búsqueda por similitud
No tiene un esquema rígido como SQL

---------------------------------------------------------

SPOILER

En crud_base.py usas: create(), get(), update(), remove()
En chromadb_connector.py usamos: add_document(), search_similar_documents(), update_document(), delete_document()

---------------------------------------------------------

CONCEPTOS PARA ENTENDER CHROMADB
Singleton: Asegura una única instancia compartida
Lazy Initialization:Técnica donde los objetos se crean solo cuando son realmente necesarios, no antes. Esto ahorra recursos al retrasar la creación hasta el momento de uso.
Encapsulación: Oculta detalles de implementación detrás de una interfaz
Búsqueda vectorial: ChromaDB usa embeddings vectoriales para encontrar similitudes semánticas

UTILIZA POR DEFECTO EL EMBEDDING all-MiniLM-L6-v2



---------------------------------------------------------

Un patrón Singleton bien implementado en el método __new__
Inicialización perezosa (lazy) en el método get_client()
Funciones CRUD completas (crear, leer, actualizar, eliminar)
Excelente manejo de errores con bloques try/except
Documentación detallada con docstrings explicativos

"""
import chromadb
import time
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import os
import uuid
from typing import List, Dict, Any, Optional
from src.core.logging_config import get_logger
from src.core.exceptions import ExternalServiceException, DatabaseException
from src.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


def load_env_file():
    """Lee el archivo .env manualmente"""
    env_vars = {}
    try:
        with open('.env', 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        return env_vars
    except FileNotFoundError:
        return {}

class ChromaDBConnector:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaDBConnector, cls).__new__(cls)
            cls._instance._client = None
            cls._instance._initialized_collections = set()  # Para rastrear colecciones inicializadas
        return cls._instance
    
    def get_client(self):
        """Inicializa el cliente si aún no existe (lazy initialization)"""
        if self._client is None:
            try:
                import chromadb
                from src.config.settings import get_settings
                settings = get_settings()
                
                # Detectar si estamos en Docker
                import os
                in_docker = os.environ.get('DOCKER_ENV', 'false').lower() == 'true'
                
                # Si estamos en Docker, usar el nombre del servicio
                host = 'chromadb' if in_docker else settings.CHROMA_HOST
                port = 8000 if in_docker else settings.CHROMA_PORT  # Puerto interno en Docker
                
                logger.info(f"Conectando a ChromaDB en {host}:{port}")
                
                # Usar el cliente HTTP para conectarse al contenedor Docker
                try:
                    self._client = chromadb.HttpClient(
                        host=host,
                        port=port
                    )
                    
                    # Verificar con heartbeat
                    self._client.heartbeat()
                    logger.info("✅ Conexión exitosa a ChromaDB!")
                    self._ensure_collection_exists("documents")
                except Exception as connection_error:
                    logger.error(f"Error al conectar con ChromaDB: {str(connection_error)}", exc_info=True)
                    raise ExternalServiceException(f"No se pudo conectar a ChromaDB: {str(connection_error)}")
                    
            except Exception as e:
                logger.error(f"Error al inicializar cliente ChromaDB: {str(e)}", exc_info=True)
                raise ExternalServiceException(f"Error inicializando ChromaDB: {str(e)}")
                
        return self._client
        

#---------------------------------------------------------
    def test_connection(self) -> bool:
        """Prueba la conexión/funcionalidad de ChromaDB"""
        try:
            # Intenta una operación simple para verificar la funcionalidad
            client = self.get_client()
            # Listar colecciones es una operación ligera para probar
            client.list_collections()
            logger.info("Conexión a ChromaDB exitosa")
            return True
        except Exception as e:
            logger.error(f"Error con ChromaDB: {str(e)}", exc_info=True)
            raise ExternalServiceException(f"Error en la conexión a ChromaDB: {str(e)}")

#---------------------------------------------------------

    
            
    def create_collection(self, collection_name: str, metadata: Optional[Dict[str, Any]] = None):
        """Crea una colección si no existe"""
        client = self.get_client()
        try:
            # Intenta obtener la colección primero
            return client.get_collection(name=collection_name)
        except:
            # Si no existe, créala
            logger.info(f"Creando colección: {collection_name}")
            return client.create_collection(
                name=collection_name,
                metadata=metadata or {}
            )
        
    def _ensure_collection_exists(self, collection_name: str):
        """Verifica que una colección exista y la crea si no"""
        if hasattr(self, '_initialized_collections') and collection_name in self._initialized_collections:
            return  # Ya fue verificada/creada
            
        try:
            # Intentar obtener la colección
            self.get_client().get_collection(collection_name)
            logger.info(f"Colección '{collection_name}' encontrada en ChromaDB")
        except Exception as e:
            if "does not exists" in str(e) or "not found" in str(e).lower():
                logger.info(f"Creando colección '{collection_name}' en ChromaDB...")
                self.get_client().create_collection(collection_name)
                logger.info(f"✅ Colección '{collection_name}' creada exitosamente")
            else:
                logger.error(f"Error al verificar colección '{collection_name}': {str(e)}")
                return
                
        # Inicializar conjunto si no existe
        if not hasattr(self, '_initialized_collections'):
            self._initialized_collections = set()
        # Marcar como inicializada
        self._initialized_collections.add(collection_name)
            


#-----------------------------------------------
  
    def add_documents(self, 
                collection_name: str, 
                document_ids: List[str], 
                chunks: List[str], 
                metadatas: Optional[List[Dict[str, Any]]] = None,
                timeout: int = 35) -> bool:
        
        """Añade documentos a ChromaDB con timeout."""
        start_time = time.time()
        try:
            # Obtener cliente y asegurar que la colección existe
            client = self.get_client()
            self._ensure_collection_exists(collection_name)
            
            # Obtener la colección
            collection = client.get_collection(collection_name)
            logger.info(f"Preparando para añadir {len(chunks)} chunks a ChromaDB")
            
            # Verificar metadatos
            if not metadatas:
                metadatas = [{"default": "true"} for _ in range(len(chunks))]
            else:
                for i, meta in enumerate(metadatas):
                    if not meta:
                        metadatas[i] = {"default": "true"}
            
            # IMPORTANTE: Procesar con timeout para evitar bloqueos
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    collection.add,
                    ids=document_ids,
                    documents=chunks,
                    metadatas=metadatas
                )
                
                try:
                    # Esperar hasta timeout
                    result = future.result(timeout=settings.CHROMA_OPERATION_TIMEOUT)
                    chroma_time = time.time() - start_time
                    logger.info(f"⏱️ ChromaDB: Añadidos {len(chunks)} chunks en {chroma_time:.3f} segundos")
                    logger.info(f"✅ Añadidos {len(chunks)} chunks a ChromaDB en {collection_name}")
                    return True
                except concurrent.futures.TimeoutError:
                    logger.error(f"⚠️ TIMEOUT de {settings.CHROMA_OPERATION_TIMEOUT}s al añadir documentos a ChromaDB")
                    raise ExternalServiceException(f"Timeout al añadir documentos a ChromaDB ({settings.CHROMA_OPERATION_TIMEOUT}s)")
                
        except ExternalServiceException:
            raise  # Re-lanzar excepciones ya manejadas
        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"❌ Error en ChromaDB después de {error_time:.3f} segundos: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al añadir documentos a ChromaDB: {str(e)}")
    
#--------------------------------------------------
  

    def search_documents(self, 
                collection_name: str,
                query_text: str,
                n_results: int = 5,
                where: Optional[Dict[str, Any]] = None):
        try:
            client = self.get_client()
            self._ensure_collection_exists(collection_name)
            collection = client.get_collection(collection_name)
            
            # Si where es un diccionario vacío, establecerlo a None
            if where is not None and not where:
                where = None
                
            # Formato correcto para where: debe incluir un operador como $eq, $gt, etc.
            # Ejemplo: {"document_id": {"$eq": "33"}}
            
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where
            )
            return results
        except Exception as e:
            logger.error(f"Error al buscar documentos: {str(e)}", exc_info=True)
            raise ExternalServiceException(f"Error en la búsqueda de ChromaDB: {str(e)}")
    
#--------------------------------------------------

    def update_document(self,
                   collection_name: str,                     # Nombre de la colección
                   document_id: str,                         # ID único del documento a actualizar
                   chunk: Optional[str] = None,              # Nuevo texto a guardar (opcional)
                   metadata: Optional[Dict[str, Any]] = None): # Nuevos metadatos (opcional
        """Actualiza un documento existente"""
        
        try:
            client = self.get_client()
            collection = client.get_collection(name=collection_name)
            collection.update(
                ids=[document_id], # ID del documento a actualizar
                documents=[chunk] if chunk else None, # Nuevo contenido del documento enviado a traves de chunk a chroma que ya existe previamente en la base de datos y si es none indica que no quiero actualizar el contenido
                metadatas=[metadata] if metadata else None # los datos por los cuales a traves vas hacer una consulta
            )
            logger.info(f"Documento {document_id} actualizado en {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error al actualizar documento: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al actualizar documento en ChromaDB: {str(e)}")


#---------------------------------------------------------

    def delete_documents(self, collection_name: str, document_ids: List[str]):
        """Elimina documentos por ID"""
        client = self.get_client()
        try:
            collection = client.get_collection(name=collection_name)
            collection.delete(ids=document_ids)
            logger.info(f"Eliminados {len(document_ids)} documentos de {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar documentos: {str(e)}", exc_info=True)
            raise DatabaseException(f"Error al eliminar documentos de ChromaDB: {str(e)}")


#---------------------------------------------------------
    def get_document(self, collection_name: str, document_id: str):
        """Obtiene un documento específico por ID"""
        client = self.get_client()
        try:
            client = self.get_client()
            collection = client.get_collection(name=collection_name)
            
            result = collection.get(ids=[document_id])
            return result
        except Exception as e:
            logger.error(f"Error al obtener documento: {str(e)}")
            return None
    
    def search_relevant_chunks(self, 
                             query: str,
                             document_ids: List[int],
                             n_results: int = 5,
                             collection_name: str = "documents") -> List[Dict[str, Any]]:
        """
        Busca chunks relevantes en documentos específicos
        
        Args:
            query: Texto de búsqueda
            document_ids: Lista de IDs de documentos
            n_results: Número de resultados a retornar
            collection_name: Nombre de la colección
            
        Returns:
            Lista de chunks con su contenido y metadata
        """
        try:
            # Construir filtro where para ChromaDB
            where = {
                "document_id": {
                    "$in": [str(doc_id) for doc_id in document_ids]
                }
            }
            
            # Realizar búsqueda
            results = self.search_documents(
                collection_name=collection_name,
                query_text=query,
                n_results=n_results,
                where=where
            )
            
            # Formatear resultados
            formatted_results = []
            if results and 'documents' in results:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if 'metadatas' in results else {},
                        'distance': results['distances'][0][i] if 'distances' in results else 0
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error buscando chunks relevantes: {str(e)}")
            return []

# Función auxiliar para obtener el conector
def get_chromadb_connector():
    """Obtiene la instancia del conector ChromaDB"""
    return ChromaDBConnector()
            
        