"""Medical code system validators.

Validates format of medical coding systems:
- SNOMED CT: Clinical terminology
- ICD-10-CM: Diagnosis codes (billing)
- RxNorm: Medication codes
- LOINC: Lab test codes
- CVX: Vaccine codes
"""

import re


def validate_snomed(code: str) -> bool:
  """
  Validate SNOMED CT code format.
  SNOMED codes are 6-18 digit numeric identifiers.
  """
  if not code:
    return False
  return bool(re.match(r"^\d{6,18}$", str(code)))


def validate_icd10(code: str) -> bool:
  """
  Validate ICD-10-CM code format.
  Format: Letter + 2 digits, optional decimal + 1-4 more chars.
  Examples: A00, J21.0, S72.001A
  """
  if not code:
    return False
  return bool(re.match(r"^[A-Z]\d{2}(\.\d{1,4}[A-Z]?)?$", str(code), re.IGNORECASE))


def validate_rxnorm(code: str) -> bool:
  """
  Validate RxNorm code format.
  RxNorm codes are numeric identifiers.
  """
  if not code:
    return False
  return bool(re.match(r"^\d+$", str(code)))


def validate_loinc(code: str) -> bool:
  """
  Validate LOINC code format.
  Format: Numeric part + hyphen + check digit.
  Examples: 2345-7, 29463-7, 8302-2
  """
  if not code:
    return False
  return bool(re.match(r"^\d+-\d$", str(code)))


def validate_cvx(code: str) -> bool:
  """
  Validate CVX vaccine code format.
  CVX codes are 1-3 digit numbers (1-999).
  """
  if not code:
    return False
  try:
    val = int(code)
    return 1 <= val <= 999
  except (ValueError, TypeError):
    return False


# Mapping of code system identifiers to validator functions
CODE_VALIDATORS = {
  # SNOMED CT
  "snomed": validate_snomed,
  "SNOMED-CT": validate_snomed,
  "http://snomed.info/sct": validate_snomed,
  # ICD-10-CM
  "icd10": validate_icd10,
  "icd-10": validate_icd10,
  "ICD-10-CM": validate_icd10,
  "http://hl7.org/fhir/sid/icd-10-cm": validate_icd10,
  # RxNorm
  "rxnorm": validate_rxnorm,
  "RxNorm": validate_rxnorm,
  "http://www.nlm.nih.gov/research/umls/rxnorm": validate_rxnorm,
  # LOINC
  "loinc": validate_loinc,
  "LOINC": validate_loinc,
  "http://loinc.org": validate_loinc,
  # CVX
  "cvx": validate_cvx,
  "CVX": validate_cvx,
  "http://hl7.org/fhir/sid/cvx": validate_cvx,
}


def validate_code(system: str | None, code: str | None) -> tuple[bool, str | None]:
  """
  Validate a medical code against its system.

  Args:
    system: The code system identifier (e.g., "snomed", "http://loinc.org")
    code: The code value to validate

  Returns:
    Tuple of (is_valid, error_message).
    If valid, error_message is None.
    If system is unknown, returns (True, None) - permissive mode.
  """
  if not code:
    return True, None  # No code to validate

  if not system:
    return True, None  # Unknown system, cannot validate

  validator = CODE_VALIDATORS.get(system)
  if not validator:
    return True, None  # Unknown system, skip validation (permissive)

  if validator(str(code)):
    return True, None

  # Determine friendly system name for error message
  system_names = {
    "snomed": "SNOMED CT",
    "SNOMED-CT": "SNOMED CT",
    "http://snomed.info/sct": "SNOMED CT",
    "icd10": "ICD-10-CM",
    "icd-10": "ICD-10-CM",
    "ICD-10-CM": "ICD-10-CM",
    "http://hl7.org/fhir/sid/icd-10-cm": "ICD-10-CM",
    "rxnorm": "RxNorm",
    "RxNorm": "RxNorm",
    "http://www.nlm.nih.gov/research/umls/rxnorm": "RxNorm",
    "loinc": "LOINC",
    "LOINC": "LOINC",
    "http://loinc.org": "LOINC",
    "cvx": "CVX",
    "CVX": "CVX",
    "http://hl7.org/fhir/sid/cvx": "CVX",
  }
  friendly_name = system_names.get(system, system)

  return False, f"Invalid {friendly_name} code format: {code}"


def normalize_code_system(system: str | None) -> str | None:
  """
  Normalize a code system URL to a short name.

  Args:
    system: The code system identifier or URL

  Returns:
    Normalized short name (e.g., "snomed", "icd10", "rxnorm", "loinc", "cvx")
    or the original value if unknown.
  """
  if not system:
    return None

  mapping = {
    "http://snomed.info/sct": "snomed",
    "SNOMED-CT": "snomed",
    "http://hl7.org/fhir/sid/icd-10-cm": "icd10",
    "ICD-10-CM": "icd10",
    "http://www.nlm.nih.gov/research/umls/rxnorm": "rxnorm",
    "RxNorm": "rxnorm",
    "http://loinc.org": "loinc",
    "LOINC": "loinc",
    "http://hl7.org/fhir/sid/cvx": "cvx",
    "CVX": "cvx",
  }

  return mapping.get(system, system)
