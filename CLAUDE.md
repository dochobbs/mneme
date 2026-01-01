# CLAUDE.md - Mneme Development Context

**Last Updated:** December 2025

This file provides context for AI assistants working on Mneme.

## Project Overview

**Mneme** is a minimal EMR (Electronic Medical Record) for medical education. It imports synthetic patient data from Oread and provides a web interface for chart review.

Named after the muse of memory (records), Mneme serves as the "chart" in the MedEd platform where learners review patient information.

## Quick Start

```bash
# Backend
cd /Users/dochobbs/Downloads/Consult/MedEd/synchart/backend
source .venv/bin/activate
python -m src.main                  # API at http://localhost:8000

# Frontend (separate terminal)
cd /Users/dochobbs/Downloads/Consult/MedEd/synchart/frontend
npm install
npm run dev                         # UI at http://localhost:5173
```

## Project Structure

```
synchart/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Settings (Supabase, CORS)
│   │   ├── models/              # Pydantic models
│   │   │   ├── patient.py       # Patient, Condition, Medication, Allergy
│   │   │   ├── encounter.py     # Encounter model
│   │   │   ├── schedule.py      # Appointment model
│   │   │   └── message.py       # Message model
│   │   ├── routers/             # API endpoints
│   │   │   ├── patients.py      # Patient list/detail
│   │   │   ├── schedule.py      # Appointments
│   │   │   ├── messages.py      # Message inbox
│   │   │   └── import_.py       # Oread JSON import
│   │   ├── importers/           # Data import logic
│   │   │   └── oread_json.py    # Parse Oread JSON → DB
│   │   └── db/
│   │       └── supabase.py      # Supabase client
│   ├── requirements.txt
│   ├── .env.example
│   └── .venv/
├── frontend/
│   ├── src/
│   │   ├── main.tsx             # App entry
│   │   ├── App.tsx              # Main app with routing
│   │   ├── pages/
│   │   │   ├── PatientList.tsx  # Patient list view
│   │   │   ├── PatientDetail.tsx # Full patient chart
│   │   │   ├── Schedule.tsx     # Day view appointments
│   │   │   ├── Messages.tsx     # Message inbox
│   │   │   └── Import.tsx       # Oread JSON import
│   │   ├── components/          # Reusable UI components
│   │   └── lib/
│   │       └── api.ts           # API client
│   ├── package.json
│   └── vite.config.ts
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql
├── PLAN.md                       # Full implementation plan
├── README.md
└── CLAUDE.md                     # This file
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12, FastAPI, Pydantic v2 |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Vite |
| **Database** | Supabase (PostgreSQL) |
| **API Client** | fetch (frontend), httpx (backend) |

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
| `/api/import/oread` | POST | Import single Oread JSON |
| `/api/import/oread/batch` | POST | Import multiple files |

### Health
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root status |
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI |

## Database Schema

Mneme uses Supabase PostgreSQL with these main tables:

| Table | Purpose |
|-------|---------|
| `patients` | Demographics, contact info |
| `conditions` | Problem list (SNOMED/ICD-10) |
| `medications` | Current and past meds (RxNorm) |
| `allergies` | Allergy list |
| `encounters` | Visit records with notes |
| `observations` | Labs, vitals, imaging (LOINC) |
| `immunizations` | Vaccine records (CVX) |
| `appointments` | Schedule |
| `messages` | Patient messages |
| `growth_data` | Pediatric growth measurements |
| `imports` | Import tracking |

See `PLAN.md` for full SQL schema.

## Importing Data from Oread

### Via Web UI
1. Go to http://localhost:5173/import
2. Drag and drop Oread JSON file
3. Wait for import to complete
4. Patient appears in Patient List

### Via API
```bash
# Single file
curl -X POST http://localhost:8000/api/import/oread \
  -H "Content-Type: application/json" \
  -d @patient.json

# Check result
curl http://localhost:8000/api/patients
```

### Import Mapping

```
Oread JSON Field   →   Mneme Table
────────────────────────────────────
demographics       →   patients
problem_list       →   conditions
medication_list    →   medications
allergy_list       →   allergies
encounters         →   encounters
observations       →   observations
immunization_record →  immunizations
patient_messages   →   messages
growth_data        →   growth_data
```

## Environment Variables

Create `.env` in `backend/`:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...

# Server
HOST=0.0.0.0
PORT=8002
DEBUG=true

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

## Frontend Views

### Patient List (`/`)
- Searchable list of imported patients
- Shows name, age, DOB, last visit
- Click to open patient detail

### Patient Detail (`/patients/{id}`)
- **Summary Tab**: Demographics, conditions, meds, allergies
- **Encounters Tab**: Visit history with expandable notes
- **Results Tab**: Lab and imaging results
- **Immunizations Tab**: Vaccine record
- **Messages Tab**: Patient communications

### Schedule (`/schedule`)
- Day view of appointments
- Status indicators (scheduled, arrived, in-progress, completed)
- Click to open patient

### Messages (`/messages`)
- Inbox with unread highlighting
- Category filters
- Click to view message with patient context

### Import (`/import`)
- Drag and drop file upload
- Import progress/status
- History of past imports

## Development Commands

```bash
# Backend
cd backend
source .venv/bin/activate
python -m src.main                  # Run server
pytest tests/                       # Run tests

# Frontend
cd frontend
npm run dev                         # Dev server with HMR
npm run build                       # Production build
npm run preview                     # Preview production build
```

## Current Status

**Phase 1 Complete:**
- [x] Project structure
- [x] Supabase schema
- [x] Pydantic models
- [x] Oread JSON importer
- [x] Basic API endpoints

**Phase 2 In Progress:**
- [x] Patient list view
- [x] Patient detail view
- [x] Schedule view
- [x] Messages view
- [x] Import view

**Phase 3 Planned:**
- [ ] FHIR R5 import support
- [ ] C-CDA import support
- [ ] Growth chart visualization
- [ ] Syrinx encounter integration

## Metis Integration

Mneme is part of the **MedEd Platform**, orchestrated by Metis.

### Platform Overview

| Project | Greek Name | Port | Purpose |
|---------|------------|------|---------|
| synpat | Oread | 8004 | Patient generation |
| synvoice | Syrinx | 8003 | Encounter scripts |
| synchart | **Mneme** | 8002 | EMR interface |
| echo | Echo | 8001 | AI tutor |
| metis | Metis | 3000 | Portal (planned) |

### Shared Models

Mneme uses shared models generated by Metis:

```bash
# Regenerate shared models after schema changes
cd /Users/dochobbs/Downloads/Consult/MedEd/metis/shared
python sync.py --project mneme
```

Generated models location: `backend/src/models/_generated/context.py`

### Starting with Metis

```bash
# Start all MedEd services at once
cd /Users/dochobbs/Downloads/Consult/MedEd/metis/scripts
./start-all.sh

# Check status
./status.sh

# Stop all
./stop-all.sh
```

### Standalone Mode

Mneme can run independently without Metis:

```bash
# Backend
cd /Users/dochobbs/Downloads/Consult/MedEd/synchart/backend
source .venv/bin/activate
python -m src.main
# API at http://localhost:8002

# Frontend (separate terminal)
cd /Users/dochobbs/Downloads/Consult/MedEd/synchart/frontend
npm run dev
# UI at http://localhost:5173
```

### Data Flow

```
Oread → [Patient JSON] → Mneme (import & chart review)
                            ↓
                         Echo (patient context for tutoring)
```

**Shared Context:**
Mneme can send patient data to Echo:

```python
class PatientContext(BaseModel):
    patient_id: str
    demographics: dict
    problem_list: list[dict]
    medication_list: list[dict]
    allergy_list: list[dict]
    recent_encounters: list[dict]
    source: Literal["mneme"]
```

## Code Locations

| Component | File | Purpose |
|-----------|------|---------|
| FastAPI App | `backend/src/main.py` | Entry point, routers |
| Config | `backend/src/config.py` | Settings, env vars |
| Patient Models | `backend/src/models/patient.py` | Pydantic schemas |
| Oread Importer | `backend/src/importers/oread_json.py` | JSON parsing |
| Supabase Client | `backend/src/db/supabase.py` | DB operations |
| React App | `frontend/src/App.tsx` | Routing, layout |
| API Client | `frontend/src/lib/api.ts` | Backend calls |

## Development Tasks

### Adding a New Tab to Patient Detail

1. Create component in `frontend/src/pages/`
2. Add tab to `PatientDetail.tsx`
3. Add API endpoint in `backend/src/routers/`
4. Update Pydantic models if needed

### Adding a New Importer

1. Create importer in `backend/src/importers/`
2. Follow `OreadImporter` pattern
3. Add endpoint in `backend/src/routers/import_.py`
4. Update Import page to support format

### Modifying Database Schema

1. Create new migration in `supabase/migrations/`
2. Run migration in Supabase SQL Editor
3. Update Pydantic models
4. Update importers and routers

## Known Issues

- Schedule is empty until appointments are manually created
- No authentication implemented yet

## Future Enhancements

- [ ] User authentication
- [ ] Growth chart visualization
- [ ] Encounter note editing
- [ ] Results pending review workflow
- [ ] Patient export back to Oread format

## Related Projects

| Project | Path | Integration |
|---------|------|-------------|
| **Metis** | `metis/` | Platform orchestration |
| **Oread** | `synpat/` | Patient data source |
| **Syrinx** | `synvoice/` | Encounter scripts |
| **Echo** | `echo/` | AI tutor for feedback |

## Code Style

- **Backend**: Python 3.12+, Pydantic v2, type hints, 2-space indent
- **Frontend**: TypeScript, React 18, Tailwind CSS
- **Both**: Google-style docstrings
