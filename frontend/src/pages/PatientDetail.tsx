import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Activity, Pill, AlertTriangle, FileText, FlaskConical, Syringe, Mic, MessageSquare } from 'lucide-react';
import { getPatientDetail, PatientDetail as PatientDetailType, GeneratedEncounter } from '../lib/api';
import GenerateEncounterModal from '../components/GenerateEncounterModal';
import EncounterViewer from '../components/EncounterViewer';
import RolePlaySetupModal from '../components/RolePlaySetupModal';
import RolePlayModal from '../components/RolePlayModal';
import { ParentPersona } from '../lib/roleplay';

type Tab = 'summary' | 'notes' | 'results' | 'immunizations';

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<PatientDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('summary');
  const [showEncounterModal, setShowEncounterModal] = useState(false);
  const [generatedEncounter, setGeneratedEncounter] = useState<GeneratedEncounter | null>(null);
  const [showRolePlaySetup, setShowRolePlaySetup] = useState(false);
  const [rolePlayConfig, setRolePlayConfig] = useState<{ chiefComplaint: string; parentPersona: ParentPersona } | null>(null);

  useEffect(() => {
    if (id) loadPatient(id);
  }, [id]);

  async function loadPatient(patientId: string) {
    try {
      setLoading(true);
      const detail = await getPatientDetail(patientId);
      setData(detail);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load patient');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div
          className="w-8 h-8 border-4 rounded-full animate-spin"
          style={{
            borderColor: 'var(--accent-light)',
            borderTopColor: 'var(--accent)'
          }}
        />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8">
        <div
          className="p-4 rounded-lg"
          style={{
            backgroundColor: 'rgba(155, 44, 44, 0.1)',
            border: '1px solid rgba(155, 44, 44, 0.2)',
            color: 'var(--clinical-error)'
          }}
        >
          {error || 'Patient not found'}
        </div>
      </div>
    );
  }

  const { patient, conditions, medications, allergies, immunizations, recent_encounters, recent_observations } = data;

  const tabs = [
    { id: 'summary' as Tab, label: 'Summary' },
    { id: 'notes' as Tab, label: 'Notes', count: recent_encounters.length },
    { id: 'results' as Tab, label: 'Results', count: recent_observations.length },
    { id: 'immunizations' as Tab, label: 'Immunizations', count: immunizations.length },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-8 py-6" style={{ backgroundColor: 'var(--bg-card)', borderBottom: '1px solid var(--border)' }}>
        <button
          onClick={() => navigate('/patients')}
          className="flex items-center mb-4 transition-colors"
          style={{ color: 'var(--text-secondary)' }}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--accent)'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Patients
        </button>

        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center"
              style={{ backgroundColor: 'var(--accent-light)' }}
            >
              <span className="text-xl font-medium" style={{ color: 'var(--accent)' }}>
                {patient.given_names[0]?.[0]}{patient.family_name[0]}
              </span>
            </div>
            <div className="ml-4">
              <h1 className="text-2xl font-display font-semibold" style={{ color: 'var(--text-primary)' }}>
                {patient.given_names.join(' ')} {patient.family_name}
              </h1>
              <p style={{ color: 'var(--text-secondary)' }}>
                {patient.age_years} years old &bull; {patient.sex_at_birth} &bull; DOB: {patient.date_of_birth}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowRolePlaySetup(true)}
              className="flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              style={{
                backgroundColor: 'var(--accent)',
                color: 'var(--text-inverse)',
              }}
              onMouseEnter={e => e.currentTarget.style.opacity = '0.9'}
              onMouseLeave={e => e.currentTarget.style.opacity = '1'}
            >
              <MessageSquare className="w-4 h-4 mr-2" />
              Practice Encounter
            </button>
            <button
              onClick={() => setShowEncounterModal(true)}
              className="flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                color: 'var(--text-secondary)',
              }}
              onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--border)'}
              onMouseLeave={e => e.currentTarget.style.backgroundColor = 'var(--bg-secondary)'}
            >
              <Mic className="w-4 h-4 mr-2" />
              Generate Script
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mt-6 -mb-px" style={{ borderBottom: '1px solid var(--border)' }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="px-4 py-2 text-sm font-medium transition-colors"
              style={{
                borderBottom: `2px solid ${activeTab === tab.id ? 'var(--accent)' : 'transparent'}`,
                color: activeTab === tab.id ? 'var(--accent)' : 'var(--text-tertiary)',
                marginBottom: '-1px'
              }}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span
                  className="ml-2 px-2 py-0.5 text-xs rounded-full"
                  style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
                >
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-8">
        {activeTab === 'summary' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Active Conditions */}
            <div className="card p-4">
              <div className="flex items-center mb-4">
                <Activity className="w-5 h-5 mr-2" style={{ color: 'var(--clinical-error)' }} />
                <h3 className="font-display font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Active Problems
                </h3>
              </div>
              {conditions.filter(c => c.clinical_status === 'active').length === 0 ? (
                <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>No active problems</p>
              ) : (
                <ul className="space-y-2">
                  {conditions.filter(c => c.clinical_status === 'active').map(c => (
                    <li key={c.id} className="text-sm">
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{c.display_name}</span>
                      {c.onset_date && (
                        <span className="ml-2" style={{ color: 'var(--text-tertiary)' }}>since {c.onset_date}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Medications */}
            <div className="card p-4">
              <div className="flex items-center mb-4">
                <Pill className="w-5 h-5 mr-2" style={{ color: 'var(--accent)' }} />
                <h3 className="font-display font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Medications
                </h3>
              </div>
              {medications.filter(m => m.status === 'active').length === 0 ? (
                <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>No active medications</p>
              ) : (
                <ul className="space-y-2">
                  {medications.filter(m => m.status === 'active').map(m => (
                    <li key={m.id} className="text-sm">
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{m.display_name}</span>
                      {m.dose_quantity && (
                        <span className="ml-2" style={{ color: 'var(--text-tertiary)' }}>
                          {m.dose_quantity} {m.dose_unit} {m.frequency}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Allergies */}
            <div className="card p-4">
              <div className="flex items-center mb-4">
                <AlertTriangle className="w-5 h-5 mr-2" style={{ color: 'var(--clinical-warning)' }} />
                <h3 className="font-display font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Allergies
                </h3>
              </div>
              {allergies.length === 0 ? (
                <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>No known allergies</p>
              ) : (
                <ul className="space-y-2">
                  {allergies.map(a => (
                    <li key={a.id} className="text-sm">
                      <span
                        className="font-medium"
                        style={{ color: a.criticality === 'high' ? 'var(--clinical-error)' : 'var(--text-primary)' }}
                      >
                        {a.display_name}
                      </span>
                      {a.reactions?.length ? (
                        <span className="ml-2" style={{ color: 'var(--text-tertiary)' }}>
                          ({a.reactions.map(r => r.manifestation).join(', ')})
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Contact Info */}
            <div className="card p-4">
              <h3 className="font-display font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
                Contact Information
              </h3>
              <dl className="space-y-2 text-sm">
                {patient.phone && (
                  <div>
                    <dt style={{ color: 'var(--text-tertiary)' }}>Phone</dt>
                    <dd style={{ color: 'var(--text-primary)' }}>{patient.phone}</dd>
                  </div>
                )}
                {patient.email && (
                  <div>
                    <dt style={{ color: 'var(--text-tertiary)' }}>Email</dt>
                    <dd style={{ color: 'var(--text-primary)' }}>{patient.email}</dd>
                  </div>
                )}
                {patient.address && (
                  <div>
                    <dt style={{ color: 'var(--text-tertiary)' }}>Address</dt>
                    <dd style={{ color: 'var(--text-primary)' }}>
                      {patient.address.line1}
                      {patient.address.line2 && <>, {patient.address.line2}</>}
                      <br />
                      {patient.address.city}, {patient.address.state} {patient.address.postal_code}
                    </dd>
                  </div>
                )}
                {patient.emergency_contact && (
                  <div>
                    <dt style={{ color: 'var(--text-tertiary)' }}>Emergency Contact</dt>
                    <dd style={{ color: 'var(--text-primary)' }}>
                      {patient.emergency_contact.name}
                      {patient.emergency_contact.relationship && (
                        <> ({patient.emergency_contact.relationship})</>
                      )}
                      {patient.emergency_contact.phone && <> &bull; {patient.emergency_contact.phone}</>}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </div>
        )}

        {activeTab === 'notes' && (
          <div className="space-y-4">
            {recent_encounters.length === 0 ? (
              <div className="text-center py-12" style={{ color: 'var(--text-tertiary)' }}>
                <FileText className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
                No encounters on file
              </div>
            ) : (
              recent_encounters.map(enc => (
                <div key={enc.id} className="card p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="font-medium capitalize" style={{ color: 'var(--text-primary)' }}>
                        {enc.encounter_type?.replace(/-/g, ' ') || 'Visit'}
                      </span>
                      <span className="ml-2" style={{ color: 'var(--text-tertiary)' }}>
                        {new Date(enc.date).toLocaleDateString()}
                      </span>
                    </div>
                    {enc.provider_name && (
                      <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
                        {enc.provider_name}
                      </span>
                    )}
                  </div>
                  {enc.chief_complaint && (
                    <p className="text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>
                      <strong>CC:</strong> {enc.chief_complaint}
                    </p>
                  )}
                  {enc.narrative_note && (
                    <p className="text-sm whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                      {enc.narrative_note}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'results' && (
          <div className="space-y-4">
            {recent_observations.length === 0 ? (
              <div className="text-center py-12" style={{ color: 'var(--text-tertiary)' }}>
                <FlaskConical className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
                No results on file
              </div>
            ) : (
              <div className="card overflow-hidden">
                <table className="min-w-full" style={{ borderCollapse: 'separate' }}>
                  <thead style={{ backgroundColor: 'var(--bg-secondary)' }}>
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-secondary)' }}>Test</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-secondary)' }}>Result</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-secondary)' }}>Status</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-secondary)' }}>Date</th>
                    </tr>
                  </thead>
                  <tbody style={{ backgroundColor: 'var(--bg-card)' }}>
                    {recent_observations.map((obs, idx) => (
                      <tr key={obs.id} style={{ borderTop: idx > 0 ? '1px solid var(--border-light)' : 'none' }}>
                        <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-primary)' }}>{obs.display_name}</td>
                        <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-primary)' }}>{obs.display_value}</td>
                        <td className="px-4 py-3">
                          {obs.interpretation && (
                            <span
                              className="text-xs px-2 py-1 rounded-full"
                              style={{
                                backgroundColor: obs.interpretation === 'normal' ? 'rgba(45, 106, 79, 0.1)'
                                  : obs.interpretation === 'abnormal' ? 'rgba(198, 112, 48, 0.1)'
                                  : obs.interpretation === 'critical' ? 'rgba(155, 44, 44, 0.1)'
                                  : 'var(--bg-secondary)',
                                color: obs.interpretation === 'normal' ? 'var(--clinical-success)'
                                  : obs.interpretation === 'abnormal' ? 'var(--clinical-warning)'
                                  : obs.interpretation === 'critical' ? 'var(--clinical-error)'
                                  : 'var(--text-secondary)'
                              }}
                            >
                              {obs.interpretation}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                          {obs.effective_date ? new Date(obs.effective_date).toLocaleDateString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'immunizations' && (
          <div className="space-y-4">
            {immunizations.length === 0 ? (
              <div className="text-center py-12" style={{ color: 'var(--text-tertiary)' }}>
                <Syringe className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
                No immunizations on file
              </div>
            ) : (
              <div className="card overflow-hidden">
                <table className="min-w-full" style={{ borderCollapse: 'separate' }}>
                  <thead style={{ backgroundColor: 'var(--bg-secondary)' }}>
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-secondary)' }}>Vaccine</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-secondary)' }}>Date</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-secondary)' }}>Dose</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-secondary)' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody style={{ backgroundColor: 'var(--bg-card)' }}>
                    {immunizations.map((imm: any, idx: number) => (
                      <tr key={imm.id} style={{ borderTop: idx > 0 ? '1px solid var(--border-light)' : 'none' }}>
                        <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-primary)' }}>{imm.display_name}</td>
                        <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-tertiary)' }}>{imm.date}</td>
                        <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                          {imm.dose_number ? `#${imm.dose_number}` : '—'}
                          {imm.series_doses ? ` of ${imm.series_doses}` : ''}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className="text-xs px-2 py-1 rounded-full"
                            style={{
                              backgroundColor: imm.status === 'completed' ? 'rgba(45, 106, 79, 0.1)' : 'var(--bg-secondary)',
                              color: imm.status === 'completed' ? 'var(--clinical-success)' : 'var(--text-secondary)'
                            }}
                          >
                            {imm.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Generate Encounter Modal */}
      {showEncounterModal && (
        <GenerateEncounterModal
          patientData={data}
          onClose={() => setShowEncounterModal(false)}
          onGenerated={(encounter) => {
            setShowEncounterModal(false);
            setGeneratedEncounter(encounter);
          }}
        />
      )}

      {/* Encounter Viewer */}
      {generatedEncounter && (
        <EncounterViewer
          encounter={generatedEncounter}
          onClose={() => setGeneratedEncounter(null)}
          onRegenerate={() => {
            setGeneratedEncounter(null);
            setShowEncounterModal(true);
          }}
        />
      )}

      {/* Role-Play Setup Modal */}
      {showRolePlaySetup && (
        <RolePlaySetupModal
          patientData={data}
          onClose={() => setShowRolePlaySetup(false)}
          onStart={(chiefComplaint, parentPersona) => {
            setShowRolePlaySetup(false);
            setRolePlayConfig({ chiefComplaint, parentPersona });
          }}
        />
      )}

      {/* Role-Play Chat Modal */}
      {rolePlayConfig && (
        <RolePlayModal
          patientData={data}
          chiefComplaint={rolePlayConfig.chiefComplaint}
          parentPersona={rolePlayConfig.parentPersona}
          onClose={() => setRolePlayConfig(null)}
        />
      )}
    </div>
  );
}
