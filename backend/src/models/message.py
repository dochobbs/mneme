"""Message models for Mneme EMR."""

from datetime import datetime
from pydantic import BaseModel


class MessageBase(BaseModel):
  """Base message model."""
  sent_datetime: datetime
  reply_datetime: datetime | None = None
  sender_name: str
  sender_is_patient: bool = True
  recipient_name: str | None = None
  replier_name: str | None = None
  replier_role: str | None = None
  category: str | None = None
  medium: str = "portal"
  subject: str | None = None
  message_body: str
  reply_body: str | None = None
  is_read: bool = False


class MessageCreate(MessageBase):
  """Model for creating a message."""
  patient_id: str


class Message(MessageBase):
  """Full message model."""
  id: str
  patient_id: str
  external_id: str | None = None
  created_at: datetime | None = None


class MessageWithPatient(Message):
  """Message with patient info for inbox view."""
  patient_name: str | None = None


class MessageThread(BaseModel):
  """A message thread (original + replies)."""
  messages: list[Message] = []
  patient_id: str
  patient_name: str | None = None
