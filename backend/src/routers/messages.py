"""Messages API routes for Mneme EMR."""

from fastapi import APIRouter, HTTPException, Query
from src.db.supabase import SupabaseDB
from src.models.message import Message, MessageWithPatient

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("")
async def list_messages(
  limit: int = Query(50, ge=1, le=100),
  offset: int = Query(0, ge=0),
  unread_only: bool = False,
) -> list[MessageWithPatient]:
  """Get all messages (inbox view)."""
  try:
    db = SupabaseDB()

    query = (
      db.client.table("messages")
      .select("*, patients(id, given_names, family_name)")
      .order("sent_datetime", desc=True)
      .range(offset, offset + limit - 1)
    )

    if unread_only:
      query = query.eq("is_read", False)

    result = query.execute()

    messages = []
    for msg in result.data:
      patient = msg.pop("patients", {}) or {}
      messages.append(MessageWithPatient(
        **msg,
        patient_name=f"{' '.join(patient.get('given_names', []))} {patient.get('family_name', '')}".strip() or None,
      ))

    return messages
  except Exception as e:
    # Table may not exist yet - return empty list
    print(f"Error fetching messages: {e}")
    return []


@router.get("/unread")
async def get_unread_messages() -> list[MessageWithPatient]:
  """Get all unread messages."""
  return await list_messages(unread_only=True)


@router.get("/unread/count")
async def get_unread_count() -> dict:
  """Get count of unread messages."""
  try:
    db = SupabaseDB()

    result = (
      db.client.table("messages")
      .select("id", count="exact")
      .eq("is_read", False)
      .execute()
    )

    return {"unread_count": result.count or 0}
  except Exception as e:
    # Table may not exist yet
    print(f"Error fetching unread count: {e}")
    return {"unread_count": 0}


@router.get("/{message_id}")
async def get_message(message_id: str) -> Message:
  """Get a single message."""
  db = SupabaseDB()

  result = (
    db.client.table("messages")
    .select("*")
    .eq("id", message_id)
    .single()
    .execute()
  )

  if not result.data:
    raise HTTPException(status_code=404, detail="Message not found")

  return Message(**result.data)


@router.patch("/{message_id}/read")
async def mark_message_read(message_id: str) -> Message:
  """Mark a message as read."""
  db = SupabaseDB()

  result = db.mark_message_read(message_id)

  if not result.data:
    raise HTTPException(status_code=404, detail="Message not found")

  return Message(**result.data[0])


@router.patch("/{message_id}/unread")
async def mark_message_unread(message_id: str) -> Message:
  """Mark a message as unread."""
  db = SupabaseDB()

  result = (
    db.client.table("messages")
    .update({"is_read": False})
    .eq("id", message_id)
    .execute()
  )

  if not result.data:
    raise HTTPException(status_code=404, detail="Message not found")

  return Message(**result.data[0])
