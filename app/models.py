import uuid, datetime
from .database import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime

def utcnow():
  return datetime.datetime.now(datetime.timezone.utc)

class User(Base):
  __tablename__ = 'users'
  id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  email = Column(String(255), unique=True, nullable=False)
  password_hash = Column(Text, nullable=False)
  name = Column(String(100))
  create_at = Column(DateTime, default=utcnow)

class Document(Base):
  __tablename__ = 'documents'
  id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete=('CASCADE')))
  filename = Column(Text, nullable=True)
  full_text = Column(Text, nullable=True)
  char_count = Column(Integer)
  created_at = Column(DateTime, default=utcnow)

class ProjectKeyUsage(Base):
  __tablename__ = 'project_key_usages'
  id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
  provider = Column(String(20), nullable=False)
  created_at = Column(DateTime, default=utcnow)