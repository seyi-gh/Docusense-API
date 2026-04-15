from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Document
from ..schemas import DocumentOut
from ..auth import get_current_user
from ..services.pdf_parser import extract_text
from typing import List
import uuid
import logging
from textwrap import dedent

router = APIRouter(prefix='/documents', tags=['documents'])
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

NO_TEXT_PLACEHOLDER = (
  'No se pudo extraer texto del PDF. '
  'Esto suele pasar con PDFs escaneados o protegidos.'
)

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
  file_bytes = await file.read()

  filename = (file.filename or '').lower()
  is_pdf_by_name = filename.endswith('.pdf')
  is_pdf_by_type = (file.content_type or '').lower() == 'application/pdf'
  is_pdf_by_magic = file_bytes.startswith(b'%PDF-')

  if not (is_pdf_by_name or is_pdf_by_type or is_pdf_by_magic):
    raise HTTPException(status_code=400, detail='Solo se permiten archivos PDF válidos')

  if len(file_bytes) > MAX_FILE_SIZE:
    raise HTTPException(status_code=400, detail='Archivo mayor a 25MB')

  text = ''
  try:
    text = extract_text(file_bytes)
  except Exception as exc:
    logger.warning('PDF processing failed for %s: %s', file.filename, exc)

  if not text.strip():
    logger.warning('No text extracted from PDF: %s', file.filename)
    text = NO_TEXT_PLACEHOLDER

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