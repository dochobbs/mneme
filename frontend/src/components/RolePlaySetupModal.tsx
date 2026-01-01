import { useState } from 'react';
import { X, MessageSquare, Stethoscope } from 'lucide-react';
import { PatientDetail } from '../lib/api';
import { ParentPersona, PARENT_PERSONAS } from '../lib/roleplay';

interface RolePlaySetupModalProps {
  patientData: PatientDetail;
  onClose: () => void;
  onStart: (chiefComplaint: string, parentPersona: ParentPersona) => void;
}

export default function RolePlaySetupModal({
  patientData,
  onClose,
  onStart,
}: RolePlaySetupModalProps) {
  const { patient, allergies, medications, conditions } = patientData;

  const [chiefComplaint, setChiefComplaint] = useState('');
  const [parentPersona, setParentPersona] = useState<ParentPersona>('anxious');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chiefComplaint.trim()) return;
    onStart(chiefComplaint.trim(), parentPersona);
  };

  const activeAllergies = allergies.filter(a => a.display_name);
  const activeMedications = medications.filter(m => m.status === 'active');
  const activeConditions = conditions.filter(c => c.clinical_status === 'active');

  const fullName = `${patient.given_names.join(' ')} ${patient.family_name}`;

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
            <MessageSquare className="w-5 h-5 mr-2" style={{ color: 'var(--accent)' }} />
            <h2 className="text-lg font-display font-semibold" style={{ color: 'var(--text-primary)' }}>
              Practice Encounter
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
          {/* Instructions */}
          <div
            className="flex items-start p-3 rounded-lg"
            style={{ backgroundColor: 'var(--accent-light)' }}
          >
            <Stethoscope className="w-5 h-5 mr-3 mt-0.5 flex-shrink-0" style={{ color: 'var(--accent)' }} />
            <p className="text-sm" style={{ color: 'var(--text-primary)' }}>
              You'll practice as the <strong>doctor</strong>. The AI will play the parent based on this patient's chart.
            </p>
          </div>

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
              placeholder="e.g., fever and fussiness for 2 days"
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
              }}
              autoFocus
              required
            />
          </div>

          {/* Parent Persona */}
          <div>
            <label
              className="block text-sm font-medium mb-1"
              style={{ color: 'var(--text-secondary)' }}
            >
              Parent Persona
            </label>
            <select
              value={parentPersona}
              onChange={e => setParentPersona(e.target.value as ParentPersona)}
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
              }}
            >
              {PARENT_PERSONAS.map(persona => (
                <option key={persona.value} value={persona.value}>
                  {persona.label}
                </option>
              ))}
            </select>
            <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
              {PARENT_PERSONAS.find(p => p.value === parentPersona)?.description}
            </p>
          </div>

          {/* Patient Context */}
          <div
            className="p-3 rounded-lg"
            style={{ backgroundColor: 'var(--bg-secondary)' }}
          >
            <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
              Patient context:
            </p>
            <ul className="text-xs space-y-1" style={{ color: 'var(--text-tertiary)' }}>
              <li>
                <strong>{fullName}</strong>, {patient.age_years} years, {patient.sex_at_birth}
              </li>
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
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center"
              style={{
                backgroundColor: 'var(--accent)',
                color: 'var(--text-inverse)',
                opacity: !chiefComplaint.trim() ? 0.6 : 1,
              }}
              disabled={!chiefComplaint.trim()}
            >
              <MessageSquare className="w-4 h-4 mr-2" />
              Start Practice
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
