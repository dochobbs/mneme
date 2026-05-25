"""Messages API routes for Mneme EMR."""

from fastapi import APIRouter, HTTPException, Query, Depends
from src.db.supabase import SupabaseDB
from src.db.helpers import first_or_500
from src.models.message import Message, MessageWithPatient
from src.middleware.auth import get_current_user, CurrentUser

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("")
async def list_messages(
  current_user: CurrentUser = Depends(get_current_user),
  limit: int = Query(50, ge=1, le=100),
  offset: int = Query(0, ge=0),
  unread_only: bool = False,
) -> list[MessageWithPatient]:
  """Get all messages for user's patients (inbox view)."""
  try:
    db = SupabaseDB()

    query = (
      db.client.table("messages")
      .select("*, patients!inner(id, given_names, family_name, user_id)")
      .eq("patients.user_id", current_user.id)
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
async def get_unread_messages(
  current_user: CurrentUser = Depends(get_current_user),
) -> list[MessageWithPatient]:
  """Get all unread messages."""
  return await list_messages(current_user=current_user, unread_only=True)


@router.get("/unread/count")
async def get_unread_count(
  current_user: CurrentUser = Depends(get_current_user),
) -> dict:
  """Get count of unread messages for user's patients."""
  try:
    db = SupabaseDB()

    result = (
      db.client.table("messages")
      .select("id, patients!inner(user_id)", count="exact")
      .eq("patients.user_id", current_user.id)
      .eq("is_read", False)
      .execute()
    )

    return {"unread_count": result.count or 0}
  except Exception as e:
    # Table may not exist yet
    print(f"Error fetching unread count: {e}")
    return {"unread_count": 0}


@router.get("/{message_id}")
async def get_message(
  message_id: str,
  current_user: CurrentUser = Depends(get_current_user),
) -> Message:
  """Get a single message."""
  db = SupabaseDB()

  result = (
    db.client.table("messages")
    .select("*, patients!inner(user_id)")
    .eq("id", message_id)
    .eq("patients.user_id", current_user.id)
    .single()
    .execute()
  )

  if not result.data:
    raise HTTPException(status_code=404, detail="Message not found")

  # Remove joined patient data before creating Message
  result.data.pop("patients", None)
  return Message(**result.data)


@router.patch("/{message_id}/read")
async def mark_message_read(
  message_id: str,
  current_user: CurrentUser = Depends(get_current_user),
) -> Message:
  """Mark a message as read."""
  db = SupabaseDB()

  # Verify message belongs to user's patient
  msg = (
    db.client.table("messages")
    .select("*, patients!inner(user_id)")
    .eq("id", message_id)
    .eq("patients.user_id", current_user.id)
    .single()
    .execute()
  )
  if not msg.data:
    raise HTTPException(status_code=404, detail="Message not found")

  result = db.mark_message_read(message_id)

  return Message(**first_or_500(result, "message"))


@router.patch("/{message_id}/unread")
async def mark_message_unread(
  message_id: str,
  current_user: CurrentUser = Depends(get_current_user),
) -> Message:
  """Mark a message as unread."""
  db = SupabaseDB()

  # Verify message belongs to user's patient
  msg = (
    db.client.table("messages")
    .select("*, patients!inner(user_id)")
    .eq("id", message_id)
    .eq("patients.user_id", current_user.id)
    .single()
    .execute()
  )
  if not msg.data:
    raise HTTPException(status_code=404, detail="Message not found")

  result = (
    db.client.table("messages")
    .update({"is_read": False})
    .eq("id", message_id)
    .execute()
  )

  return Message(**first_or_500(result, "message"))
