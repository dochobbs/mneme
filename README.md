# Mneme EMR

A minimal EMR for medical education, integrated with oread synthetic patients and syrinx voice encounters.

## Quick Start

### 1. Run the Supabase Migration

Copy the contents of `supabase/migrations/001_initial_schema.sql` and run it in your Supabase SQL Editor.

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials:
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_ANON_KEY=your-anon-key

# Run the server
python -m src.main
```

The API will be available at http://localhost:8000

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will be available at http://localhost:5173

## Features

- **Patient List**: View and search imported patients
- **Patient Detail**: View conditions, medications, allergies, encounters, results, immunizations
- **Schedule**: Day view of appointments with status management
- **Messages**: Inbox with unread tracking
- **Import**: Drag & drop oread JSON files

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/patients` | List patients |
| `GET /api/patients/{id}/detail` | Full patient with clinical data |
| `GET /api/schedule/today` | Today's appointments |
| `GET /api/messages` | Message inbox |
| `POST /api/import/oread` | Import oread JSON file |

## Importing Data from Oread

1. Generate a patient with oread:
   ```bash
   cd ../synthetic\ patients
   oread generate --age 5 --conditions "asthma,eczema" --format json
   ```

2. In Mneme, go to the Import page and drag the JSON file

## Project Structure

```
synchart/
├── backend/
│   ├── src/
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py         # Settings
│   │   ├── models/           # Pydantic models
│   │   ├── routers/          # API routes
│   │   ├── importers/        # Data importers
│   │   └── db/               # Supabase client
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main app
│   │   ├── pages/            # Page components
│   │   ├── components/       # Reusable components
│   │   └── lib/api.ts        # API client
│   └── package.json
└── supabase/
    └── migrations/           # Database schema
```

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Pydantic
- **Frontend**: React 18, TypeScript, Tailwind CSS, Vite
- **Database**: Supabase (PostgreSQL)

## Future Enhancements

- [ ] FHIR R5 import support
- [ ] C-CDA import support
- [ ] Syrinx encounter integration
- [ ] Growth chart visualization
- [ ] Patient export to oread format
