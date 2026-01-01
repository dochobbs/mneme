"""Pydantic models for the Learning Visit system."""

from datetime import datetime
from typing import Literal, Any
from pydantic import BaseModel, Field
from uuid import UUID


# --- Action Types ---

ActionType = Literal[
    "question",         # Ask patient/parent a question
    "exam_request",     # Request a physical exam finding
    "lab_order",        # Order a lab test
    "imaging_order",    # Order imaging
    "add_differential", # Add diagnosis to differential
    "remove_differential",
    "rank_differential", # Reorder differential
    "make_diagnosis",   # Commit to final diagnosis
    "make_disposition", # Commit to disposition
    "ask_echo",         # Ask Echo for help
]

SessionStatus = Literal["active", "paused", "completed", "abandoned"]

Phase = Literal[
    "chief_complaint",
    "hpi",
    "ros",
    "exam",
    "assessment",
    "plan",
    "debrief",
]

LearnerLevel = Literal[
    "student",
    "resident",
    "np_student",
    "fellow",
    "attending",
]

EncounterType = Literal[
    "acute",
    "well-child",
    "mental-health",
    "follow-up",
]


# --- Embedded Models ---

class ActionRecord(BaseModel):
    """Record of a learner action."""
    id: str
    timestamp: datetime
    action_type: ActionType
    content: str
    target: str | None = None
    phase: Phase
    echo_response_id: str | None = None


class DifferentialEntry(BaseModel):
    """Entry in learner's differential diagnosis."""
    diagnosis: str
    rank: int
    added_at: datetime
    confidence: str | None = None  # "low", "medium", "high"
    reasoning: str | None = None


class OrderRecord(BaseModel):
    """Record of an order placed by learner."""
    id: str
    order_type: Literal["lab", "imaging", "medication", "referral"]
    item: str
    rationale: str | None = None
    timestamp: datetime
    result_id: str | None = None
    status: Literal["pending", "resulted", "cancelled"] = "pending"


class EchoMessage(BaseModel):
    """Message in Echo conversation."""
    id: str
    role: Literal["learner", "echo"]
    content: str
    timestamp: datetime
    triggered_by: str | None = None  # Action ID that triggered this
    is_proactive: bool = False


class TeachingMoment(BaseModel):
    """Proactive coaching moment triggered by the system."""
    id: str
    timestamp: datetime
    trigger: str  # What triggered this moment
    trigger_type: str  # "missed_red_flag", "incomplete_history", etc.
    message: str
    acknowledged: bool = False


class DecisionPoint(BaseModel):
    """Record of a branching decision point."""
    id: str
    timestamp: datetime
    branch_id: str
    trigger: dict
    consequence: str
    new_findings: list[dict] = []


class RevealedData(BaseModel):
    """Structure of revealed clinical data."""
    chief_complaint: str | None = None
    hpi_elements: list[dict] = []
    ros_findings: list[dict] = []
    pmh_details: list[dict] = []
    family_history: list[dict] = []
    social_history: list[dict] = []
    vital_signs: dict | None = None
    exam_findings: list[dict] = []
    lab_results: list[dict] = []
    imaging_results: list[dict] = []


# --- Request Models ---

class StartSessionRequest(BaseModel):
    """Request to start a new learning session."""
    patient_id: str
    encounter_type: EncounterType
    chief_complaint: str
    appointment_id: str | None = None
    case_id: str | None = None  # Optional: use predefined case
    learner_level: LearnerLevel = "student"


class LearnerAction(BaseModel):
    """A learner action submitted during a session."""
    action_type: ActionType
    content: str
    target: str | None = None  # For exams: body area; for orders: specific test


class AdvancePhaseRequest(BaseModel):
    """Request to advance to next phase."""
    to_phase: Phase | None = None  # If None, advance to next logical phase


class CompleteSessionRequest(BaseModel):
    """Request to complete the session."""
    final_diagnosis: str
    final_disposition: str


class UpdateSessionRequest(BaseModel):
    """Request to update session status."""
    status: Literal["paused", "active", "abandoned"]


# --- Response Models ---

class ActionResponse(BaseModel):
    """Response after processing a learner action."""
    success: bool
    action_id: str
    revealed_data: dict | None = None  # New data revealed by this action
    echo_feedback: EchoMessage | None = None  # Immediate Echo feedback
    phase_changed: bool = False
    new_phase: Phase | None = None
    teaching_moment: TeachingMoment | None = None  # Proactive coaching triggered
    branch_triggered: DecisionPoint | None = None  # If branching occurred
    order_result: dict | None = None  # If order resulted immediately


class SessionSummary(BaseModel):
    """Summary view of a learning session."""
    id: str
    patient_id: str
    patient_name: str | None = None
    status: SessionStatus
    current_phase: Phase
    encounter_type: EncounterType
    chief_complaint: str
    started_at: datetime
    completed_at: datetime | None = None


class LearningSession(BaseModel):
    """Full learning session state."""
    id: str
    patient_id: str
    appointment_id: str | None = None
    case_id: str | None = None

    # Metadata
    status: SessionStatus
    started_at: datetime
    paused_at: datetime | None = None
    completed_at: datetime | None = None

    # Context
    encounter_type: EncounterType
    chief_complaint: str
    learner_level: LearnerLevel

    # Phase
    current_phase: Phase

    # Clinical data
    revealed_data: RevealedData
    locked_data: dict = {}

    # Learner state
    actions: list[ActionRecord] = []
    differential: list[DifferentialEntry] = []
    orders_placed: list[OrderRecord] = []

    # Echo
    echo_messages: list[EchoMessage] = []
    teaching_moments: list[TeachingMoment] = []

    # Branching
    active_branch: str = "main"
    branch_history: list[str] = []
    decision_points: list[DecisionPoint] = []

    # Final assessment
    final_diagnosis: str | None = None
    final_disposition: str | None = None
    correct_diagnosis: str | None = None
    correct_disposition: str | None = None

    # Metrics
    time_in_phase: dict = {}
    questions_asked: int = 0
    exams_performed: int = 0

    created_at: datetime | None = None
    updated_at: datetime | None = None


class DebriefResult(BaseModel):
    """Result of post-encounter debrief from Echo."""
    summary: str
    score: dict | None = None  # {total: int, breakdown: {...}}
    strengths: list[str] = []
    areas_for_improvement: list[str] = []
    missed_items: list[str] = []
    teaching_points: list[str] = []
    follow_up_resources: list[str] = []
    correct_diagnosis: str
    correct_disposition: str
    was_correct: bool


# --- Case Definition Models ---

class BranchTrigger(BaseModel):
    """Trigger condition for a case branch."""
    trigger_type: Literal["order", "diagnosis", "disposition", "action"]
    condition: dict


class CaseBranch(BaseModel):
    """A branching path in a case."""
    id: str
    name: str
    trigger: BranchTrigger
    consequence: str
    new_findings: list[dict] = []
    echo_message: str
    severity: Literal["info", "warning", "critical"] = "warning"
    educational_point: str


class CaseDefinition(BaseModel):
    """A predefined teaching case."""
    id: str
    patient_id: str | None = None
    name: str
    description: str | None = None
    difficulty: Literal["easy", "standard", "challenging"] = "standard"
    target_learner_level: LearnerLevel = "student"
    estimated_duration_minutes: int = 30

    chief_complaint: str
    encounter_type: EncounterType

    case_data: dict  # Full clinical data for drip
    correct_diagnosis: str
    correct_disposition: str
    key_findings: list[str] = []
    red_flags: list[str] = []

    branches: dict = {}  # branch_id -> CaseBranch
    learning_objectives: list[str] = []
    teaching_points: list[str] = []

    is_active: bool = True
    created_at: datetime | None = None


class CreateCaseRequest(BaseModel):
    """Request to create a case definition."""
    patient_id: str | None = None
    name: str
    description: str | None = None
    difficulty: Literal["easy", "standard", "challenging"] = "standard"
    chief_complaint: str
    encounter_type: EncounterType
    case_data: dict
    correct_diagnosis: str
    correct_disposition: str
    key_findings: list[str] = []
    red_flags: list[str] = []
    branches: dict = {}
    learning_objectives: list[str] = []
    teaching_points: list[str] = []
