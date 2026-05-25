-- Migration: Add authentication system
-- Adds learners table and user_id to existing tables for per-user data isolation
--
-- PREREQUISITE: Run 003_learning_sessions.sql first if learning_sessions table is needed
--
-- This migration:
-- 1. Creates learners table linked to auth.users
-- 2. Adds user_id to patients, learning_sessions, imports
-- 3. Enables RLS with proper user isolation policies
-- 4. Removes old permissive "Allow all" policies from migration 003

-- ============================================
-- 0. Drop old permissive policies (from migration 003)
-- ============================================
DO $$
BEGIN
    -- Drop old permissive policies on learning_sessions if they exist
    DROP POLICY IF EXISTS "Allow all learning_sessions" ON learning_sessions;
    DROP POLICY IF EXISTS "Allow all case_definitions" ON case_definitions;
EXCEPTION
    WHEN undefined_table THEN NULL;
END $$;

-- ============================================
-- 1. Create learners table (extends auth.users)
-- ============================================

CREATE TABLE IF NOT EXISTS learners (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',  -- student, resident, fellow, attending, admin
    institution TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learners_email ON learners(email);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_learners_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER learners_updated_at
    BEFORE UPDATE ON learners
    FOR EACH ROW
    EXECUTE FUNCTION update_learners_updated_at();

COMMENT ON TABLE learners IS 'Extended user profiles for learners';

-- ============================================
-- 2. Add user_id to patients table
-- ============================================

ALTER TABLE patients
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_patients_user_id ON patients(user_id);

-- ============================================
-- 3. Add user_id to learning_sessions table (if it exists)
-- ============================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'learning_sessions') THEN
        ALTER TABLE learning_sessions
        ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

        CREATE INDEX IF NOT EXISTS idx_learning_sessions_user_id ON learning_sessions(user_id);
    END IF;
END $$;

-- ============================================
-- 4. Add user_id to imports table
-- ============================================

ALTER TABLE imports
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_imports_user_id ON imports(user_id);

-- ============================================
-- 5. Enable Row Level Security
-- ============================================

-- Patients table
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own patients" ON patients
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own patients" ON patients
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own patients" ON patients
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own patients" ON patients
    FOR DELETE USING (auth.uid() = user_id);

-- Service role bypass for backend operations
CREATE POLICY "Service role has full access to patients" ON patients
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Learning sessions table (if it exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'learning_sessions') THEN
        ALTER TABLE learning_sessions ENABLE ROW LEVEL SECURITY;

        -- Drop old permissive policy if it exists
        DROP POLICY IF EXISTS "Allow all learning_sessions" ON learning_sessions;

        CREATE POLICY "Users can view own learning sessions" ON learning_sessions
            FOR SELECT USING (auth.uid() = user_id);

        CREATE POLICY "Users can insert own learning sessions" ON learning_sessions
            FOR INSERT WITH CHECK (auth.uid() = user_id);

        CREATE POLICY "Users can update own learning sessions" ON learning_sessions
            FOR UPDATE USING (auth.uid() = user_id);

        CREATE POLICY "Users can delete own learning sessions" ON learning_sessions
            FOR DELETE USING (auth.uid() = user_id);

        CREATE POLICY "Service role has full access to learning sessions" ON learning_sessions
            FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
    END IF;
END $$;

-- Case definitions table (if it exists) - allow all access via service role
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'case_definitions') THEN
        ALTER TABLE case_definitions ENABLE ROW LEVEL SECURITY;

        -- Drop old permissive policy if it exists
        DROP POLICY IF EXISTS "Allow all case_definitions" ON case_definitions;

        -- Case definitions are shared teaching content, accessible to all authenticated users
        CREATE POLICY "Authenticated users can view case definitions" ON case_definitions
            FOR SELECT USING (auth.role() = 'authenticated');

        CREATE POLICY "Service role has full access to case definitions" ON case_definitions
            FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
    END IF;
END $$;

-- Imports table
ALTER TABLE imports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own imports" ON imports
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own imports" ON imports
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own imports" ON imports
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Service role has full access to imports" ON imports
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Learners table (users can only see their own profile)
ALTER TABLE learners ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile" ON learners
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON learners
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Service role has full access to learners" ON learners
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- ============================================
-- 6. RLS for child tables (cascade from patients)
-- ============================================

-- Conditions
ALTER TABLE conditions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access conditions via patients" ON conditions
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM patients
            WHERE patients.id = conditions.patient_id
            AND patients.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to conditions" ON conditions
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Medications
ALTER TABLE medications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access medications via patients" ON medications
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM patients
            WHERE patients.id = medications.patient_id
            AND patients.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to medications" ON medications
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Allergies
ALTER TABLE allergies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access allergies via patients" ON allergies
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM patients
            WHERE patients.id = allergies.patient_id
            AND patients.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to allergies" ON allergies
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Encounters
ALTER TABLE encounters ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access encounters via patients" ON encounters
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM patients
            WHERE patients.id = encounters.patient_id
            AND patients.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to encounters" ON encounters
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Observations
ALTER TABLE observations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access observations via patients" ON observations
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM patients
            WHERE patients.id = observations.patient_id
            AND patients.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to observations" ON observations
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Immunizations
ALTER TABLE immunizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access immunizations via patients" ON immunizations
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM patients
            WHERE patients.id = immunizations.patient_id
            AND patients.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to immunizations" ON immunizations
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Appointments
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access appointments via patients" ON appointments
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM patients
            WHERE patients.id = appointments.patient_id
            AND patients.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to appointments" ON appointments
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Messages
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access messages via patients" ON messages
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM patients
            WHERE patients.id = messages.patient_id
            AND patients.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to messages" ON messages
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Growth data
ALTER TABLE growth_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access growth_data via patients" ON growth_data
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM patients
            WHERE patients.id = growth_data.patient_id
            AND patients.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to growth_data" ON growth_data
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- ============================================
-- 7. Function to auto-create learner on signup
-- ============================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.learners (id, email, display_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data ->> 'display_name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger on auth.users to auto-create learner profile
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
