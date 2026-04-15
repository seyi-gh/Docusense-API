import logging
from datetime import datetime, timedelta
from ..models import User
from ..database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..schemas import UserRegister, UserLogin, TokenResponse
from fastapi import APIRouter, Depends, HTTPException, status
from ..auth import hash_password, verify_password, create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/auth', tags=['auth'])

# In-memory rate limiting (15 failed attempts in 15 minutes = blocked)
login_attempts: dict[str, list[tuple[datetime, bool]]] = {}

def normalize_email(value: str) -> str:
  """Normalize emails for consistent auth lookups and storage."""
  return value.strip().lower()

def is_login_throttled(email: str) -> bool:
  """Check if email is throttled due to too many failed attempts."""
  now = datetime.now()
  window = now - timedelta(minutes=15)
  
  attempts = login_attempts.get(email, [])
  # Keep only attempts within the 15-minute window
  attempts = [(ts, ok) for ts, ok in attempts if ts > window]
  login_attempts[email] = attempts
  
  # Count failed attempts
  failed_count = sum(1 for ts, ok in attempts if not ok)
  
  return failed_count >= 5

def record_login_attempt(email: str, success: bool) -> None:
  """Record a login attempt for rate limiting."""
  now = datetime.now()
  if email not in login_attempts:
    login_attempts[email] = []
  login_attempts[email].append((now, success))
  
  # Log for security audit (never log password or sensitive data)
  status_str = 'SUCCESS' if success else 'FAILED'
  # Redact email for privacy in non-monitoring contexts
  email_hash = hash(email) % 10000  # Simple hash for grouping
  logger.warning(f'Login attempt [{status_str}] from account group {email_hash}')

@router.post('/register', response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: UserRegister, db: Session = Depends(get_db)):
  normalized_email = normalize_email(body.email)

  existing = db.query(User).filter(func.lower(User.email) == normalized_email).first()
  if existing:
    logger.warning(f'Registration attempt with existing email: {normalized_email}')
    raise HTTPException(status_code=400, detail='Email ya registrado')

  user = User(
    email=normalized_email,
    password_hash=hash_password(body.password),
    name=body.name
  )
  db.add(user)
  db.commit()
  db.refresh(user)

  token = create_access_token({'sub': str(user.id)})
  logger.info(f'New user registered: {user.id} ({user.email})')
  return {'access_token': token, 'token_type': 'bearer'}

@router.post('/login', response_model=TokenResponse)
def login(body: UserLogin, db: Session = Depends(get_db)):
  normalized_email = normalize_email(body.email)

  # Check rate limiting
  if is_login_throttled(normalized_email):
    logger.warning(f'Login throttled for email: {normalized_email}')
    raise HTTPException(
      status_code=429,
      detail='Too many failed login attempts. Try again in 15 minutes.'
    )
  
  user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
  password_valid = user and verify_password(body.password, user.password_hash)
  
  if not password_valid:
    record_login_attempt(normalized_email, False)
    raise HTTPException(status_code=401, detail='Credenciales inválidas')

  record_login_attempt(normalized_email, True)
  token = create_access_token({'sub': str(user.id)})
  logger.info(f'User login successful: {user.id} ({user.email})')
  return {'access_token': token, 'token_type': 'bearer'}