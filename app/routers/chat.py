import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone, timedelta
from ..database import get_db
from ..models import Document, ProjectKeyUsage
from ..schemas import ChatRequest, ProviderConfig
from ..auth import get_current_user
from openai import OpenAI
import requests
import json
import uuid
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/chat', tags=['chat'])

DEFAULT_MODELS = {
  'openai': 'gpt-4o-mini',  # Única opción con API del proyecto
  'deepseek': 'deepseek-chat',  # Requiere API key personal
  'claude': 'claude-3-5-sonnet-latest',  # Requiere API key personal
}

PROJECT_KEY_COOLDOWN = timedelta(days=2)
PROJECT_KEY_MAX_REQUESTS = 5  # Máximo 5 requests cada 48 horas

PROVIDER_ENV_KEYS = {
  'openai': 'OPENAI_API_KEY',
  'deepseek': 'DEEPSEEK_API_KEY',
  'claude': 'ANTHROPIC_API_KEY',
}

OPENAI_COMPATIBLE_BASE_URLS = {
  'openai': 'https://api.openai.com/v1',
  'deepseek': 'https://api.deepseek.com/v1',
}


def resolve_provider_settings(provider_config: ProviderConfig):
  """Resolve provider settings for project and personal API keys."""
  provider = provider_config.provider or 'openai'
  model = provider_config.model or DEFAULT_MODELS[provider]

  # Project key mode is only available for OpenAI in this deployment.
  if provider_config.use_project_key:
    provider = 'openai'
    model = provider_config.model or DEFAULT_MODELS[provider]

    api_key = os.getenv(PROVIDER_ENV_KEYS[provider])
    if not api_key:
      raise HTTPException(
        status_code=500,
        detail='OPENAI_API_KEY no esta configurada en el servidor.',
      )

    return provider, model, api_key
  
  # Personal key mode (user-provided key)
  api_key = provider_config.api_key
  
  if not api_key:
    raise HTTPException(
      status_code=400,
      detail='Falta tu API key personal para el proveedor seleccionado.',
    )

  # Log that user's key is being used (but NOT the key itself)
  logger.warning(f'User personal key mode enabled for provider={provider}')
  return provider, model, api_key


def get_project_key_cooldown_remaining_ms(db: Session, user_id):
  """Check if user has exceeded 5 requests in the last 48 hours."""
  now = datetime.now(timezone.utc)
  window_start = now - PROJECT_KEY_COOLDOWN
  
  # Count requests in the last 48 hours
  recent_requests = db.query(ProjectKeyUsage).filter(
    ProjectKeyUsage.user_id == user_id,
    ProjectKeyUsage.created_at >= window_start,
  ).count()
  
  if recent_requests >= PROJECT_KEY_MAX_REQUESTS:
    # Find the oldest request in the window to calculate when the cooldown ends
    oldest_usage = db.query(ProjectKeyUsage).filter(
      ProjectKeyUsage.user_id == user_id,
      ProjectKeyUsage.created_at >= window_start,
    ).order_by(ProjectKeyUsage.created_at).first()
    
    if oldest_usage:
      remaining = (oldest_usage.created_at + PROJECT_KEY_COOLDOWN) - now
      return max(0, int(remaining.total_seconds() * 1000))
  
  return 0


def stream_anthropic(api_key: str, model: str, system_prompt: str, messages: list[dict]):
  payload = {
    'model': model,
    'max_tokens': 1024,
    'temperature': 0.3,
    'system': system_prompt,
    'messages': messages,
    'stream': True,
  }

  response = requests.post(
    'https://api.anthropic.com/v1/messages',
    headers={
      'x-api-key': api_key,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json',
    },
    json=payload,
    stream=True,
    timeout=120,
  )

  if response.status_code >= 400:
    raise HTTPException(status_code=502, detail='Error al conectar con Claude')

  def generator():
    full_response = ''
    current_event = ''

    for line in response.iter_lines(decode_unicode=True):
      if not line:
        continue

      if line.startswith('event:'):
        current_event = line[len('event:'):].strip()
        continue

      if not line.startswith('data:'):
        continue

      raw_data = line[len('data:'):].strip()
      if raw_data == '[DONE]':
        break

      try:
        payload = json.loads(raw_data)
      except json.JSONDecodeError:
        continue

      if current_event == 'content_block_delta':
        delta = payload.get('delta', {}).get('text', '')
        if delta:
          full_response += delta
          yield f'data: {delta}\n\n'

    response.close()

  return generator()

@router.post('/{doc_id}')
async def chat(
  doc_id: uuid.UUID,
  body: ChatRequest,
  user=Depends(get_current_user),
  db: Session = Depends(get_db)
):
  doc = db.query(Document).filter(
    Document.id == doc_id,
    Document.user_id == user.id
  ).first()

  if not doc:
    raise HTTPException(status_code=404, detail='Documento no encontrado')

  doc_excerpt = doc.full_text[:8000]
  if len(doc.full_text) > 8000:
    doc_excerpt += '\n\n[... documento truncado ...]'

  system_prompt = f'''Eres un asistente experto en análisis de documentos.
El usuario ha subido el siguiente documento:

--- INICIO DEL DOCUMENTO ---
{doc_excerpt}
--- FIN DEL DOCUMENTO ---

Responde SOLO basándote en el contenido del documento.
Si la respuesta no está en el documento, dilo claramente.
Cita la parte relevante cuando sea posible.'''

  messages = [{'role': 'system', 'content': system_prompt}]
  messages += [{'role': msg.role, 'content': msg.content} for msg in body.history]
  messages.append({'role': 'user', 'content': body.message})
  provider, model, api_key = resolve_provider_settings(body.provider_config)

  if body.provider_config.use_project_key:
    remaining_ms = get_project_key_cooldown_remaining_ms(db, user.id)
    if remaining_ms > 0:
      logger.warning(f'Project API rate limit exceeded for user {user.id}')
      raise HTTPException(
        status_code=429,
        detail={
          'message': f'Límite de {PROJECT_KEY_MAX_REQUESTS} requests cada 48 horas alcanzado. Usa tu propia clave o espera a que expire la ventana.',
          'retry_after_ms': remaining_ms,
        },
      )

  async def stream_response():
    full_response = ''

    if provider == 'claude':
      anthropic_messages = [
        {'role': msg['role'], 'content': msg['content']}
        for msg in messages
        if msg['role'] in {'user', 'assistant'}
      ]

      for chunk in stream_anthropic(api_key, model, system_prompt, anthropic_messages):
        full_response += chunk.replace('data: ', '').replace('\n\n', '')
        yield chunk

      if body.provider_config.use_project_key:
        usage = ProjectKeyUsage(user_id=user.id, provider=provider)
        db.add(usage)
        db.commit()
        logger.info(f'Project API used by user {user.id} with provider {provider}')
      return

    logger.info(f'Chat: User {user.id} using provider {provider}')
    client = OpenAI(
      api_key=api_key,
      base_url=OPENAI_COMPATIBLE_BASE_URLS.get(provider),
    )

    stream = client.chat.completions.create(
      model=model,
      messages=messages,
      stream=True,
      max_tokens=1024,
      temperature=0.3,
    )

    for chunk in stream:
      delta = chunk.choices[0].delta.content
      if delta:
        full_response += delta
        yield f'data: {delta}\n\n'

    if body.provider_config.use_project_key:
      usage = ProjectKeyUsage(user_id=user.id, provider=provider)
      db.add(usage)
      db.commit()
      logger.info(f'Project API used by user {user.id} with provider {provider}')
  return StreamingResponse(stream_response(), media_type='text/event-stream')