# Configurar timezone a UTC
from src.utils.timezone_utils import get_utc_now, ensure_utc, format_for_db

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError
from src.api.routes import api_router
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
from src.utils.chromadb_connector import ChromaDBConnector, get_chromadb_connector
from src.config.settings import get_settings
import logging
import sentry_sdk
from loguru import logger
# from sentry_sdk.integrations.fastapi import FastAPIIntegration  # Comentado temporalmente
from src.services.token_blacklist_service import token_blacklist
from src.core.token_middleware import TokenMiddleware

# Importar los manejadores de excepciones
from src.api.middleware.exception_handlers import (
    app_exception_handler,
    http_exception_handler,
    generic_exception_handler
)
from src.core.exceptions import AppException
from fastapi.exceptions import HTTPException

# Obtener configuración
settings = get_settings()

# Configurar el limiter para rate limiting
limiter = Limiter(key_func=get_remote_address)

# Configuración de seguridad JWT
security = HTTPBearer(
    scheme_name="JWT Bearer Token",
    description="Token JWT para autenticación. Formato: Bearer <token>"
)

# Metadatos completos para la documentación OpenAPI
api_metadata = {
    "title": "ChatBot API - Sistema RAG Inteligente",
    "description": """
## 🤖 ChatBot API con RAG (Retrieval-Augmented Generation)

**Una API completa para un chatbot inteligente que procesa documentos y genera respuestas contextuales.**

### 🚀 Características principales:

* **📄 Procesamiento de documentos:** Sube PDFs, archivos de texto y más
* **🧠 RAG (Retrieval-Augmented Generation):** Respuestas basadas en tus documentos
* **🔐 Autenticación JWT:** Sistema seguro con refresh tokens
* **⚡ Rate Limiting:** Protección contra abuso
* **📊 Estadísticas:** Monitoreo de uso y rendimiento
* **👥 Gestión de usuarios:** Registro, login y perfiles
* **🛡️ Administración:** Panel de admin para gestión avanzada

### 🔧 Tecnologías utilizadas:

* **FastAPI** - Framework web moderno y rápido
* **Supabase** - Base de datos PostgreSQL en la nube
* **ChromaDB** - Base de datos vectorial para embeddings
* **Gemini AI** - Modelo de lenguaje para generación de respuestas
* **JWT** - Autenticación segura con tokens
* **Pydantic** - Validación de datos y serialización

### 📚 Documentación:

* **Swagger UI:** [/docs](/docs) - Interfaz interactiva
* **ReDoc:** [/redoc](/redoc) - Documentación alternativa
* **OpenAPI JSON:** [/openapi.json](/openapi.json) - Especificación completa
    """,
    "version": "2.0.0",
    "contact": {
        "name": "ChatBot API Team"
    },
    "license_info": {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    "servers": [
        {
            "url": "http://localhost:2690",
            "description": "Servidor de desarrollo"
        },
        {
            "url": "https://api.chatbot.com",
            "description": "Servidor de producción"
        }
    ]
}

# Tags para organizar los endpoints
tags_metadata = [
    {
        "name": "🏥 Health",
        "description": "Endpoints para verificar el estado del servicio y realizar diagnósticos."
    },
    {
        "name": "👤 Usuarios",
        "description": """
        Gestión completa de usuarios: registro, autenticación, perfiles y tokens.
        
        **Flujo de autenticación:**
        1. Registrarse con `/register`
        2. Hacer login con `/login` para obtener tokens
        3. Usar el `access_token` en el header `Authorization: Bearer <token>`
        4. Refrescar tokens con `/refresh-token` cuando expiren
        """
    },
    {
        "name": "📄 Documentos",
        "description": """
        Upload, procesamiento y gestión de documentos para el sistema RAG.
        
        **Tipos de archivo soportados:**
        * PDF (hasta 50MB)
        * Archivos de texto (hasta 10MB)  
        * Excel/CSV (hasta 25MB)
        
        **Proceso:**
        1. Subir documento con `/upload`
        2. El sistema extrae y vectoriza el contenido automáticamente
        3. El documento queda disponible para consultas de chat
        """
    },
    {
        "name": "💬 Chat",
        "description": """
        Sistema de chat inteligente con RAG (Retrieval-Augmented Generation).
        
        **Cómo funciona:**
        1. Envía una pregunta con `/question`
        2. El sistema busca información relevante en tus documentos
        3. Genera una respuesta contextual usando IA
        4. Mantiene historial de conversaciones
        """
    },
    {
        "name": "📊 Estadísticas",
        "description": "Métricas de uso, rendimiento y análisis del sistema."
    },
    {
        "name": "📁 Archivos",
        "description": "Servir y gestionar archivos subidos de forma segura."
    },
    {
        "name": "🛡️ Admin",
        "description": """
        Panel de administración para usuarios con permisos elevados.
        
        **Requiere:** Usuario con `is_admin: true`
        """
    }
]

# Crear la aplicación con configuración completa
app = FastAPI(
    **api_metadata,
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Agregar el manejador de errores para rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Registrar los manejadores de excepciones personalizadas
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Manejador de excepciones personalizado para errores de validación
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    
    # Procesar los mensajes de error para quitar el prefijo "Value error, "
    cleaned_errors = []
    for error in errors:
        msg = error.get('msg', '')
        # Quitar el prefijo "Value error, " si existe
        if msg.startswith('Value error, '):
            msg = msg.replace('Value error, ', '')
        
        # Actualizar el mensaje de error
        error['msg'] = msg
        cleaned_errors.append(error)
    
    # Si hay un solo error, devolver solo el mensaje
    if len(cleaned_errors) == 1:
        return JSONResponse(
            status_code=422,
            content={"detail": cleaned_errors[0]['msg']}
        )
    
    # Si hay múltiples errores, devolver todos
    return JSONResponse(
        status_code=422,
        content={"detail": cleaned_errors}
    )

# Configuración de CORS - SEGURA
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins,  # Orígenes específicos según el entorno
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    expose_headers=["*"],  # Headers que el cliente puede acceder
    max_age=3600  # Cache de preflight en segundos
)

# Agregar middleware de manejo de tokens
app.add_middleware(TokenMiddleware)

# Inicializar Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        # integrations=[FastAPIIntegration()]  # Comentado temporalmente
    )

# Configurar Loguru
logger.add("logs/app.log", rotation="10 MB", retention="10 days", level="DEBUG")

# Capturar logs de FastAPI
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    try:
        body = await response.body()
    except Exception:
        body = "<body not available>"
    logger.info(f"Response: {response.status_code} {body}")
    return response

# Endpoint de health check mejorado con documentación
@app.get(
    "/health",
    tags=["🏥 Health"],
    summary="❤️ Estado del servicio",
    description="""
    Verifica que el servicio esté funcionando correctamente.
    
    **Retorna:**
    - Estado del servicio
    - Entorno de ejecución
    - Configuración de CORS
    - Estado del rate limiting
    
    **Uso:** Ideal para health checks de load balancers y monitoreo.
    """,
    responses={
        200: {
            "description": "Servicio funcionando correctamente",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "environment": "development",
                        "cors_enabled": True,
                        "rate_limiting_enabled": True
                    }
                }
            }
        }
    }
)
async def health_check():
    """Endpoint para verificar que el servicio está activo"""
    return {
        "status": "healthy",
        "environment": settings.APP_ENVIRONMENT,
        "cors_enabled": True,
        "rate_limiting_enabled": settings.RATE_LIMIT_ENABLED
    }

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
    
    # Inicializar servicio de token blacklist
    await token_blacklist.start()
    logging.info("🔐 Token Blacklist Service iniciado")
    
    # Log de configuración de seguridad
    logging.info(f"🔒 CORS configurado para: {settings.get_cors_origins}")
    logging.info(f"🚦 Rate limiting: {'ACTIVADO' if settings.RATE_LIMIT_ENABLED else 'DESACTIVADO'}")
    logging.info(f"🌍 Entorno: {settings.APP_ENVIRONMENT}")

# Evento de cierre de la aplicación
@app.on_event("shutdown")
async def shutdown():
    # Detener servicio de token blacklist
    await token_blacklist.stop()
    logging.info("🔐 Token Blacklist Service detenido")

# Incluir el router principal
app.include_router(api_router, prefix="/api")

# Incluir página de documentación personalizada
from src.api.docs_page import docs_router
app.include_router(docs_router)

# Configuración personalizada de OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=api_metadata["title"],
        version=api_metadata["version"],
        description=api_metadata["description"],
        routes=app.routes,
    )
    
    # Agregar configuración de seguridad JWT
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": """
            Token JWT para autenticación.
            
            **Cómo obtener el token:**
            1. Registrarse con POST /api/users/register
            2. Hacer login con POST /api/users/login
            3. Usar el access_token recibido
            
            **Formato:** Bearer <access_token>
            
            **Ejemplo:** Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
            """
        }
    }
    
    # Agregar información de contacto y licencia
    openapi_schema["info"]["contact"] = api_metadata["contact"]
    openapi_schema["info"]["license"] = api_metadata["license_info"]
    
    # Agregar servidores
    openapi_schema["servers"] = api_metadata["servers"]
    
    # Agregar ejemplos de respuestas de error comunes
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "error_code": {
                "type": "string",
                "example": "VALIDATION_ERROR"
            },
            "message": {
                "type": "string", 
                "example": "Los datos proporcionados no son válidos"
            },
            "details": {
                "type": "object",
                "example": {}
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Asignar la función personalizada
app.openapi = custom_openapi

# NOTA: El rate limiting se aplica individualmente en cada endpoint que lo necesita
# usando los decoradores @rate_limit_* en los archivos de endpoints

if __name__ == "__main__":
    # Configuraciones adicionales de uvicorn para el servidor
    config = uvicorn.Config(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        limit_concurrency=1000,  # Límite de conexiones concurrentes
        limit_max_requests=10000,  # Límite de peticiones máximas
        timeout_keep_alive=120,   # Tiempo de espera para mantener la conexión viva
        backlog=2048,            # Cola de conexiones pendientes
    )
    
    server = uvicorn.Server(config)
    server.run()
