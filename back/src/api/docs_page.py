"""
📚 PÁGINA DE DOCUMENTACIÓN PERSONALIZADA PARA LA API
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

# Router para documentación
docs_router = APIRouter(prefix="/api-docs", tags=["📚 Documentación"])

@docs_router.get("/", response_class=HTMLResponse)
async def api_documentation():
    """Página de documentación interactiva de la API"""
    
    html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChatBot API - Documentación</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card { transition: transform 0.2s ease-in-out; }
        .card:hover { transform: translateY(-2px); }
    </style>
</head>
<body class="bg-gray-50">
    <!-- Header -->
    <header class="gradient-bg text-white">
        <div class="container mx-auto px-6 py-12">
            <div class="text-center">
                <h1 class="text-5xl font-bold mb-4">🤖 ChatBot API</h1>
                <p class="text-xl text-blue-100 mb-6">Sistema RAG Inteligente - Documentación Completa</p>
                <div class="flex justify-center space-x-4">
                    <a href="/docs" class="bg-white text-blue-600 px-6 py-3 rounded-lg font-semibold hover:bg-blue-50 transition">
                        📖 Swagger UI
                    </a>
                    <a href="/redoc" class="bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-800 transition">
                        📚 ReDoc
                    </a>
                    <a href="/openapi.json" class="bg-transparent border-2 border-white text-white px-6 py-3 rounded-lg font-semibold hover:bg-white hover:text-blue-600 transition">
                        📄 OpenAPI JSON
                    </a>
                </div>
            </div>
        </div>
    </header>

    <div class="container mx-auto px-6 py-8">
        <!-- Quick Start -->
        <section class="mb-16">
            <h2 class="text-3xl font-bold text-gray-800 mb-6">🚀 Inicio Rápido</h2>
            <div class="grid md:grid-cols-2 gap-8">
                <div class="card bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-4">🔧 Configuración Base</h3>
                    <pre class="bg-gray-100 p-4 rounded"><code>BASE_URL = "http://localhost:2690/api"

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}</code></pre>
                </div>
                
                <div class="card bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-4">⚡ Health Check</h3>
                    <pre class="bg-gray-100 p-4 rounded"><code>curl -X GET "http://localhost:2690/health"

# Respuesta:
{
    "status": "healthy",
    "environment": "development"
}</code></pre>
                </div>
            </div>
        </section>

        <!-- Authentication -->
        <section class="mb-16">
            <h2 class="text-3xl font-bold text-gray-800 mb-6">🔐 Autenticación</h2>
            
            <div class="bg-blue-50 border-l-4 border-blue-400 p-6 mb-8">
                <h4 class="text-lg font-semibold text-blue-800 mb-2">📋 Proceso</h4>
                <ol class="list-decimal list-inside text-blue-700 space-y-2">
                    <li><strong>Registrarse:</strong> POST /api/users/register</li>
                    <li><strong>Login:</strong> POST /api/users/login</li>
                    <li><strong>Usar token:</strong> Header Authorization: Bearer &lt;token&gt;</li>
                    <li><strong>Refrescar:</strong> POST /api/users/refresh-token</li>
                </ol>
            </div>

            <div class="grid md:grid-cols-2 gap-8">
                <div class="card bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-4">📝 Registro</h3>
                    <pre class="bg-gray-100 p-4 rounded text-sm"><code>POST /api/users/register

{
    "username": "mi_usuario",
    "email": "usuario@ejemplo.com",
    "password": "mi_password_seguro"
}</code></pre>
                </div>

                <div class="card bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-4">🔑 Login</h3>
                    <pre class="bg-gray-100 p-4 rounded text-sm"><code>POST /api/users/login

Form data:
username: "mi_usuario"
password: "mi_password_seguro"</code></pre>
                </div>
            </div>
        </section>

        <!-- Endpoints -->
        <section class="mb-16">
            <h2 class="text-3xl font-bold text-gray-800 mb-6">📡 Endpoints Principales</h2>
            
            <div class="grid md:grid-cols-3 gap-6">
                <div class="card bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-4">👤 Usuarios</h3>
                    <ul class="space-y-2 text-sm">
                        <li><span class="bg-green-100 px-2 py-1 rounded text-xs">POST</span> /users/register</li>
                        <li><span class="bg-green-100 px-2 py-1 rounded text-xs">POST</span> /users/login</li>
                        <li><span class="bg-blue-100 px-2 py-1 rounded text-xs">GET</span> /users/me</li>
                        <li><span class="bg-yellow-100 px-2 py-1 rounded text-xs">PUT</span> /users/me</li>
                        <li><span class="bg-green-100 px-2 py-1 rounded text-xs">POST</span> /users/refresh-token</li>
                    </ul>
                </div>

                <div class="card bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-4">📄 Documentos</h3>
                    <ul class="space-y-2 text-sm">
                        <li><span class="bg-green-100 px-2 py-1 rounded text-xs">POST</span> /documents/upload</li>
                        <li><span class="bg-blue-100 px-2 py-1 rounded text-xs">GET</span> /documents/</li>
                        <li><span class="bg-blue-100 px-2 py-1 rounded text-xs">GET</span> /documents/{id}</li>
                        <li><span class="bg-red-100 px-2 py-1 rounded text-xs">DELETE</span> /documents/{id}</li>
                        <li><span class="bg-blue-100 px-2 py-1 rounded text-xs">GET</span> /documents/{id}/status</li>
                    </ul>
                </div>

                <div class="card bg-white p-6 rounded-lg shadow-lg">
                    <h3 class="text-xl font-semibold mb-4">💬 Chat</h3>
                    <ul class="space-y-2 text-sm">
                        <li><span class="bg-green-100 px-2 py-1 rounded text-xs">POST</span> /chat/question</li>
                        <li><span class="bg-blue-100 px-2 py-1 rounded text-xs">GET</span> /chat/history</li>
                        <li><span class="bg-blue-100 px-2 py-1 rounded text-xs">GET</span> /chat/conversations</li>
                        <li><span class="bg-red-100 px-2 py-1 rounded text-xs">DELETE</span> /chat/{id}</li>
                    </ul>
                </div>
            </div>
        </section>

        <!-- Quick Example -->
        <section class="mb-16">
            <h2 class="text-3xl font-bold text-gray-800 mb-6">💡 Ejemplo Práctico</h2>
            
            <div class="card bg-white p-6 rounded-lg shadow-lg">
                <h3 class="text-xl font-semibold mb-4">🔄 Flujo completo: Login → Upload → Chat</h3>
                <pre class="bg-gray-100 p-4 rounded text-sm overflow-x-auto"><code># 1. Login
POST /api/users/login
Data: username=mi_usuario&password=mi_password

# 2. Upload documento (con token del login)
POST /api/documents/upload
Header: Authorization: Bearer {access_token}
Body: FormData con archivo

# 3. Hacer pregunta
POST /api/chat/question
Header: Authorization: Bearer {access_token}
Body: {"question": "¿Qué dice el documento sobre ventas?"}</code></pre>
            </div>
        </section>

        <!-- Rate Limits -->
        <section class="mb-16">
            <h2 class="text-3xl font-bold text-gray-800 mb-6">⚡ Límites de Velocidad</h2>
            
            <div class="bg-yellow-50 border-l-4 border-yellow-400 p-6">
                <h4 class="text-lg font-semibold text-yellow-800 mb-2">⚠️ Límites por Endpoint</h4>
                <ul class="text-yellow-700 space-y-1">
                    <li>📝 <strong>Registro:</strong> 5 requests/minuto</li>
                    <li>🔑 <strong>Login:</strong> 10 requests/minuto</li>
                    <li>📤 <strong>Upload:</strong> 10 requests/minuto</li>
                    <li>💬 <strong>Chat:</strong> 30 requests/minuto</li>
                    <li>📊 <strong>General:</strong> 100 requests/minuto</li>
                </ul>
            </div>
        </section>
    </div>

    <!-- Footer -->
    <footer class="bg-gray-800 text-white py-12">
        <div class="container mx-auto px-6 text-center">
            <h3 class="text-2xl font-bold mb-4">🤖 ChatBot API</h3>
            <p class="text-gray-400 mb-6">Sistema RAG Inteligente - Documentación</p>
            <div class="flex justify-center space-x-6">
                <a href="/docs" class="text-blue-400 hover:text-blue-300">📖 Swagger UI</a>
                <a href="/redoc" class="text-blue-400 hover:text-blue-300">📚 ReDoc</a>
                <a href="/openapi.json" class="text-blue-400 hover:text-blue-300">📄 OpenAPI Schema</a>
            </div>
            <p class="text-gray-500 mt-6">© 2024 ChatBot API. Desarrollado con FastAPI.</p>
        </div>
    </footer>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)
