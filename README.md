# Mneme EMR

**A minimal EMR for medical education**, integrated with Oread synthetic patients, Syrinx voice encounters, and Echo AI tutoring.

Part of the **MedEd Platform** -- see [metis/](../metis/) for platform orchestration.

**Port:** 9102 (backend API), 5173 (frontend dev server)

---

## Features

- **Patient List** -- Search and browse imported patients
- **Patient Detail** -- Full chart: conditions, medications, allergies, encounters, results, immunizations
- **Schedule** -- Day view of appointments with status management
- **Messages** -- Inbox with unread tracking and category filters
- **Import** -- Drag-and-drop Oread JSON files, FHIR R5 bundles, or C-CDA documents
- **Learning Sessions** -- Structured chart review with Echo integration
- **Echo Integration** -- AI tutor client for clinical feedback

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Supabase project (for database)

### 1. Database Setup

Copy `supabase/migrations/001_initial_schema.sql` and run it in your Supabase SQL Editor.

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env:
#   SUPABASE_URL=https://your-project.supabase.co
#   SUPABASE_ANON_KEY=your-anon-key

# Run
python -m src.main
# API at http://localhost:9102
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# UI at http://localhost:5173
```

## API Endpoints

### Patients
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/patients` | GET | List all patients |
| `/api/patients/{id}/detail` | GET | Full patient with clinical data |

### Schedule
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/schedule/today` | GET | Today's appointments |
| `/api/appointments/{id}` | PATCH | Update appointment status |

### Messages
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/messages` | GET | Message inbox |
| `/api/messages/{id}/read` | PATCH | Mark message as read |

### Import
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/import/oread` | POST | Import Oread JSON (file upload, auth required) |
| `/api/import/oread/json` | POST | Import Oread JSON body (auth optional) |
| `/api/import/oread/batch` | POST | Import multiple Oread files |
| `/api/import/fhir` | POST | Import FHIR R5 Bundle |
| `/api/import/ccda` | POST | Import C-CDA 2.1 XML |
| `/api/import/history` | GET | Recent import operations |
| `/api/import/{id}` | GET | Import status |

### Health
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root status |
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI |

## Database Schema

Mneme uses Supabase PostgreSQL with these tables:

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `patients` | Demographics | name, dob, sex, mrn |
| `conditions` | Problem list | display_name, snomed_code, icd10_code, status |
| `medications` | Current/past meds | name, rxnorm_code, dose, frequency, status |
| `allergies` | Allergy list | allergen, reaction, severity |
| `encounters` | Visit records | date, type, chief_complaint, notes |
| `observations` | Labs, vitals, imaging | loinc_code, value, unit, date |
| `immunizations` | Vaccine records | cvx_code, vaccine_name, date |
| `appointments` | Schedule | date, time, status, patient_id |
| `messages` | Patient messages | subject, body, category, read |
| `growth_data` | Growth measurements | weight, height, head_circ, percentiles |
| `imports` | Import tracking | source_type, status, patient_count |

See `supabase/migrations/001_initial_schema.sql` for the full schema.

## Importing Data from Oread

### Via Web UI

1. Open http://localhost:5173/import
2. Drag and drop an Oread JSON file
3. Patient appears in the Patient List

### Via API (JSON body -- used by Metis Dashboard)

```bash
# Get patient from Oread
curl -s http://localhost:9104/api/patients/{id}?format=json > /tmp/patient.json

# Import to Mneme (no auth required)
curl -s -X POST http://localhost:9102/api/import/oread/json \
  -H 'Content-Type: application/json' \
  -d @/tmp/patient.json
```

### Via API (file upload -- requires auth)

```bash
curl -X POST http://localhost:9102/api/import/oread \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@patient.json"
```

### Import Data Mapping

```
Oread JSON Field     ->  Mneme Table
--------------------------------------
demographics         ->  patients
problem_list         ->  conditions
medication_list      ->  medications
allergy_list         ->  allergies
encounters           ->  encounters
observations         ->  observations
immunization_record  ->  immunizations
patient_messages     ->  messages
growth_data          ->  growth_data
```

## Frontend Views

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | PatientList | Searchable patient list with age, DOB, last visit |
| `/patients/{id}` | PatientDetail | Tabbed chart: Summary, Encounters, Results, Immunizations, Messages |
| `/schedule` | Schedule | Day view with status indicators (scheduled, arrived, in-progress, completed) |
| `/messages` | Messages | Inbox with unread highlighting and category filters |
| `/import` | Import | Drag-and-drop upload with import history |

## Echo Integration

Mneme includes an `EchoClient` (`backend/src/services/echo_client.py`) for sending patient context to Echo for AI tutoring. The client uses the `PatientContext` format with flat fields:

```python
PatientContext(
  patient_id="...",
  source="mneme",
  name="...",
  age_years=2,
  age_months=24,
  sex="female",
  problem_list=[{"display_name": "Asthma", "is_active": True}],
  medication_list=[...],
  allergy_list=[...],
)
```

## Project Structure

```
synchart/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings (Supabase, CORS, Echo URL)
│   │   ├── models/              # Pydantic models
│   │   │   ├── patient.py       # Patient, Condition, Medication, Allergy
│   │   │   ├── encounter.py     # Encounter
│   │   │   ├── schedule.py      # Appointment
│   │   │   └── message.py       # Message
│   │   ├── routers/             # API endpoints
│   │   │   ├── patients.py      # Patient list/detail
│   │   │   ├── schedule.py      # Appointments
│   │   │   ├── messages.py      # Message inbox
│   │   │   ├── import_.py       # Oread/FHIR/C-CDA import
│   │   │   ├── encounters.py    # Encounter endpoints
│   │   │   ├── learning.py      # Learning sessions
│   │   │   └── auth.py          # Authentication
│   │   ├── importers/           # Data import logic
│   │   │   ├── oread_json.py    # Oread JSON parser
│   │   │   ├── fhir_bundle.py   # FHIR R5 Bundle parser
│   │   │   ├── ccda.py          # C-CDA 2.1 parser
│   │   │   └── base.py          # Base importer
│   │   ├── services/
│   │   │   └── echo_client.py   # Echo AI tutor client
│   │   ├── middleware/
│   │   │   └── auth.py          # Auth middleware (get_current_user, get_optional_user)
│   │   └── db/
│   │       └── supabase.py      # Supabase client
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main app with routing
│   │   ├── pages/               # Page components
│   │   ├── components/          # Reusable UI components
│   │   └── lib/api.ts           # API client
│   ├── package.json
│   └── vite.config.ts
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql
├── PLAN.md                      # Full implementation plan
└── CLAUDE.md                    # Development context
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12, FastAPI, Pydantic v2 |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Vite |
| **Database** | Supabase (PostgreSQL) |
| **Auth** | Supabase Auth (JWT) |

## Environment Variables

Create `.env` in `backend/`:

```bash
# Supabase (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...

# Server
HOST=0.0.0.0
PORT=9102
DEBUG=true

# Echo integration
ECHO_URL=http://localhost:9101

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

## Cross-Service Integration

Mneme connects to the MedEd platform through:

- **Oread** -- Imports synthetic patients via JSON, FHIR, or C-CDA
- **Echo** -- Sends patient context for AI tutoring via `EchoClient`
- **Metis** -- Dashboard sends patients via `/api/import/oread/json` endpoint

See [docs/INTEGRATION.md](../docs/INTEGRATION.md) for the full integration guide.

## Development

```bash
# Backend
cd backend && source .venv/bin/activate
python -m src.main                  # Run server
pytest tests/                       # Run tests

# Frontend
cd frontend
npm run dev                         # Dev server with HMR
npm run build                       # Production build
```

## License

Internal use only -- Medical education.
