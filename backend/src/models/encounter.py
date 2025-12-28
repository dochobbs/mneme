"""Encounter/visit models for Mneme EMR."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel


class VitalSigns(BaseModel):
  """Vital signs recorded at encounter."""
  temperature_f: float | None = None
  heart_rate: int | None = None
  respiratory_rate: int | None = None
  blood_pressure_systolic: int | None = None
  blood_pressure_diastolic: int | None = None
  oxygen_saturation: float | None = None
  weight_kg: float | None = None
  height_cm: float | None = None


class Assessment(BaseModel):
  """Clinical assessment item."""
  condition: str
  status: str | None = None
  notes: str | None = None


class PlanItem(BaseModel):
  """Treatment plan item."""
  description: str
  category: str | None = None


class Encounter(BaseModel):
  """Clinical encounter/visit."""
  id: str
  patient_id: str
  external_id: str | None = None
  encounter_type: str | None = None
  status: str = "finished"
  encounter_class: str = "ambulatory"
  date: datetime
  end_date: datetime | None = None
  chief_complaint: str | None = None
  provider_name: str | None = None
  location_name: str | None = None
  vital_signs: VitalSigns | dict | None = None
  hpi: str | None = None
  physical_exam: dict | None = None
  assessment: list[Assessment] | list[dict] | None = None
  plan: list[PlanItem] | list[dict] | None = None
  narrative_note: str | None = None
  billing_codes: dict | None = None
  created_at: datetime | None = None


class EncounterSummary(BaseModel):
  """Minimal encounter info for list views."""
  id: str
  patient_id: str
  encounter_type: str | None = None
  date: datetime
  chief_complaint: str | None = None
  provider_name: str | None = None


class EncounterCreate(BaseModel):
  """Model for creating an encounter."""
  patient_id: str
  encounter_type: str
  date: datetime
  chief_complaint: str | None = None
  provider_name: str | None = None
  location_name: str | None = None
