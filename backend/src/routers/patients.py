"""Patient API routes for Mneme EMR."""

from fastapi import APIRouter, HTTPException, Query
from src.db.supabase import SupabaseDB
from src.models.patient import Patient, PatientSummary, PatientDetail, Condition, Medication, Allergy, Immunization, Observation, GrowthData
from src.models.encounter import Encounter

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("")
async def list_patients(
  limit: int = Query(50, ge=1, le=100),
  offset: int = Query(0, ge=0),
  search: str | None = None,
) -> list[PatientSummary]:
  """Get paginated list of patients."""
  try:
    db = SupabaseDB()
    result = db.get_patients(limit=limit, offset=offset)
    return [PatientSummary(**p) for p in result.data]
  except Exception as e:
    # Table may not exist yet - return empty list
    print(f"Error fetching patients: {e}")
    return []


@router.get("/{patient_id}")
async def get_patient(patient_id: str) -> Patient:
  """Get patient by ID."""
  db = SupabaseDB()
  try:
    result = db.get_patient(patient_id)
    return Patient(**result.data)
  except Exception:
    raise HTTPException(status_code=404, detail="Patient not found")


@router.get("/{patient_id}/detail")
async def get_patient_detail(patient_id: str) -> PatientDetail:
  """Get patient with full clinical data."""
  db = SupabaseDB()

  try:
    patient_result = db.get_patient(patient_id)
    patient = Patient(**patient_result.data)
  except Exception:
    raise HTTPException(status_code=404, detail="Patient not found")

  # Fetch related data
  conditions_result = db.get_patient_conditions(patient_id)
  medications_result = db.get_patient_medications(patient_id)
  allergies_result = db.get_patient_allergies(patient_id)
  immunizations_result = db.get_patient_immunizations(patient_id)
  encounters_result = db.get_patient_encounters(patient_id, limit=10)
  observations_result = db.get_patient_observations(patient_id)
  growth_result = db.get_patient_growth(patient_id)

  return PatientDetail(
    patient=patient,
    conditions=[Condition(**c) for c in conditions_result.data],
    medications=[Medication(**m) for m in medications_result.data],
    allergies=[Allergy(**a) for a in allergies_result.data],
    immunizations=[Immunization(**i) for i in immunizations_result.data],
    recent_encounters=[Encounter(**e) for e in encounters_result.data],
    recent_observations=[Observation(**o) for o in observations_result.data],
    growth_data=[GrowthData(**g) for g in growth_result.data],
  )


@router.get("/{patient_id}/conditions")
async def get_patient_conditions(patient_id: str) -> list[Condition]:
  """Get patient's conditions/problems."""
  db = SupabaseDB()
  result = db.get_patient_conditions(patient_id)
  return [Condition(**c) for c in result.data]


@router.get("/{patient_id}/medications")
async def get_patient_medications(patient_id: str) -> list[Medication]:
  """Get patient's medications."""
  db = SupabaseDB()
  result = db.get_patient_medications(patient_id)
  return [Medication(**m) for m in result.data]


@router.get("/{patient_id}/allergies")
async def get_patient_allergies(patient_id: str) -> list[Allergy]:
  """Get patient's allergies."""
  db = SupabaseDB()
  result = db.get_patient_allergies(patient_id)
  return [Allergy(**a) for a in result.data]


@router.get("/{patient_id}/immunizations")
async def get_patient_immunizations(patient_id: str) -> list[Immunization]:
  """Get patient's immunizations."""
  db = SupabaseDB()
  result = db.get_patient_immunizations(patient_id)
  return [Immunization(**i) for i in result.data]


@router.get("/{patient_id}/encounters")
async def get_patient_encounters(
  patient_id: str,
  limit: int = Query(20, ge=1, le=100),
) -> list[Encounter]:
  """Get patient's encounters/notes."""
  db = SupabaseDB()
  result = db.get_patient_encounters(patient_id, limit=limit)
  return [Encounter(**e) for e in result.data]


@router.get("/{patient_id}/observations")
async def get_patient_observations(
  patient_id: str,
  category: str | None = None,
) -> list[Observation]:
  """Get patient's observations (labs, vitals)."""
  db = SupabaseDB()
  result = db.get_patient_observations(patient_id, category=category)
  return [Observation(**o) for o in result.data]


@router.get("/{patient_id}/growth")
async def get_patient_growth(patient_id: str) -> list[GrowthData]:
  """Get patient's growth data."""
  db = SupabaseDB()
  result = db.get_patient_growth(patient_id)
  return [GrowthData(**g) for g in result.data]


@router.get("/{patient_id}/messages")
async def get_patient_messages(patient_id: str):
  """Get patient's messages."""
  db = SupabaseDB()
  result = db.get_patient_messages(patient_id)
  return result.data
