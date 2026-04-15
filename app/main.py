import os
import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth, documents, chat

logger = logging.getLogger(__name__)

# Validate required environment variables
required_env_vars = [
    'SECRET_KEY',
    'ALGORITHM',
    'ACCESS_TOKEN_EXPIRE_MINUTES',
    'DATABASE_URL',
]

missing = [var for var in required_env_vars if not os.getenv(var)]
if missing:
    print(f"ERROR: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configure CORS from environment
raw_allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000')
origin_tokens = raw_allowed_origins.replace('\n', ',').replace(';', ',').split(',')
allowed_origins = []
for token in origin_tokens:
  normalized = token.strip().strip('"').strip("'").rstrip('/')
  if normalized:
    allowed_origins.append(normalized)

# Remove duplicates while preserving order
allowed_origins = list(dict.fromkeys(allowed_origins))

logger.info('CORS allowed origins: %s', allowed_origins)

app.add_middleware(
  CORSMiddleware,
  allow_origins=allowed_origins,
  allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allow_headers=['*'],
  allow_credentials=True,
  max_age=3600,
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)

@app.get('/')
def root():
  return {'status': 'DocuSense API running'}