-- Add debrief storage to learning_sessions
-- Persists the full Echo /debrief response so it can be re-read later
-- without re-calling Echo. Shape matches DebriefResult (Mneme model)
-- which is a superset of DebriefResponse (Echo response).

ALTER TABLE learning_sessions
ADD COLUMN IF NOT EXISTS debrief_json JSONB;

COMMENT ON COLUMN learning_sessions.debrief_json IS
'Full debrief result from Echo /debrief endpoint. Populated on session completion. Null if Echo was unreachable.';
