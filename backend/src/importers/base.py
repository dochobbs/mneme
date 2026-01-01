"""Base importer with validation and rollback support.

Provides abstract base class for patient data importers. Handles:
- Pre-import validation (permissive mode - warns but continues)
- Sequential insert of patient then child records
- Rollback on failure via CASCADE delete
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.db.supabase import SupabaseDB
from src.importers.validation.validators import ImportValidator, ValidationWarning


@dataclass
class ImportResult:
  """Result of an import operation."""
  success: bool
  patient_id: str | None = None
  source_file: str = "unknown"
  format: str = "unknown"
  counts: dict = field(default_factory=dict)
  errors: list[str] = field(default_factory=list)
  warnings: list[ValidationWarning] = field(default_factory=list)

  def to_dict(self) -> dict:
    """Convert to dictionary for JSON serialization."""
    return {
      "success": self.success,
      "patient_id": self.patient_id,
      "source_file": self.source_file,
      "format": self.format,
      "counts": self.counts,
      "errors": self.errors,
      "warnings": [w.to_dict() for w in self.warnings],
    }


@dataclass
class ExtractedPatient:
  """Container for all extracted patient data ready for insert."""
  patient: dict
  conditions: list[dict] = field(default_factory=list)
  medications: list[dict] = field(default_factory=list)
  allergies: list[dict] = field(default_factory=list)
  encounters: list[dict] = field(default_factory=list)
  observations: list[dict] = field(default_factory=list)
  immunizations: list[dict] = field(default_factory=list)
  messages: list[dict] = field(default_factory=list)
  growth_data: list[dict] = field(default_factory=list)


class BaseImporter(ABC):
  """
  Base class for patient data importers with validation and rollback.

  Subclasses must implement:
  - extract_patient(data) -> ExtractedPatient
  - format_name property

  Import process:
  1. Extract all data from source format (subclass)
  2. Validate all data (permissive - returns warnings)
  3. Insert patient first, capture ID
  4. Insert all child records
  5. On failure, delete patient (CASCADE handles children)
  """

  def __init__(self, db: SupabaseDB | None = None):
    self.db = db or SupabaseDB()
    self.validator = ImportValidator()

  @property
  @abstractmethod
  def format_name(self) -> str:
    """Return format name for logging (e.g., 'fhir-r5', 'oread-json')."""
    pass

  @abstractmethod
  def extract_patient(self, data: Any) -> ExtractedPatient:
    """
    Extract patient data from source format.

    Override in subclass to parse specific format (FHIR, Oread JSON, etc.)
    and return normalized ExtractedPatient dataclass.

    Args:
      data: Source data in native format

    Returns:
      ExtractedPatient with all clinical data ready for insert
    """
    pass

  def import_patient(self, data: Any, source_file: str = "unknown") -> ImportResult:
    """
    Import patient with validation and rollback support.

    1. Extract all data from source format
    2. Validate all data (permissive - collects warnings)
    3. Insert patient first, capture ID
    4. Insert all child records
    5. On any failure, delete patient (CASCADE handles cleanup)

    Args:
      data: Source data in native format
      source_file: Name of source file for tracking

    Returns:
      ImportResult with success status, patient_id, counts, and any warnings/errors
    """
    result = ImportResult(
      success=False,
      source_file=source_file,
      format=self.format_name,
    )
    patient_id = None

    try:
      # Step 1: Extract all data from source format
      extracted = self.extract_patient(data)

      # Step 2: Validate all data (permissive - collect warnings)
      warnings = self.validator.validate_all(extracted)
      result.warnings = warnings

      # Step 3: Insert patient first, capture ID
      patient_response = self.db.insert_patient(extracted.patient)
      patient_id = patient_response.data[0]["id"]
      result.patient_id = patient_id

      # Step 4: Insert all child records
      counts = self._insert_child_records(patient_id, extracted)
      result.counts = counts
      result.success = True

    except Exception as e:
      result.errors.append(str(e))
      # Step 5: Rollback - delete patient if created (CASCADE handles children)
      if patient_id:
        try:
          self.db.delete_patient(patient_id)
          result.errors.append("Rolled back: patient and related records deleted")
        except Exception as rollback_error:
          result.errors.append(f"Rollback failed: {rollback_error}")

    return result

  def _insert_child_records(
    self,
    patient_id: str,
    extracted: ExtractedPatient,
  ) -> dict:
    """
    Insert all child records for a patient.

    Args:
      patient_id: UUID of the inserted patient
      extracted: ExtractedPatient with all clinical data

    Returns:
      Dictionary of counts per table (e.g., {"conditions": 5, "medications": 3})
    """
    counts: dict[str, int] = {}

    # Insert encounters first to get ID mapping for observations/growth_data
    encounter_id_map: dict[str, str] = {}
    if extracted.encounters:
      for enc in extracted.encounters:
        enc["patient_id"] = patient_id
      enc_response = self.db.insert_encounters(extracted.encounters)
      counts["encounters"] = len(extracted.encounters)
      # Build mapping from external_id to new database id
      for i, enc in enumerate(enc_response.data):
        ext_id = extracted.encounters[i].get("external_id")
        if ext_id:
          encounter_id_map[ext_id] = enc["id"]

    # Insert conditions
    if extracted.conditions:
      for cond in extracted.conditions:
        cond["patient_id"] = patient_id
      self.db.insert_conditions(extracted.conditions)
      counts["conditions"] = len(extracted.conditions)

    # Insert medications
    if extracted.medications:
      for med in extracted.medications:
        med["patient_id"] = patient_id
      self.db.insert_medications(extracted.medications)
      counts["medications"] = len(extracted.medications)

    # Insert allergies
    if extracted.allergies:
      for allergy in extracted.allergies:
        allergy["patient_id"] = patient_id
      self.db.insert_allergies(extracted.allergies)
      counts["allergies"] = len(extracted.allergies)

    # Insert observations (with encounter ID mapping)
    if extracted.observations:
      for obs in extracted.observations:
        obs["patient_id"] = patient_id
        # Resolve temporary encounter reference if present
        if "_temp_encounter_ref" in obs:
          ext_enc_id = obs.pop("_temp_encounter_ref")
          if ext_enc_id:
            obs["encounter_id"] = encounter_id_map.get(ext_enc_id)
      self.db.insert_observations(extracted.observations)
      counts["observations"] = len(extracted.observations)

    # Insert immunizations
    if extracted.immunizations:
      for imm in extracted.immunizations:
        imm["patient_id"] = patient_id
      self.db.insert_immunizations(extracted.immunizations)
      counts["immunizations"] = len(extracted.immunizations)

    # Insert messages
    if extracted.messages:
      for msg in extracted.messages:
        msg["patient_id"] = patient_id
      self.db.insert_messages(extracted.messages)
      counts["messages"] = len(extracted.messages)

    # Insert growth data (with encounter ID mapping)
    if extracted.growth_data:
      for gd in extracted.growth_data:
        gd["patient_id"] = patient_id
        # Resolve temporary encounter reference if present
        if "_temp_encounter_ref" in gd:
          ext_enc_id = gd.pop("_temp_encounter_ref")
          if ext_enc_id:
            gd["encounter_id"] = encounter_id_map.get(ext_enc_id)
      self.db.insert_growth_data(extracted.growth_data)
      counts["growth_data"] = len(extracted.growth_data)

    return counts
