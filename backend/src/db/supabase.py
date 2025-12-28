"""Supabase client for Mneme EMR."""

from functools import lru_cache
from supabase import create_client, Client
from src.config import get_settings


@lru_cache
def get_supabase() -> Client:
  """Get cached Supabase client instance."""
  settings = get_settings()
  return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_supabase_admin() -> Client:
  """Get Supabase client with service role key for admin operations."""
  settings = get_settings()
  if not settings.supabase_service_key:
    raise ValueError("SUPABASE_SERVICE_KEY not configured")
  return create_client(settings.supabase_url, settings.supabase_service_key)


class SupabaseDB:
  """Helper class for common database operations."""

  def __init__(self, client: Client | None = None):
    self.client = client or get_supabase()

  # Patients
  def get_patients(self, limit: int = 50, offset: int = 0):
    """Get paginated list of patients."""
    return (
      self.client.table("patients")
      .select("*")
      .order("family_name")
      .range(offset, offset + limit - 1)
      .execute()
    )

  def get_patient(self, patient_id: str):
    """Get patient by ID with full clinical data."""
    return (
      self.client.table("patients")
      .select("*")
      .eq("id", patient_id)
      .single()
      .execute()
    )

  def get_patient_conditions(self, patient_id: str):
    """Get patient's conditions/problems."""
    return (
      self.client.table("conditions")
      .select("*")
      .eq("patient_id", patient_id)
      .order("onset_date", desc=True)
      .execute()
    )

  def get_patient_medications(self, patient_id: str):
    """Get patient's medications."""
    return (
      self.client.table("medications")
      .select("*")
      .eq("patient_id", patient_id)
      .order("start_date", desc=True)
      .execute()
    )

  def get_patient_allergies(self, patient_id: str):
    """Get patient's allergies."""
    return (
      self.client.table("allergies")
      .select("*")
      .eq("patient_id", patient_id)
      .execute()
    )

  def get_patient_encounters(self, patient_id: str, limit: int = 20):
    """Get patient's encounters/notes."""
    return (
      self.client.table("encounters")
      .select("*")
      .eq("patient_id", patient_id)
      .order("date", desc=True)
      .limit(limit)
      .execute()
    )

  def get_patient_observations(self, patient_id: str, category: str | None = None):
    """Get patient's observations (labs, vitals)."""
    query = (
      self.client.table("observations")
      .select("*")
      .eq("patient_id", patient_id)
    )
    if category:
      query = query.eq("category", category)
    return query.order("effective_date", desc=True).execute()

  def get_patient_messages(self, patient_id: str):
    """Get patient's messages."""
    return (
      self.client.table("messages")
      .select("*")
      .eq("patient_id", patient_id)
      .order("sent_datetime", desc=True)
      .execute()
    )

  def get_patient_immunizations(self, patient_id: str):
    """Get patient's immunization record."""
    return (
      self.client.table("immunizations")
      .select("*")
      .eq("patient_id", patient_id)
      .order("date", desc=True)
      .execute()
    )

  def get_patient_growth(self, patient_id: str):
    """Get patient's growth data."""
    return (
      self.client.table("growth_data")
      .select("*")
      .eq("patient_id", patient_id)
      .order("date")
      .execute()
    )

  # Schedule
  def get_appointments(self, start_date: str, end_date: str):
    """Get appointments in date range."""
    return (
      self.client.table("appointments")
      .select("*, patients(id, given_names, family_name, date_of_birth)")
      .gte("scheduled_time", start_date)
      .lte("scheduled_time", end_date)
      .order("scheduled_time")
      .execute()
    )

  def get_today_appointments(self):
    """Get today's appointments."""
    from datetime import date
    today = date.today().isoformat()
    tomorrow = date.today().isoformat()
    return self.get_appointments(f"{today}T00:00:00", f"{today}T23:59:59")

  # Messages
  def get_unread_messages(self):
    """Get all unread messages."""
    return (
      self.client.table("messages")
      .select("*, patients(id, given_names, family_name)")
      .eq("is_read", False)
      .order("sent_datetime", desc=True)
      .execute()
    )

  def mark_message_read(self, message_id: str):
    """Mark a message as read."""
    return (
      self.client.table("messages")
      .update({"is_read": True})
      .eq("id", message_id)
      .execute()
    )

  # Import operations
  def insert_patient(self, data: dict):
    """Insert a new patient."""
    return self.client.table("patients").insert(data).execute()

  def insert_conditions(self, data: list[dict]):
    """Insert conditions."""
    if not data:
      return None
    return self.client.table("conditions").insert(data).execute()

  def insert_medications(self, data: list[dict]):
    """Insert medications."""
    if not data:
      return None
    return self.client.table("medications").insert(data).execute()

  def insert_allergies(self, data: list[dict]):
    """Insert allergies."""
    if not data:
      return None
    return self.client.table("allergies").insert(data).execute()

  def insert_encounters(self, data: list[dict]):
    """Insert encounters."""
    if not data:
      return None
    return self.client.table("encounters").insert(data).execute()

  def insert_observations(self, data: list[dict]):
    """Insert observations."""
    if not data:
      return None
    return self.client.table("observations").insert(data).execute()

  def insert_immunizations(self, data: list[dict]):
    """Insert immunizations."""
    if not data:
      return None
    return self.client.table("immunizations").insert(data).execute()

  def insert_messages(self, data: list[dict]):
    """Insert messages."""
    if not data:
      return None
    return self.client.table("messages").insert(data).execute()

  def insert_growth_data(self, data: list[dict]):
    """Insert growth data."""
    if not data:
      return None
    return self.client.table("growth_data").insert(data).execute()

  def create_import_record(self, filename: str, format: str):
    """Create an import tracking record."""
    return (
      self.client.table("imports")
      .insert({"filename": filename, "format": format, "status": "processing"})
      .execute()
    )

  def update_import_record(self, import_id: str, status: str, patient_count: int = 0, error: str | None = None):
    """Update import record status."""
    data = {"status": status, "patient_count": patient_count}
    if error:
      data["error_message"] = error
    if status in ("completed", "failed"):
      from datetime import datetime
      data["completed_at"] = datetime.now().isoformat()
    return (
      self.client.table("imports")
      .update(data)
      .eq("id", import_id)
      .execute()
    )
