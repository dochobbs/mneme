"""Learning Visit API routes for Mneme EMR."""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from src.db.supabase import SupabaseDB
from src.db.helpers import first_or_500
from src.middleware.auth import get_current_user, CurrentUser
from src.engines.drip import DripEngine
from src.services.echo_client import (
    get_echo_client,
    build_patient_context,
    build_encounter_context,
    FeedbackRequest,
    QuestionRequest,
    DebriefRequest,
)
from src.models.learning import (
    StartSessionRequest,
    LearnerAction,
    AdvancePhaseRequest,
    CompleteSessionRequest,
    UpdateSessionRequest,
    ActionResponse,
    LearningSession,
    SessionSummary,
    DebriefResult,
    ActionRecord,
    EchoMessage,
    DifferentialEntry,
    OrderRecord,
    RevealedData,
    Phase,
)

router = APIRouter(prefix="/api/learning", tags=["learning"])


# Phase progression order
PHASE_ORDER: list[Phase] = [
    "chief_complaint",
    "hpi",
    "ros",
    "exam",
    "assessment",
    "plan",
    "debrief",
]


def get_next_phase(current: Phase) -> Phase | None:
    """Get the next phase in the progression."""
    try:
        idx = PHASE_ORDER.index(current)
        if idx < len(PHASE_ORDER) - 1:
            return PHASE_ORDER[idx + 1]
        return None
    except ValueError:
        return None


def parse_session(data: dict) -> LearningSession:
    """Parse database row into LearningSession model."""
    # Parse revealed_data from JSONB
    revealed = data.get("revealed_data", {})
    if isinstance(revealed, str):
        import json
        revealed = json.loads(revealed)

    return LearningSession(
        id=str(data["id"]),
        patient_id=str(data["patient_id"]),
        appointment_id=str(data["appointment_id"]) if data.get("appointment_id") else None,
        case_id=str(data["case_id"]) if data.get("case_id") else None,
        status=data["status"],
        started_at=data["started_at"],
        paused_at=data.get("paused_at"),
        completed_at=data.get("completed_at"),
        encounter_type=data["encounter_type"],
        chief_complaint=data["chief_complaint"],
        learner_level=data.get("learner_level", "student"),
        current_phase=data["current_phase"],
        revealed_data=RevealedData(**revealed),
        locked_data=data.get("locked_data", {}),
        actions=data.get("actions", []),
        differential=data.get("differential", []),
        orders_placed=data.get("orders_placed", []),
        echo_messages=data.get("echo_messages", []),
        teaching_moments=data.get("teaching_moments", []),
        active_branch=data.get("active_branch", "main"),
        branch_history=data.get("branch_history", []),
        decision_points=data.get("decision_points", []),
        final_diagnosis=data.get("final_diagnosis"),
        final_disposition=data.get("final_disposition"),
        correct_diagnosis=data.get("correct_diagnosis"),
        correct_disposition=data.get("correct_disposition"),
        time_in_phase=data.get("time_in_phase", {}),
        questions_asked=data.get("questions_asked", 0),
        exams_performed=data.get("exams_performed", 0),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


# --- Session CRUD ---

@router.post("/sessions", response_model=LearningSession)
async def start_session(
    request: StartSessionRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Start a new learning session.

    Creates a session for the specified patient with the given chief complaint.
    If a case_id is provided, loads predefined case data.
    """
    db = SupabaseDB()

    # Verify patient exists and belongs to user
    patient = db.client.table("patients").select("*").eq("id", request.patient_id).eq("user_id", current_user.id).single().execute()
    if not patient.data:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Initialize locked_data from patient's clinical data
    # This will be populated with case data or generated data
    locked_data = {}
    correct_diagnosis = None
    correct_disposition = None

    # If case_id provided, load case definition
    if request.case_id:
        case = db.client.table("case_definitions").select("*").eq("id", request.case_id).single().execute()
        if not case.data:
            raise HTTPException(status_code=404, detail="Case not found")
        locked_data = case.data.get("case_data", {})
        correct_diagnosis = case.data.get("correct_diagnosis")
        correct_disposition = case.data.get("correct_disposition")

    # Create session record
    session_data = {
        "user_id": current_user.id,
        "patient_id": request.patient_id,
        "appointment_id": request.appointment_id,
        "case_id": request.case_id,
        "encounter_type": request.encounter_type,
        "chief_complaint": request.chief_complaint,
        "learner_level": request.learner_level,
        "status": "active",
        "current_phase": "chief_complaint",
        "revealed_data": {
            "chief_complaint": request.chief_complaint,
            "hpi_elements": [],
            "ros_findings": [],
            "pmh_details": [],
            "family_history": [],
            "social_history": [],
            "vital_signs": None,
            "exam_findings": [],
            "lab_results": [],
            "imaging_results": [],
        },
        "locked_data": locked_data,
        "correct_diagnosis": correct_diagnosis,
        "correct_disposition": correct_disposition,
    }

    result = db.client.table("learning_sessions").insert(session_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create session")

    return parse_session(first_or_500(result, "learning session"))


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    status: str | None = None,
    patient_id: str | None = None,
    limit: int = 20,
):
    """List learning sessions with optional filters."""
    db = SupabaseDB()

    query = db.client.table("learning_sessions").select(
        "id, patient_id, status, current_phase, encounter_type, chief_complaint, started_at, completed_at"
    ).eq("user_id", current_user.id)

    if status:
        query = query.eq("status", status)
    if patient_id:
        query = query.eq("patient_id", patient_id)

    query = query.order("started_at", desc=True).limit(limit)
    result = query.execute()

    sessions = []
    for row in result.data:
        sessions.append(SessionSummary(
            id=str(row["id"]),
            patient_id=str(row["patient_id"]),
            status=row["status"],
            current_phase=row["current_phase"],
            encounter_type=row["encounter_type"],
            chief_complaint=row["chief_complaint"],
            started_at=row["started_at"],
            completed_at=row.get("completed_at"),
        ))

    return sessions


@router.get("/sessions/active", response_model=list[SessionSummary])
async def get_active_sessions(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get all active learning sessions."""
    return await list_sessions(current_user=current_user, status="active")


@router.get("/sessions/{session_id}", response_model=LearningSession)
async def get_session(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get full state of a learning session."""
    db = SupabaseDB()

    result = db.client.table("learning_sessions").select("*").eq("id", session_id).eq("user_id", current_user.id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    return parse_session(result.data)


@router.patch("/sessions/{session_id}", response_model=LearningSession)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update session status (pause/resume/abandon)."""
    db = SupabaseDB()

    # Get current session (verify ownership)
    current = db.client.table("learning_sessions").select("*").eq("id", session_id).eq("user_id", current_user.id).single().execute()
    if not current.data:
        raise HTTPException(status_code=404, detail="Session not found")

    if current.data["status"] == "completed":
        raise HTTPException(status_code=400, detail="Cannot modify completed session")

    update_data = {"status": request.status}

    if request.status == "paused":
        update_data["paused_at"] = datetime.utcnow().isoformat()
    elif request.status == "active":
        update_data["paused_at"] = None
    elif request.status == "abandoned":
        update_data["completed_at"] = datetime.utcnow().isoformat()

    result = db.client.table("learning_sessions").update(update_data).eq("id", session_id).execute()

    return parse_session(first_or_500(result, "learning session"))


# --- Actions ---

@router.post("/sessions/{session_id}/action", response_model=ActionResponse)
async def submit_action(
    session_id: str,
    action: LearnerAction,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Submit a learner action during a session.

    Processes the action, potentially reveals new data, and returns
    Echo feedback if applicable.
    """
    db = SupabaseDB()

    # Get current session (verify ownership)
    session_result = db.client.table("learning_sessions").select("*").eq("id", session_id).eq("user_id", current_user.id).single().execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = session_result.data

    if session_data["status"] != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    # Create action record
    action_id = str(uuid.uuid4())
    action_record = {
        "id": action_id,
        "timestamp": datetime.utcnow().isoformat(),
        "action_type": action.action_type,
        "content": action.content,
        "target": action.target,
        "phase": session_data["current_phase"],
    }

    # Add action to session
    actions = session_data.get("actions", [])
    actions.append(action_record)

    # Update metrics
    questions_asked = session_data.get("questions_asked", 0)
    exams_performed = session_data.get("exams_performed", 0)

    if action.action_type == "question":
        questions_asked += 1
    elif action.action_type == "exam_request":
        exams_performed += 1

    # Handle differential actions
    differential = session_data.get("differential", [])
    if action.action_type == "add_differential":
        differential.append({
            "diagnosis": action.content,
            "rank": len(differential) + 1,
            "added_at": datetime.utcnow().isoformat(),
        })
    elif action.action_type == "remove_differential":
        differential = [d for d in differential if d["diagnosis"] != action.content]
        # Re-rank
        for i, d in enumerate(differential):
            d["rank"] = i + 1

    # Handle orders
    orders = session_data.get("orders_placed", [])
    if action.action_type in ("lab_order", "imaging_order"):
        order_type = "lab" if action.action_type == "lab_order" else "imaging"
        orders.append({
            "id": str(uuid.uuid4()),
            "order_type": order_type,
            "item": action.content,
            "rationale": action.target,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending",
        })

    # Get patient data for context
    patient_result = db.client.table("patients").select("*").eq("id", session_data["patient_id"]).single().execute()
    patient_data = patient_result.data if patient_result.data else {}

    # Build patient context for Echo
    conditions = db.client.table("conditions").select("*").eq("patient_id", session_data["patient_id"]).execute()
    medications = db.client.table("medications").select("*").eq("patient_id", session_data["patient_id"]).execute()
    allergies = db.client.table("allergies").select("*").eq("patient_id", session_data["patient_id"]).execute()

    patient_context = build_patient_context(
        patient_id=str(session_data["patient_id"]),
        patient_data=patient_data,
        conditions=conditions.data if conditions.data else [],
        medications=medications.data if medications.data else [],
        allergies=allergies.data if allergies.data else [],
    )

    # Process action through DripEngine
    drip_engine = DripEngine(echo_client=get_echo_client())
    drip_result = await drip_engine.process_action(
        action=action,
        session_data=session_data,
        patient_context=patient_context,
    )

    # Merge revealed data into session
    revealed_data = session_data.get("revealed_data", {})
    for category, new_data in drip_result.revealed.items():
        if category in revealed_data:
            if isinstance(revealed_data[category], list) and isinstance(new_data, list):
                revealed_data[category].extend(new_data)
            elif isinstance(revealed_data[category], list):
                revealed_data[category].append(new_data)
            else:
                revealed_data[category] = new_data
        else:
            revealed_data[category] = new_data

    # Check for teaching moments
    teaching_moment = drip_engine.check_teaching_moment(session_data, action)
    teaching_moments = session_data.get("teaching_moments", [])
    if teaching_moment:
        teaching_moments.append(teaching_moment.model_dump())

    # Handle Echo sidebar questions
    echo_feedback = None
    if action.action_type == "ask_echo":
        echo_client = get_echo_client()
        encounter_context = build_encounter_context(patient_context, session_data)
        question_response = await echo_client.ask_question(
            QuestionRequest(
                patient=patient_context,
                encounter=encounter_context,
                learner_question=action.content,
                learner_level=session_data.get("learner_level", "student"),
            )
        )
        if question_response:
            echo_msg = EchoMessage(
                id=str(uuid.uuid4()),
                role="echo",
                content=question_response.question,
                timestamp=datetime.utcnow(),
                triggered_by=action_id,
                is_proactive=False,
            )
            echo_messages = session_data.get("echo_messages", [])
            echo_messages.append(echo_msg.model_dump())
            echo_feedback = echo_msg

    # Update session with all changes
    update_data = {
        "actions": actions,
        "differential": differential,
        "orders_placed": orders,
        "questions_asked": questions_asked,
        "exams_performed": exams_performed,
        "revealed_data": revealed_data,
        "teaching_moments": teaching_moments,
    }
    if action.action_type == "ask_echo" and echo_feedback:
        update_data["echo_messages"] = session_data.get("echo_messages", [])

    db.client.table("learning_sessions").update(update_data).eq("id", session_id).execute()

    return ActionResponse(
        success=True,
        action_id=action_id,
        revealed_data=drip_result.revealed if drip_result.revealed else None,
        echo_feedback=echo_feedback,
        phase_changed=False,
        teaching_moment=teaching_moment,
    )


@router.post("/sessions/{session_id}/advance", response_model=LearningSession)
async def advance_phase(
    session_id: str,
    request: AdvancePhaseRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Advance the session to the next phase."""
    db = SupabaseDB()

    session_result = db.client.table("learning_sessions").select("*").eq("id", session_id).eq("user_id", current_user.id).single().execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = session_result.data
    current_phase = session_data["current_phase"]

    if session_data["status"] != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    # Determine target phase
    if request.to_phase:
        target_phase = request.to_phase
    else:
        target_phase = get_next_phase(current_phase)
        if not target_phase:
            raise HTTPException(status_code=400, detail="Already at final phase")

    # Validate phase transition
    current_idx = PHASE_ORDER.index(current_phase)
    target_idx = PHASE_ORDER.index(target_phase)

    # Allow going forward or back one phase
    if target_idx > current_idx + 1:
        raise HTTPException(status_code=400, detail="Cannot skip phases")

    # Update time spent in current phase
    time_in_phase = session_data.get("time_in_phase", {})
    # Note: actual time tracking would need more sophisticated logic

    # Update session
    update_data = {
        "current_phase": target_phase,
        "time_in_phase": time_in_phase,
    }

    result = db.client.table("learning_sessions").update(update_data).eq("id", session_id).execute()

    return parse_session(first_or_500(result, "learning session"))


@router.post("/sessions/{session_id}/complete", response_model=DebriefResult)
async def complete_session(
    session_id: str,
    request: CompleteSessionRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Complete the session and trigger debrief.

    Sets final diagnosis/disposition and calls Echo for debrief analysis.
    """
    db = SupabaseDB()

    session_result = db.client.table("learning_sessions").select("*").eq("id", session_id).eq("user_id", current_user.id).single().execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = session_result.data

    if session_data["status"] != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    correct_diagnosis = session_data.get("correct_diagnosis", "")
    correct_disposition = session_data.get("correct_disposition", "")

    # Check if diagnosis is correct (simple string comparison for now)
    was_correct = (
        request.final_diagnosis.lower() == correct_diagnosis.lower() and
        request.final_disposition.lower() == correct_disposition.lower()
    )

    # Update session
    update_data = {
        "status": "completed",
        "current_phase": "debrief",
        "completed_at": datetime.utcnow().isoformat(),
        "final_diagnosis": request.final_diagnosis,
        "final_disposition": request.final_disposition,
    }

    db.client.table("learning_sessions").update(update_data).eq("id", session_id).execute()

    # TODO: Call Echo /debrief endpoint for full analysis
    # For now, return a basic debrief result

    return DebriefResult(
        summary=f"Session completed. You diagnosed {request.final_diagnosis} with disposition {request.final_disposition}.",
        strengths=["Completed the encounter"],
        areas_for_improvement=[],
        missed_items=[],
        teaching_points=[],
        correct_diagnosis=correct_diagnosis or "Not specified",
        correct_disposition=correct_disposition or "Not specified",
        was_correct=was_correct,
    )


@router.get("/sessions/{session_id}/transcript")
async def get_session_transcript(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get the full transcript of a session including all actions and Echo messages."""
    db = SupabaseDB()

    session_result = db.client.table("learning_sessions").select("*").eq("id", session_id).eq("user_id", current_user.id).single().execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = session_result.data

    # Combine and sort all events by timestamp
    events = []

    for action in session_data.get("actions", []):
        events.append({
            "type": "action",
            "timestamp": action["timestamp"],
            "data": action,
        })

    for message in session_data.get("echo_messages", []):
        events.append({
            "type": "echo_message",
            "timestamp": message["timestamp"],
            "data": message,
        })

    for moment in session_data.get("teaching_moments", []):
        events.append({
            "type": "teaching_moment",
            "timestamp": moment["timestamp"],
            "data": moment,
        })

    for decision in session_data.get("decision_points", []):
        events.append({
            "type": "decision_point",
            "timestamp": decision["timestamp"],
            "data": decision,
        })

    # Sort by timestamp
    events.sort(key=lambda e: e["timestamp"])

    return {
        "session_id": session_id,
        "patient_id": session_data["patient_id"],
        "encounter_type": session_data["encounter_type"],
        "chief_complaint": session_data["chief_complaint"],
        "started_at": session_data["started_at"],
        "completed_at": session_data.get("completed_at"),
        "final_diagnosis": session_data.get("final_diagnosis"),
        "final_disposition": session_data.get("final_disposition"),
        "events": events,
    }
