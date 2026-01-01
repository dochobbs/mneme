import { useState } from 'react';
import { X, Mic, Loader2, AlertCircle } from 'lucide-react';
import {
  generateEncounter,
  GenerateEncounterRequest,
  GeneratedEncounter,
  PatientDetail,
} from '../lib/api';

interface GenerateEncounterModalProps {
  patientData: PatientDetail;
  onClose: () => void;
  onGenerated: (encounter: GeneratedEncounter) => void;
}

export default function GenerateEncounterModal({
  patientData,
  onClose,
  onGenerated,
}: GenerateEncounterModalProps) {
  const { patient, allergies, medications, conditions } = patientData;

  const [chiefComplaint, setChiefComplaint] = useState('');
  const [encounterType, setEncounterType] = useState<GenerateEncounterRequest['encounter_type']>('acute');
  const [duration, setDuration] = useState<GenerateEncounterRequest['duration']>('medium');
  const [errorType, setErrorType] = useState<GenerateEncounterRequest['error_type']>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chiefComplaint.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const encounter = await generateEncounter({
        patient_id: patient.id,
        chief_complaint: chiefComplaint,
        encounter_type: encounterType,
        duration,
        error_type: errorType,
      });
      onGenerated(encounter);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate encounter');
    } finally {
      setLoading(false);
    }
  };

  const activeAllergies = allergies.filter(a => a.display_name);
  const activeMedications = medications.filter(m => m.status === 'active');
  const activeConditions = conditions.filter(c => c.clinical_status === 'active');

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl shadow-xl"
        style={{ backgroundColor: 'var(--bg-card)' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          <div className="flex items-center">
            <Mic className="w-5 h-5 mr-2" style={{ color: 'var(--accent)' }} />
            <h2 className="text-lg font-display font-semibold" style={{ color: 'var(--text-primary)' }}>
              Generate Voice Encounter
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg transition-colors"
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--bg-secondary)'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Chief Complaint */}
          <div>
            <label
              className="block text-sm font-medium mb-1"
              style={{ color: 'var(--text-secondary)' }}
            >
              Chief Complaint *
            </label>
            <input
              type="text"
              value={chiefComplaint}
              onChange={e => setChiefComplaint(e.target.value)}
              placeholder="e.g., fever x2 days, irritable"
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
              }}
              disabled={loading}
              required
            />
          </div>

          {/* Encounter Type */}
          <div>
            <label
              className="block text-sm font-medium mb-1"
              style={{ color: 'var(--text-secondary)' }}
            >
              Encounter Type
            </label>
            <select
              value={encounterType}
              onChange={e => setEncounterType(e.target.value as GenerateEncounterRequest['encounter_type'])}
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
              }}
              disabled={loading}
            >
              <option value="acute">Acute Visit</option>
              <option value="well-child">Well-Child Visit</option>
              <option value="mental-health">Mental Health</option>
              <option value="follow-up">Follow-up</option>
            </select>
          </div>

          {/* Duration */}
          <div>
            <label
              className="block text-sm font-medium mb-1"
              style={{ color: 'var(--text-secondary)' }}
            >
              Duration
            </label>
            <select
              value={duration}
              onChange={e => setDuration(e.target.value as GenerateEncounterRequest['duration'])}
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
              }}
              disabled={loading}
            >
              <option value="short">Short (2-3 min)</option>
              <option value="medium">Medium (4-5 min)</option>
              <option value="long">Long (6-8 min)</option>
            </select>
          </div>

          {/* Error Injection (optional) */}
          <div>
            <label
              className="block text-sm font-medium mb-1"
              style={{ color: 'var(--text-secondary)' }}
            >
              Error Injection (optional)
            </label>
            <select
              value={errorType || ''}
              onChange={e => setErrorType(e.target.value as GenerateEncounterRequest['error_type'] || null)}
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
              }}
              disabled={loading}
            >
              <option value="">None</option>
              <option value="clinical">Clinical Error</option>
              <option value="communication">Communication Error</option>
            </select>
          </div>

          {/* Patient Context */}
          <div
            className="p-3 rounded-lg"
            style={{ backgroundColor: 'var(--bg-secondary)' }}
          >
            <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
              Patient context will include:
            </p>
            <ul className="text-xs space-y-1" style={{ color: 'var(--text-tertiary)' }}>
              <li>
                <strong>Allergies:</strong>{' '}
                {activeAllergies.length > 0
                  ? activeAllergies.map(a => a.display_name).join(', ')
                  : 'None known'}
              </li>
              <li>
                <strong>Medications:</strong>{' '}
                {activeMedications.length > 0
                  ? activeMedications.map(m => m.display_name).join(', ')
                  : 'None active'}
              </li>
              <li>
                <strong>Conditions:</strong>{' '}
                {activeConditions.length > 0
                  ? activeConditions.map(c => c.display_name).join(', ')
                  : 'None active'}
              </li>
            </ul>
          </div>

          {/* Error Message */}
          {error && (
            <div
              className="flex items-center p-3 rounded-lg"
              style={{
                backgroundColor: 'rgba(155, 44, 44, 0.1)',
                border: '1px solid rgba(155, 44, 44, 0.2)',
              }}
            >
              <AlertCircle className="w-4 h-4 mr-2" style={{ color: 'var(--clinical-error)' }} />
              <span className="text-sm" style={{ color: 'var(--clinical-error)' }}>
                {error}
              </span>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                color: 'var(--text-secondary)',
              }}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center"
              style={{
                backgroundColor: 'var(--accent)',
                color: 'var(--text-inverse)',
                opacity: loading || !chiefComplaint.trim() ? 0.6 : 1,
              }}
              disabled={loading || !chiefComplaint.trim()}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Mic className="w-4 h-4 mr-2" />
                  Generate Encounter
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
