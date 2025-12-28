"""Patient and related clinical models for Mneme EMR."""

from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, Field, computed_field


class Address(BaseModel):
  """Patient address."""
  line1: str | None = None
  line2: str | None = None
  city: str | None = None
  state: str | None = None
  postal_code: str | None = None
  country: str = "US"


class Contact(BaseModel):
  """Emergency or guardian contact."""
  name: str
  relationship: str | None = None
  phone: str | None = None
  email: str | None = None


class PatientBase(BaseModel):
  """Base patient model."""
  given_names: list[str]
  family_name: str
  date_of_birth: date
  sex_at_birth: str | None = None
  gender_identity: str | None = None
  race: list[str] | None = None
  ethnicity: str | None = None
  preferred_language: str = "English"
  phone: str | None = None
  email: str | None = None
  address: Address | None = None
  emergency_contact: Contact | None = None
  legal_guardian: Contact | None = None


class PatientCreate(PatientBase):
  """Model for creating a patient."""
  external_id: str | None = None


class Patient(PatientBase):
  """Full patient model with database fields."""
  id: str
  external_id: str | None = None
  created_at: datetime | None = None
  updated_at: datetime | None = None

  @computed_field
  @property
  def full_name(self) -> str:
    return f"{' '.join(self.given_names)} {self.family_name}"

  @computed_field
  @property
  def age_years(self) -> int:
    today = date.today()
    return today.year - self.date_of_birth.year - (
      (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
    )


class PatientSummary(BaseModel):
  """Minimal patient info for list views."""
  id: str
  given_names: list[str]
  family_name: str
  date_of_birth: date
  sex_at_birth: str | None = None
  phone: str | None = None

  @computed_field
  @property
  def full_name(self) -> str:
    return f"{' '.join(self.given_names)} {self.family_name}"

  @computed_field
  @property
  def age_years(self) -> int:
    today = date.today()
    return today.year - self.date_of_birth.year - (
      (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
    )


class CodeableConcept(BaseModel):
  """Medical code reference."""
  system: str | None = None
  code: str | None = None
  display: str | None = None


class Condition(BaseModel):
  """Medical condition/diagnosis."""
  id: str
  patient_id: str
  external_id: str | None = None
  code_system: str | None = None
  code: str | None = None
  display_name: str
  clinical_status: str = "active"
  verification_status: str = "confirmed"
  severity: str | None = None
  onset_date: date | None = None
  abatement_date: date | None = None
  notes: str | None = None
  created_at: datetime | None = None


class Medication(BaseModel):
  """Medication record."""
  id: str
  patient_id: str
  external_id: str | None = None
  code_system: str | None = None
  code: str | None = None
  display_name: str
  status: str = "active"
  dose_quantity: str | None = None
  dose_unit: str | None = None
  frequency: str | None = None
  route: str = "oral"
  instructions: str | None = None
  prn: bool = False
  start_date: date | None = None
  end_date: date | None = None
  prescriber: str | None = None
  indication: str | None = None
  created_at: datetime | None = None


class AllergyReaction(BaseModel):
  """Allergy reaction detail."""
  manifestation: str
  severity: str | None = None


class Allergy(BaseModel):
  """Allergy record."""
  id: str
  patient_id: str
  external_id: str | None = None
  display_name: str
  category: str | None = None
  criticality: str = "low"
  reactions: list[AllergyReaction] | None = None
  clinical_status: str = "active"
  onset_date: date | None = None
  notes: str | None = None
  created_at: datetime | None = None


class Immunization(BaseModel):
  """Immunization record."""
  id: str
  patient_id: str
  external_id: str | None = None
  vaccine_code: str | None = None
  display_name: str
  status: str = "completed"
  date: date
  dose_number: int | None = None
  series_doses: int | None = None
  site: str | None = None
  lot_number: str | None = None
  performer: str | None = None
  notes: str | None = None
  created_at: datetime | None = None


class Observation(BaseModel):
  """Lab result, vital sign, or other observation."""
  id: str
  patient_id: str
  encounter_id: str | None = None
  external_id: str | None = None
  category: str
  code_system: str | None = None
  code: str | None = None
  display_name: str
  value_quantity: float | None = None
  value_string: str | None = None
  value_unit: str | None = None
  interpretation: str | None = None
  reference_range: dict | None = None
  effective_date: datetime | None = None
  performer: str | None = None
  notes: str | None = None
  created_at: datetime | None = None

  @computed_field
  @property
  def display_value(self) -> str:
    if self.value_quantity is not None:
      unit = f" {self.value_unit}" if self.value_unit else ""
      return f"{self.value_quantity}{unit}"
    if self.value_string:
      return self.value_string
    return "N/A"


class GrowthData(BaseModel):
  """Pediatric growth measurement."""
  id: str
  patient_id: str
  encounter_id: str | None = None
  date: date
  age_in_days: int | None = None
  weight_kg: float | None = None
  height_cm: float | None = None
  head_circumference_cm: float | None = None
  bmi: float | None = None
  weight_percentile: float | None = None
  height_percentile: float | None = None
  bmi_percentile: float | None = None
  created_at: datetime | None = None


class PatientDetail(BaseModel):
  """Full patient with all clinical data."""
  patient: Patient
  conditions: list[Condition] = []
  medications: list[Medication] = []
  allergies: list[Allergy] = []
  immunizations: list[Immunization] = []
  recent_encounters: list["Encounter"] = []
  recent_observations: list[Observation] = []
  growth_data: list[GrowthData] = []


# Forward reference for Encounter
from .encounter import Encounter
PatientDetail.model_rebuild()
