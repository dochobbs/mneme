import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Play,
  Pause,
  ChevronRight,
  MessageSquare,
  Stethoscope,
  FlaskConical,
  Image,
  ListChecks,
  Send,
  AlertCircle,
} from 'lucide-react';
import {
  getLearningSession,
  submitLearnerAction,
  advanceLearningPhase,
  updateLearningSession,
  getPatient,
} from '../lib/api';
import type {
  LearningSession,
  LearnerAction,
  TeachingMoment,
} from '../types/learning';
import { PHASE_LABELS, PHASE_ORDER } from '../types/learning';
import type { Patient } from '../lib/api';

export default function LearningVisit() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<LearningSession | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action panel state
  const [actionInput, setActionInput] = useState('');
  const [selectedActionType, setSelectedActionType] = useState<'question' | 'exam_request' | 'lab_order' | 'imaging_order'>('question');
  const [submitting, setSubmitting] = useState(false);

  // Echo sidebar state
  const [echoInput, setEchoInput] = useState('');

  // Teaching moment popup
  const [activeTeachingMoment, setActiveTeachingMoment] = useState<TeachingMoment | null>(null);

  // Differential state
  const [newDiagnosis, setNewDiagnosis] = useState('');

  // Load session data
  useEffect(() => {
    async function loadSession() {
      if (!sessionId) return;

      try {
        setLoading(true);
        const sessionData = await getLearningSession(sessionId);
        setSession(sessionData);

        // Load patient data
        const patientData = await getPatient(sessionData.patient_id);
        setPatient(patientData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load session');
      } finally {
        setLoading(false);
      }
    }

    loadSession();
  }, [sessionId]);

  // Handle action submission
  const handleSubmitAction = useCallback(async () => {
    if (!sessionId || !actionInput.trim() || submitting) return;

    try {
      setSubmitting(true);
      const action: LearnerAction = {
        action_type: selectedActionType,
        content: actionInput.trim(),
      };

      const response = await submitLearnerAction(sessionId, action);

      // Refresh session to get updated state
      const updatedSession = await getLearningSession(sessionId);
      setSession(updatedSession);

      // Show teaching moment if triggered
      if (response.teaching_moment) {
        setActiveTeachingMoment(response.teaching_moment);
      }

      setActionInput('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit action');
    } finally {
      setSubmitting(false);
    }
  }, [sessionId, actionInput, selectedActionType, submitting]);

  // Handle Echo question
  const handleAskEcho = useCallback(async () => {
    if (!sessionId || !echoInput.trim() || submitting) return;

    try {
      setSubmitting(true);
      const action: LearnerAction = {
        action_type: 'ask_echo',
        content: echoInput.trim(),
      };

      await submitLearnerAction(sessionId, action);

      // Refresh session to get Echo response
      const updatedSession = await getLearningSession(sessionId);
      setSession(updatedSession);

      setEchoInput('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to ask Echo');
    } finally {
      setSubmitting(false);
    }
  }, [sessionId, echoInput, submitting]);

  // Handle phase advance
  const handleAdvancePhase = useCallback(async () => {
    if (!sessionId || submitting) return;

    try {
      setSubmitting(true);
      const updatedSession = await advanceLearningPhase(sessionId);
      setSession(updatedSession);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to advance phase');
    } finally {
      setSubmitting(false);
    }
  }, [sessionId, submitting]);

  // Handle pause/resume
  const handleTogglePause = useCallback(async () => {
    if (!sessionId || !session) return;

    try {
      const newStatus = session.status === 'paused' ? 'active' : 'paused';
      const updatedSession = await updateLearningSession(sessionId, { status: newStatus });
      setSession(updatedSession);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update session');
    }
  }, [sessionId, session]);

  // Handle add differential
  const handleAddDifferential = useCallback(async () => {
    if (!sessionId || !newDiagnosis.trim() || submitting) return;

    try {
      setSubmitting(true);
      await submitLearnerAction(sessionId, {
        action_type: 'add_differential',
        content: newDiagnosis.trim(),
      });

      const updatedSession = await getLearningSession(sessionId);
      setSession(updatedSession);
      setNewDiagnosis('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add diagnosis');
    } finally {
      setSubmitting(false);
    }
  }, [sessionId, newDiagnosis, submitting]);

  // Get current phase index
  const currentPhaseIndex = session ? PHASE_ORDER.indexOf(session.current_phase) : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin w-8 h-8 border-2 rounded-full" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="p-8">
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'rgba(155, 44, 44, 0.1)', color: 'var(--clinical-error)' }}>
          {error || 'Session not found'}
        </div>
        <button onClick={() => navigate(-1)} className="mt-4 btn-secondary">
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Patient Banner */}
      <div className="flex-shrink-0 p-4 border-b" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate(-1)} className="p-2 rounded-lg hover:bg-gray-100">
              <ArrowLeft className="w-5 h-5" style={{ color: 'var(--text-secondary)' }} />
            </button>
            <div>
              <h1 className="text-xl font-display font-semibold" style={{ color: 'var(--text-primary)' }}>
                {patient?.full_name || 'Patient'}
              </h1>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                {patient?.age_years}yo {patient?.sex_at_birth} | CC: {session.chief_complaint}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Phase Progress */}
            <div className="flex items-center gap-2">
              {PHASE_ORDER.slice(0, -1).map((phase, idx) => (
                <div
                  key={phase}
                  className="w-3 h-3 rounded-full"
                  style={{
                    backgroundColor: idx <= currentPhaseIndex ? 'var(--accent)' : 'var(--border)',
                  }}
                  title={PHASE_LABELS[phase]}
                />
              ))}
            </div>

            <span className="px-3 py-1 rounded-full text-sm font-medium" style={{ backgroundColor: 'var(--accent-light)', color: 'var(--accent)' }}>
              {PHASE_LABELS[session.current_phase]}
            </span>

            <button
              onClick={handleTogglePause}
              className="p-2 rounded-lg hover:bg-gray-100"
              title={session.status === 'paused' ? 'Resume' : 'Pause'}
            >
              {session.status === 'paused' ? (
                <Play className="w-5 h-5" style={{ color: 'var(--clinical-success)' }} />
              ) : (
                <Pause className="w-5 h-5" style={{ color: 'var(--text-secondary)' }} />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Drip Content & Actions */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Drip Content Area */}
          <div className="flex-1 overflow-y-auto p-6">
            {/* Chief Complaint */}
            <div className="mb-6">
              <h3 className="font-display font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                Chief Complaint
              </h3>
              <p className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)' }}>
                {session.revealed_data.chief_complaint || session.chief_complaint}
              </p>
            </div>

            {/* HPI Elements */}
            {session.revealed_data.hpi_elements.length > 0 && (
              <div className="mb-6">
                <h3 className="font-display font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                  History of Present Illness
                </h3>
                <ul className="space-y-2">
                  {session.revealed_data.hpi_elements.map((item, idx) => (
                    <li key={idx} className="p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                      <span className="font-medium" style={{ color: 'var(--accent)' }}>{item.key}:</span>{' '}
                      <span style={{ color: 'var(--text-primary)' }}>{typeof item.content === 'string' ? item.content : JSON.stringify(item.content)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Exam Findings */}
            {session.revealed_data.exam_findings.length > 0 && (
              <div className="mb-6">
                <h3 className="font-display font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                  Physical Exam
                </h3>
                <ul className="space-y-2">
                  {session.revealed_data.exam_findings.map((item, idx) => (
                    <li key={idx} className="p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                      <span className="font-medium" style={{ color: 'var(--accent)' }}>{item.key}:</span>{' '}
                      <span style={{ color: 'var(--text-primary)' }}>{typeof item.finding === 'string' ? item.finding : JSON.stringify(item.finding)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Vital Signs */}
            {session.revealed_data.vital_signs && (
              <div className="mb-6">
                <h3 className="font-display font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                  Vital Signs
                </h3>
                <div className="p-4 rounded-lg grid grid-cols-3 gap-4" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                  {Object.entries(session.revealed_data.vital_signs).map(([key, value]) => (
                    <div key={key}>
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{key}:</span>{' '}
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Lab Results */}
            {session.revealed_data.lab_results.length > 0 && (
              <div className="mb-6">
                <h3 className="font-display font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                  Lab Results
                </h3>
                <ul className="space-y-2">
                  {session.revealed_data.lab_results.map((result, idx) => (
                    <li key={idx} className="p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{result.name}:</span>{' '}
                      <span style={{ color: 'var(--text-primary)' }}>{result.value} {result.unit}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Action Panel */}
          <div className="flex-shrink-0 p-4 border-t" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-card)' }}>
            <div className="flex gap-2 mb-3">
              <button
                onClick={() => setSelectedActionType('question')}
                className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5 ${selectedActionType === 'question' ? 'bg-accent text-white' : ''}`}
                style={selectedActionType !== 'question' ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' } : { backgroundColor: 'var(--accent)', color: 'white' }}
              >
                <MessageSquare className="w-4 h-4" /> Ask Question
              </button>
              <button
                onClick={() => setSelectedActionType('exam_request')}
                className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5`}
                style={selectedActionType !== 'exam_request' ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' } : { backgroundColor: 'var(--accent)', color: 'white' }}
              >
                <Stethoscope className="w-4 h-4" /> Exam
              </button>
              <button
                onClick={() => setSelectedActionType('lab_order')}
                className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5`}
                style={selectedActionType !== 'lab_order' ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' } : { backgroundColor: 'var(--accent)', color: 'white' }}
              >
                <FlaskConical className="w-4 h-4" /> Lab
              </button>
              <button
                onClick={() => setSelectedActionType('imaging_order')}
                className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5`}
                style={selectedActionType !== 'imaging_order' ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' } : { backgroundColor: 'var(--accent)', color: 'white' }}
              >
                <Image className="w-4 h-4" /> Imaging
              </button>

              <div className="flex-1" />

              <button
                onClick={handleAdvancePhase}
                disabled={submitting || session.current_phase === 'debrief'}
                className="px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5"
                style={{ backgroundColor: 'var(--accent)', color: 'white', opacity: session.current_phase === 'debrief' ? 0.5 : 1 }}
              >
                Next Phase <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={actionInput}
                onChange={(e) => setActionInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSubmitAction()}
                placeholder={
                  selectedActionType === 'question' ? 'Ask the patient/parent a question...' :
                  selectedActionType === 'exam_request' ? 'Request an exam (e.g., "Check ears")...' :
                  selectedActionType === 'lab_order' ? 'Order a lab (e.g., "CBC")...' :
                  'Order imaging (e.g., "Chest X-ray")...'
                }
                className="flex-1 px-4 py-2 rounded-lg border"
                style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-primary)' }}
                disabled={submitting || session.status === 'paused'}
              />
              <button
                onClick={handleSubmitAction}
                disabled={submitting || !actionInput.trim() || session.status === 'paused'}
                className="px-4 py-2 rounded-lg"
                style={{ backgroundColor: 'var(--accent)', color: 'white', opacity: submitting || !actionInput.trim() ? 0.5 : 1 }}
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Panel - Echo Sidebar & Differential */}
        <div className="w-96 flex flex-col border-l" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-card)' }}>
          {/* Echo Chat */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="p-4 border-b" style={{ borderColor: 'var(--border)' }}>
              <h3 className="font-display font-medium" style={{ color: 'var(--text-primary)' }}>
                Ask Echo
              </h3>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Your AI teaching assistant
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {session.echo_messages.length === 0 ? (
                <p className="text-sm text-center py-4" style={{ color: 'var(--text-tertiary)' }}>
                  Ask Echo for help with the case...
                </p>
              ) : (
                session.echo_messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`p-3 rounded-lg ${msg.role === 'learner' ? 'ml-4' : 'mr-4'}`}
                    style={{
                      backgroundColor: msg.role === 'echo' ? 'var(--accent-light)' : 'var(--bg-secondary)',
                    }}
                  >
                    <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{msg.content}</p>
                  </div>
                ))
              )}
            </div>

            <div className="p-4 border-t" style={{ borderColor: 'var(--border)' }}>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={echoInput}
                  onChange={(e) => setEchoInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAskEcho()}
                  placeholder="Ask Echo..."
                  className="flex-1 px-3 py-2 rounded-lg border text-sm"
                  style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-primary)' }}
                  disabled={submitting || session.status === 'paused'}
                />
                <button
                  onClick={handleAskEcho}
                  disabled={submitting || !echoInput.trim() || session.status === 'paused'}
                  className="px-3 py-2 rounded-lg"
                  style={{ backgroundColor: 'var(--accent)', color: 'white', opacity: submitting || !echoInput.trim() ? 0.5 : 1 }}
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Differential Diagnosis */}
          <div className="border-t p-4" style={{ borderColor: 'var(--border)' }}>
            <h3 className="font-display font-medium mb-3 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <ListChecks className="w-4 h-4" /> My Differential
            </h3>

            {session.differential.length === 0 ? (
              <p className="text-sm mb-3" style={{ color: 'var(--text-tertiary)' }}>
                Add diagnoses to your differential...
              </p>
            ) : (
              <ol className="space-y-2 mb-3">
                {session.differential.map((d, idx) => (
                  <li key={idx} className="flex items-center gap-2 text-sm">
                    <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs" style={{ backgroundColor: 'var(--accent-light)', color: 'var(--accent)' }}>
                      {d.rank}
                    </span>
                    <span style={{ color: 'var(--text-primary)' }}>{d.diagnosis}</span>
                  </li>
                ))}
              </ol>
            )}

            <div className="flex gap-2">
              <input
                type="text"
                value={newDiagnosis}
                onChange={(e) => setNewDiagnosis(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddDifferential()}
                placeholder="Add diagnosis..."
                className="flex-1 px-3 py-1.5 rounded-lg border text-sm"
                style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-primary)' }}
                disabled={submitting || session.status === 'paused'}
              />
              <button
                onClick={handleAddDifferential}
                disabled={submitting || !newDiagnosis.trim() || session.status === 'paused'}
                className="px-3 py-1.5 rounded-lg text-sm"
                style={{ backgroundColor: 'var(--accent)', color: 'white', opacity: submitting || !newDiagnosis.trim() ? 0.5 : 1 }}
              >
                Add
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Teaching Moment Popup */}
      {activeTeachingMoment && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md mx-4 shadow-xl">
            <div className="flex items-start gap-3 mb-4">
              <AlertCircle className="w-6 h-6 flex-shrink-0" style={{ color: 'var(--clinical-warning)' }} />
              <div>
                <h3 className="font-display font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
                  Teaching Moment
                </h3>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  {activeTeachingMoment.message}
                </p>
              </div>
            </div>
            <button
              onClick={() => setActiveTeachingMoment(null)}
              className="w-full py-2 rounded-lg"
              style={{ backgroundColor: 'var(--accent)', color: 'white' }}
            >
              Got it
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
