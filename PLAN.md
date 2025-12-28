# Mneme EMR Implementation Plan

## Overview

Mneme is a minimal fake EMR designed to:
1. Import synthetic patient data from oread (JSON, FHIR R5, CCDA)
2. Display schedule, notes, messages, results in a web UI
3. Integrate with syrinx for future encounter documentation

## Tech Stack

- **Backend**: Python 3.12 + FastAPI
- **Frontend**: React + Tailwind CSS (Vite build)
- **Database**: Supabase PostgreSQL
- **CCDA Parser**: lxml for XML parsing
- **FHIR**: fhir.resources library (R5)

## Project Structure

```
synchart/
├── backend/
│   ├── src/
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── config.py               # Supabase/env config
│   │   ├── models/                 # Pydantic models (mirror oread)
│   │   │   ├── patient.py
│   │   │   ├── encounter.py
│   │   │   ├── schedule.py
│   │   │   ├── message.py
│   │   │   └── result.py
│   │   ├── routers/                # API endpoints
│   │   │   ├── patients.py
│   │   │   ├── schedule.py
│   │   │   ├── notes.py
│   │   │   ├── messages.py
│   │   │   ├── results.py
│   │   │   └── import_.py
│   │   ├── importers/              # Data import logic
│   │   │   ├── oread_json.py       # Import from oread JSON
│   │   │   ├── fhir_r5.py          # Import from FHIR R5 Bundle
│   │   │   └── ccda.py             # Import from CCDA XML
│   │   └── db/
│   │       └── supabase.py         # Supabase client
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── PatientList.tsx
│   │   │   ├── PatientDetail.tsx
│   │   │   ├── Schedule.tsx
│   │   │   ├── Notes.tsx
│   │   │   ├── Messages.tsx
│   │   │   ├── Results.tsx
│   │   │   └── Import.tsx
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── PatientCard.tsx
│   │   │   ├── NoteCard.tsx
│   │   │   └── ...
│   │   └── lib/
│   │       └── api.ts              # API client
│   ├── package.json
│   └── vite.config.ts
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql
└── PLAN.md
```

## Database Schema (Supabase)

```sql
-- Core patient table
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT,                    -- oread ID for deduplication
    given_names TEXT[],
    family_name TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    sex_at_birth TEXT,
    gender_identity TEXT,
    race TEXT[],
    ethnicity TEXT,
    preferred_language TEXT DEFAULT 'English',
    phone TEXT,
    email TEXT,
    address JSONB,                       -- Full address object
    emergency_contact JSONB,
    legal_guardian JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Problem list / conditions
CREATE TABLE conditions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    external_id TEXT,
    code_system TEXT,                    -- "snomed", "icd10"
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
CREATE TABLE medications (
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
CREATE TABLE allergies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    external_id TEXT,
    display_name TEXT NOT NULL,
    category TEXT,                       -- food, medication, environment
    criticality TEXT DEFAULT 'low',
    reactions JSONB,                     -- Array of reaction objects
    clinical_status TEXT DEFAULT 'active',
    onset_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Encounters (visits)
CREATE TABLE encounters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    external_id TEXT,
    encounter_type TEXT,                 -- well-child, acute-illness, etc.
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
    narrative_note TEXT,                 -- Full clinical note
    billing_codes JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Observations (labs, vitals, etc.)
CREATE TABLE observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    encounter_id UUID REFERENCES encounters(id),
    external_id TEXT,
    category TEXT,                       -- laboratory, vital-signs, imaging
    code_system TEXT,
    code TEXT,
    display_name TEXT NOT NULL,
    value_quantity NUMERIC,
    value_string TEXT,
    value_unit TEXT,
    interpretation TEXT,                 -- normal, abnormal, critical
    reference_range JSONB,
    effective_date TIMESTAMPTZ,
    performer TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Immunizations
CREATE TABLE immunizations (
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
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    scheduled_time TIMESTAMPTZ NOT NULL,
    duration_minutes INT DEFAULT 20,
    appointment_type TEXT,               -- well-child, sick, follow-up
    status TEXT DEFAULT 'scheduled',     -- scheduled, arrived, in-progress, completed, cancelled
    provider_name TEXT,
    location_name TEXT,
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Patient messages
CREATE TABLE messages (
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
    category TEXT,                       -- refill-request, clinical-question, etc.
    medium TEXT DEFAULT 'portal',
    subject TEXT,
    message_body TEXT NOT NULL,
    reply_body TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Growth data (pediatric)
CREATE TABLE growth_data (
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
CREATE TABLE imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    format TEXT NOT NULL,                -- oread-json, fhir-r5, ccda
    status TEXT DEFAULT 'pending',       -- pending, processing, completed, failed
    patient_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_conditions_patient ON conditions(patient_id);
CREATE INDEX idx_medications_patient ON medications(patient_id);
CREATE INDEX idx_allergies_patient ON allergies(patient_id);
CREATE INDEX idx_encounters_patient ON encounters(patient_id);
CREATE INDEX idx_encounters_date ON encounters(date);
CREATE INDEX idx_observations_patient ON observations(patient_id);
CREATE INDEX idx_observations_category ON observations(category);
CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_time ON appointments(scheduled_time);
CREATE INDEX idx_messages_patient ON messages(patient_id);
CREATE INDEX idx_growth_patient ON growth_data(patient_id);
```

## API Endpoints

### Patients
- `GET /api/patients` - List all patients (paginated)
- `GET /api/patients/{id}` - Get patient with full clinical data
- `GET /api/patients/{id}/summary` - Get patient summary (for list view)

### Schedule
- `GET /api/schedule` - Get appointments for a date range
- `GET /api/schedule/today` - Get today's appointments
- `POST /api/appointments` - Create appointment
- `PATCH /api/appointments/{id}` - Update appointment status

### Notes (Encounters)
- `GET /api/patients/{id}/encounters` - Get patient's encounters
- `GET /api/encounters/{id}` - Get encounter with full note

### Messages
- `GET /api/messages` - Get all messages (inbox)
- `GET /api/messages/unread` - Get unread messages
- `GET /api/patients/{id}/messages` - Get patient's messages
- `PATCH /api/messages/{id}/read` - Mark as read

### Results
- `GET /api/patients/{id}/observations` - Get patient's lab/imaging results
- `GET /api/observations?category=laboratory` - Filter by category
- `GET /api/observations/pending-review` - Results needing review

### Import
- `POST /api/import/oread` - Import oread JSON file
- `POST /api/import/fhir` - Import FHIR R5 Bundle
- `POST /api/import/ccda` - Import CCDA XML
- `GET /api/imports` - List import history
- `GET /api/imports/{id}` - Get import status/details

## Frontend Views

### 1. Sidebar Navigation
- Patient List
- Schedule (today)
- Messages (inbox with unread count)
- Import

### 2. Patient List View
- Searchable/filterable list
- Shows: name, age, DOB, last visit
- Click to open patient detail

### 3. Patient Detail View (tabs)
- **Summary**: Demographics, active conditions, active meds, allergies
- **Notes**: List of encounters with expandable notes
- **Results**: Lab/imaging results with interpretation
- **Messages**: Patient messages (thread view)
- **Growth** (pediatric): Growth chart visualization

### 4. Schedule View
- Calendar day view showing appointments
- Time slots with patient info
- Status indicators (arrived, in-progress, completed)

### 5. Messages Inbox
- List of all messages across patients
- Unread highlighting
- Category filters
- Click to open message (with patient context)

### 6. Import View
- File upload (drag & drop)
- Format auto-detection
- Import progress/status
- History of past imports

## Implementation Phases

### Phase 1: Foundation (Backend + DB)
1. Set up project structure
2. Create Supabase schema (run migrations)
3. Implement Supabase client
4. Create Pydantic models
5. Implement oread JSON importer (primary)
6. Create basic API endpoints (patients, encounters)

### Phase 2: Core API
7. Complete all API endpoints
8. Implement FHIR R5 importer
9. Implement CCDA importer
10. Add import tracking

### Phase 3: Frontend MVP
11. Set up React + Vite + Tailwind
12. Create layout with sidebar
13. Implement Patient List view
14. Implement Patient Detail view
15. Implement Schedule view

### Phase 4: Polish
16. Implement Messages inbox
17. Implement Import view with file upload
18. Add search/filter functionality
19. Basic error handling and loading states

## Oread JSON Import Mapping

```
oread Patient JSON → Mneme Tables
─────────────────────────────────
demographics     → patients
problem_list     → conditions
medication_list  → medications
allergy_list     → allergies
encounters       → encounters
observations     → observations
immunization_record → immunizations
patient_messages → messages
growth_data      → growth_data
```

## Open Decisions (for your input)

1. **Schedule source**: Oread doesn't generate appointments. Should we:
   - Generate sample appointments from encounter history?
   - Leave schedule empty until manually created?
   - Add appointment generation to oread?

2. **Frontend framework**: React is proposed but could also use:
   - Vue.js (simpler)
   - Svelte (lighter)
   - Plain HTML + htmx (simplest, but less interactive)

3. **Supabase project**: Do you have an existing Supabase project to use, or should I include setup instructions for creating one?

## Dependencies

### Backend (requirements.txt)
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
python-multipart>=0.0.6
supabase>=2.3.0
lxml>=5.1.0
fhir.resources>=7.0.0
python-dotenv>=1.0.0
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "@supabase/supabase-js": "^2.39.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```
