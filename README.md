<div align="center">

# DocuSense API

Backend REST para análisis inteligente de documentos PDF con autenticación JWT, streaming de respuestas en tiempo real, gestión de documentos y chat contextualizado con IA.

<p>
  <img src="https://img.shields.io/badge/FastAPI-0.135.3-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PostgreSQL-15+-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/JWT-Secured-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white" alt="JWT">
  <img src="https://img.shields.io/badge/OpenAI-GPT--4-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI">
</p>

</div>

## Documentación de API

- Documentación interactiva: `/docs`
- OpenAPI JSON: `/openapi.json`
- Health check: `/health`

## Tabla de contenido

1. [Visión del proyecto](#visión-del-proyecto)
2. [Cómo funciona la API](#cómo-funciona-la-api)
3. [Flujos principales](#flujos-principales)
4. [Stack y versiones](#stack-y-versiones)
5. [Arquitectura backend](#arquitectura-backend)
6. [Endpoints principales](#endpoints-principales)
7. [Respuestas principales](#respuestas-principales)
8. [Configuración](#configuración)
9. [Ejecución local](#ejecución-local)
10. [Docker](#docker)
11. [Estructura del proyecto](#estructura-del-proyecto)
12. [Decisiones técnicas](#decisiones-técnicas)
13. [Seguridad](#seguridad)

## Visión del proyecto

DocuSense API fue construida para democratizar el análisis inteligente de documentos PDF permitiendo usuarios conversar con sus archivos usando IA de forma segura y eficiente.

- Autenticación sin estado con JWT.
- Carga y procesamiento seguro de documentos PDF.
- Extracción de contenido con librerías especializadas (pdfplumber, markitdown).
- Streaming de respuestas en tiempo real para UX fluida.
- Chat contextualizado: responde basado en contenido del documento.
- Gestión de sesiones de usuario con SQLAlchemy ORM.
- Persistencia relacional con PostgreSQL.
- Rate limiting y validación de entrada robusta.
- Manejo consistente de errores con códigos REST semánticos.

## Cómo funciona la API

El flujo principal es:

1. El usuario se registra o inicia sesión en `/auth/register` o `/auth/login`.
2. El backend valida credenciales, hashea contraseña con bcrypt y devuelve JWT.
3. El cliente adjunta el token en `Authorization: Bearer <token>` en cada solicitud.
4. La API valida el token con middleware JWT stateless.
5. El usuario carga documentos PDF en `/documents/upload`.
6. El backend extrae texto, almacena el documento y genera resumen inicial.
7. El usuario inicia chat en `/chat/stream` con el documento como contexto.
8. La API llama a OpenAI con el contexto del PDF + pregunta del usuario.
9. Las respuestas se devuelven como server-sent events (SSE) para streaming en tiempo real.
10. Si el token expira o es inválido, el backend responde con 401 Unauthorized.

La aplicación prioriza la experiencia del usuario: extracción de documentos es silenciosa, el chat es reactivo y las respuestas llegan parcialmente conforme se generan.

## Flujos principales

### Upload de Documento

1. Cliente POST `/documents/upload` con PDF multipart/form-data
2. Backend valida tipo MIME y tamaño máximo (ajustable)
3. Extrae texto con pdfplumber + markitdown
4. Genera resumen inicial con OpenAI
5. Almacena en BD: documento, contenido, metadata
6. Devuelve `DocumentResponse` con ID, nombre, tamaño, fecha

### Chat Contextualizado

1. Cliente GET `/chat/stream?doc_id=X&message=Y` con streaming aceptado
2. Backend valida documento pertenece al usuario autenticado
3. Recupera contenido del PDF desde BD
4. Construye prompt: contexto del PDF + pregunta del usuario
5. Llama OpenAI API con parámetro `stream=true`
6. Devuelve eventos SSE mientras OpenAI genera respuesta
7. Cliente recibe chunks parciales y actualiza UI en tiempo real

### Autenticación

1. Usuario POST `/auth/register` con email, password, name
2. Backend normaliza email (trim + lowercase)
3. Valida password: mínimo 8 caracteres, 1 mayúscula, 1 dígito
4. Hashea password con bcrypt (10 rounds por defecto)
5. Almacena usuario en BD
6. Devuelve token JWT con `email` y `exp` en payload
7. Token expira en 30 minutos (configurable)

## Stack y versiones

| Tecnología | Versión | Uso principal |
|---|---|---|
| FastAPI | 0.135.3 | Framework web asincrónico |
| Python | 3.11+ | Runtime |
| SQLAlchemy | 2.0.49 | ORM y persistencia |
| Pydantic | 2.13.1 | Validación de schemas |
| psycopg2-binary | 2.9.11 | Driver PostgreSQL |
| PostgreSQL | 15+ | Base de datos relacional |
| Passlib | 1.7.4 | Hash y verificación de contraseñas |
| bcrypt | 4.1.3 | Backend de criptografía |
| pdfplumber | Última | Extracción de texto de PDFs |
| markitdown | Última | Conversión PDF → Markdown |
| magika | Última | Detección automática de tipo MIME |
| python-jose | 3.3.0 | JWT encoding/decoding |
| OpenAI | 1.70.0 | Cliente oficial de OpenAI API |
| email-validator | 2.3.0 | Validación de direcciones email |
| uvicorn | 0.44.0 | ASGI server de producción |

## Arquitectura backend

### Capa web

- Routers REST en `app/routers/`.
- Schemas Pydantic en `app/schemas.py` para validación de entrada/salida.
- Middleware de CORS, rate limiting y logging centralizado.

### Capa de negocio

- `app/routers/auth.py`: Registro, login, validación de credenciales.
- `app/routers/documents.py`: Upload, listado, metadata de documentos.
- `app/routers/chat.py`: Streaming de chat contextualizado.
- Servicios específicos en `app/services/`:
  - `pdf_parser.py`: Extracción de texto y análisis de contenido.

### Capa de persistencia

- Modelos SQLAlchemy en `app/models.py`:
  - `User`: Información de usuario, email normalizado, contraseña hasheada.
  - `Document`: Metadata del PDF, contenido, propietario.
  - `ChatMessage`: Historial de chat por documento.
- Conexión a PostgreSQL con pool de conexiones automático.
- DDL automático en desarrollo; en producción se recomienda migraciones.

### Capa de seguridad

- Middleware JWT: valida token en cada request protegido.
- Rate limiting: 5 intentos fallidos de login por email en 15 minutos.
- Email normalization: trim + lowercase para evitar duplicados.
- Password validation: regex y reglas semánticas.
- CORS: origins validados exactamente (con normalización de trailing slash).
- Security headers: CSP, HSTS, X-Frame-Options, Permissions-Policy.

### Capa transversal

- `app/main.py`: Inicialización de app, middleware, validación de entorno.
- `app/database.py`: Configuración de sesión SQLAlchemy.
- `.env`: Variables de entorno críticas.

## Endpoints principales

### Autenticación

```
POST   /auth/register           # Crear cuenta nueva
POST   /auth/login              # Obtener token JWT
```

### Documentos

```
GET    /documents/              # Listar documentos del usuario
POST   /documents/upload        # Cargar nuevo PDF
GET    /documents/{doc_id}      # Obtener metadata de documento
DELETE /documents/{doc_id}      # Eliminar documento
```

### Chat

```
GET    /chat/stream             # Chat streaming contextualizado
                                # Parámetros: doc_id, message
```

## Respuestas principales

### AuthResponse

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIS...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### DocumentResponse

```json
{
  "id": "uuid-123",
  "name": "contract.pdf",
  "size_bytes": 245821,
  "content_preview": "Legal document describing...",
  "created_at": "2025-04-15T10:30:00Z",
  "owner_id": "user-123"
}
```

### ChatStreamResponse (SSE)

```
data: {"type":"start","timestamp":"2025-04-15T10:35:00Z"}
data: {"type":"content","chunk":"The contract..."}
data: {"type":"content","chunk":" is valid..."}
data: {"type":"content","chunk":" for 1 year"}
data: {"type":"end","message_id":"msg-456"}
```

### ErrorResponse

```json
{
  "detail": "Invalid email or password",
  "status_code": 401,
  "timestamp": "2025-04-15T10:30:00Z"
}
```

## Configuración

La aplicación Lee sus valores desde variables de entorno con defaults de desarrollo en `app/main.py`.

### Variables principales

```env
# Base de datos
DATABASE_URL=postgresql://user:password@localhost:5432/docusense?sslmode=require

# Autenticación
SECRET_KEY=super-secret-key-change-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://docusense-web.vercel.app

# OpenAI
OPENAI_API_KEY=sk-proj-...

# Servidor
HOST=0.0.0.0
PORT=8000

# Archivos
MAX_FILE_SIZE_MB=50
UPLOAD_DIR=./uploads

# Logging
LOG_LEVEL=INFO
```

### Notas de configuración

- `DATABASE_URL` es requerida; usa `sslmode=require` en producción (Neon).
- `SECRET_KEY` debe ser fuerte (32+ caracteres); cambiar en producción.
- `ALLOWED_ORIGINS` se normaliza automáticamente (trim, lowercase, strip trailing slash).
- `OPENAI_API_KEY` se lee como proyecto por defecto; no se expone en respuestas.
- El servidor se inicia en `HOST:PORT` configurables por entorno.

## Ejecución local

### Requisitos

- Python 3.11+
- PostgreSQL 15+
- pip y virtualenv

### 1. Clonar y crear entorno virtual

```bash
git clone <repo>
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
# O para reproducibilidad exacta:
pip install -r requirements.lock.txt
```

### 3. Configurar base de datos

```bash
# Crear BD en PostgreSQL
createdb docusense

# Exportar variables (o editar .env)
export DATABASE_URL="postgresql://postgres:password@localhost:5432/docusense"
export SECRET_KEY="dev-secret-change-in-prod"
export OPENAI_API_KEY="sk-..."
export ALLOWED_ORIGINS="http://localhost:3000"
```

### 4. Ejecutar la aplicación

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Abrir la documentación

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### 6. Probar manualmente

```bash
# Registrar usuario
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "name": "John Doe"
  }'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'

# Usar token en requests subsecuentes
TOKEN="eyJhbGciOiJIUzI1NiIS..."
curl -X GET http://localhost:8000/documents/ \
  -H "Authorization: Bearer $TOKEN"
```

## Docker

El proyecto incluye configuración para ejecución en contenedores.

### Build

```bash
docker build -t docusense-api .
```

### Run local

```bash
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql://postgres:password@host.docker.internal:5432/docusense" \
  -e SECRET_KEY="dev-secret" \
  -e OPENAI_API_KEY="sk-..." \
  -e ALLOWED_ORIGINS="http://localhost:3000" \
  docusense-api
```

### Notas de despliegue

- La imagen se puede deployar en Render, Railway, AWS ECS.
- Las variables de entorno se inyectan en el runtime.
- El puerto es configurable vía `PORT`.
- Render duerme la app si no recibe tráfico; el frontend muestra disclaimer de "cold start".

## Estructura del proyecto

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                # App FastAPI, CORS, middleware setup
│   ├── database.py            # Configuración SQLAlchemy
│   ├── models.py              # Entidades: User, Document, ChatMessage
│   ├── schemas.py             # Pydantic models para validación
│   ├── routers/
│   │   ├── auth.py            # Endpoints: register, login
│   │   ├── documents.py       # Endpoints: upload, list, delete
│   │   └── chat.py            # Endpoints: stream chat
│   └── services/
│       └── pdf_parser.py      # Extracción de texto y análisis
├── requirements.txt           # Dependencias
├── requirements.lock.txt      # Frozen dependencies (reproducible)
├── export_requirements.sh     # Script para regenerar lock
├── docker-compose.yml         # Orquestación local con PostgreSQL
├── Dockerfile                 # Build de imagen
├── .env.example               # Template de variables
├── start.sh                   # Script de inicio para producción
└── README.md
```

## Decisiones técnicas

- **FastAPI**: Elegido por async nativa, validación automática con Pydantic, documentación generada automáticamente.
- **JWT stateless**: Simplifica escalado horizontal; no requiere sesiones en servidor.
- **Streaming SSE**: Las respuestas llegan parcialmente mientras OpenAI genera, mejorando UX.
- **Email normalization**: Evita duplicados por variaciones de casing/whitespace.
- **Bcrypt 4.1.3**: Pinned específicamente por compatibilidad con passlib 1.7.4 (v5.x rompe).
- **Rate limiting en memoria**: Suficiente para Render single-process; en escala horizontal usar Redis.
- **PDF processing**: pdfplumber para extracción precisa + markitdown para conversión a texto legible.
- **SQLAlchemy ORM**: Proporciona seguridad contra SQL injection y abstracción de BD.
- **Requirements.lock.txt**: Garantiza reproducibilidad exacta en Render; se regene con `export_requirements.sh`.

## Seguridad

### Implementaciones activas

- **JWT con HS256**: Token firmado, no puede ser modificado sin `SECRET_KEY`.
- **CORS exacto**: Solo permite origenes configurados; normaliza automáticamente.
- **Rate limiting**: 5 intentos de login fallidos = 15 minutos bloqueado por email.
- **Password hashing**: bcrypt con 10 rounds; irreversible.
- **Email validation**: RFC compliant; también normalizado para lookup.
- **Input validation**: Pydantic valida tamaño, tipo, formato de cada campo.
- **Security headers**:
  - Content-Security-Policy: Strict
  - Strict-Transport-Security: 1 año
  - X-Frame-Options: DENY
  - Permissions-Policy: Restrictiva
- **No logs de secretos**: Credenciales y tokens se redactan en logs.
- **Errores genéricos**: No expone detalles internos en respuestas HTTP.

### Recomendaciones para producción

- Usar HTTPS obligatoriamente (`sslmode=require` en DATABASE_URL).
- Cambiar `SECRET_KEY` a valor fuerte antes de desplegar.
- Usar `OPENAI_API_KEY` de cuenta de servicio; no de cuenta personal.
- Monitorear logs en Render por intentos de acceso anómalo.
- Implementar rate limiting global con Nginx o WAF si escala horizontalmente.
- Hacer backup regular de base de datos PostgreSQL.
- Rotar `SECRET_KEY` periódicamente para invalidar tokens antiguos.

## Próximos pasos

1. Deployar backend e frontend juntos.
2. Validar flujo end-to-end: Registro → Upload PDF → Chat.
3. Monitorear logs en producción por errores o intentos de ataque.
4. Escalar a múltiples réplicas si crecimiento de usuarios.

## Autor

Desarrollado por Darlene
