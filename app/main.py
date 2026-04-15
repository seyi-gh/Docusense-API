import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth, documents, chat

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
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
allowed_origins = [origin.strip() for origin in allowed_origins]

app.add_middleware(
  CORSMiddleware,
  allow_origins=allowed_origins,
  allow_methods=['GET', 'POST', 'OPTIONS'],
  allow_headers=['Content-Type', 'Authorization'],
  allow_credentials=True,
  max_age=3600,
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)

@app.get('/')
def root():
  return {'status': 'DocuSense API running'}