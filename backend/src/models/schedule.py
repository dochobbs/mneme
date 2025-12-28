"""Schedule/appointment models for Mneme EMR."""

from datetime import datetime
from pydantic import BaseModel


class AppointmentBase(BaseModel):
  """Base appointment model."""
  scheduled_time: datetime
  duration_minutes: int = 20
  appointment_type: str | None = None
  status: str = "scheduled"
  provider_name: str | None = None
  location_name: str | None = None
  reason: str | None = None
  notes: str | None = None


class AppointmentCreate(AppointmentBase):
  """Model for creating an appointment."""
  patient_id: str


class Appointment(AppointmentBase):
  """Full appointment model."""
  id: str
  patient_id: str
  created_at: datetime | None = None


class AppointmentWithPatient(Appointment):
  """Appointment with patient info for schedule view."""
  patient_name: str | None = None
  patient_dob: str | None = None
  patient_age: int | None = None


class ScheduleDay(BaseModel):
  """A day's worth of appointments."""
  date: str
  appointments: list[AppointmentWithPatient] = []
