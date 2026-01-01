import { useState } from 'react';
import { X, Save, RefreshCw, User, Stethoscope, Loader2, Check } from 'lucide-react';
import { GeneratedEncounter, saveEncounter, ScriptLine } from '../lib/api';

interface EncounterViewerProps {
  encounter: GeneratedEncounter;
  onClose: () => void;
  onRegenerate: () => void;
}

export default function EncounterViewer({
  encounter,
  onClose,
  onRegenerate,
}: EncounterViewerProps) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      await saveEncounter({
        patient_id: encounter.patient_id,
        syrinx_id: encounter.id,
        encounter_type: encounter.metadata.encounter_type,
        chief_complaint: encounter.chief_complaint,
        metadata: encounter.metadata,
        script: encounter.script,
      });
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save encounter');
    } finally {
      setSaving(false);
    }
  };

  const getSpeakerIcon = (speaker: string) => {
    const lowerSpeaker = speaker.toLowerCase();
    if (lowerSpeaker.includes('doctor') || lowerSpeaker.includes('dr.') || lowerSpeaker.includes('physician')) {
      return <Stethoscope className="w-4 h-4" />;
    }
    return <User className="w-4 h-4" />;
  };

  const getSpeakerColor = (speaker: string) => {
    const lowerSpeaker = speaker.toLowerCase();
    if (lowerSpeaker.includes('doctor') || lowerSpeaker.includes('dr.') || lowerSpeaker.includes('physician')) {
      return 'var(--accent)';
    }
    return 'var(--accent-tertiary)';
  };

  const getSpeakerBgColor = (speaker: string) => {
    const lowerSpeaker = speaker.toLowerCase();
    if (lowerSpeaker.includes('doctor') || lowerSpeaker.includes('dr.') || lowerSpeaker.includes('physician')) {
      return 'var(--accent-light)';
    }
    return 'rgba(115, 140, 130, 0.15)';
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[90vh] flex flex-col rounded-xl shadow-xl"
        style={{ backgroundColor: 'var(--bg-card)' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4 flex-shrink-0"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          <div>
            <h2 className="text-lg font-display font-semibold" style={{ color: 'var(--text-primary)' }}>
              Generated Encounter
            </h2>
            <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
              {encounter.patient_name} &bull; {encounter.metadata.encounter_type} &bull; {encounter.chief_complaint}
            </p>
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

        {/* Script Content */}
        <div className="flex-1 overflow-auto p-6 space-y-4">
          {encounter.script.map((line: ScriptLine, index: number) => (
            <div key={index} className="flex gap-3">
              {/* Speaker Icon */}
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ backgroundColor: getSpeakerBgColor(line.speaker), color: getSpeakerColor(line.speaker) }}
              >
                {getSpeakerIcon(line.speaker)}
              </div>

              {/* Content */}
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium" style={{ color: getSpeakerColor(line.speaker) }}>
                    {line.speaker}
                  </span>
                  {line.direction && (
                    <span
                      className="text-xs italic px-2 py-0.5 rounded"
                      style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-tertiary)' }}
                    >
                      {line.direction}
                    </span>
                  )}
                </div>
                <p className="text-sm" style={{ color: 'var(--text-primary)' }}>
                  {line.line}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div
          className="flex items-center justify-between px-6 py-4 flex-shrink-0"
          style={{ borderTop: '1px solid var(--border)' }}
        >
          <div className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
            {encounter.script.length} lines &bull; {encounter.metadata.duration} duration
          </div>

          <div className="flex gap-3">
            {error && (
              <span className="text-sm" style={{ color: 'var(--clinical-error)' }}>
                {error}
              </span>
            )}

            <button
              onClick={onRegenerate}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                color: 'var(--text-secondary)',
              }}
              disabled={saving}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Regenerate
            </button>

            <button
              onClick={handleSave}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center"
              style={{
                backgroundColor: saved ? 'var(--clinical-success)' : 'var(--accent)',
                color: 'var(--text-inverse)',
                opacity: saving ? 0.6 : 1,
              }}
              disabled={saving || saved}
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : saved ? (
                <>
                  <Check className="w-4 h-4 mr-2" />
                  Saved
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Encounter
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
