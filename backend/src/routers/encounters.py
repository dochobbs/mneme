"""Syrinx voice encounter generation routes for Mneme EMR."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from src.db.supabase import SupabaseDB


router = APIRouter(prefix="/api/encounters", tags=["encounters"])

SYRINX_URL = "http://localhost:8003"


class GenerateEncounterRequest(BaseModel):
  """Request to generate a voice encounter from patient data."""
  patient_id: str
  chief_complaint: str
  encounter_type: str = "acute"  # acute, well-child, mental-health, follow-up
  duration: str = "medium"  # short, medium, long
  error_type: Optional[str] = None  # clinical, communication, None


class SaveEncounterRequest(BaseModel):
  """Request to save a generated encounter."""
  patient_id: str
  syrinx_id: str
  encounter_type: str
  chief_complaint: str
  metadata: dict
  script: list


def calculate_age_string(patient: dict) -> str:
  """Calculate age string from patient data."""
  from datetime import date

  if not patient.get("date_of_birth"):
    return "unknown age"

  dob = patient["date_of_birth"]
  if isinstance(dob, str):
    dob = date.fromisoformat(dob)

  today = date.today()
  age_days = (today - dob).days

  if age_days < 30:
    return f"{age_days} days"
  elif age_days < 365:
    months = age_days // 30
    return f"{months} month{'s' if months != 1 else ''}"
  else:
    years = age_days // 365
    return f"{years} year{'s' if years != 1 else ''}"


def build_syrinx_payload(patient: dict, request: GenerateEncounterRequest, clinical_data: dict) -> dict:
  """Transform Mneme patient to Syrinx generation payload."""

  age_str = calculate_age_string(patient)
  full_name = f"{patient.get('given_name', '')} {patient.get('family_name', '')}".strip()

  # Build description
  description = f"{age_str} old {patient.get('sex_at_birth', 'child')} named {full_name}"
  if request.chief_complaint:
    description += f" presenting with {request.chief_complaint}"

  # Extract allergies
  allergies = []
  for allergy in clinical_data.get("allergies", []):
    name = allergy.get("display_name") or allergy.get("substance_code")
    if name:
      reaction = allergy.get("reaction_description", "")
      if reaction:
        allergies.append(f"{name} ({reaction})")
      else:
        allergies.append(name)

  # Extract medications
  medications = []
  for med in clinical_data.get("medications", []):
    name = med.get("display_name") or med.get("medication_code")
    if name:
      medications.append(name)

  # Extract chronic conditions
  chronic_conditions = []
  for cond in clinical_data.get("conditions", []):
    name = cond.get("display_name") or cond.get("condition_code")
    if name and cond.get("clinical_status") == "active":
      chronic_conditions.append(name)

  payload = {
    "description": description,
    "duration": request.duration,
    "patient": {
      "name": full_name,
      "age": age_str,
      "sex": patient.get("sex_at_birth", "unknown"),
      "allergies": allergies if allergies else ["None known"],
      "medications": medications if medications else ["None active"],
      "chronic_conditions": chronic_conditions if chronic_conditions else ["None active"],
    },
  }

  # Add error injection if requested
  if request.error_type:
    payload["error_injection"] = request.error_type

  return payload


@router.post("/generate")
async def generate_encounter(request: GenerateEncounterRequest):
  """Generate a voice encounter using Syrinx."""
  db = SupabaseDB()

  # Fetch patient data
  try:
    patient_result = db.get_patient(request.patient_id)
    patient = patient_result.data
  except Exception:
    raise HTTPException(status_code=404, detail="Patient not found")

  # Fetch clinical data
  try:
    conditions_result = db.get_patient_conditions(request.patient_id)
    medications_result = db.get_patient_medications(request.patient_id)
    allergies_result = db.get_patient_allergies(request.patient_id)

    clinical_data = {
      "conditions": conditions_result.data,
      "medications": medications_result.data,
      "allergies": allergies_result.data,
    }
  except Exception:
    clinical_data = {
      "conditions": [],
      "medications": [],
      "allergies": [],
    }

  # Build Syrinx payload
  payload = build_syrinx_payload(patient, request, clinical_data)

  # Call Syrinx
  try:
    async with httpx.AsyncClient(timeout=120.0) as client:
      response = await client.post(
        f"{SYRINX_URL}/api/generate",
        json=payload,
      )
      response.raise_for_status()
      encounter = response.json()
  except httpx.ConnectError:
    raise HTTPException(
      status_code=503,
      detail="Syrinx service unavailable. Ensure it's running on port 8003.",
    )
  except httpx.TimeoutException:
    raise HTTPException(
      status_code=504,
      detail="Syrinx generation timed out. Try a shorter duration.",
    )
  except httpx.HTTPStatusError as e:
    raise HTTPException(
      status_code=e.response.status_code,
      detail=f"Syrinx error: {e.response.text}",
    )
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f"Failed to generate encounter: {str(e)}",
    )

  # Add patient context to response
  encounter["patient_id"] = request.patient_id
  encounter["patient_name"] = f"{patient.get('given_name', '')} {patient.get('family_name', '')}".strip()
  encounter["chief_complaint"] = request.chief_complaint

  return encounter


@router.post("/save")
async def save_encounter(request: SaveEncounterRequest):
  """Save a generated encounter to the database."""
  db = SupabaseDB()

  try:
    result = db.client.table("encounters_generated").insert({
      "patient_id": request.patient_id,
      "syrinx_id": request.syrinx_id,
      "encounter_type": request.encounter_type,
      "chief_complaint": request.chief_complaint,
      "metadata": request.metadata,
      "script": request.script,
    }).execute()

    return {"id": result.data[0]["id"], "status": "saved"}
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f"Failed to save encounter: {str(e)}",
    )


@router.get("/{patient_id}/generated")
async def get_generated_encounters(patient_id: str):
  """Get previously generated encounters for a patient."""
  db = SupabaseDB()

  try:
    result = db.client.table("encounters_generated").select("*").eq(
      "patient_id", patient_id
    ).order("created_at", desc=True).execute()

    return result.data
  except Exception as e:
    # Table may not exist yet
    print(f"Error fetching generated encounters: {e}")
    return []
