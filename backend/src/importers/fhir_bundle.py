"""FHIR R5 Bundle Importer for Mneme EMR.

Parses FHIR R5 Bundle JSON and extracts clinical resources into Mneme format.
Uses the fhir.resources library for parsing and validation.

Supported FHIR Resources:
- Patient → patients
- Condition → conditions
- MedicationStatement/MedicationRequest → medications
- AllergyIntolerance → allergies
- Encounter → encounters
- Observation → observations
- Immunization → immunizations
- Communication → messages
"""

from datetime import date, datetime
from typing import Any

from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient as FHIRPatient
from fhir.resources.condition import Condition as FHIRCondition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.encounter import Encounter as FHIREncounter
from fhir.resources.observation import Observation as FHIRObservation
from fhir.resources.immunization import Immunization as FHIRImmunization
from fhir.resources.communication import Communication

from src.db.supabase import SupabaseDB
from src.importers.base import BaseImporter, ExtractedPatient, ImportResult
from src.importers.validation.codes import normalize_code_system


class FHIRBundleImporter(BaseImporter):
  """Import FHIR R5 Bundle into Mneme EMR."""

  def __init__(self, db: SupabaseDB | None = None):
    super().__init__(db)
    self._resource_map: dict[str, Any] = {}  # Maps FHIR reference to resource
    self._patient_id: str | None = None       # FHIR Patient resource ID

  @property
  def format_name(self) -> str:
    return "fhir-r5"

  def import_bundle(self, bundle_json: dict, source_file: str = "unknown") -> ImportResult:
    """
    Import a FHIR R5 Bundle.

    Expects a Bundle with type "collection" or "transaction" containing
    Patient and related clinical resources.

    Args:
      bundle_json: FHIR Bundle as dictionary
      source_file: Name of source file for tracking

    Returns:
      ImportResult with success status, patient_id, counts, warnings/errors
    """
    # Parse bundle using fhir.resources library
    try:
      bundle = Bundle.model_validate(bundle_json)
    except Exception as e:
      return ImportResult(
        success=False,
        source_file=source_file,
        format=self.format_name,
        errors=[f"Invalid FHIR Bundle: {e}"],
      )

    # Build resource map for reference resolution
    self._build_resource_map(bundle)

    # Find patient resource
    patient_resource = self._find_patient()
    if not patient_resource:
      return ImportResult(
        success=False,
        source_file=source_file,
        format=self.format_name,
        errors=["No Patient resource found in Bundle"],
      )

    self._patient_id = patient_resource.id

    # Use base class import_patient with bundle data
    return self.import_patient(bundle, source_file)

  def extract_patient(self, bundle: Bundle) -> ExtractedPatient:
    """Extract all resources from FHIR Bundle."""
    patient_resource = self._find_patient()
    if not patient_resource:
      raise ValueError("No Patient resource found")

    return ExtractedPatient(
      patient=self._extract_patient(patient_resource),
      conditions=self._extract_conditions(),
      medications=self._extract_medications(),
      allergies=self._extract_allergies(),
      encounters=self._extract_encounters(),
      observations=self._extract_observations(),
      immunizations=self._extract_immunizations(),
      messages=self._extract_messages(),
    )

  def _build_resource_map(self, bundle: Bundle) -> None:
    """Build map of resource references to resources."""
    self._resource_map.clear()
    if bundle.entry:
      for entry in bundle.entry:
        if entry.resource:
          resource = entry.resource
          # Map by full URL
          if entry.fullUrl:
            self._resource_map[entry.fullUrl] = resource
          # Map by type/id
          if hasattr(resource, "id") and resource.id:
            type_name = resource.__class__.__name__
            self._resource_map[f"{type_name}/{resource.id}"] = resource

  def _find_patient(self) -> FHIRPatient | None:
    """Find Patient resource in bundle."""
    for ref, resource in self._resource_map.items():
      if isinstance(resource, FHIRPatient):
        return resource
    return None

  def _references_patient(self, reference: Any) -> bool:
    """Check if a reference points to the patient."""
    if not reference or not self._patient_id:
      return False
    if hasattr(reference, "reference"):
      ref_str = reference.reference
      return ref_str and self._patient_id in ref_str
    return False

  # ─────────────────────────────────────────────────────────────────────────────
  # Patient Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_patient(self, fhir_patient: FHIRPatient) -> dict:
    """Convert FHIR Patient to Mneme format."""
    # Extract names
    given_names = ["Unknown"]
    family_name = "Unknown"
    if fhir_patient.name:
      name = fhir_patient.name[0]  # Use first name
      if name.given:
        given_names = list(name.given)
      if name.family:
        family_name = name.family

    # Extract address
    address = None
    if fhir_patient.address:
      addr = fhir_patient.address[0]
      address = {
        "line1": addr.line[0] if addr.line else None,
        "line2": addr.line[1] if addr.line and len(addr.line) > 1 else None,
        "city": addr.city,
        "state": addr.state,
        "postal_code": addr.postalCode,
        "country": addr.country or "US",
      }

    # Extract telecom
    phone = None
    email = None
    if fhir_patient.telecom:
      for telecom in fhir_patient.telecom:
        if telecom.system == "phone" and not phone:
          phone = telecom.value
        elif telecom.system == "email" and not email:
          email = telecom.value

    # Extract contacts (emergency contact, guardian)
    emergency_contact = None
    legal_guardian = None
    if fhir_patient.contact:
      for contact in fhir_patient.contact:
        contact_data = self._extract_contact(contact)
        # Determine if emergency contact or guardian based on relationship
        if contact.relationship:
          for rel in contact.relationship:
            if rel.coding:
              rel_code = rel.coding[0].code
              if rel_code in ("C", "emergency"):
                emergency_contact = contact_data
              elif rel_code in ("PRN", "guardian", "parent"):
                legal_guardian = contact_data
        # Default to emergency contact if not categorized
        if not emergency_contact:
          emergency_contact = contact_data

    return {
      "external_id": fhir_patient.id,
      "given_names": given_names,
      "family_name": family_name,
      "date_of_birth": fhir_patient.birthDate,
      "sex_at_birth": self._map_gender(fhir_patient.gender),
      "gender_identity": None,
      "race": None,  # Would need US Core Race extension
      "ethnicity": None,  # Would need US Core Ethnicity extension
      "preferred_language": self._extract_language(fhir_patient),
      "phone": phone,
      "email": email,
      "address": address,
      "emergency_contact": emergency_contact,
      "legal_guardian": legal_guardian,
    }

  def _extract_contact(self, contact: Any) -> dict:
    """Extract contact info from FHIR PatientContact."""
    name = None
    if contact.name:
      parts = []
      if contact.name.given:
        parts.extend(contact.name.given)
      if contact.name.family:
        parts.append(contact.name.family)
      name = " ".join(parts) if parts else None

    relationship = None
    if contact.relationship:
      for rel in contact.relationship:
        if rel.text:
          relationship = rel.text
          break
        if rel.coding and rel.coding[0].display:
          relationship = rel.coding[0].display
          break

    phone = None
    email = None
    if contact.telecom:
      for tc in contact.telecom:
        if tc.system == "phone" and not phone:
          phone = tc.value
        elif tc.system == "email" and not email:
          email = tc.value

    return {
      "name": name,
      "relationship": relationship,
      "phone": phone,
      "email": email,
    }

  def _map_gender(self, fhir_gender: str | None) -> str | None:
    """Map FHIR gender to Mneme sex_at_birth."""
    mapping = {
      "male": "male",
      "female": "female",
      "other": "other",
      "unknown": None,
    }
    return mapping.get(fhir_gender) if fhir_gender else None

  def _extract_language(self, fhir_patient: FHIRPatient) -> str:
    """Extract preferred language from Patient."""
    if fhir_patient.communication:
      for comm in fhir_patient.communication:
        if comm.preferred and comm.language:
          if comm.language.text:
            return comm.language.text
          if comm.language.coding and comm.language.coding[0].display:
            return comm.language.coding[0].display
    return "English"

  # ─────────────────────────────────────────────────────────────────────────────
  # Condition Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_conditions(self) -> list[dict]:
    """Extract Condition resources for patient."""
    conditions = []
    for ref, resource in self._resource_map.items():
      if not isinstance(resource, FHIRCondition):
        continue
      if not self._references_patient(resource.subject):
        continue

      code_system = None
      code_value = None
      display = "Unknown"
      if resource.code and resource.code.coding:
        coding = resource.code.coding[0]
        code_system = normalize_code_system(coding.system)
        code_value = coding.code
        display = coding.display or resource.code.text or display

      conditions.append({
        "external_id": resource.id,
        "code_system": code_system,
        "code": code_value,
        "display_name": display,
        "clinical_status": self._extract_codeable_code(resource.clinicalStatus) or "active",
        "verification_status": self._extract_codeable_code(resource.verificationStatus) or "confirmed",
        "severity": self._extract_codeable_code(resource.severity),
        "onset_date": self._extract_date(getattr(resource, "onsetDateTime", None)),
        "abatement_date": self._extract_date(getattr(resource, "abatementDateTime", None)),
        "notes": None,
      })

    return conditions

  # ─────────────────────────────────────────────────────────────────────────────
  # Medication Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_medications(self) -> list[dict]:
    """Extract MedicationStatement/MedicationRequest resources."""
    medications = []

    for ref, resource in self._resource_map.items():
      if isinstance(resource, MedicationStatement):
        if self._references_patient(resource.subject):
          medications.append(self._med_statement_to_dict(resource))
      elif isinstance(resource, MedicationRequest):
        if self._references_patient(resource.subject):
          medications.append(self._med_request_to_dict(resource))

    return medications

  def _med_statement_to_dict(self, med: MedicationStatement) -> dict:
    """Convert MedicationStatement to Mneme format."""
    code_system = None
    code_value = None
    display = "Unknown"

    # Extract medication code from CodeableReference
    if med.medication:
      if hasattr(med.medication, "concept") and med.medication.concept:
        concept = med.medication.concept
        if concept.coding:
          coding = concept.coding[0]
          code_system = normalize_code_system(coding.system)
          code_value = coding.code
          display = coding.display or concept.text or display
        elif concept.text:
          display = concept.text

    # Extract dosage info
    dose_quantity = None
    dose_unit = None
    frequency = None
    route = "oral"
    instructions = None

    if med.dosage:
      dosage = med.dosage[0]
      if dosage.doseAndRate and dosage.doseAndRate[0].doseQuantity:
        dq = dosage.doseAndRate[0].doseQuantity
        dose_quantity = str(dq.value) if dq.value else None
        dose_unit = dq.unit
      if dosage.timing and dosage.timing.code:
        frequency = self._extract_codeable_display(dosage.timing.code)
      if dosage.route:
        route = self._extract_codeable_code(dosage.route) or "oral"
      if dosage.text:
        instructions = dosage.text

    # Extract dates
    start_date = None
    if hasattr(med, "effectiveDateTime") and med.effectiveDateTime:
      start_date = self._extract_date(med.effectiveDateTime)
    elif hasattr(med, "effectivePeriod") and med.effectivePeriod:
      start_date = self._extract_date(med.effectivePeriod.start)

    return {
      "external_id": med.id,
      "code_system": code_system,
      "code": code_value,
      "display_name": display,
      "status": med.status or "active",
      "dose_quantity": dose_quantity,
      "dose_unit": dose_unit,
      "frequency": frequency,
      "route": route,
      "instructions": instructions,
      "prn": False,
      "start_date": start_date,
      "end_date": None,
      "prescriber": None,
      "indication": None,
    }

  def _med_request_to_dict(self, med: MedicationRequest) -> dict:
    """Convert MedicationRequest to Mneme format."""
    code_system = None
    code_value = None
    display = "Unknown"

    # Extract medication code
    if med.medication:
      if hasattr(med.medication, "concept") and med.medication.concept:
        concept = med.medication.concept
        if concept.coding:
          coding = concept.coding[0]
          code_system = normalize_code_system(coding.system)
          code_value = coding.code
          display = coding.display or concept.text or display
        elif concept.text:
          display = concept.text

    # Extract dosage
    prn = False
    if med.dosageInstruction:
      di = med.dosageInstruction[0]
      if hasattr(di, "asNeeded") and di.asNeeded:
        prn = True

    return {
      "external_id": med.id,
      "code_system": code_system,
      "code": code_value,
      "display_name": display,
      "status": med.status or "active",
      "dose_quantity": None,
      "dose_unit": None,
      "frequency": None,
      "route": "oral",
      "instructions": None,
      "prn": prn,
      "start_date": None,
      "end_date": None,
      "prescriber": None,
      "indication": None,
    }

  # ─────────────────────────────────────────────────────────────────────────────
  # Allergy Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_allergies(self) -> list[dict]:
    """Extract AllergyIntolerance resources."""
    allergies = []

    for ref, resource in self._resource_map.items():
      if not isinstance(resource, AllergyIntolerance):
        continue
      if not self._references_patient(resource.patient):
        continue

      display = "Unknown"
      if resource.code and resource.code.coding:
        display = resource.code.coding[0].display or resource.code.text or display
      elif resource.code and resource.code.text:
        display = resource.code.text

      # Extract reactions
      reactions = None
      if resource.reaction:
        reactions = []
        for r in resource.reaction:
          manifestation = None
          if r.manifestation:
            for m in r.manifestation:
              if hasattr(m, "concept") and m.concept:
                manifestation = m.concept.text or (
                  m.concept.coding[0].display if m.concept.coding else None
                )
                break
          reactions.append({
            "manifestation": manifestation,
            "severity": r.severity,
          })

      allergies.append({
        "external_id": resource.id,
        "display_name": display,
        "category": resource.category[0] if resource.category else None,
        "criticality": resource.criticality or "low",
        "reactions": reactions,
        "clinical_status": self._extract_codeable_code(resource.clinicalStatus) or "active",
        "onset_date": self._extract_date(getattr(resource, "onsetDateTime", None)),
        "notes": None,
      })

    return allergies

  # ─────────────────────────────────────────────────────────────────────────────
  # Encounter Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_encounters(self) -> list[dict]:
    """Extract Encounter resources."""
    encounters = []

    for ref, resource in self._resource_map.items():
      if not isinstance(resource, FHIREncounter):
        continue
      if not self._references_patient(resource.subject):
        continue

      # Extract encounter type
      encounter_type = None
      if resource.type:
        encounter_type = self._extract_codeable_display(resource.type[0])

      # Extract dates from actualPeriod
      enc_date = None
      end_date = None
      if resource.actualPeriod:
        enc_date = resource.actualPeriod.start
        end_date = resource.actualPeriod.end

      # Extract chief complaint from reason
      chief_complaint = None
      if resource.reason:
        for reason in resource.reason:
          if reason.value:
            for val in reason.value:
              if hasattr(val, "concept") and val.concept:
                chief_complaint = self._extract_codeable_display(val.concept)
                break
          if chief_complaint:
            break

      encounters.append({
        "external_id": resource.id,
        "encounter_type": encounter_type,
        "status": resource.status or "finished",
        "encounter_class": self._extract_encounter_class(resource),
        "date": enc_date,
        "end_date": end_date,
        "chief_complaint": chief_complaint,
        "provider_name": None,  # Would need participant lookup
        "location_name": None,  # Would need location lookup
        "vital_signs": None,
        "hpi": None,
        "physical_exam": None,
        "assessment": None,
        "plan": None,
        "narrative_note": resource.text.div if resource.text else None,
        "billing_codes": None,
      })

    return encounters

  def _extract_encounter_class(self, encounter: FHIREncounter) -> str:
    """Extract encounter class from FHIR Encounter."""
    if encounter.class_:
      for cls in encounter.class_:
        if hasattr(cls, "coding") and cls.coding:
          code = cls.coding[0].code
          # Map FHIR encounter class codes to Mneme
          mapping = {
            "AMB": "ambulatory",
            "EMER": "emergency",
            "IMP": "inpatient",
            "VR": "virtual",
            "HH": "home",
          }
          return mapping.get(code, code)
    return "ambulatory"

  # ─────────────────────────────────────────────────────────────────────────────
  # Observation Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_observations(self) -> list[dict]:
    """Extract Observation resources."""
    observations = []

    for ref, resource in self._resource_map.items():
      if not isinstance(resource, FHIRObservation):
        continue
      if not self._references_patient(resource.subject):
        continue

      code_system = None
      code_value = None
      display = "Unknown"
      if resource.code and resource.code.coding:
        coding = resource.code.coding[0]
        code_system = normalize_code_system(coding.system)
        code_value = coding.code
        display = coding.display or resource.code.text or display

      # Determine category
      category = "laboratory"
      if resource.category:
        cat_code = self._extract_codeable_code(resource.category[0])
        if cat_code:
          category = cat_code

      # Extract value
      value_quantity = None
      value_string = None
      value_unit = None
      if resource.valueQuantity:
        value_quantity = float(resource.valueQuantity.value) if resource.valueQuantity.value else None
        value_unit = resource.valueQuantity.unit
      elif resource.valueString:
        value_string = resource.valueString
      elif resource.valueCodeableConcept:
        value_string = self._extract_codeable_display(resource.valueCodeableConcept)

      # Reference range
      ref_range = None
      if resource.referenceRange:
        rr = resource.referenceRange[0]
        ref_range = {
          "low": float(rr.low.value) if rr.low and rr.low.value else None,
          "high": float(rr.high.value) if rr.high and rr.high.value else None,
          "text": rr.text,
        }

      # Get encounter reference for later mapping
      enc_ref = None
      if resource.encounter and resource.encounter.reference:
        enc_ref = resource.encounter.reference

      observations.append({
        "external_id": resource.id,
        "_temp_encounter_ref": enc_ref,  # Will be resolved during insert
        "category": category,
        "code_system": code_system,
        "code": code_value,
        "display_name": display,
        "value_quantity": value_quantity,
        "value_string": value_string,
        "value_unit": value_unit,
        "interpretation": self._extract_codeable_code(resource.interpretation[0]) if resource.interpretation else None,
        "reference_range": ref_range,
        "effective_date": resource.effectiveDateTime,
        "performer": None,
        "notes": None,
      })

    return observations

  # ─────────────────────────────────────────────────────────────────────────────
  # Immunization Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_immunizations(self) -> list[dict]:
    """Extract Immunization resources."""
    immunizations = []

    for ref, resource in self._resource_map.items():
      if not isinstance(resource, FHIRImmunization):
        continue
      if not self._references_patient(resource.patient):
        continue

      vaccine_code = None
      display = "Unknown"
      if resource.vaccineCode and resource.vaccineCode.coding:
        coding = resource.vaccineCode.coding[0]
        vaccine_code = coding.code
        display = coding.display or resource.vaccineCode.text or display
      elif resource.vaccineCode and resource.vaccineCode.text:
        display = resource.vaccineCode.text

      immunizations.append({
        "external_id": resource.id,
        "vaccine_code": vaccine_code,
        "display_name": display,
        "status": resource.status or "completed",
        "date": self._extract_date(resource.occurrenceDateTime),
        "dose_number": None,  # Would need protocolApplied
        "series_doses": None,
        "site": self._extract_codeable_display(resource.site) if resource.site else None,
        "lot_number": resource.lotNumber,
        "performer": None,
        "notes": None,
      })

    return immunizations

  # ─────────────────────────────────────────────────────────────────────────────
  # Message Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_messages(self) -> list[dict]:
    """Extract Communication resources as messages."""
    messages = []

    for ref, resource in self._resource_map.items():
      if not isinstance(resource, Communication):
        continue
      if not self._references_patient(resource.subject):
        continue

      # Extract message body from payload
      message_body = ""
      if resource.payload:
        for payload in resource.payload:
          if hasattr(payload, "contentString") and payload.contentString:
            message_body = payload.contentString
            break

      messages.append({
        "external_id": resource.id,
        "sent_datetime": resource.sent,
        "reply_datetime": resource.received,
        "sender_name": "Unknown",  # Would need sender lookup
        "sender_is_patient": True,
        "recipient_name": None,
        "replier_name": None,
        "replier_role": None,
        "category": self._extract_codeable_code(resource.category[0]) if resource.category else None,
        "medium": "portal",
        "subject": resource.topic.text if resource.topic else None,
        "message_body": message_body,
        "reply_body": None,
        "is_read": False,
      })

    return messages

  # ─────────────────────────────────────────────────────────────────────────────
  # Helper Methods
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_codeable_code(self, codeable: Any) -> str | None:
    """Extract code from CodeableConcept."""
    if not codeable:
      return None
    if hasattr(codeable, "coding") and codeable.coding:
      return codeable.coding[0].code
    return None

  def _extract_codeable_display(self, codeable: Any) -> str | None:
    """Extract display text from CodeableConcept."""
    if not codeable:
      return None
    if hasattr(codeable, "text") and codeable.text:
      return codeable.text
    if hasattr(codeable, "coding") and codeable.coding:
      return codeable.coding[0].display
    return None

  def _extract_date(self, dt: Any) -> date | None:
    """Extract date from datetime or string."""
    if not dt:
      return None
    if isinstance(dt, datetime):
      return dt.date()
    if isinstance(dt, date):
      return dt
    if isinstance(dt, str):
      try:
        return date.fromisoformat(dt[:10])
      except (ValueError, TypeError):
        return None
    return None
