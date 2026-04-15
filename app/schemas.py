from uuid import UUID
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, field_validator

class UserRegister(BaseModel):
  email: EmailStr
  password: str
  name: str
  
  @field_validator('password')
  @classmethod
  def validate_password(cls, v: str) -> str:
    if len(v) < 8:
      raise ValueError('Password must be at least 8 characters')
    if not any(c.isupper() for c in v):
      raise ValueError('Password must contain at least one uppercase letter')
    if not any(c.isdigit() for c in v):
      raise ValueError('Password must contain at least one digit')
    return v
  
  @field_validator('name')
  @classmethod
  def validate_name(cls, v: str) -> str:
    if len(v.strip()) < 2:
      raise ValueError('Name must be at least 2 characters')
    if len(v.strip()) > 100:
      raise ValueError('Name must be less than 100 characters')
    return v.strip()

class UserLogin(BaseModel):
  email: EmailStr
  password: str

class TokenResponse(BaseModel):
  access_token: str
  token_type: str

class DocumentOut(BaseModel):
  id: UUID
  filename: str
  char_count: int
  created_at: datetime

  class Config:
    from_attributes = True

class ProviderConfig(BaseModel):
  provider: Literal['openai', 'deepseek', 'claude'] = 'openai'
  model: str | None = None
  api_key: str | None = None
  use_project_key: bool = False
  
  @field_validator('model')
  @classmethod
  def validate_model(cls, v: str | None) -> str | None:
    if v is not None and len(v.strip()) == 0:
      return None
    return v

class ChatTurn(BaseModel):
  role: Literal['user', 'assistant']
  content: str
  
  @field_validator('content')
  @classmethod
  def validate_content(cls, v: str) -> str:
    if len(v.strip()) == 0:
      raise ValueError('Message content cannot be empty')
    if len(v) > 50000:
      raise ValueError('Message content must be less than 50000 characters')
    return v.strip()

class ChatRequest(BaseModel):
  message: str = Field(..., min_length=1, max_length=50000)
  history: list[ChatTurn] = Field(default_factory=list)
  provider_config: ProviderConfig = Field(default_factory=ProviderConfig)
  
  @field_validator('history')
  @classmethod
  def validate_history(cls, v: list[ChatTurn]) -> list[ChatTurn]:
    if len(v) > 100:
      raise ValueError('Chat history cannot exceed 100 messages')
    return v