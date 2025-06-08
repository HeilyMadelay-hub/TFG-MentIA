from fastapi import FastAPI
from src.api.routes import api_router
from fastapi.middleware.cors import CORSMiddleware
from src.models.schemas.user import UserCreate, UserResponse
from src.models.schemas.document import DocumentBase, DocumentResponse
from src.models.schemas.chat import ChatMessage
import uvicorn
from src.utils.chromadb_connector import ChromaDBConnector, get_chromadb_connector
import logging

# Crear la aplicación
app = FastAPI(
    title="ChatBot Backend",
    description="API para el chatbot con manejo de documentos grandes",
    version="1.0.0"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Evento de inicio de la aplicación
@app.on_event("startup")
async def startup():
    # Configuraciones para manejar archivos grandes
    uvicorn.config.LIFESPAN_ON_STARTUP = True
    uvicorn.config.LOOP_WAIT = 0.1
    uvicorn.config.HTTP_TIMEOUT_KEEP_ALIVE = 120
    
    # Inicializar ChromaDB
    global chroma_db
    chroma_db = ChromaDBConnector()
    logging.info("ChromaDB inicializado correctamente")

# Incluir el router principal
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    # Configuraciones adicionales de uvicorn para el servidor
    config = uvicorn.Config(
        "src.main:app",
        host="127.0.0.1",
        port=2690,
        reload=True,
        limit_concurrency=1000,  # Límite de conexiones concurrentes
        limit_max_requests=10000,  # Límite de peticiones máximas
        timeout_keep_alive=120,   # Tiempo de espera para mantener la conexión viva
        backlog=2048,            # Cola de conexiones pendientes
    )
    
    server = uvicorn.Server(config)
    server.run()