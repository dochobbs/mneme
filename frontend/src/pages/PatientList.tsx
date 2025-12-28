import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, User, ChevronRight } from 'lucide-react';
import { getPatients, PatientSummary } from '../lib/api';

export default function PatientList() {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    loadPatients();
  }, []);

  async function loadPatients() {
    try {
      setLoading(true);
      const data = await getPatients(100);
      setPatients(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load patients');
      setPatients([]);
    } finally {
      setLoading(false);
    }
  }

  const filteredPatients = patients.filter(p => {
    const searchLower = search.toLowerCase();
    const fullName = `${p.given_names.join(' ')} ${p.family_name}`.toLowerCase();
    return fullName.includes(searchLower);
  });

  function formatAge(years: number): string {
    if (years < 1) return '<1 yr';
    if (years === 1) return '1 yr';
    return `${years} yrs`;
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-display font-semibold" style={{ color: 'var(--text-primary)' }}>Patients</h1>
        <p style={{ color: 'var(--text-secondary)' }} className="mt-1">View and manage patient records</p>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
          <input
            type="text"
            placeholder="Search patients..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div
          className="mb-6 p-4 rounded-lg"
          style={{
            backgroundColor: 'rgba(155, 44, 44, 0.1)',
            border: '1px solid rgba(155, 44, 44, 0.2)',
            color: 'var(--clinical-error)'
          }}
        >
          {error}
          <button
            onClick={loadPatients}
            className="ml-4 underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div
            className="w-8 h-8 border-4 rounded-full animate-spin"
            style={{
              borderColor: 'var(--accent-light)',
              borderTopColor: 'var(--accent)'
            }}
          />
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && filteredPatients.length === 0 && (
        <div className="text-center py-16 card p-8">
          <User className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
          <h3 className="text-lg font-display font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
            No patients found
          </h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            {search ? 'Try a different search term' : 'Import patient data to get started'}
          </p>
        </div>
      )}

      {/* Patient list */}
      {!loading && !error && filteredPatients.length > 0 && (
        <div className="card overflow-hidden">
          <table className="min-w-full" style={{ borderCollapse: 'separate' }}>
            <thead style={{ backgroundColor: 'var(--bg-secondary)' }}>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                  Patient
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                  Age / DOB
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                  Sex
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                  Phone
                </th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody style={{ backgroundColor: 'var(--bg-card)' }}>
              {filteredPatients.map((patient, idx) => (
                <tr
                  key={patient.id}
                  onClick={() => navigate(`/patients/${patient.id}`)}
                  className="cursor-pointer transition-colors hover:opacity-90"
                  style={{
                    borderTop: idx > 0 ? '1px solid var(--border-light)' : 'none',
                  }}
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--accent-light)'}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = 'var(--bg-card)'}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div
                        className="w-10 h-10 rounded-full flex items-center justify-center"
                        style={{ backgroundColor: 'var(--accent-light)' }}
                      >
                        <span className="font-medium" style={{ color: 'var(--accent)' }}>
                          {patient.given_names[0]?.[0]}{patient.family_name[0]}
                        </span>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                          {patient.given_names.join(' ')} {patient.family_name}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm" style={{ color: 'var(--text-primary)' }}>{formatAge(patient.age_years)}</div>
                    <div className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{patient.date_of_birth}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm capitalize" style={{ color: 'var(--text-secondary)' }}>
                      {patient.sex_at_birth || '—'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm" style={{ color: 'var(--text-tertiary)' }}>
                    {patient.phone || '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <ChevronRight className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
