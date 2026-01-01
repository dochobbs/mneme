"""C-CDA (Consolidated Clinical Document Architecture) Importer for Mneme EMR.

Parses C-CDA 2.1 XML documents and extracts clinical data into Mneme format.
Supports the standard CCD (Continuity of Care Document) sections.

Supported Sections:
- Problems (2.16.840.1.113883.10.20.22.2.5.1) → conditions
- Medications (2.16.840.1.113883.10.20.22.2.1.1) → medications
- Allergies (2.16.840.1.113883.10.20.22.2.6.1) → allergies
- Immunizations (2.16.840.1.113883.10.20.22.2.2.1) → immunizations
- Encounters (2.16.840.1.113883.10.20.22.2.22.1) → encounters
- Vital Signs (2.16.840.1.113883.10.20.22.2.4.1) → observations
- Results (2.16.840.1.113883.10.20.22.2.3.1) → observations
"""

from datetime import date, datetime
from typing import Any
from lxml import etree

from src.db.supabase import SupabaseDB
from src.importers.base import BaseImporter, ExtractedPatient, ImportResult
from src.importers.validation.codes import normalize_code_system


# C-CDA namespaces
NAMESPACES = {
  "hl7": "urn:hl7-org:v3",
  "xsi": "http://www.w3.org/2001/XMLSchema-instance",
  "sdtc": "urn:hl7-org:sdtc",
}

# Section Template OIDs
SECTION_OIDS = {
  "problems": "2.16.840.1.113883.10.20.22.2.5.1",
  "medications": "2.16.840.1.113883.10.20.22.2.1.1",
  "allergies": "2.16.840.1.113883.10.20.22.2.6.1",
  "immunizations": "2.16.840.1.113883.10.20.22.2.2.1",
  "encounters": "2.16.840.1.113883.10.20.22.2.22.1",
  "vital_signs": "2.16.840.1.113883.10.20.22.2.4.1",
  "results": "2.16.840.1.113883.10.20.22.2.3.1",
  "procedures": "2.16.840.1.113883.10.20.22.2.7.1",
  "social_history": "2.16.840.1.113883.10.20.22.2.17",
}

# Code System OID to short name mapping
CODE_SYSTEM_MAP = {
  "2.16.840.1.113883.6.96": "snomed",
  "2.16.840.1.113883.6.90": "icd10",
  "2.16.840.1.113883.6.3": "icd10",
  "2.16.840.1.113883.6.88": "rxnorm",
  "2.16.840.1.113883.6.1": "loinc",
}


class CCDAImporter(BaseImporter):
  """Import C-CDA 2.1 documents into Mneme EMR."""

  def __init__(self, db: SupabaseDB | None = None):
    super().__init__(db)
    self._root: etree._Element | None = None

  @property
  def format_name(self) -> str:
    return "ccda"

  def import_ccda(self, xml_content: str | bytes, source_file: str = "unknown") -> ImportResult:
    """
    Import a C-CDA XML document.

    Args:
      xml_content: C-CDA XML as string or bytes
      source_file: Name of source file for tracking

    Returns:
      ImportResult with success status, patient_id, counts, warnings/errors
    """
    # Parse XML
    try:
      if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")
      self._root = etree.fromstring(xml_content)
    except etree.XMLSyntaxError as e:
      return ImportResult(
        success=False,
        source_file=source_file,
        format=self.format_name,
        errors=[f"Invalid XML: {e}"],
      )

    # Use base class import_patient
    return self.import_patient(self._root, source_file)

  def extract_patient(self, root: etree._Element) -> ExtractedPatient:
    """Extract all data from C-CDA document."""
    self._root = root

    return ExtractedPatient(
      patient=self._extract_patient(),
      conditions=self._extract_problems(),
      medications=self._extract_medications(),
      allergies=self._extract_allergies(),
      encounters=self._extract_encounters(),
      observations=self._extract_observations(),
      immunizations=self._extract_immunizations(),
      messages=[],  # C-CDA doesn't have messages
      growth_data=[],  # Could extract from vital signs if needed
    )

  # ─────────────────────────────────────────────────────────────────────────────
  # Helper Methods
  # ─────────────────────────────────────────────────────────────────────────────

  def _find_section(self, template_oid: str) -> etree._Element | None:
    """Find a section by its template OID."""
    xpath = f".//hl7:section[hl7:templateId[@root='{template_oid}']]"
    sections = self._root.xpath(xpath, namespaces=NAMESPACES)
    return sections[0] if sections else None

  def _get_text(self, element: etree._Element, xpath: str) -> str | None:
    """Get text content from an element using xpath."""
    if element is None:
      return None
    results = element.xpath(xpath, namespaces=NAMESPACES)
    if results:
      if isinstance(results[0], str):
        return results[0].strip() if results[0].strip() else None
      if hasattr(results[0], "text"):
        return results[0].text.strip() if results[0].text else None
    return None

  def _get_attr(self, element: etree._Element, xpath: str, attr: str) -> str | None:
    """Get attribute value from an element using xpath."""
    if element is None:
      return None
    results = element.xpath(xpath, namespaces=NAMESPACES)
    if results and hasattr(results[0], "get"):
      return results[0].get(attr)
    return None

  def _parse_date(self, value: str | None) -> date | None:
    """Parse C-CDA date format (YYYYMMDD or YYYYMMDDHHMMSS)."""
    if not value:
      return None
    try:
      # Handle YYYYMMDD format
      if len(value) >= 8:
        return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except (ValueError, TypeError):
      pass
    return None

  def _parse_datetime(self, value: str | None) -> datetime | None:
    """Parse C-CDA datetime format."""
    if not value:
      return None
    try:
      if len(value) >= 14:
        return datetime(
          int(value[:4]), int(value[4:6]), int(value[6:8]),
          int(value[8:10]), int(value[10:12]), int(value[12:14])
        )
      elif len(value) >= 8:
        return datetime(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except (ValueError, TypeError):
      pass
    return None

  def _extract_code(self, element: etree._Element, xpath: str = ".") -> dict:
    """Extract code, codeSystem, and displayName from a coded element."""
    code_elem = element.xpath(xpath, namespaces=NAMESPACES)
    if not code_elem:
      return {"code": None, "code_system": None, "display": None}

    elem = code_elem[0]
    code_system_oid = elem.get("codeSystem")
    code_system = CODE_SYSTEM_MAP.get(code_system_oid, code_system_oid)

    return {
      "code": elem.get("code"),
      "code_system": code_system,
      "display": elem.get("displayName"),
    }

  # ─────────────────────────────────────────────────────────────────────────────
  # Patient Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_patient(self) -> dict:
    """Extract patient demographics from recordTarget."""
    patient_role = self._root.xpath(
      ".//hl7:recordTarget/hl7:patientRole",
      namespaces=NAMESPACES
    )
    if not patient_role:
      return {
        "given_names": ["Unknown"],
        "family_name": "Unknown",
        "date_of_birth": None,
      }

    pr = patient_role[0]
    patient = pr.xpath("hl7:patient", namespaces=NAMESPACES)
    patient = patient[0] if patient else None

    # Extract names
    given_names = ["Unknown"]
    family_name = "Unknown"
    if patient is not None:
      given = patient.xpath("hl7:name/hl7:given/text()", namespaces=NAMESPACES)
      family = patient.xpath("hl7:name/hl7:family/text()", namespaces=NAMESPACES)
      if given:
        given_names = [g.strip() for g in given if g.strip()]
      if family:
        family_name = family[0].strip()

    # Extract DOB
    dob = None
    if patient is not None:
      dob_value = self._get_attr(patient, "hl7:birthTime", "value")
      dob = self._parse_date(dob_value)

    # Extract gender
    gender = None
    if patient is not None:
      gender_code = self._get_attr(patient, "hl7:administrativeGenderCode", "code")
      gender_map = {"M": "male", "F": "female", "UN": "unknown"}
      gender = gender_map.get(gender_code)

    # Extract address
    address = None
    addr_elem = pr.xpath("hl7:addr", namespaces=NAMESPACES)
    if addr_elem:
      addr = addr_elem[0]
      street = addr.xpath("hl7:streetAddressLine/text()", namespaces=NAMESPACES)
      city = addr.xpath("hl7:city/text()", namespaces=NAMESPACES)
      state = addr.xpath("hl7:state/text()", namespaces=NAMESPACES)
      postal = addr.xpath("hl7:postalCode/text()", namespaces=NAMESPACES)
      country = addr.xpath("hl7:country/text()", namespaces=NAMESPACES)
      address = {
        "line1": street[0] if street else None,
        "line2": street[1] if len(street) > 1 else None,
        "city": city[0] if city else None,
        "state": state[0] if state else None,
        "postal_code": postal[0] if postal else None,
        "country": country[0] if country else "US",
      }

    # Extract phone
    phone = None
    telecom = pr.xpath("hl7:telecom[@use='HP']/@value", namespaces=NAMESPACES)
    if telecom:
      phone = telecom[0].replace("tel:", "")

    # Extract email
    email = None
    email_elem = pr.xpath("hl7:telecom[starts-with(@value,'mailto:')]/@value", namespaces=NAMESPACES)
    if email_elem:
      email = email_elem[0].replace("mailto:", "")

    # Extract race (from sdtc extension)
    race = None
    if patient is not None:
      race_codes = patient.xpath("sdtc:raceCode/@displayName", namespaces=NAMESPACES)
      if race_codes:
        race = list(race_codes)

    # Extract ethnicity
    ethnicity = None
    if patient is not None:
      eth = patient.xpath("sdtc:ethnicGroupCode/@displayName", namespaces=NAMESPACES)
      if eth:
        ethnicity = eth[0]

    # Extract preferred language
    language = "English"
    if patient is not None:
      lang = patient.xpath("hl7:languageCommunication/hl7:languageCode/@code", namespaces=NAMESPACES)
      if lang:
        lang_map = {"en": "English", "es": "Spanish", "zh": "Chinese", "vi": "Vietnamese"}
        language = lang_map.get(lang[0][:2], lang[0])

    # Extract ID for external reference
    external_id = None
    ids = pr.xpath("hl7:id/@root", namespaces=NAMESPACES)
    if ids:
      external_id = ids[0]

    return {
      "external_id": external_id,
      "given_names": given_names or ["Unknown"],
      "family_name": family_name,
      "date_of_birth": dob,
      "sex_at_birth": gender,
      "gender_identity": None,
      "race": race,
      "ethnicity": ethnicity,
      "preferred_language": language,
      "phone": phone,
      "email": email,
      "address": address,
      "emergency_contact": None,  # C-CDA has this in participant but complex to extract
      "legal_guardian": None,
    }

  # ─────────────────────────────────────────────────────────────────────────────
  # Problems/Conditions Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_problems(self) -> list[dict]:
    """Extract problems from Problems section."""
    section = self._find_section(SECTION_OIDS["problems"])
    if section is None:
      return []

    problems = []
    # Find all problem concern acts
    entries = section.xpath(
      ".//hl7:entry/hl7:act[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.3']]",
      namespaces=NAMESPACES
    )

    for entry in entries:
      # Get the problem observation within the act
      obs = entry.xpath(
        ".//hl7:observation[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.4']]",
        namespaces=NAMESPACES
      )
      if not obs:
        continue

      obs = obs[0]

      # Extract code from value element
      code_info = self._extract_code(obs, "hl7:value")
      if not code_info["code"]:
        # Try code element as fallback
        code_info = self._extract_code(obs, "hl7:code")

      # Extract status
      status_code = self._get_attr(obs, "hl7:statusCode", "code")
      clinical_status = "active" if status_code == "active" else "resolved"

      # Extract effective time (onset)
      onset_date = None
      onset_value = self._get_attr(obs, "hl7:effectiveTime/hl7:low", "value")
      if onset_value:
        onset_date = self._parse_date(onset_value)

      # Extract abatement date if resolved
      abatement_date = None
      if clinical_status == "resolved":
        abate_value = self._get_attr(obs, "hl7:effectiveTime/hl7:high", "value")
        if abate_value:
          abatement_date = self._parse_date(abate_value)

      # Get ID
      external_id = self._get_attr(obs, "hl7:id", "root")

      problems.append({
        "external_id": external_id,
        "code_system": code_info["code_system"],
        "code": code_info["code"],
        "display_name": code_info["display"] or "Unknown",
        "clinical_status": clinical_status,
        "verification_status": "confirmed",
        "severity": None,
        "onset_date": onset_date,
        "abatement_date": abatement_date,
        "notes": None,
      })

    return problems

  # ─────────────────────────────────────────────────────────────────────────────
  # Medications Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_medications(self) -> list[dict]:
    """Extract medications from Medications section."""
    section = self._find_section(SECTION_OIDS["medications"])
    if section is None:
      return []

    medications = []
    # Find all medication activities
    entries = section.xpath(
      ".//hl7:entry/hl7:substanceAdministration[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.16']]",
      namespaces=NAMESPACES
    )

    for entry in entries:
      # Extract medication code
      code_info = self._extract_code(
        entry,
        ".//hl7:consumable/hl7:manufacturedProduct/hl7:manufacturedMaterial/hl7:code"
      )

      # Extract status
      status_code = self._get_attr(entry, "hl7:statusCode", "code")
      status = "active" if status_code in ("active", None) else status_code

      # Extract dates
      start_date = None
      end_date = None
      eff_low = self._get_attr(entry, "hl7:effectiveTime/hl7:low", "value")
      eff_high = self._get_attr(entry, "hl7:effectiveTime/hl7:high", "value")
      if eff_low:
        start_date = self._parse_date(eff_low)
      if eff_high:
        end_date = self._parse_date(eff_high)

      # Extract dose
      dose_quantity = None
      dose_unit = None
      dose_elem = entry.xpath("hl7:doseQuantity", namespaces=NAMESPACES)
      if dose_elem:
        dose_quantity = dose_elem[0].get("value")
        dose_unit = dose_elem[0].get("unit")

      # Extract route
      route = "oral"
      route_elem = entry.xpath("hl7:routeCode/@displayName", namespaces=NAMESPACES)
      if route_elem:
        route = route_elem[0].lower()

      # Extract frequency from effectiveTime with operator
      frequency = None
      freq_elem = entry.xpath("hl7:effectiveTime[@operator='A']/hl7:period", namespaces=NAMESPACES)
      if freq_elem:
        period_value = freq_elem[0].get("value")
        period_unit = freq_elem[0].get("unit")
        if period_value and period_unit:
          frequency = f"every {period_value} {period_unit}"

      # Get ID
      external_id = self._get_attr(entry, "hl7:id", "root")

      medications.append({
        "external_id": external_id,
        "code_system": code_info["code_system"],
        "code": code_info["code"],
        "display_name": code_info["display"] or "Unknown Medication",
        "status": status,
        "dose_quantity": dose_quantity,
        "dose_unit": dose_unit,
        "frequency": frequency,
        "route": route,
        "instructions": None,
        "prn": False,
        "start_date": start_date,
        "end_date": end_date,
        "prescriber": None,
        "indication": None,
      })

    return medications

  # ─────────────────────────────────────────────────────────────────────────────
  # Allergies Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_allergies(self) -> list[dict]:
    """Extract allergies from Allergies section."""
    section = self._find_section(SECTION_OIDS["allergies"])
    if section is None:
      return []

    allergies = []
    # Find all allergy concern acts
    entries = section.xpath(
      ".//hl7:entry/hl7:act[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.30']]",
      namespaces=NAMESPACES
    )

    for entry in entries:
      # Get the allergy observation within the act
      obs = entry.xpath(
        ".//hl7:observation[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.7']]",
        namespaces=NAMESPACES
      )
      if not obs:
        continue

      obs = obs[0]

      # Extract allergen from participant
      display_name = "Unknown Allergen"
      participant = obs.xpath(
        ".//hl7:participant/hl7:participantRole/hl7:playingEntity/hl7:code",
        namespaces=NAMESPACES
      )
      if participant:
        display_name = participant[0].get("displayName") or display_name

      # Extract status
      status_code = self._get_attr(obs, "hl7:statusCode", "code")
      clinical_status = "active" if status_code == "active" else "inactive"

      # Extract reactions
      reactions = []
      reaction_obs = obs.xpath(
        ".//hl7:entryRelationship/hl7:observation[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.9']]",
        namespaces=NAMESPACES
      )
      for rxn in reaction_obs:
        rxn_code = rxn.xpath("hl7:value/@displayName", namespaces=NAMESPACES)
        severity = rxn.xpath(
          ".//hl7:observation[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.8']]/hl7:value/@displayName",
          namespaces=NAMESPACES
        )
        reactions.append({
          "manifestation": rxn_code[0] if rxn_code else None,
          "severity": severity[0].lower() if severity else None,
        })

      # Determine criticality from severity
      criticality = "low"
      if reactions:
        severities = [r.get("severity", "").lower() for r in reactions]
        if any(s in ("severe", "life-threatening") for s in severities):
          criticality = "high"

      # Extract category
      category = None
      value_code = obs.xpath("hl7:value/@code", namespaces=NAMESPACES)
      if value_code:
        # Map SNOMED allergy types to categories
        cat_map = {
          "416098002": "medication",  # Drug allergy
          "414285001": "food",         # Food allergy
          "419199007": "environment",  # Allergy to substance
        }
        category = cat_map.get(value_code[0])

      # Get ID
      external_id = self._get_attr(obs, "hl7:id", "root")

      allergies.append({
        "external_id": external_id,
        "display_name": display_name,
        "category": category,
        "criticality": criticality,
        "reactions": reactions if reactions else None,
        "clinical_status": clinical_status,
        "onset_date": None,
        "notes": None,
      })

    return allergies

  # ─────────────────────────────────────────────────────────────────────────────
  # Encounters Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_encounters(self) -> list[dict]:
    """Extract encounters from Encounters section."""
    section = self._find_section(SECTION_OIDS["encounters"])
    if section is None:
      return []

    encounters = []
    # Find all encounter activities
    entries = section.xpath(
      ".//hl7:entry/hl7:encounter[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.49']]",
      namespaces=NAMESPACES
    )

    for entry in entries:
      # Extract encounter type
      code_info = self._extract_code(entry, "hl7:code")
      encounter_type = code_info["display"]

      # Extract dates
      enc_date = None
      end_date = None
      eff_low = self._get_attr(entry, "hl7:effectiveTime/hl7:low", "value")
      eff_high = self._get_attr(entry, "hl7:effectiveTime/hl7:high", "value")
      eff_value = self._get_attr(entry, "hl7:effectiveTime", "value")

      if eff_low:
        enc_date = self._parse_datetime(eff_low)
      elif eff_value:
        enc_date = self._parse_datetime(eff_value)
      if eff_high:
        end_date = self._parse_datetime(eff_high)

      # Extract performer (provider)
      provider_name = None
      performer = entry.xpath(
        ".//hl7:performer/hl7:assignedEntity/hl7:assignedPerson/hl7:name",
        namespaces=NAMESPACES
      )
      if performer:
        given = performer[0].xpath("hl7:given/text()", namespaces=NAMESPACES)
        family = performer[0].xpath("hl7:family/text()", namespaces=NAMESPACES)
        parts = []
        if given:
          parts.extend(given)
        if family:
          parts.append(family[0])
        provider_name = " ".join(parts) if parts else None

      # Get ID
      external_id = self._get_attr(entry, "hl7:id", "root")

      encounters.append({
        "external_id": external_id,
        "encounter_type": encounter_type,
        "status": "finished",
        "encounter_class": "ambulatory",
        "date": enc_date,
        "end_date": end_date,
        "chief_complaint": None,
        "provider_name": provider_name,
        "location_name": None,
        "vital_signs": None,
        "hpi": None,
        "physical_exam": None,
        "assessment": None,
        "plan": None,
        "narrative_note": None,
        "billing_codes": None,
      })

    return encounters

  # ─────────────────────────────────────────────────────────────────────────────
  # Observations Extraction (Vital Signs + Results)
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_observations(self) -> list[dict]:
    """Extract observations from Vital Signs and Results sections."""
    observations = []

    # Extract vital signs
    vs_section = self._find_section(SECTION_OIDS["vital_signs"])
    if vs_section is not None:
      observations.extend(self._extract_vitals_from_section(vs_section))

    # Extract lab results
    results_section = self._find_section(SECTION_OIDS["results"])
    if results_section is not None:
      observations.extend(self._extract_results_from_section(results_section))

    return observations

  def _extract_vitals_from_section(self, section: etree._Element) -> list[dict]:
    """Extract vital sign observations."""
    vitals = []

    # Find all organizers containing vitals
    organizers = section.xpath(
      ".//hl7:entry/hl7:organizer[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.26']]",
      namespaces=NAMESPACES
    )

    for org in organizers:
      # Get date from organizer
      eff_date = None
      eff_value = self._get_attr(org, "hl7:effectiveTime", "value")
      if eff_value:
        eff_date = self._parse_datetime(eff_value)

      # Extract each vital observation
      obs_list = org.xpath(
        ".//hl7:component/hl7:observation[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.27']]",
        namespaces=NAMESPACES
      )

      for obs in obs_list:
        code_info = self._extract_code(obs, "hl7:code")

        # Extract value
        value_quantity = None
        value_unit = None
        value_elem = obs.xpath("hl7:value", namespaces=NAMESPACES)
        if value_elem:
          value_quantity = value_elem[0].get("value")
          if value_quantity:
            try:
              value_quantity = float(value_quantity)
            except ValueError:
              pass
          value_unit = value_elem[0].get("unit")

        external_id = self._get_attr(obs, "hl7:id", "root")

        vitals.append({
          "external_id": external_id,
          "category": "vital-signs",
          "code_system": code_info["code_system"],
          "code": code_info["code"],
          "display_name": code_info["display"] or "Vital Sign",
          "value_quantity": value_quantity,
          "value_string": None,
          "value_unit": value_unit,
          "interpretation": None,
          "reference_range": None,
          "effective_date": eff_date,
          "performer": None,
          "notes": None,
        })

    return vitals

  def _extract_results_from_section(self, section: etree._Element) -> list[dict]:
    """Extract lab result observations."""
    results = []

    # Find all result organizers
    organizers = section.xpath(
      ".//hl7:entry/hl7:organizer[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.1']]",
      namespaces=NAMESPACES
    )

    for org in organizers:
      # Extract each result observation
      obs_list = org.xpath(
        ".//hl7:component/hl7:observation[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.2']]",
        namespaces=NAMESPACES
      )

      for obs in obs_list:
        code_info = self._extract_code(obs, "hl7:code")

        # Extract value
        value_quantity = None
        value_string = None
        value_unit = None
        value_elem = obs.xpath("hl7:value", namespaces=NAMESPACES)
        if value_elem:
          xsi_type = value_elem[0].get("{http://www.w3.org/2001/XMLSchema-instance}type")
          if xsi_type == "PQ":  # Physical Quantity
            value_quantity = value_elem[0].get("value")
            if value_quantity:
              try:
                value_quantity = float(value_quantity)
              except ValueError:
                pass
            value_unit = value_elem[0].get("unit")
          elif xsi_type == "ST":  # String
            value_string = value_elem[0].text
          elif xsi_type == "CD":  # Coded
            value_string = value_elem[0].get("displayName")

        # Extract interpretation
        interpretation = None
        interp_elem = obs.xpath("hl7:interpretationCode/@code", namespaces=NAMESPACES)
        if interp_elem:
          interp_map = {"N": "normal", "H": "high", "L": "low", "A": "abnormal"}
          interpretation = interp_map.get(interp_elem[0], interp_elem[0])

        # Extract reference range
        ref_range = None
        ref_elem = obs.xpath("hl7:referenceRange/hl7:observationRange/hl7:text/text()", namespaces=NAMESPACES)
        if ref_elem:
          ref_range = {"text": ref_elem[0]}

        # Extract date
        eff_date = None
        eff_value = self._get_attr(obs, "hl7:effectiveTime", "value")
        if eff_value:
          eff_date = self._parse_datetime(eff_value)

        external_id = self._get_attr(obs, "hl7:id", "root")

        results.append({
          "external_id": external_id,
          "category": "laboratory",
          "code_system": code_info["code_system"],
          "code": code_info["code"],
          "display_name": code_info["display"] or "Lab Result",
          "value_quantity": value_quantity,
          "value_string": value_string,
          "value_unit": value_unit,
          "interpretation": interpretation,
          "reference_range": ref_range,
          "effective_date": eff_date,
          "performer": None,
          "notes": None,
        })

    return results

  # ─────────────────────────────────────────────────────────────────────────────
  # Immunizations Extraction
  # ─────────────────────────────────────────────────────────────────────────────

  def _extract_immunizations(self) -> list[dict]:
    """Extract immunizations from Immunizations section."""
    section = self._find_section(SECTION_OIDS["immunizations"])
    if section is None:
      return []

    immunizations = []
    # Find all immunization activities
    entries = section.xpath(
      ".//hl7:entry/hl7:substanceAdministration[hl7:templateId[@root='2.16.840.1.113883.10.20.22.4.52']]",
      namespaces=NAMESPACES
    )

    for entry in entries:
      # Extract vaccine code
      code_info = self._extract_code(
        entry,
        ".//hl7:consumable/hl7:manufacturedProduct/hl7:manufacturedMaterial/hl7:code"
      )

      # Extract date
      imm_date = None
      eff_value = self._get_attr(entry, "hl7:effectiveTime", "value")
      if eff_value:
        imm_date = self._parse_date(eff_value)

      # Extract status
      status = "completed"
      neg_ind = entry.get("negationInd")
      if neg_ind == "true":
        status = "not-done"

      # Extract lot number
      lot_number = None
      lot_elem = entry.xpath(
        ".//hl7:consumable/hl7:manufacturedProduct/hl7:manufacturedMaterial/hl7:lotNumberText/text()",
        namespaces=NAMESPACES
      )
      if lot_elem:
        lot_number = lot_elem[0]

      # Get ID
      external_id = self._get_attr(entry, "hl7:id", "root")

      immunizations.append({
        "external_id": external_id,
        "vaccine_code": code_info["code"],
        "display_name": code_info["display"] or "Immunization",
        "status": status,
        "date": imm_date,
        "dose_number": None,
        "series_doses": None,
        "site": None,
        "lot_number": lot_number,
        "performer": None,
        "notes": None,
      })

    return immunizations
