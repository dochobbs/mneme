import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, Clock, User, ChevronLeft, ChevronRight } from 'lucide-react';
import { format, addDays, subDays } from 'date-fns';
import { getSchedule, updateAppointmentStatus, Appointment } from '../lib/api';

export default function Schedule() {
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSchedule();
  }, [selectedDate]);

  async function loadSchedule() {
    try {
      setLoading(true);
      const dateStr = format(selectedDate, 'yyyy-MM-dd');
      const data = await getSchedule(`${dateStr}T00:00:00`, `${dateStr}T23:59:59`);
      setAppointments(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load schedule');
      setAppointments([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusChange(id: string, status: string) {
    try {
      await updateAppointmentStatus(id, status);
      loadSchedule();
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  }

  function getStatusStyle(status: string): { bg: string; color: string } {
    switch (status) {
      case 'arrived': return { bg: 'rgba(198, 112, 48, 0.1)', color: 'var(--clinical-warning)' };
      case 'in-progress': return { bg: 'rgba(45, 90, 74, 0.1)', color: 'var(--accent)' };
      case 'completed': return { bg: 'rgba(45, 106, 79, 0.1)', color: 'var(--clinical-success)' };
      case 'cancelled': return { bg: 'var(--bg-secondary)', color: 'var(--text-tertiary)' };
      case 'no-show': return { bg: 'rgba(155, 44, 44, 0.1)', color: 'var(--clinical-error)' };
      default: return { bg: 'var(--bg-secondary)', color: 'var(--text-secondary)' };
    }
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-display font-semibold" style={{ color: 'var(--text-primary)' }}>
            Schedule
          </h1>
          <p style={{ color: 'var(--text-secondary)' }} className="mt-1">
            Today's appointments
          </p>
        </div>

        {/* Date navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedDate(d => subDays(d, 1))}
            className="p-2 rounded-lg transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--bg-secondary)'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={() => setSelectedDate(new Date())}
            className="px-4 py-2 rounded-lg flex items-center gap-2 card"
          >
            <Calendar className="w-4 h-4" style={{ color: 'var(--accent)' }} />
            <span style={{ color: 'var(--text-primary)' }}>
              {format(selectedDate, 'EEEE, MMMM d, yyyy')}
            </span>
          </button>
          <button
            onClick={() => setSelectedDate(d => addDays(d, 1))}
            className="p-2 rounded-lg transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--bg-secondary)'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <ChevronRight className="w-5 h-5" />
          </button>
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
            onClick={loadSchedule}
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
      {!loading && !error && appointments.length === 0 && (
        <div className="text-center py-16 card p-8">
          <Calendar className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
          <h3 className="text-lg font-display font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
            No appointments
          </h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            No appointments scheduled for this day
          </p>
        </div>
      )}

      {/* Appointments list */}
      {!loading && !error && appointments.length > 0 && (
        <div className="space-y-4">
          {appointments.map(apt => {
            const statusStyle = getStatusStyle(apt.status);
            return (
              <div
                key={apt.id}
                className="card p-4 transition-shadow hover:shadow-md"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    {/* Time */}
                    <div className="text-center min-w-[80px]">
                      <div className="flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
                        <Clock className="w-4 h-4" />
                        <span className="font-medium">
                          {format(new Date(apt.scheduled_time), 'h:mm a')}
                        </span>
                      </div>
                      <div className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
                        {apt.duration_minutes} min
                      </div>
                    </div>

                    {/* Patient info */}
                    <div>
                      <div
                        onClick={() => apt.patient_id && navigate(`/patients/${apt.patient_id}`)}
                        className="flex items-center gap-2 cursor-pointer transition-colors"
                        style={{ color: 'var(--text-primary)' }}
                        onMouseEnter={e => e.currentTarget.style.color = 'var(--accent)'}
                        onMouseLeave={e => e.currentTarget.style.color = 'var(--text-primary)'}
                      >
                        <User className="w-4 h-4" />
                        <span className="font-medium">
                          {apt.patient_name || 'Unknown Patient'}
                        </span>
                      </div>
                      {apt.reason && (
                        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                          {apt.reason}
                        </p>
                      )}
                      {apt.appointment_type && (
                        <span
                          className="inline-block mt-2 text-xs px-2 py-1 rounded capitalize"
                          style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
                        >
                          {apt.appointment_type.replace(/-/g, ' ')}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Status and actions */}
                  <div className="flex items-center gap-2">
                    <span
                      className="text-xs px-2 py-1 rounded-full font-medium"
                      style={{ backgroundColor: statusStyle.bg, color: statusStyle.color }}
                    >
                      {apt.status.replace(/-/g, ' ')}
                    </span>
                    <select
                      value={apt.status}
                      onChange={e => handleStatusChange(apt.id, e.target.value)}
                      className="input text-sm py-1"
                      style={{ width: 'auto' }}
                    >
                      <option value="scheduled">Scheduled</option>
                      <option value="arrived">Arrived</option>
                      <option value="in-progress">In Progress</option>
                      <option value="completed">Completed</option>
                      <option value="cancelled">Cancelled</option>
                      <option value="no-show">No Show</option>
                    </select>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
