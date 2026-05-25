# Changelog

## [Unreleased]

### Added (committed in `88dff32` on 2026-05-25)
- **Authentication system** (was sitting untracked; landed in the same commit as the data-guard work due to an over-broad `git add -A`):
  - `backend/src/routers/auth.py` — `/auth/signup`, `/auth/login`, `/auth/logout`, `/auth/me`, `/auth/profile`
  - `backend/src/middleware/auth.py` — JWT validation, `get_current_user` + `get_optional_user` dependencies
  - `supabase/migrations/004_auth_system.sql` — `learners` table, RLS policies, `user_id` on patients/imports/learning_sessions
  - Frontend: `pages/Login.tsx`, `pages/Signup.tsx`, `context/AuthContext.tsx`, `components/ProtectedRoute.tsx`
- **Learning visit** flow: `frontend/src/pages/LearningVisit.tsx`, `frontend/src/types/learning.ts`

### Fixed (committed in `88dff32`)
- **Beta-readiness W2.2:** all 15 unchecked `response.data[0]` access sites now guarded via
  `src/db/helpers.py::first_or_500()` — previously these would raise `IndexError`, surfacing
  as opaque 500s when Supabase returned an empty list.

### Fixed (committed in `3593b1f`)
- **Beta-readiness W7.1:** lifespan() warns loudly via stderr if Supabase isn't configured
  at startup, so operators don't discover the misconfig through silent 500s on every endpoint.

### Fixed (committed in `4e9e657`)
- **Beta-readiness W7.2:** stale port references in `README.md` (8002 → 9102, plus
  cross-service URLs Oread 8004 → 9104 and Echo 8001 → 9101) and `backend/.env.example`
  (8000 → 9102). README + .env had drifted from `config.py`.

### Still TODO (W2 remaining)
- W2.4: Echo `/debrief` callback in `routers/learning.py:532` (currently `# TODO` stub)
- W2.5: Backend smoke tests (currently zero) — auth flow, import flow, .data[0] edge cases
- W2.6: `frontend/package.json` depends on `file:../../echo/widget` — needs to be either
  published to npm, vendored, or made optional
- Validation of the new auth flow end-to-end with a real Supabase instance
