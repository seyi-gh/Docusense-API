from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Document
from ..schemas import DocumentOut
from ..auth import get_current_user
from ..services.pdf_parser import extract_text
from typing import List
import uuid
from textwrap import dedent

router = APIRouter(prefix='/documents', tags=['documents'])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

DEMO_DOCUMENT_TEXT = dedent('''
  Documento de prueba de DocuSense.

  Este texto existe para validar la aplicacion sin subir archivos propios.

  Puntos clave:
  - El flujo soporta autenticacion por token.
  - Los documentos se consultan mediante chat contextual.
  - Las conversaciones se guardan en el navegador.
  - El proveedor de IA puede ser OpenAI, Claude o DeepSeek.

  Usa este documento para hacer dos pruebas:
  1. Resume el contenido en 3 puntos.
  2. Indica cuales son las limitaciones actuales del sistema.
''').strip()

@router.post('/upload', response_model=DocumentOut, status_code=201)
async def upload(
  file: UploadFile = File(...),
  user=Depends(get_current_user),
  db: Session = Depends(get_db)
):
  if file.content_type != 'application/pdf':
    raise HTTPException(status_code=400, detail='Solo se permiten archivos PDF')

  file_bytes = await file.read()

  if len(file_bytes) > MAX_FILE_SIZE:
    raise HTTPException(status_code=400, detail='Archivo mayor a 10MB')

  text = extract_text(file_bytes)

  if not text.strip():
    raise HTTPException(status_code=400, detail='No se pudo extraer texto del PDF')

  doc = Document(
    user_id=user.id,
    filename=file.filename,
    full_text=text,
    char_count=len(text)
  )
  db.add(doc)
  db.commit()
  db.refresh(doc)
  return doc

@router.get('/', response_model=List[DocumentOut])
def list_documents(user=Depends(get_current_user), db: Session = Depends(get_db)):
  return db.query(Document).filter(Document.user_id == user.id).all()


@router.post('/demo', response_model=DocumentOut, status_code=201)
def create_demo_document(user=Depends(get_current_user), db: Session = Depends(get_db)):
  existing = db.query(Document).filter(
    Document.user_id == user.id,
    Document.filename == 'Demo - DocuSense'
  ).first()

  if existing:
    return existing

  doc = Document(
    user_id=user.id,
    filename='Demo - DocuSense',
    full_text=DEMO_DOCUMENT_TEXT,
    char_count=len(DEMO_DOCUMENT_TEXT),
  )
  db.add(doc)
  db.commit()
  db.refresh(doc)
  return doc

@router.delete('/{doc_id}', status_code=204)
def delete_document(doc_id: uuid.UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
  doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user.id).first()
  if not doc:
    raise HTTPException(status_code=404, detail='Documento no encontrado')
  db.delete(doc)
  db.commit()