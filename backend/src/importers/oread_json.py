"""
Oread JSON Importer for Mneme EMR.

Imports synthetic patient data from oread JSON format into Supabase.
Handles the full patient model including demographics, conditions,
medications, allergies, encounters, observations, immunizations,
messages, and growth data.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.db.supabase import SupabaseDB


class OreadImporter:
  """Import oread JSON patient files into Mneme EMR."""

  def __init__(self, db: SupabaseDB | None = None):
    self.db = db or SupabaseDB()

  def import_file(self, filepath: str | Path) -> dict:
    """
    Import a single oread JSON file.

    Returns dict with import results including patient_id and any errors.
    """
    filepath = Path(filepath)
    if not filepath.exists():
      raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath) as f:
      data = json.load(f)

    return self.import_patient(data, source_file=filepath.name)

  def import_patient(self, data: dict, source_file: str = "unknown") -> dict:
    """
    Import a single patient from oread JSON data.

    Args:
        data: Oread patient JSON as dict
        source_file: Name of source file for tracking

    Returns:
        Dict with patient_id, counts, and any errors
    """
    result = {
      "success": False,
      "patient_id": None,
      "source_file": source_file,
      "counts": {},
      "errors": [],
    }

    try:
      # Extract and insert patient demographics
      patient_data = self._extract_patient(data)
      patient_response = self.db.insert_patient(patient_data)
      patient_id = patient_response.data[0]["id"]
      result["patient_id"] = patient_id

      # Import related clinical data
      counts = {}

      # Conditions
      conditions = self._extract_conditions(data, patient_id)
      if conditions:
        self.db.insert_conditions(conditions)
        counts["conditions"] = len(conditions)

      # Medications
      medications = self._extract_medications(data, patient_id)
      if medications:
        self.db.insert_medications(medications)
        counts["medications"] = len(medications)

      # Allergies
      allergies = self._extract_allergies(data, patient_id)
      if allergies:
        self.db.insert_allergies(allergies)
        counts["allergies"] = len(allergies)

      # Encounters
      encounters = self._extract_encounters(data, patient_id)
      encounter_id_map = {}
      if encounters:
        enc_response = self.db.insert_encounters(encounters)
        counts["encounters"] = len(encounters)
        # Build mapping from external_id to new id
        for i, enc in enumerate(enc_response.data):
          if encounters[i].get("external_id"):
            encounter_id_map[encounters[i]["external_id"]] = enc["id"]

      # Observations (need encounter ID mapping)
      observations = self._extract_observations(data, patient_id, encounter_id_map)
      if observations:
        self.db.insert_observations(observations)
        counts["observations"] = len(observations)

      # Immunizations
      immunizations = self._extract_immunizations(data, patient_id)
      if immunizations:
        self.db.insert_immunizations(immunizations)
        counts["immunizations"] = len(immunizations)

      # Messages
      messages = self._extract_messages(data, patient_id)
      if messages:
        self.db.insert_messages(messages)
        counts["messages"] = len(messages)

      # Growth data
      growth = self._extract_growth_data(data, patient_id, encounter_id_map)
      if growth:
        self.db.insert_growth_data(growth)
        counts["growth_data"] = len(growth)

      result["counts"] = counts
      result["success"] = True

    except Exception as e:
      result["errors"].append(str(e))

    return result

  def _extract_patient(self, data: dict) -> dict:
    """Extract patient demographics from oread format."""
    demo = data.get("demographics", {})

    # Build address JSONB
    address = None
    if addr := demo.get("address"):
      address = {
        "line1": addr.get("line1"),
        "line2": addr.get("line2"),
        "city": addr.get("city"),
        "state": addr.get("state"),
        "postal_code": addr.get("postal_code"),
        "country": addr.get("country", "US"),
      }

    # Build emergency contact JSONB
    emergency_contact = None
    if ec := demo.get("emergency_contact"):
      emergency_contact = {
        "name": ec.get("name"),
        "relationship": ec.get("relationship"),
        "phone": ec.get("phone"),
        "email": ec.get("email"),
      }

    # Build legal guardian JSONB
    legal_guardian = None
    if lg := demo.get("legal_guardian"):
      legal_guardian = {
        "name": lg.get("name"),
        "relationship": lg.get("relationship"),
        "phone": lg.get("phone"),
        "email": lg.get("email"),
      }

    return {
      "external_id": data.get("id"),
      "given_names": demo.get("given_names", []),
      "family_name": demo.get("family_name", "Unknown"),
      "date_of_birth": demo.get("date_of_birth"),
      "sex_at_birth": demo.get("sex_at_birth"),
      "gender_identity": demo.get("gender_identity"),
      "race": demo.get("race"),
      "ethnicity": demo.get("ethnicity"),
      "preferred_language": demo.get("preferred_language", "English"),
      "phone": demo.get("phone"),
      "email": demo.get("email"),
      "address": address,
      "emergency_contact": emergency_contact,
      "legal_guardian": legal_guardian,
    }

  def _extract_conditions(self, data: dict, patient_id: str) -> list[dict]:
    """Extract conditions/problems from oread format."""
    conditions = []
    for cond in data.get("problem_list", []):
      code = cond.get("code", {})
      conditions.append({
        "patient_id": patient_id,
        "external_id": cond.get("id"),
        "code_system": code.get("system"),
        "code": code.get("code"),
        "display_name": cond.get("display_name", code.get("display", "Unknown")),
        "clinical_status": cond.get("clinical_status", "active"),
        "verification_status": cond.get("verification_status", "confirmed"),
        "severity": cond.get("severity"),
        "onset_date": cond.get("onset_date"),
        "abatement_date": cond.get("abatement_date"),
        "notes": cond.get("notes"),
      })
    return conditions

  def _extract_medications(self, data: dict, patient_id: str) -> list[dict]:
    """Extract medications from oread format."""
    medications = []
    for med in data.get("medication_list", []):
      code = med.get("code", {})
      medications.append({
        "patient_id": patient_id,
        "external_id": med.get("id"),
        "code_system": code.get("system"),
        "code": code.get("code"),
        "display_name": med.get("display_name", code.get("display", "Unknown")),
        "status": med.get("status", "active"),
        "dose_quantity": med.get("dose_quantity"),
        "dose_unit": med.get("dose_unit"),
        "frequency": med.get("frequency"),
        "route": med.get("route", "oral"),
        "instructions": med.get("instructions"),
        "prn": med.get("prn", False),
        "start_date": med.get("start_date"),
        "end_date": med.get("end_date"),
        "prescriber": med.get("prescriber"),
        "indication": med.get("indication"),
      })
    return medications

  def _extract_allergies(self, data: dict, patient_id: str) -> list[dict]:
    """Extract allergies from oread format."""
    allergies = []
    for allergy in data.get("allergy_list", []):
      # Convert reactions to JSONB format
      reactions = None
      if rxns := allergy.get("reactions"):
        reactions = [
          {"manifestation": r.get("manifestation"), "severity": r.get("severity")}
          for r in rxns
        ]

      allergies.append({
        "patient_id": patient_id,
        "external_id": allergy.get("id"),
        "display_name": allergy.get("display_name", "Unknown"),
        "category": allergy.get("category"),
        "criticality": allergy.get("criticality", "low"),
        "reactions": reactions,
        "clinical_status": allergy.get("clinical_status", "active"),
        "onset_date": allergy.get("onset_date"),
        "notes": allergy.get("notes"),
      })
    return allergies

  def _extract_encounters(self, data: dict, patient_id: str) -> list[dict]:
    """Extract encounters from oread format."""
    encounters = []
    for enc in data.get("encounters", []):
      # Extract provider name
      provider_name = None
      if provider := enc.get("provider"):
        provider_name = provider.get("name")

      # Extract location name
      location_name = None
      if location := enc.get("location"):
        location_name = location.get("name")

      # Convert vital signs
      vital_signs = None
      if vs := enc.get("vital_signs"):
        vital_signs = {
          "temperature_f": vs.get("temperature_f"),
          "heart_rate": vs.get("heart_rate"),
          "respiratory_rate": vs.get("respiratory_rate"),
          "blood_pressure_systolic": vs.get("blood_pressure_systolic"),
          "blood_pressure_diastolic": vs.get("blood_pressure_diastolic"),
          "oxygen_saturation": vs.get("oxygen_saturation"),
          "weight_kg": vs.get("weight_kg"),
          "height_cm": vs.get("height_cm"),
        }

      # Convert assessment and plan
      assessment = None
      if assess := enc.get("assessment"):
        assessment = [
          {"condition": a.get("condition", a.get("problem")), "status": a.get("status"), "notes": a.get("notes")}
          for a in assess
        ]

      plan = None
      if p := enc.get("plan"):
        plan = [
          {"description": item.get("description", str(item)), "category": item.get("category")}
          for item in p
        ]

      encounters.append({
        "patient_id": patient_id,
        "external_id": enc.get("id"),
        "encounter_type": enc.get("type"),
        "status": enc.get("status", "finished"),
        "encounter_class": enc.get("encounter_class", "ambulatory"),
        "date": enc.get("date"),
        "end_date": enc.get("end_date"),
        "chief_complaint": enc.get("chief_complaint"),
        "provider_name": provider_name,
        "location_name": location_name,
        "vital_signs": vital_signs,
        "hpi": enc.get("hpi"),
        "physical_exam": enc.get("physical_exam"),
        "assessment": assessment,
        "plan": plan,
        "narrative_note": enc.get("narrative_note"),
        "billing_codes": enc.get("billing"),
      })
    return encounters

  def _extract_observations(self, data: dict, patient_id: str, encounter_id_map: dict) -> list[dict]:
    """Extract observations (labs, vitals) from oread format."""
    observations = []
    for obs in data.get("observations", []):
      code = obs.get("code", {})

      # Map encounter ID if present
      encounter_id = None
      if ext_enc_id := obs.get("encounter_id"):
        encounter_id = encounter_id_map.get(ext_enc_id)

      # Extract reference range
      ref_range = None
      if rr := obs.get("reference_range"):
        ref_range = {
          "low": rr.get("low"),
          "high": rr.get("high"),
          "text": rr.get("text"),
        }

      observations.append({
        "patient_id": patient_id,
        "encounter_id": encounter_id,
        "external_id": obs.get("id"),
        "category": obs.get("category", "laboratory"),
        "code_system": code.get("system"),
        "code": code.get("code"),
        "display_name": code.get("display", obs.get("display_name", "Unknown")),
        "value_quantity": obs.get("value_quantity"),
        "value_string": obs.get("value_string"),
        "value_unit": obs.get("unit"),
        "interpretation": obs.get("interpretation"),
        "reference_range": ref_range,
        "effective_date": obs.get("effective_date"),
        "performer": obs.get("performer"),
        "notes": obs.get("notes"),
      })
    return observations

  def _extract_immunizations(self, data: dict, patient_id: str) -> list[dict]:
    """Extract immunizations from oread format."""
    immunizations = []
    for imm in data.get("immunization_record", []):
      vaccine_code = None
      if vc := imm.get("vaccine_code"):
        vaccine_code = vc.get("code")

      immunizations.append({
        "patient_id": patient_id,
        "external_id": imm.get("id"),
        "vaccine_code": vaccine_code,
        "display_name": imm.get("display_name", "Unknown"),
        "status": imm.get("status", "completed"),
        "date": imm.get("date"),
        "dose_number": imm.get("dose_number"),
        "series_doses": imm.get("series_doses"),
        "site": imm.get("site"),
        "lot_number": imm.get("lot_number"),
        "performer": imm.get("performer"),
        "notes": imm.get("notes"),
      })
    return immunizations

  def _extract_messages(self, data: dict, patient_id: str) -> list[dict]:
    """Extract patient messages from oread format."""
    messages = []
    for msg in data.get("patient_messages", []):
      messages.append({
        "patient_id": patient_id,
        "external_id": msg.get("id"),
        "sent_datetime": msg.get("sent_datetime"),
        "reply_datetime": msg.get("reply_datetime"),
        "sender_name": msg.get("sender_name", "Unknown"),
        "sender_is_patient": msg.get("sender_is_patient", True),
        "recipient_name": msg.get("recipient_name"),
        "replier_name": msg.get("replier_name"),
        "replier_role": msg.get("replier_role"),
        "category": msg.get("category"),
        "medium": msg.get("medium", "portal"),
        "subject": msg.get("subject"),
        "message_body": msg.get("message_body", ""),
        "reply_body": msg.get("reply_body"),
        "is_read": False,
      })
    return messages

  def _extract_growth_data(self, data: dict, patient_id: str, encounter_id_map: dict) -> list[dict]:
    """Extract pediatric growth data from oread format."""
    growth = []
    for gd in data.get("growth_data", []):
      # Map encounter ID if present
      encounter_id = None
      if ext_enc_id := gd.get("encounter_id"):
        encounter_id = encounter_id_map.get(ext_enc_id)

      growth.append({
        "patient_id": patient_id,
        "encounter_id": encounter_id,
        "date": gd.get("date"),
        "age_in_days": gd.get("age_in_days"),
        "weight_kg": gd.get("weight_kg"),
        "height_cm": gd.get("height_cm"),
        "head_circumference_cm": gd.get("head_circumference_cm"),
        "bmi": gd.get("bmi"),
        "weight_percentile": gd.get("weight_percentile"),
        "height_percentile": gd.get("height_percentile"),
        "bmi_percentile": gd.get("bmi_percentile"),
      })
    return growth

  def import_directory(self, dirpath: str | Path) -> dict:
    """
    Import all JSON files from a directory.

    Returns summary of import results.
    """
    dirpath = Path(dirpath)
    if not dirpath.is_dir():
      raise NotADirectoryError(f"Not a directory: {dirpath}")

    results = {
      "total_files": 0,
      "successful": 0,
      "failed": 0,
      "patients": [],
      "errors": [],
    }

    for filepath in dirpath.glob("*.json"):
      results["total_files"] += 1
      try:
        patient_result = self.import_file(filepath)
        if patient_result["success"]:
          results["successful"] += 1
          results["patients"].append({
            "file": filepath.name,
            "patient_id": patient_result["patient_id"],
            "counts": patient_result["counts"],
          })
        else:
          results["failed"] += 1
          results["errors"].extend(patient_result["errors"])
      except Exception as e:
        results["failed"] += 1
        results["errors"].append(f"{filepath.name}: {str(e)}")

    return results
