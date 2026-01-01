-- Syrinx Generated Encounters Schema
-- Stores voice encounters generated from patient data via Syrinx

CREATE TABLE IF NOT EXISTS encounters_generated (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    syrinx_id TEXT,
    encounter_type TEXT NOT NULL,
    chief_complaint TEXT,
    metadata JSONB,
    script JSONB,
    audio_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient patient lookup
CREATE INDEX IF NOT EXISTS idx_encounters_generated_patient_id
    ON encounters_generated(patient_id);

-- Index for ordering by creation date
CREATE INDEX IF NOT EXISTS idx_encounters_generated_created_at
    ON encounters_generated(created_at DESC);

-- Enable Row Level Security
ALTER TABLE encounters_generated ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read all encounters
CREATE POLICY "Allow read access to encounters_generated"
    ON encounters_generated FOR SELECT
    TO authenticated
    USING (true);

-- Allow authenticated users to insert encounters
CREATE POLICY "Allow insert access to encounters_generated"
    ON encounters_generated FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Allow service role full access
CREATE POLICY "Allow service role full access to encounters_generated"
    ON encounters_generated FOR ALL
    TO service_role
    USING (true);
