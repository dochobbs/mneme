"""Schedule/appointment API routes for Mneme EMR."""

from datetime import date, datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from src.db.supabase import SupabaseDB
from src.models.schedule import Appointment, AppointmentCreate, AppointmentWithPatient

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.get("")
async def get_schedule(
  start_date: str | None = None,
  end_date: str | None = None,
) -> list[AppointmentWithPatient]:
  """Get appointments for a date range."""
  try:
    db = SupabaseDB()

    # Default to today if not specified
    if not start_date:
      start_date = date.today().isoformat() + "T00:00:00"
    if not end_date:
      end_date = date.today().isoformat() + "T23:59:59"

    result = db.get_appointments(start_date, end_date)

    appointments = []
    for apt in result.data:
      patient = apt.pop("patients", {}) or {}
      appointments.append(AppointmentWithPatient(
        **apt,
        patient_name=f"{' '.join(patient.get('given_names', []))} {patient.get('family_name', '')}".strip() or None,
        patient_dob=patient.get("date_of_birth"),
      ))

    return appointments
  except Exception as e:
    # Table may not exist yet - return empty list
    print(f"Error fetching schedule: {e}")
    return []


@router.get("/today")
async def get_today_schedule() -> list[AppointmentWithPatient]:
  """Get today's appointments."""
  today = date.today().isoformat()
  return await get_schedule(
    start_date=f"{today}T00:00:00",
    end_date=f"{today}T23:59:59",
  )


@router.get("/week")
async def get_week_schedule() -> list[AppointmentWithPatient]:
  """Get this week's appointments."""
  today = date.today()
  start = today - timedelta(days=today.weekday())  # Monday
  end = start + timedelta(days=6)  # Sunday

  return await get_schedule(
    start_date=f"{start.isoformat()}T00:00:00",
    end_date=f"{end.isoformat()}T23:59:59",
  )


@router.post("")
async def create_appointment(appointment: AppointmentCreate) -> Appointment:
  """Create a new appointment."""
  db = SupabaseDB()

  data = {
    "patient_id": appointment.patient_id,
    "scheduled_time": appointment.scheduled_time.isoformat(),
    "duration_minutes": appointment.duration_minutes,
    "appointment_type": appointment.appointment_type,
    "status": appointment.status,
    "provider_name": appointment.provider_name,
    "location_name": appointment.location_name,
    "reason": appointment.reason,
    "notes": appointment.notes,
  }

  result = db.client.table("appointments").insert(data).execute()
  return Appointment(**result.data[0])


class AppointmentStatusUpdate(BaseModel):
  status: str


@router.patch("/{appointment_id}/status")
async def update_appointment_status(
  appointment_id: str,
  update: AppointmentStatusUpdate,
) -> Appointment:
  """Update appointment status."""
  db = SupabaseDB()

  valid_statuses = ["scheduled", "arrived", "in-progress", "completed", "cancelled", "no-show"]
  if update.status not in valid_statuses:
    raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

  result = (
    db.client.table("appointments")
    .update({"status": update.status})
    .eq("id", appointment_id)
    .execute()
  )

  if not result.data:
    raise HTTPException(status_code=404, detail="Appointment not found")

  return Appointment(**result.data[0])


@router.delete("/{appointment_id}")
async def cancel_appointment(appointment_id: str) -> dict:
  """Cancel an appointment (soft delete by setting status)."""
  db = SupabaseDB()

  result = (
    db.client.table("appointments")
    .update({"status": "cancelled"})
    .eq("id", appointment_id)
    .execute()
  )

  if not result.data:
    raise HTTPException(status_code=404, detail="Appointment not found")

  return {"success": True, "message": "Appointment cancelled"}
