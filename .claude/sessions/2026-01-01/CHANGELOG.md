# Changelog - 2026-01-01

## Features

### Syrinx Script Generation
- Added `backend/src/routers/encounters.py` - Proxy to Syrinx /api/generate
- Added `frontend/src/components/GenerateEncounterModal.tsx` - Script generation form
- Added `frontend/src/components/EncounterViewer.tsx` - Script display with save option
- Added encounter API functions to `frontend/src/lib/api.ts`
- Added "Generate Script" button to PatientDetail page

### Interactive Role-Play
- Added `frontend/src/hooks/useSyrinxSession.ts` - WebSocket hook for Syrinx
- Added `frontend/src/lib/roleplay.ts` - Scenario builder with 6 parent personas
- Added `frontend/src/components/RolePlaySetupModal.tsx` - Practice session setup
- Added `frontend/src/components/RolePlayModal.tsx` - Full-screen chat interface
- Added "Practice Encounter" button to PatientDetail page

### Database
- Added `supabase/migrations/002_encounters_generated.sql` - Storage for generated scripts

## Fixes
- Fixed search icon vertical alignment in PatientList page
- Fixed TypeScript type error in useSyrinxSession hook (message text type)

## Configuration
- Changed Mneme backend port from 8002 to 8000 (avoid Echo conflict)
- Updated frontend proxy to target port 8000
- Added httpx dependency to backend requirements

## Files Changed
```
Modified:
  backend/.env (port 8000)
  backend/requirements.txt (+httpx)
  backend/src/main.py (+encounters router)
  frontend/vite.config.ts (proxy to 8000)
  frontend/src/lib/api.ts (+encounter functions)
  frontend/src/pages/PatientDetail.tsx (+buttons, modals)
  frontend/src/pages/PatientList.tsx (search icon fix)

Created:
  backend/src/routers/encounters.py
  frontend/src/hooks/useSyrinxSession.ts
  frontend/src/lib/roleplay.ts
  frontend/src/components/GenerateEncounterModal.tsx
  frontend/src/components/EncounterViewer.tsx
  frontend/src/components/RolePlaySetupModal.tsx
  frontend/src/components/RolePlayModal.tsx
  supabase/migrations/002_encounters_generated.sql
```
