"""Echo AI Tutor Client for Mneme EMR.

This module provides a client for interacting with the Echo tutoring service,
which provides Socratic feedback, questions, and debriefs for medical education.
"""

import httpx
from typing import Any
from pydantic import BaseModel
from src.config import get_settings


# --- Request/Response Models ---

class PatientContext(BaseModel):
    """Patient context for Echo requests."""
    patient_id: str
    source: str = "mneme"
    name: str
    age_years: int | None = None
    age_months: int | None = None
    sex: str | None = None
    problem_list: list[dict] = []
    medication_list: list[dict] = []
    allergy_list: list[dict] = []
    recent_encounters: list[dict] = []
    family_history: str | None = None
    social_history: str | None = None


class EncounterContext(BaseModel):
    """Encounter context for Echo debrief requests."""
    patient: PatientContext
    encounter_type: str
    chief_complaint: str
    phase: str
    history_gathered: list[str] = []
    exam_findings: list[str] = []
    differential: list[str] = []
    orders_placed: list[str] = []
    known_errors: list[str] = []


class FeedbackRequest(BaseModel):
    """Request for Echo feedback on a learner action."""
    patient: PatientContext
    learner_action: str
    action_type: str  # question, exam_finding, diagnosis, medication_order, lab_order, etc.
    learner_level: str = "student"
    context: str | None = None
    voice_response: bool = False


class FeedbackResponse(BaseModel):
    """Response from Echo feedback endpoint."""
    feedback: str
    feedback_type: str  # praise, correction, question, suggestion
    clinical_issue: str | None = None
    follow_up_question: str | None = None
    audio_url: str | None = None


class QuestionRequest(BaseModel):
    """Request for Echo to answer a learner's question."""
    patient: PatientContext | None = None
    encounter: EncounterContext | None = None
    learner_question: str
    topic: str | None = None
    learner_level: str = "student"
    voice_response: bool = False


class QuestionResponse(BaseModel):
    """Response from Echo question endpoint."""
    question: str  # Echo's Socratic response (could be a question, guidance, or reframe)
    hint: str | None = None
    topic: str
    audio_url: str | None = None


class DebriefRequest(BaseModel):
    """Request for Echo to provide encounter debrief."""
    patient: PatientContext
    encounter: EncounterContext
    learner_level: str = "student"
    focus_areas: list[str] = []
    voice_response: bool = False


class DebriefResponse(BaseModel):
    """Response from Echo debrief endpoint."""
    summary: str
    strengths: list[str] = []
    areas_for_improvement: list[str] = []
    missed_items: list[str] = []
    teaching_points: list[str] = []
    follow_up_resources: list[str] = []
    audio_url: str | None = None


class EchoClient:
    """Client for interacting with the Echo AI Tutor service."""

    def __init__(self, base_url: str | None = None, timeout: float = 30.0):
        """
        Initialize the Echo client.

        Args:
            base_url: Echo service URL. Defaults to http://localhost:8001
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or "http://localhost:8001"
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def health_check(self) -> bool:
        """Check if Echo service is available."""
        try:
            response = await self._client.get("/health")
            return response.status_code == 200
        except Exception:
            return False

    async def get_feedback(self, request: FeedbackRequest) -> FeedbackResponse | None:
        """
        Get feedback on a learner action.

        Args:
            request: FeedbackRequest with patient context and learner action

        Returns:
            FeedbackResponse with feedback and optional follow-up question
        """
        try:
            response = await self._client.post(
                "/feedback",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return FeedbackResponse(**response.json())
        except httpx.HTTPStatusError as e:
            print(f"Echo feedback error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"Echo feedback connection error: {e}")
            return None

    async def ask_question(self, request: QuestionRequest) -> QuestionResponse | None:
        """
        Get Echo's response to a learner's question.

        Args:
            request: QuestionRequest with learner's question and context

        Returns:
            QuestionResponse with Socratic response
        """
        try:
            response = await self._client.post(
                "/question",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return QuestionResponse(**response.json())
        except httpx.HTTPStatusError as e:
            print(f"Echo question error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"Echo question connection error: {e}")
            return None

    async def get_debrief(self, request: DebriefRequest) -> DebriefResponse | None:
        """
        Get a comprehensive debrief after an encounter.

        Args:
            request: DebriefRequest with patient and encounter context

        Returns:
            DebriefResponse with analysis and teaching points
        """
        try:
            response = await self._client.post(
                "/debrief",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return DebriefResponse(**response.json())
        except httpx.HTTPStatusError as e:
            print(f"Echo debrief error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"Echo debrief connection error: {e}")
            return None


# --- Helper Functions ---

def build_patient_context(
    patient_id: str,
    patient_data: dict,
    conditions: list[dict] | None = None,
    medications: list[dict] | None = None,
    allergies: list[dict] | None = None,
    encounters: list[dict] | None = None,
) -> PatientContext:
    """
    Build PatientContext from Mneme patient data.

    Args:
        patient_id: Patient UUID
        patient_data: Patient record from database
        conditions: List of active conditions
        medications: List of current medications
        allergies: List of allergies
        encounters: List of recent encounters

    Returns:
        PatientContext ready for Echo requests
    """
    # Calculate age
    from datetime import date
    dob = patient_data.get("date_of_birth")
    age_years = None
    age_months = None

    if dob:
        if isinstance(dob, str):
            dob = date.fromisoformat(dob)
        today = date.today()
        age_years = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            age_years -= 1
        # For infants, calculate months
        if age_years < 2:
            age_months = (today.year - dob.year) * 12 + (today.month - dob.month)
            if today.day < dob.day:
                age_months -= 1

    # Build name
    given_names = patient_data.get("given_names", [])
    family_name = patient_data.get("family_name", "")
    name = f"{' '.join(given_names)} {family_name}".strip()

    # Build problem list
    problem_list = []
    for c in (conditions or []):
        if c.get("clinical_status") == "active":
            problem_list.append({
                "display_name": c.get("display_name", ""),
                "code": c.get("code"),
                "code_system": c.get("code_system"),
                "is_active": True,
            })

    # Build medication list
    medication_list = []
    for m in (medications or []):
        if m.get("status") == "active":
            medication_list.append({
                "display_name": m.get("display_name", ""),
                "dose": m.get("dose_quantity"),
                "frequency": m.get("frequency"),
                "code": m.get("code"),
                "is_active": True,
            })

    # Build allergy list
    allergy_list = []
    for a in (allergies or []):
        reactions = a.get("reactions", [])
        reaction_str = reactions[0].get("manifestation") if reactions else None
        allergy_list.append({
            "display_name": a.get("display_name", ""),
            "reaction": reaction_str,
            "severity": a.get("criticality"),
        })

    # Build recent encounters summary
    recent_encounters = []
    for e in (encounters or [])[:5]:  # Limit to 5 most recent
        recent_encounters.append({
            "date": e.get("date"),
            "type": e.get("encounter_type"),
            "chief_complaint": e.get("chief_complaint"),
        })

    return PatientContext(
        patient_id=patient_id,
        source="mneme",
        name=name,
        age_years=age_years,
        age_months=age_months,
        sex=patient_data.get("sex_at_birth"),
        problem_list=problem_list,
        medication_list=medication_list,
        allergy_list=allergy_list,
        recent_encounters=recent_encounters,
    )


def build_encounter_context(
    patient_context: PatientContext,
    session_data: dict,
) -> EncounterContext:
    """
    Build EncounterContext from learning session data.

    Args:
        patient_context: Patient context
        session_data: Learning session data

    Returns:
        EncounterContext ready for Echo requests
    """
    # Extract history gathered from revealed data
    revealed = session_data.get("revealed_data", {})
    history_gathered = []
    for item in revealed.get("hpi_elements", []):
        if isinstance(item, dict):
            history_gathered.append(item.get("content", str(item)))
        else:
            history_gathered.append(str(item))

    # Extract exam findings
    exam_findings = []
    for item in revealed.get("exam_findings", []):
        if isinstance(item, dict):
            exam_findings.append(item.get("finding", str(item)))
        else:
            exam_findings.append(str(item))

    # Extract differential
    differential = []
    for d in session_data.get("differential", []):
        differential.append(d.get("diagnosis", str(d)))

    # Extract orders placed
    orders_placed = []
    for o in session_data.get("orders_placed", []):
        orders_placed.append(o.get("item", str(o)))

    return EncounterContext(
        patient=patient_context,
        encounter_type=session_data.get("encounter_type", "acute"),
        chief_complaint=session_data.get("chief_complaint", ""),
        phase=session_data.get("current_phase", "chief_complaint"),
        history_gathered=history_gathered,
        exam_findings=exam_findings,
        differential=differential,
        orders_placed=orders_placed,
    )


# --- Singleton Instance ---

_echo_client: EchoClient | None = None


def get_echo_client() -> EchoClient:
    """Get or create the Echo client singleton."""
    global _echo_client
    if _echo_client is None:
        settings = get_settings()
        echo_url = getattr(settings, "echo_url", "http://localhost:8001")
        _echo_client = EchoClient(base_url=echo_url)
    return _echo_client
