"""Drip Engine for AI-paced clinical data revelation.

The DripEngine manages the progressive revelation of clinical data during
a learning session, deciding when to reveal new information based on
learner actions, questions, and the current phase.
"""

import re
from typing import Any
from dataclasses import dataclass, field
from src.models.learning import (
    LearnerAction,
    Phase,
    TeachingMoment,
    ActionType,
)
from src.services.echo_client import (
    EchoClient,
    PatientContext,
    FeedbackRequest,
    get_echo_client,
)


@dataclass
class DripResult:
    """Result of processing an action through the drip engine."""
    revealed: dict = field(default_factory=dict)  # New data revealed
    teaching_moment: TeachingMoment | None = None
    phase_suggestion: Phase | None = None  # Suggest advancing to this phase
    feedback_text: str | None = None  # Feedback from Echo


@dataclass
class RevealRule:
    """Rule for revealing clinical data."""
    name: str
    trigger_keywords: list[str]  # Keywords that trigger this reveal
    reveals_category: str  # Category of data to reveal (hpi, ros, exam, etc.)
    reveals_key: str  # Specific key within the category
    required_phase: Phase | None = None  # Must be in this phase
    requires_revealed: list[str] = field(default_factory=list)  # Must have revealed these first


# Default reveal rules
DEFAULT_REVEAL_RULES = [
    # HPI reveals
    RevealRule(
        name="fever_onset",
        trigger_keywords=["when", "start", "began", "onset", "how long"],
        reveals_category="hpi_elements",
        reveals_key="onset",
    ),
    RevealRule(
        name="fever_duration",
        trigger_keywords=["how long", "duration", "days", "hours", "since when"],
        reveals_category="hpi_elements",
        reveals_key="duration",
    ),
    RevealRule(
        name="fever_severity",
        trigger_keywords=["how high", "temperature", "fever", "max temp", "highest"],
        reveals_category="hpi_elements",
        reveals_key="severity",
    ),
    RevealRule(
        name="associated_symptoms",
        trigger_keywords=["other symptoms", "anything else", "associated", "along with"],
        reveals_category="hpi_elements",
        reveals_key="associated_symptoms",
    ),
    RevealRule(
        name="fever_treatment",
        trigger_keywords=["tried", "given", "tylenol", "ibuprofen", "motrin", "acetaminophen", "medicine"],
        reveals_category="hpi_elements",
        reveals_key="treatment_tried",
    ),

    # ROS reveals
    RevealRule(
        name="ros_respiratory",
        trigger_keywords=["cough", "breathing", "respiratory", "wheeze", "congestion", "runny nose"],
        reveals_category="ros_findings",
        reveals_key="respiratory",
        required_phase="ros",
    ),
    RevealRule(
        name="ros_gi",
        trigger_keywords=["vomit", "diarrhea", "eating", "drinking", "appetite", "nausea", "stomach"],
        reveals_category="ros_findings",
        reveals_key="gi",
    ),
    RevealRule(
        name="ros_urinary",
        trigger_keywords=["pee", "urinate", "urine", "wet diapers", "potty"],
        reveals_category="ros_findings",
        reveals_key="urinary",
    ),
    RevealRule(
        name="ros_neuro",
        trigger_keywords=["headache", "neck", "stiff", "light", "photophobia", "lethargy", "activity"],
        reveals_category="ros_findings",
        reveals_key="neuro",
    ),
    RevealRule(
        name="ros_skin",
        trigger_keywords=["rash", "skin", "spots", "bumps", "hives"],
        reveals_category="ros_findings",
        reveals_key="skin",
    ),
    RevealRule(
        name="ros_ent",
        trigger_keywords=["ear", "ears", "pulling", "throat", "sore throat", "swallow"],
        reveals_category="ros_findings",
        reveals_key="ent",
    ),

    # PMH reveals
    RevealRule(
        name="pmh_conditions",
        trigger_keywords=["medical history", "medical problems", "conditions", "chronic", "past medical"],
        reveals_category="pmh_details",
        reveals_key="conditions",
    ),
    RevealRule(
        name="pmh_hospitalizations",
        trigger_keywords=["hospital", "hospitalized", "admitted", "surgery", "operations"],
        reveals_category="pmh_details",
        reveals_key="hospitalizations",
    ),
    RevealRule(
        name="pmh_medications",
        trigger_keywords=["medications", "medicines", "taking anything", "regular medications"],
        reveals_category="pmh_details",
        reveals_key="current_medications",
    ),

    # Family history reveals
    RevealRule(
        name="family_history",
        trigger_keywords=["family", "parents", "siblings", "inherited", "runs in family"],
        reveals_category="family_history",
        reveals_key="general",
    ),

    # Social history reveals
    RevealRule(
        name="social_daycare",
        trigger_keywords=["daycare", "school", "preschool", "childcare", "sick contacts"],
        reveals_category="social_history",
        reveals_key="daycare",
    ),
    RevealRule(
        name="social_exposures",
        trigger_keywords=["sick", "exposed", "contact", "anyone else", "travel"],
        reveals_category="social_history",
        reveals_key="exposures",
    ),
    RevealRule(
        name="social_smoke",
        trigger_keywords=["smoke", "smoking", "cigarette", "vape", "secondhand"],
        reveals_category="social_history",
        reveals_key="smoke_exposure",
    ),
]

# Exam reveal rules (require exam phase and explicit request)
EXAM_REVEAL_RULES = [
    RevealRule(
        name="vital_signs",
        trigger_keywords=["vitals", "vital signs", "temperature", "heart rate", "blood pressure", "check vitals"],
        reveals_category="vital_signs",
        reveals_key="all",
        required_phase="exam",
    ),
    RevealRule(
        name="exam_general",
        trigger_keywords=["general", "appearance", "looks", "sick", "toxic", "well-appearing"],
        reveals_category="exam_findings",
        reveals_key="general",
        required_phase="exam",
    ),
    RevealRule(
        name="exam_heent",
        trigger_keywords=["head", "eyes", "ears", "nose", "throat", "tympanic", "tm", "oropharynx"],
        reveals_category="exam_findings",
        reveals_key="heent",
        required_phase="exam",
    ),
    RevealRule(
        name="exam_neck",
        trigger_keywords=["neck", "lymph", "nodes", "stiff", "meningeal", "nuchal"],
        reveals_category="exam_findings",
        reveals_key="neck",
        required_phase="exam",
    ),
    RevealRule(
        name="exam_cardiac",
        trigger_keywords=["heart", "cardiac", "chest", "murmur", "rhythm"],
        reveals_category="exam_findings",
        reveals_key="cardiac",
        required_phase="exam",
    ),
    RevealRule(
        name="exam_respiratory",
        trigger_keywords=["lungs", "respiratory", "breathing", "breath sounds", "wheeze", "crackles"],
        reveals_category="exam_findings",
        reveals_key="respiratory",
        required_phase="exam",
    ),
    RevealRule(
        name="exam_abdomen",
        trigger_keywords=["abdomen", "belly", "stomach", "abdominal", "tenderness"],
        reveals_category="exam_findings",
        reveals_key="abdomen",
        required_phase="exam",
    ),
    RevealRule(
        name="exam_skin",
        trigger_keywords=["skin", "rash", "lesions", "petechiae", "purpura"],
        reveals_category="exam_findings",
        reveals_key="skin",
        required_phase="exam",
    ),
    RevealRule(
        name="exam_neuro",
        trigger_keywords=["neuro", "neurological", "fontanelle", "reflexes", "tone", "mental status"],
        reveals_category="exam_findings",
        reveals_key="neuro",
        required_phase="exam",
    ),
]


class DripEngine:
    """
    Manages AI-paced revelation of clinical data.

    The DripEngine processes learner actions and decides what clinical
    data to reveal based on:
    1. Keyword matching against reveal rules
    2. Current phase of the encounter
    3. Echo's AI assessment of the question quality
    """

    def __init__(
        self,
        echo_client: EchoClient | None = None,
        rules: list[RevealRule] | None = None,
    ):
        """
        Initialize the DripEngine.

        Args:
            echo_client: Optional Echo client for AI-assisted reveals
            rules: Optional custom reveal rules (defaults to built-in rules)
        """
        self.echo_client = echo_client
        self.rules = rules or (DEFAULT_REVEAL_RULES + EXAM_REVEAL_RULES)

    async def process_action(
        self,
        action: LearnerAction,
        session_data: dict,
        patient_context: PatientContext | None = None,
    ) -> DripResult:
        """
        Process a learner action and determine what data to reveal.

        Args:
            action: The learner's action
            session_data: Current session state
            patient_context: Patient context for Echo calls

        Returns:
            DripResult with revealed data and optional teaching moment
        """
        current_phase = session_data.get("current_phase", "chief_complaint")
        revealed_data = session_data.get("revealed_data", {})
        locked_data = session_data.get("locked_data", {})

        result = DripResult()

        # Handle different action types
        if action.action_type == "question":
            result = await self._process_question(
                action.content,
                current_phase,
                revealed_data,
                locked_data,
                patient_context,
            )

        elif action.action_type == "exam_request":
            result = await self._process_exam_request(
                action.content,
                action.target,
                current_phase,
                revealed_data,
                locked_data,
            )

        elif action.action_type in ("lab_order", "imaging_order"):
            result = await self._process_order(
                action.action_type,
                action.content,
                locked_data,
            )

        return result

    async def _process_question(
        self,
        question: str,
        current_phase: Phase,
        revealed_data: dict,
        locked_data: dict,
        patient_context: PatientContext | None = None,
    ) -> DripResult:
        """Process a question action and determine reveals."""
        result = DripResult()
        question_lower = question.lower()

        # Check rules for matching reveals
        for rule in self.rules:
            # Check if any trigger keyword matches
            if not any(kw in question_lower for kw in rule.trigger_keywords):
                continue

            # Check phase requirement
            if rule.required_phase and current_phase != rule.required_phase:
                continue

            # Check if already revealed
            category_data = revealed_data.get(rule.reveals_category, [])
            if isinstance(category_data, list):
                if any(isinstance(item, dict) and item.get("key") == rule.reveals_key for item in category_data):
                    continue
            elif isinstance(category_data, dict):
                if rule.reveals_key in category_data:
                    continue

            # Find matching data in locked_data
            locked_category = locked_data.get(rule.reveals_category, {})
            if isinstance(locked_category, dict):
                data_to_reveal = locked_category.get(rule.reveals_key)
            elif isinstance(locked_category, list):
                data_to_reveal = next(
                    (item for item in locked_category if isinstance(item, dict) and item.get("key") == rule.reveals_key),
                    None
                )
            else:
                data_to_reveal = None

            if data_to_reveal:
                # Add to result
                if rule.reveals_category not in result.revealed:
                    result.revealed[rule.reveals_category] = []

                if isinstance(result.revealed[rule.reveals_category], list):
                    result.revealed[rule.reveals_category].append({
                        "key": rule.reveals_key,
                        "content": data_to_reveal,
                    })
                else:
                    result.revealed[rule.reveals_category] = data_to_reveal

        # Optionally call Echo for feedback on the question
        if self.echo_client and patient_context:
            try:
                feedback = await self.echo_client.get_feedback(
                    FeedbackRequest(
                        patient=patient_context,
                        learner_action=question,
                        action_type="question",
                        context=f"Current phase: {current_phase}",
                    )
                )
                if feedback:
                    result.feedback_text = feedback.feedback
            except Exception as e:
                print(f"Echo feedback error: {e}")

        return result

    async def _process_exam_request(
        self,
        request: str,
        target: str | None,
        current_phase: Phase,
        revealed_data: dict,
        locked_data: dict,
    ) -> DripResult:
        """Process an exam request action."""
        result = DripResult()

        # Must be in exam phase
        if current_phase != "exam":
            result.feedback_text = "You should complete the history before performing the physical exam."
            return result

        request_lower = request.lower()
        target_lower = (target or "").lower()

        # Check exam rules
        for rule in EXAM_REVEAL_RULES:
            # Check if request matches this exam type
            if not any(kw in request_lower or kw in target_lower for kw in rule.trigger_keywords):
                continue

            # Find matching data in locked_data
            if rule.reveals_category == "vital_signs":
                data_to_reveal = locked_data.get("vital_signs")
                if data_to_reveal:
                    result.revealed["vital_signs"] = data_to_reveal
            else:
                locked_exam = locked_data.get("exam_findings", {})
                if isinstance(locked_exam, dict):
                    data_to_reveal = locked_exam.get(rule.reveals_key)
                    if data_to_reveal:
                        if "exam_findings" not in result.revealed:
                            result.revealed["exam_findings"] = []
                        result.revealed["exam_findings"].append({
                            "key": rule.reveals_key,
                            "finding": data_to_reveal,
                        })

        return result

    async def _process_order(
        self,
        order_type: str,
        order_item: str,
        locked_data: dict,
    ) -> DripResult:
        """Process a lab or imaging order."""
        result = DripResult()

        order_lower = order_item.lower()

        if order_type == "lab_order":
            # Check for matching lab result in locked data
            available_labs = locked_data.get("labs_available", [])
            for lab in available_labs:
                if isinstance(lab, dict):
                    lab_name = lab.get("name", "").lower()
                    if order_lower in lab_name or lab_name in order_lower:
                        if "lab_results" not in result.revealed:
                            result.revealed["lab_results"] = []
                        result.revealed["lab_results"].append(lab)

        elif order_type == "imaging_order":
            # Check for matching imaging result in locked data
            available_imaging = locked_data.get("imaging_available", [])
            for img in available_imaging:
                if isinstance(img, dict):
                    img_name = img.get("name", "").lower()
                    if order_lower in img_name or img_name in order_lower:
                        if "imaging_results" not in result.revealed:
                            result.revealed["imaging_results"] = []
                        result.revealed["imaging_results"].append(img)

        return result

    def check_teaching_moment(
        self,
        session_data: dict,
        action: LearnerAction,
    ) -> TeachingMoment | None:
        """
        Check if the current state triggers a teaching moment.

        Args:
            session_data: Current session state
            action: The action that was just taken

        Returns:
            TeachingMoment if triggered, None otherwise
        """
        import uuid
        from datetime import datetime

        current_phase = session_data.get("current_phase")
        revealed_data = session_data.get("revealed_data", {})
        locked_data = session_data.get("locked_data", {})
        differential = session_data.get("differential", [])

        # Check for missed red flags when advancing to assessment
        if current_phase == "assessment":
            red_flags = locked_data.get("red_flags", [])
            revealed_exam = revealed_data.get("exam_findings", [])
            revealed_hpi = revealed_data.get("hpi_elements", [])

            for flag in red_flags:
                flag_key = flag.get("key") if isinstance(flag, dict) else flag
                # Check if this red flag was revealed
                found = False
                for item in revealed_exam + revealed_hpi:
                    if isinstance(item, dict) and item.get("key") == flag_key:
                        found = True
                        break
                if not found:
                    return TeachingMoment(
                        id=str(uuid.uuid4()),
                        timestamp=datetime.utcnow(),
                        trigger=f"Red flag not explored: {flag_key}",
                        trigger_type="missed_red_flag",
                        message=f"Before making your assessment, have you fully evaluated all concerning features?",
                        acknowledged=False,
                    )

        # Check for incomplete history when advancing to exam
        if current_phase == "exam":
            hpi_elements = revealed_data.get("hpi_elements", [])
            if len(hpi_elements) < 3:
                return TeachingMoment(
                    id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    trigger="Incomplete HPI",
                    trigger_type="incomplete_history",
                    message="You've moved to the exam phase quickly. Have you gathered enough history to guide your exam?",
                    acknowledged=False,
                )

        return None
