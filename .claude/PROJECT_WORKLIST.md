# Mneme EMR - Project Worklist

## Completed This Session
- [x] Syrinx script generation integration
- [x] Interactive role-play feature with WebSocket
- [x] Parent persona system (6 types)
- [x] Search icon alignment fix

## High Priority

### Database Migration Required
- [ ] Run `002_encounters_generated.sql` in Supabase SQL Editor
- Table stores generated scripts for later review

### Testing Needed
- [ ] Test role-play feature with Syrinx running on 8003
- [ ] Test script generation end-to-end
- [ ] Verify port configuration (8000 backend, 8001 Echo, 8003 Syrinx)

## Medium Priority

### Role-Play Enhancements
- [ ] Add session save/history to database
- [ ] Add timer display during practice sessions
- [ ] Add feedback/scoring after session ends
- [ ] Support for multiple speakers (e.g., both parents)

### Voice Features (Phase 2)
- [ ] Voice input via Web Speech API
- [ ] Audio playback of AI responses (Syrinx TTS)
- [ ] Generate audio for saved scripts

### UI Polish
- [ ] Add loading skeletons for patient list
- [ ] Improve mobile responsiveness
- [ ] Add keyboard shortcuts for chat (Enter to send)

## Low Priority

### Analytics
- [ ] Track learner performance across sessions
- [ ] Instructor dashboard for reviewing sessions
- [ ] Export session transcripts

### Integration
- [ ] Connect Echo tutor to role-play context
- [ ] Link generated scripts to patient encounters
- [ ] FHIR export for encounters

## Technical Debt
- [ ] Add proper error boundaries
- [ ] Add unit tests for components
- [ ] Document API endpoints

## Port Reference
| Service | Port |
|---------|------|
| Mneme Frontend | 5173 |
| Mneme Backend | 8000 |
| Echo | 8001 |
| Syrinx | 8003 |
