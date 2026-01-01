"""Validation schemas for import data using Pydantic."""

from datetime import date, datetime
from typing import Literal, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class PatientValidation(BaseModel):
  """Validation schema for patient demographics."""
  given_names: list[str] = Field(default_factory=lambda: ["Unknown"])
  family_name: str = Field(default="Unknown", min_length=1)
  date_of_birth: date | str | None = None
  sex_at_birth: Literal["male", "female", "other", "unknown", "intersex"] | None = None
  gender_identity: str | None = None
  race: list[str] | None = None
  ethnicity: str | None = None
  preferred_language: str = "English"
  phone: str | None = None
  email: str | None = None
  address: dict | None = None
  emergency_contact: dict | None = None
  legal_guardian: dict | None = None

  @field_validator("date_of_birth", mode="before")
  @classmethod
  def parse_dob(cls, v: Any) -> date | None:
    if v is None:
      return None
    if isinstance(v, date):
      return v
    if isinstance(v, str):
      try:
        return date.fromisoformat(v)
      except ValueError:
        return None
    return None

  @field_validator("given_names", mode="before")
  @classmethod
  def ensure_list(cls, v: Any) -> list[str]:
    if v is None:
      return ["Unknown"]
    if isinstance(v, str):
      return [v]
    if isinstance(v, list):
      return v if v else ["Unknown"]
    return ["Unknown"]

  model_config = {"extra": "ignore"}


class ConditionValidation(BaseModel):
  """Validation schema for conditions/problems."""
  display_name: str = Field(default="Unknown", min_length=1)
  code_system: str | None = None
  code: str | None = None
  clinical_status: Literal[
    "active", "recurrence", "relapse", "inactive",
    "remission", "resolved"
  ] | str = "active"
  verification_status: Literal[
    "unconfirmed", "provisional", "differential",
    "confirmed", "refuted", "entered-in-error"
  ] | str = "confirmed"
  severity: Literal["mild", "moderate", "severe"] | None = None
  onset_date: date | str | None = None
  abatement_date: date | str | None = None
  notes: str | None = None

  @field_validator("onset_date", "abatement_date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> date | None:
    if v is None:
      return None
    if isinstance(v, date):
      return v
    if isinstance(v, datetime):
      return v.date()
    if isinstance(v, str):
      try:
        return date.fromisoformat(v[:10])
      except ValueError:
        return None
    return None

  model_config = {"extra": "ignore"}


class MedicationValidation(BaseModel):
  """Validation schema for medications."""
  display_name: str = Field(default="Unknown", min_length=1)
  status: Literal[
    "active", "completed", "entered-in-error", "intended",
    "stopped", "on-hold", "unknown", "not-taken", "cancelled"
  ] | str = "active"
  code_system: str | None = None
  code: str | None = None
  dose_quantity: str | None = None
  dose_unit: str | None = None
  frequency: str | None = None
  route: str = "oral"
  instructions: str | None = None
  prn: bool = False
  start_date: date | str | None = None
  end_date: date | str | None = None
  prescriber: str | None = None
  indication: str | None = None

  @field_validator("start_date", "end_date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> date | None:
    if v is None:
      return None
    if isinstance(v, date):
      return v
    if isinstance(v, datetime):
      return v.date()
    if isinstance(v, str):
      try:
        return date.fromisoformat(v[:10])
      except ValueError:
        return None
    return None

  model_config = {"extra": "ignore"}


class AllergyValidation(BaseModel):
  """Validation schema for allergies."""
  display_name: str = Field(default="Unknown", min_length=1)
  category: Literal["food", "medication", "environment", "biologic"] | str | None = None
  criticality: Literal["low", "high", "unable-to-assess"] | str = "low"
  reactions: list[dict] | None = None
  clinical_status: Literal["active", "inactive", "resolved"] | str = "active"
  onset_date: date | str | None = None
  notes: str | None = None

  @field_validator("onset_date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> date | None:
    if v is None:
      return None
    if isinstance(v, date):
      return v
    if isinstance(v, datetime):
      return v.date()
    if isinstance(v, str):
      try:
        return date.fromisoformat(v[:10])
      except ValueError:
        return None
    return None

  model_config = {"extra": "ignore"}


class EncounterValidation(BaseModel):
  """Validation schema for encounters."""
  date: datetime | str | None = None
  end_date: datetime | str | None = None
  encounter_type: str | None = None
  status: Literal[
    "planned", "in-progress", "on-hold", "discharged",
    "completed", "cancelled", "discontinued", "entered-in-error",
    "finished", "unknown"
  ] | str = "finished"
  encounter_class: Literal[
    "ambulatory", "emergency", "inpatient", "virtual",
    "home", "field", "AMB", "EMER", "IMP"
  ] | str = "ambulatory"
  chief_complaint: str | None = None
  provider_name: str | None = None
  location_name: str | None = None
  vital_signs: dict | None = None
  hpi: str | None = None
  physical_exam: dict | None = None
  assessment: list[dict] | None = None
  plan: list[dict] | None = None
  narrative_note: str | None = None
  billing_codes: dict | None = None

  @field_validator("date", "end_date", mode="before")
  @classmethod
  def parse_datetime(cls, v: Any) -> datetime | None:
    if v is None:
      return None
    if isinstance(v, datetime):
      return v
    if isinstance(v, date):
      return datetime.combine(v, datetime.min.time())
    if isinstance(v, str):
      try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
      except ValueError:
        try:
          return datetime.fromisoformat(v[:19])
        except ValueError:
          return None
    return None

  model_config = {"extra": "ignore"}


class ObservationValidation(BaseModel):
  """Validation schema for observations (labs, vitals, imaging)."""
  display_name: str = Field(default="Unknown", min_length=1)
  category: Literal[
    "vital-signs", "laboratory", "imaging", "procedure",
    "survey", "exam", "therapy", "activity", "social-history"
  ] | str = "laboratory"
  code_system: str | None = None
  code: str | None = None
  value_quantity: float | int | None = None
  value_string: str | None = None
  value_unit: str | None = None
  interpretation: str | None = None
  reference_range: dict | None = None
  effective_date: datetime | str | None = None
  performer: str | None = None
  notes: str | None = None

  @field_validator("effective_date", mode="before")
  @classmethod
  def parse_datetime(cls, v: Any) -> datetime | None:
    if v is None:
      return None
    if isinstance(v, datetime):
      return v
    if isinstance(v, date):
      return datetime.combine(v, datetime.min.time())
    if isinstance(v, str):
      try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
      except ValueError:
        try:
          return datetime.fromisoformat(v[:19])
        except ValueError:
          return None
    return None

  model_config = {"extra": "ignore"}


class ImmunizationValidation(BaseModel):
  """Validation schema for immunizations."""
  display_name: str = Field(default="Unknown", min_length=1)
  date: date | str | None = None
  status: Literal["completed", "entered-in-error", "not-done"] | str = "completed"
  vaccine_code: str | None = None
  dose_number: int | None = None
  series_doses: int | None = None
  site: str | None = None
  lot_number: str | None = None
  performer: str | None = None
  notes: str | None = None

  @field_validator("date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> date | None:
    if v is None:
      return None
    if isinstance(v, date):
      return v
    if isinstance(v, datetime):
      return v.date()
    if isinstance(v, str):
      try:
        return date.fromisoformat(v[:10])
      except ValueError:
        return None
    return None

  model_config = {"extra": "ignore"}


class MessageValidation(BaseModel):
  """Validation schema for patient messages."""
  sent_datetime: datetime | str | None = None
  reply_datetime: datetime | str | None = None
  sender_name: str = Field(default="Unknown", min_length=1)
  sender_is_patient: bool = True
  recipient_name: str | None = None
  replier_name: str | None = None
  replier_role: str | None = None
  category: str | None = None
  medium: Literal["portal", "phone", "email", "in-person", "fax", "sms"] | str = "portal"
  subject: str | None = None
  message_body: str = ""
  reply_body: str | None = None
  is_read: bool = False

  @field_validator("sent_datetime", "reply_datetime", mode="before")
  @classmethod
  def parse_datetime(cls, v: Any) -> datetime | None:
    if v is None:
      return None
    if isinstance(v, datetime):
      return v
    if isinstance(v, date):
      return datetime.combine(v, datetime.min.time())
    if isinstance(v, str):
      try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
      except ValueError:
        try:
          return datetime.fromisoformat(v[:19])
        except ValueError:
          return None
    return None

  model_config = {"extra": "ignore"}


class GrowthDataValidation(BaseModel):
  """Validation schema for pediatric growth data."""
  date: date | str | None = None
  age_in_days: int | None = None
  weight_kg: float | None = None
  height_cm: float | None = None
  head_circumference_cm: float | None = None
  bmi: float | None = None
  weight_percentile: float | None = None
  height_percentile: float | None = None
  bmi_percentile: float | None = None

  @field_validator("date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> date | None:
    if v is None:
      return None
    if isinstance(v, date):
      return v
    if isinstance(v, datetime):
      return v.date()
    if isinstance(v, str):
      try:
        return date.fromisoformat(v[:10])
      except ValueError:
        return None
    return None

  model_config = {"extra": "ignore"}
