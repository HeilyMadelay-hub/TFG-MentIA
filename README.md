# 📚 DocuMente - Asistente de Documentos con IA

## 🎬 Demo del Proyecto

### Video Presentación del TFG
https://github.com/tu-usuario/documenta/assets/123456/demo-documenta-tfg.mp4

*Video demostrativo mostrando todas las funcionalidades del sistema*

## 🎯 Descripción General

**DocuMente** es una aplicación web completa que transforma documentos empresariales en información accesible mediante IA conversacional. Reduce drásticamente el tiempo de búsqueda de información permitiendo a los usuarios interactuar con sus documentos usando lenguaje natural.

### 🌟 Características Principales

- **🤖 Chat con RAG**: IA conversacional usando Google Gemini para consultas inteligentes
- **📄 Soporte Multi-formato**: Procesa PDFs y archivos de texto hasta 100MB
- **🔍 Búsqueda Semántica**: Búsqueda vectorial avanzada con ChromaDB
- **👥 Compartir Documentos**: Comparte documentos con usuarios específicos
- **🔐 Seguridad Empresarial**: Autenticación JWT con refresh tokens
- **📊 Panel Administrativo**: Panel completo para gestión del sistema
- **📱 Diseño Responsivo**: Interfaz Flutter Web que funciona en todos los dispositivos
- **⚡ Alto Rendimiento**: Soporta 1000+ conexiones concurrentes

## 🏗️ Arquitectura

### Arquitectura Backend
```
backend/
├── src/
│   ├── api/          # Endpoints API (60+ endpoints REST)
│   ├── services/     # Capa de lógica de negocio
│   ├── repositories/ # Capa de acceso a datos
│   ├── models/       # Modelos de dominio y esquemas
│   ├── config/       # Gestión de configuración
│   ├── utils/        # Utilidades y helpers
│   └── main.py       # Punto de entrada de la aplicación
```

### Arquitectura Frontend
```
frontend/
├── lib/
│   ├── screens/      # Pantallas de la aplicación
│   ├── services/     # Servicios y API clients
│   ├── providers/    # Gestión de estado (Provider)
│   ├── models/       # Modelos de datos
│   ├── widgets/      # Componentes reutilizables
│   └── main.dart     # Entrada de la aplicación
```

## 🚀 Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web moderno y de alto rendimiento
- **PostgreSQL/Supabase**: Base de datos relacional con capacidades en tiempo real
- **ChromaDB**: Base de datos vectorial para búsqueda semántica
- **Google Gemini**: Modelo de IA para procesamiento de lenguaje natural
- **Docker**: Containerización para ChromaDB
- **JWT**: Autenticación segura con tokens

### Frontend
- **Flutter Web**: Framework para desarrollo web responsivo
- **Provider**: Gestión de estado
- **Dio/HTTP**: Clientes HTTP para comunicación con API
- **Material Design 3**: Sistema de diseño moderno

## 📋 Requisitos Previos

- Python 3.9 o superior
- Flutter 3.10 o superior
- Docker y Docker Compose
- PostgreSQL o cuenta en Supabase
- Clave API de Google Gemini

## 🚀 Inicio Rápido

```bash
# Backend
cd backend
python -m uvicorn src.main:app --host 127.0.0.1 --port 2690 --reload

# Frontend (en otra terminal)
cd frontend/frontend_flutter
flutter run -d chrome --web-port=53793
```

## 🛠️ Instalación

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/documenta.git
cd documenta
```

### 2. Configurar el Backend

#### Crear entorno virtual
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
```

#### Instalar dependencias
```bash
pip install -r requirements.txt
```

#### Configurar variables de entorno

Copiar el archivo de ejemplo y editarlo con tus credenciales:

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales reales:

```env
# Base de datos
SUPABASE_URL=tu_supabase_url
SUPABASE_KEY=tu_supabase_key
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key

# ChromaDB
CHROMADB_HOST=localhost
CHROMADB_PORT=8050

# Google Gemini
GOOGLE_API_KEY=tu_google_api_key

# JWT
JWT_SECRET_KEY=tu_clave_secreta_segura
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# SMTP (para recuperación de contraseñas)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu_email@gmail.com
SMTP_PASSWORD=tu_contraseña_app
SMTP_FROM_EMAIL=tu_email@gmail.com
SMTP_FROM_NAME=DocuMente

# Servidor
APP_HOST=127.0.0.1
APP_PORT=2690
```

#### Iniciar ChromaDB con Docker
```bash
docker-compose up -d
```

#### Ejecutar migraciones (si aplica)
```bash
python -m src.migrations.run_migrations
```

#### Iniciar el servidor
```bash
python -m uvicorn src.main:app --host 127.0.0.1 --port 2690 --reload
```

El backend estará disponible en `http://localhost:2690`

### 3. Configurar el Frontend

#### Navegar a la carpeta del frontend
```bash
cd ../frontend/frontend_flutter
```

#### Instalar dependencias
```bash
flutter pub get
```

#### Configurar la URL del API

Editar `lib/config/api_config.dart`:

```dart
class ApiConfig {
  static const String baseUrl = 'http://localhost:2690/api';
}
```

#### Ejecutar la aplicación
```bash
flutter run -d chrome --web-port=53793
```

La aplicación estará disponible en `http://localhost:53793`

## 📖 Uso

### 1. Registro e Inicio de Sesión

- Accede a la aplicación web en `http://localhost:53793`
- **Usuario de ejemplo:**
  - Email: `heily1857@gmail.com`
  - Contraseña: `paco 1234`

- **Usuario administrador:**
  - Usuario: `ivan`
  - Contraseña: `ivan1234`

### 2. Recuperación de Contraseñas

Para que funcione la recuperación de contraseñas, debes configurar las credenciales SMTP en el archivo `.env`:

```env
# Configuración SMTP para envío de emails
SMTP_HOST=smtp.gmail.com        # o tu servidor SMTP
SMTP_PORT=587
SMTP_USERNAME=tu_email@gmail.com
SMTP_PASSWORD=tu_contraseña_app  # Para Gmail, usa una contraseña de aplicación
SMTP_FROM_EMAIL=tu_email@gmail.com
SMTP_FROM_NAME=DocuMente
```

**Nota para Gmail:**
- Activa la verificación en dos pasos en tu cuenta
- Genera una contraseña de aplicación en: https://myaccount.google.com/apppasswords
- Usa esa contraseña en lugar de tu contraseña normal

### 3. Gestión de Documentos

- **Subir Documentos**: Arrastra y suelta o selecciona archivos PDF/TXT
- **Ver Documentos**: Lista todos tus documentos con opciones de filtrado
- **Compartir**: Comparte documentos con otros usuarios del sistema
- **Buscar**: Usa la búsqueda semántica para encontrar información

### 4. Chat con IA

- Crea nuevas conversaciones
- Haz preguntas sobre tus documentos
- El sistema responderá basándose en el contenido de los documentos
- Puedes especificar documentos específicos para las consultas

### 5. Panel Administrativo (Solo Admin)

- Ver estadísticas del sistema
- Gestionar usuarios
- Administrar todos los documentos
- Monitorear conversaciones

## 🔧 API Endpoints Principales

### Autenticación
- `POST /api/users/login` - Iniciar sesión
- `POST /api/users/register` - Registrar usuario
- `POST /api/users/refresh-token` - Renovar token
- `GET /api/users/me` - Obtener usuario actual

### Documentos
- `POST /api/documents/upload` - Subir documento
- `GET /api/documents` - Listar documentos del usuario
- `POST /api/documents/{id}/share` - Compartir documento
- `GET /api/documents/search` - Buscar en documentos
- `DELETE /api/documents/{id}` - Eliminar documento

### Chat
- `POST /api/chats` - Crear chat
- `GET /api/chats` - Listar chats
- `POST /api/chats/{id}/messages` - Enviar mensaje
- `GET /api/chats/{id}/messages` - Obtener mensajes

### Estadísticas
- `GET /api/statistics/dashboard` - Datos del dashboard
- `GET /api/statistics/global` - Estadísticas globales

## 🐳 Despliegue con Docker

### Docker Compose Completo

```yaml
version: '3.8'

services:
  chromadb:
    image: ghcr.io/chroma-core/chroma:latest
    ports:
      - "8050:8000"
    volumes:
      - ./chroma-data:/chroma/chroma
    environment:
      - ALLOW_RESET=true
      - PERSIST_DIRECTORY=/chroma/chroma

  backend:
    build: ./backend
    ports:
      - "2690:2690"
    depends_on:
      - chromadb
    environment:
      - CHROMADB_HOST=chromadb
    env_file:
      - ./backend/.env

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/
```

### Frontend Tests
```bash
cd frontend/frontend_flutter
flutter test
```

## 📊 Características de Rendimiento

- **Procesamiento Asíncrono**: Documentos grandes se procesan en segundo plano
- **Caché de Vectores**: ChromaDB almacena embeddings para búsquedas rápidas
- **Paginación**: Todos los endpoints de listado soportan paginación
- **Rate Limiting**: Protección contra abuso de API
- **Conexiones Concurrentes**: Soporta 1000+ usuarios simultáneos

## 🔒 Seguridad

- **Autenticación JWT**: Tokens seguros con expiración
- **Refresh Tokens**: Renovación automática de sesiones
- **Validación de Entrada**: Todos los datos son validados con Pydantic
- **Permisos Granulares**: Control de acceso a nivel de documento
- **CORS Configurado**: Protección contra peticiones no autorizadas
- **Variables de Entorno**: El archivo `.env` está en `.gitignore` para proteger credenciales

> ⚠️ **IMPORTANTE**: Nunca subas el archivo `.env` a GitHub. Crea un archivo `.env.example` con valores de ejemplo para referencia.

## 🤝 Contribuir

1. Fork el proyecto
2. Crea tu rama de características (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📸 Capturas de Pantalla

<details>
<summary>🔐 Pantalla de Login</summary>
<br>
<img src="docs/screenshots/login.png" alt="Login Screen" width="600">
<p><em>Interfaz de inicio de sesión con diseño moderno y responsivo</em></p>
</details>

<details>
<summary>📊 Dashboard Principal</summary>
<br>
<img src="docs/screenshots/dashboard.png" alt="Dashboard" width="600">
<p><em>Panel principal con estadísticas y accesos rápidos</em></p>
</details>

<details>
<summary>📄 Gestión de Documentos</summary>
<br>
<img src="docs/screenshots/documents.png" alt="Documents Management" width="600">
<p><em>Vista de documentos con opciones de filtrado y búsqueda</em></p>
</details>

<details>
<summary>💬 Chat con IA</summary>
<br>
<img src="docs/screenshots/chat.png" alt="AI Chat" width="600">
<p><em>Interfaz de chat conversacional con respuestas basadas en documentos</em></p>
</details>

<details>
<summary>👥 Compartir Documentos</summary>
<br>
<img src="docs/screenshots/share.png" alt="Share Documents" width="600">
<p><em>Sistema de permisos para compartir documentos con usuarios específicos</em></p>
</details>

<details>
<summary>🎛️ Panel Administrativo</summary>
<br>
<img src="docs/screenshots/admin.png" alt="Admin Panel" width="600">
<p><em>Panel completo para administradores con gestión de usuarios y sistema</em></p>
</details>

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 👥 Equipo

- **Desarrollador Principal**: [Tu Nombre]
- **Contacto**: [tu-email@ejemplo.com]

---

<p align="center">
  <strong>⭐ Si te gusta este proyecto, no olvides darle una estrella! ⭐</strong>
</p>
