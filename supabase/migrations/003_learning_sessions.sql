-- Learning Sessions and Case Definitions
-- Migration for interactive learning visit system

-- Learning Sessions table
-- Tracks active and completed learning sessions with full state
CREATE TABLE learning_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Links
    appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,

    -- Session metadata
    status TEXT NOT NULL DEFAULT 'active',  -- active, paused, completed, abandoned
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paused_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Encounter context
    encounter_type TEXT NOT NULL,  -- acute, well-child, mental-health, follow-up
    chief_complaint TEXT NOT NULL,
    learner_level TEXT DEFAULT 'student',  -- student, resident, np_student, fellow

    -- Phase tracking
    current_phase TEXT NOT NULL DEFAULT 'chief_complaint',
    -- Phases: chief_complaint, hpi, ros, exam, assessment, plan, debrief

    -- Clinical data drip state (JSONB for flexibility)
    revealed_data JSONB NOT NULL DEFAULT '{
        "chief_complaint": null,
        "hpi_elements": [],
        "ros_findings": [],
        "pmh_details": [],
        "family_history": [],
        "social_history": [],
        "vital_signs": null,
        "exam_findings": [],
        "lab_results": [],
        "imaging_results": []
    }',

    -- Locked data (available but not yet revealed)
    locked_data JSONB NOT NULL DEFAULT '{}',

    -- Learner actions log
    actions JSONB NOT NULL DEFAULT '[]',
    -- Each action: {id, timestamp, type, content, phase, echo_response_id}

    -- Learner's working differential and orders
    differential JSONB NOT NULL DEFAULT '[]',
    -- Each entry: {diagnosis, rank, added_at, confidence, reasoning}

    orders_placed JSONB NOT NULL DEFAULT '[]',
    -- Each order: {id, type, item, rationale, timestamp, result_id, status}

    -- Branching state
    active_branch TEXT DEFAULT 'main',
    branch_history JSONB NOT NULL DEFAULT '[]',
    decision_points JSONB NOT NULL DEFAULT '[]',

    -- Echo interactions
    echo_messages JSONB NOT NULL DEFAULT '[]',
    -- Each: {id, role, content, timestamp, triggered_by, is_proactive}

    teaching_moments JSONB NOT NULL DEFAULT '[]',
    -- Triggered proactive coaching: {id, timestamp, trigger, message, acknowledged}

    -- Final assessment
    final_diagnosis TEXT,
    final_disposition TEXT,
    correct_diagnosis TEXT,  -- Set from case data
    correct_disposition TEXT,

    -- Metrics
    time_in_phase JSONB DEFAULT '{}',  -- Phase -> seconds spent
    questions_asked INT DEFAULT 0,
    exams_performed INT DEFAULT 0,

    -- Case link (optional - for predefined cases)
    case_id UUID,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for learning_sessions
CREATE INDEX idx_learning_sessions_patient ON learning_sessions(patient_id);
CREATE INDEX idx_learning_sessions_status ON learning_sessions(status);
CREATE INDEX idx_learning_sessions_appointment ON learning_sessions(appointment_id);
CREATE INDEX idx_learning_sessions_started ON learning_sessions(started_at DESC);

-- Updated_at trigger for learning_sessions
CREATE OR REPLACE FUNCTION update_learning_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_learning_sessions_updated_at
    BEFORE UPDATE ON learning_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_learning_session_timestamp();


-- Case Definitions table
-- Teaching cases with predefined data and branching logic
CREATE TABLE case_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,

    -- Case metadata
    name TEXT NOT NULL,
    description TEXT,
    difficulty TEXT DEFAULT 'standard',  -- easy, standard, challenging
    target_learner_level TEXT DEFAULT 'student',
    estimated_duration_minutes INT DEFAULT 30,

    -- Clinical scenario
    chief_complaint TEXT NOT NULL,
    encounter_type TEXT NOT NULL,

    -- Full clinical data (dripped to learner)
    case_data JSONB NOT NULL,
    -- Structure:
    -- {
    --   "chief_complaint_detail": "...",
    --   "hpi": {"elements": [...], "reveal_triggers": {...}},
    --   "ros": {...},
    --   "pmh": {...},
    --   "family_history": {...},
    --   "social_history": {...},
    --   "vital_signs": {...},
    --   "physical_exam": {"findings": [...], "reveal_triggers": {...}},
    --   "labs_available": [...],
    --   "imaging_available": [...]
    -- }

    -- Correct answers
    correct_diagnosis TEXT NOT NULL,
    correct_disposition TEXT NOT NULL,
    key_findings JSONB NOT NULL DEFAULT '[]',
    red_flags JSONB DEFAULT '[]',

    -- Branching logic
    branches JSONB DEFAULT '{}',
    -- Structure:
    -- {
    --   "branch_id": {
    --     "trigger": {"order_type": "medication", "matches": ["penicillin"]},
    --     "consequence": "allergy_reaction",
    --     "new_findings": [...],
    --     "echo_message": "..."
    --   }
    -- }

    -- Teaching points
    learning_objectives JSONB DEFAULT '[]',
    teaching_points JSONB DEFAULT '[]',

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add foreign key from learning_sessions to case_definitions
ALTER TABLE learning_sessions
ADD CONSTRAINT fk_learning_sessions_case
FOREIGN KEY (case_id) REFERENCES case_definitions(id) ON DELETE SET NULL;

-- Indexes for case_definitions
CREATE INDEX idx_case_definitions_patient ON case_definitions(patient_id);
CREATE INDEX idx_case_definitions_active ON case_definitions(is_active);
CREATE INDEX idx_case_definitions_difficulty ON case_definitions(difficulty);

-- Updated_at trigger for case_definitions
CREATE TRIGGER update_case_definitions_updated_at
    BEFORE UPDATE ON case_definitions
    FOR EACH ROW
    EXECUTE FUNCTION update_learning_session_timestamp();


-- Enable RLS (Row Level Security) for future auth
ALTER TABLE learning_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_definitions ENABLE ROW LEVEL SECURITY;

-- Temporary permissive policies (allow all for now)
CREATE POLICY "Allow all learning_sessions" ON learning_sessions FOR ALL USING (true);
CREATE POLICY "Allow all case_definitions" ON case_definitions FOR ALL USING (true);
