-- Mneme EMR Initial Schema
-- Run this in Supabase SQL Editor or via supabase db push

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core patient table
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT,
    given_names TEXT[] NOT NULL,
    family_name TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    sex_at_birth TEXT,
    gender_identity TEXT,
    race TEXT[],
    ethnicity TEXT,
    preferred_language TEXT DEFAULT 'English',
    phone TEXT,
    email TEXT,
    address JSONB,
    emergency_contact JSONB,
    legal_guardian JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Problem list / conditions
CREATE TABLE IF NOT EXISTS conditions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    external_id TEXT,
    code_system TEXT,
    code TEXT,
    display_name TEXT NOT NULL,
    clinical_status TEXT DEFAULT 'active',
    verification_status TEXT DEFAULT 'confirmed',
    severity TEXT,
    onset_date DATE,
    abatement_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Medications
CREATE TABLE IF NOT EXISTS medications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    external_id TEXT,
    code_system TEXT,
    code TEXT,
    display_name TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    dose_quantity TEXT,
    dose_unit TEXT,
    frequency TEXT,
    route TEXT DEFAULT 'oral',
    instructions TEXT,
    prn BOOLEAN DEFAULT FALSE,
    start_date DATE,
    end_date DATE,
    prescriber TEXT,
    indication TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Allergies
CREATE TABLE IF NOT EXISTS allergies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    external_id TEXT,
    display_name TEXT NOT NULL,
    category TEXT,
    criticality TEXT DEFAULT 'low',
    reactions JSONB,
    clinical_status TEXT DEFAULT 'active',
    onset_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Encounters (visits)
CREATE TABLE IF NOT EXISTS encounters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    external_id TEXT,
    encounter_type TEXT,
    status TEXT DEFAULT 'finished',
    encounter_class TEXT DEFAULT 'ambulatory',
    date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    chief_complaint TEXT,
    provider_name TEXT,
    location_name TEXT,
    vital_signs JSONB,
    hpi TEXT,
    physical_exam JSONB,
    assessment JSONB,
    plan JSONB,
    narrative_note TEXT,
    billing_codes JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Observations (labs, vitals, etc.)
CREATE TABLE IF NOT EXISTS observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    encounter_id UUID REFERENCES encounters(id),
    external_id TEXT,
    category TEXT,
    code_system TEXT,
    code TEXT,
    display_name TEXT NOT NULL,
    value_quantity NUMERIC,
    value_string TEXT,
    value_unit TEXT,
    interpretation TEXT,
    reference_range JSONB,
    effective_date TIMESTAMPTZ,
    performer TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Immunizations
CREATE TABLE IF NOT EXISTS immunizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    external_id TEXT,
    vaccine_code TEXT,
    display_name TEXT NOT NULL,
    status TEXT DEFAULT 'completed',
    date DATE NOT NULL,
    dose_number INT,
    series_doses INT,
    site TEXT,
    lot_number TEXT,
    performer TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Schedule / Appointments
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    scheduled_time TIMESTAMPTZ NOT NULL,
    duration_minutes INT DEFAULT 20,
    appointment_type TEXT,
    status TEXT DEFAULT 'scheduled',
    provider_name TEXT,
    location_name TEXT,
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Patient messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    external_id TEXT,
    sent_datetime TIMESTAMPTZ NOT NULL,
    reply_datetime TIMESTAMPTZ,
    sender_name TEXT NOT NULL,
    sender_is_patient BOOLEAN DEFAULT TRUE,
    recipient_name TEXT,
    replier_name TEXT,
    replier_role TEXT,
    category TEXT,
    medium TEXT DEFAULT 'portal',
    subject TEXT,
    message_body TEXT NOT NULL,
    reply_body TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Growth data (pediatric)
CREATE TABLE IF NOT EXISTS growth_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    encounter_id UUID REFERENCES encounters(id),
    date DATE NOT NULL,
    age_in_days INT,
    weight_kg NUMERIC,
    height_cm NUMERIC,
    head_circumference_cm NUMERIC,
    bmi NUMERIC,
    weight_percentile NUMERIC,
    height_percentile NUMERIC,
    bmi_percentile NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Import tracking
CREATE TABLE IF NOT EXISTS imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    format TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    patient_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(family_name, given_names);
CREATE INDEX IF NOT EXISTS idx_conditions_patient ON conditions(patient_id);
CREATE INDEX IF NOT EXISTS idx_conditions_status ON conditions(clinical_status);
CREATE INDEX IF NOT EXISTS idx_medications_patient ON medications(patient_id);
CREATE INDEX IF NOT EXISTS idx_medications_status ON medications(status);
CREATE INDEX IF NOT EXISTS idx_allergies_patient ON allergies(patient_id);
CREATE INDEX IF NOT EXISTS idx_encounters_patient ON encounters(patient_id);
CREATE INDEX IF NOT EXISTS idx_encounters_date ON encounters(date);
CREATE INDEX IF NOT EXISTS idx_observations_patient ON observations(patient_id);
CREATE INDEX IF NOT EXISTS idx_observations_category ON observations(category);
CREATE INDEX IF NOT EXISTS idx_observations_encounter ON observations(encounter_id);
CREATE INDEX IF NOT EXISTS idx_immunizations_patient ON immunizations(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_time ON appointments(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_messages_patient ON messages(patient_id);
CREATE INDEX IF NOT EXISTS idx_messages_read ON messages(is_read);
CREATE INDEX IF NOT EXISTS idx_growth_patient ON growth_data(patient_id);

-- Updated_at trigger for patients
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Row Level Security (RLS) - disabled for now, enable when adding auth
-- ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE conditions ENABLE ROW LEVEL SECURITY;
-- etc.

COMMENT ON TABLE patients IS 'Core patient demographics and contact info';
COMMENT ON TABLE conditions IS 'Problem list - active and historical diagnoses';
COMMENT ON TABLE medications IS 'Medication list - active and historical';
COMMENT ON TABLE allergies IS 'Allergy and intolerance list';
COMMENT ON TABLE encounters IS 'Clinical visits/encounters with notes';
COMMENT ON TABLE observations IS 'Lab results, vital signs, and other observations';
COMMENT ON TABLE immunizations IS 'Vaccination records';
COMMENT ON TABLE appointments IS 'Scheduled appointments';
COMMENT ON TABLE messages IS 'Patient-provider messages (portal, phone)';
COMMENT ON TABLE growth_data IS 'Pediatric growth measurements and percentiles';
COMMENT ON TABLE imports IS 'Track import operations and status';
