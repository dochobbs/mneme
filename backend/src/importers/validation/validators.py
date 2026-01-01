"""Import data validators.

Orchestrates validation of all imported patient data using Pydantic schemas
and medical code validators. Operates in permissive mode - returns warnings
but allows import to proceed.
"""

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING
from pydantic import ValidationError as PydanticValidationError

from .schemas import (
  PatientValidation,
  ConditionValidation,
  MedicationValidation,
  AllergyValidation,
  EncounterValidation,
  ObservationValidation,
  ImmunizationValidation,
  MessageValidation,
  GrowthDataValidation,
)
from .codes import validate_code

if TYPE_CHECKING:
  from src.importers.base import ExtractedPatient


@dataclass
class ValidationWarning:
  """A single validation warning."""
  path: str         # e.g., "patient.family_name" or "conditions[2].code"
  message: str      # Warning description
  value: Any = None # The problematic value

  def to_dict(self) -> dict:
    """Convert to dictionary for JSON serialization."""
    return {
      "path": self.path,
      "message": self.message,
      "value": str(self.value) if self.value is not None else None,
    }


class ImportValidator:
  """
  Validates extracted patient data before database insert.

  Operates in PERMISSIVE mode: returns warnings but does not block import.
  Validation errors become warnings that are returned to the caller.
  """

  def validate_all(self, extracted: "ExtractedPatient") -> list[ValidationWarning]:
    """
    Validate all extracted data.

    Args:
      extracted: ExtractedPatient dataclass with all patient data

    Returns:
      List of validation warnings (empty if all data is valid).
    """
    warnings: list[ValidationWarning] = []

    # Validate patient (required)
    warnings.extend(self._validate_patient(extracted.patient))

    # Validate child records
    warnings.extend(self._validate_list("conditions", extracted.conditions, ConditionValidation))
    warnings.extend(self._validate_list("medications", extracted.medications, MedicationValidation))
    warnings.extend(self._validate_list("allergies", extracted.allergies, AllergyValidation))
    warnings.extend(self._validate_list("encounters", extracted.encounters, EncounterValidation))
    warnings.extend(self._validate_list("observations", extracted.observations, ObservationValidation))
    warnings.extend(self._validate_list("immunizations", extracted.immunizations, ImmunizationValidation))
    warnings.extend(self._validate_list("messages", extracted.messages, MessageValidation))
    warnings.extend(self._validate_list("growth_data", extracted.growth_data, GrowthDataValidation))

    # Validate medical codes
    warnings.extend(self._validate_codes(extracted))

    return warnings

  def _validate_patient(self, data: dict) -> list[ValidationWarning]:
    """Validate patient demographics."""
    try:
      PatientValidation(**data)
      return []
    except PydanticValidationError as e:
      return self._pydantic_to_warnings("patient", e)
    except Exception as e:
      return [ValidationWarning(path="patient", message=str(e))]

  def _validate_list(
    self,
    name: str,
    items: list[dict],
    schema: type,
  ) -> list[ValidationWarning]:
    """Validate a list of items against a Pydantic schema."""
    warnings: list[ValidationWarning] = []
    for i, item in enumerate(items):
      try:
        schema(**item)
      except PydanticValidationError as e:
        warnings.extend(self._pydantic_to_warnings(f"{name}[{i}]", e))
      except Exception as e:
        warnings.append(ValidationWarning(path=f"{name}[{i}]", message=str(e)))
    return warnings

  def _validate_codes(self, extracted: "ExtractedPatient") -> list[ValidationWarning]:
    """Validate medical codes across all resources."""
    warnings: list[ValidationWarning] = []

    # Conditions (SNOMED/ICD-10)
    for i, cond in enumerate(extracted.conditions):
      valid, msg = validate_code(cond.get("code_system"), cond.get("code"))
      if not valid and msg:
        warnings.append(ValidationWarning(
          path=f"conditions[{i}].code",
          message=msg,
          value=cond.get("code"),
        ))

    # Medications (RxNorm)
    for i, med in enumerate(extracted.medications):
      valid, msg = validate_code(med.get("code_system"), med.get("code"))
      if not valid and msg:
        warnings.append(ValidationWarning(
          path=f"medications[{i}].code",
          message=msg,
          value=med.get("code"),
        ))

    # Observations (LOINC)
    for i, obs in enumerate(extracted.observations):
      valid, msg = validate_code(obs.get("code_system"), obs.get("code"))
      if not valid and msg:
        warnings.append(ValidationWarning(
          path=f"observations[{i}].code",
          message=msg,
          value=obs.get("code"),
        ))

    # Immunizations (CVX)
    for i, imm in enumerate(extracted.immunizations):
      valid, msg = validate_code("cvx", imm.get("vaccine_code"))
      if not valid and msg:
        warnings.append(ValidationWarning(
          path=f"immunizations[{i}].vaccine_code",
          message=msg,
          value=imm.get("vaccine_code"),
        ))

    return warnings

  def _pydantic_to_warnings(
    self,
    prefix: str,
    exc: PydanticValidationError,
  ) -> list[ValidationWarning]:
    """Convert Pydantic validation error to our warning format."""
    warnings: list[ValidationWarning] = []
    for err in exc.errors():
      path_parts = [str(x) for x in err.get("loc", [])]
      full_path = f"{prefix}.{'.'.join(path_parts)}" if path_parts else prefix
      warnings.append(ValidationWarning(
        path=full_path,
        message=err.get("msg", "Validation error"),
        value=err.get("input"),
      ))
    return warnings
