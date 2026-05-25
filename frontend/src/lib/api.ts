/**
 * API client for Mneme EMR backend.
 */

import { getAccessToken } from '../context/AuthContext';

const API_BASE = '/api';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  // Get auth token if available
  const token = getAccessToken();

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options?.headers,
    },
  });

  // Handle 401 Unauthorized - redirect to login
  if (response.status === 401) {
    // Clear stored tokens and redirect
    localStorage.removeItem('mneme_access_token');
    localStorage.removeItem('mneme_refresh_token');
    localStorage.removeItem('mneme_user');
    window.location.href = '/login';
    throw new Error('Session expired');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Types
export interface PatientSummary {
  id: string;
  given_names: string[];
  family_name: string;
  date_of_birth: string;
  sex_at_birth?: string;
  phone?: string;
  full_name: string;
  age_years: number;
}

export interface Patient extends PatientSummary {
  external_id?: string;
  gender_identity?: string;
  race?: string[];
  ethnicity?: string;
  preferred_language: string;
  email?: string;
  address?: {
    line1?: string;
    line2?: string;
    city?: string;
    state?: string;
    postal_code?: string;
  };
  emergency_contact?: {
    name: string;
    relationship?: string;
    phone?: string;
  };
}

export interface Condition {
  id: string;
  display_name: string;
  clinical_status: string;
  severity?: string;
  onset_date?: string;
}

export interface Medication {
  id: string;
  display_name: string;
  status: string;
  dose_quantity?: string;
  dose_unit?: string;
  frequency?: string;
  route?: string;
}

export interface Allergy {
  id: string;
  display_name: string;
  category?: string;
  criticality: string;
  reactions?: { manifestation: string; severity?: string }[];
}

export interface Encounter {
  id: string;
  encounter_type?: string;
  date: string;
  chief_complaint?: string;
  provider_name?: string;
  narrative_note?: string;
}

export interface Observation {
  id: string;
  category: string;
  display_name: string;
  value_quantity?: number;
  value_string?: string;
  value_unit?: string;
  interpretation?: string;
  effective_date?: string;
  display_value: string;
}

export interface PatientDetail {
  patient: Patient;
  conditions: Condition[];
  medications: Medication[];
  allergies: Allergy[];
  immunizations: any[];
  recent_encounters: Encounter[];
  recent_observations: Observation[];
  growth_data: any[];
}

export interface Appointment {
  id: string;
  patient_id: string;
  scheduled_time: string;
  duration_minutes: number;
  appointment_type?: string;
  status: string;
  provider_name?: string;
  reason?: string;
  patient_name?: string;
  patient_dob?: string;
}

export interface Message {
  id: string;
  patient_id: string;
  sent_datetime: string;
  sender_name: string;
  subject?: string;
  message_body: string;
  reply_body?: string;
  replier_name?: string;
  replier_role?: string;
  category?: string;
  is_read: boolean;
  patient_name?: string;
}

// API Functions

// Patients
export async function getPatients(limit = 50, offset = 0): Promise<PatientSummary[]> {
  return fetchAPI<PatientSummary[]>(`/patients?limit=${limit}&offset=${offset}`);
}

export async function getPatient(id: string): Promise<Patient> {
  return fetchAPI<Patient>(`/patients/${id}`);
}

export async function getPatientDetail(id: string): Promise<PatientDetail> {
  return fetchAPI<PatientDetail>(`/patients/${id}/detail`);
}

export async function getPatientEncounters(id: string): Promise<Encounter[]> {
  return fetchAPI<Encounter[]>(`/patients/${id}/encounters`);
}

export async function getPatientObservations(id: string, category?: string): Promise<Observation[]> {
  const query = category ? `?category=${category}` : '';
  return fetchAPI<Observation[]>(`/patients/${id}/observations${query}`);
}

// Schedule
export async function getTodaySchedule(): Promise<Appointment[]> {
  return fetchAPI<Appointment[]>('/schedule/today');
}

export async function getSchedule(startDate?: string, endDate?: string): Promise<Appointment[]> {
  const params = new URLSearchParams();
  if (startDate) params.set('start_date', startDate);
  if (endDate) params.set('end_date', endDate);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchAPI<Appointment[]>(`/schedule${query}`);
}

export async function updateAppointmentStatus(id: string, status: string): Promise<Appointment> {
  return fetchAPI<Appointment>(`/schedule/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

// Messages
export async function getMessages(limit = 50, unreadOnly = false): Promise<Message[]> {
  return fetchAPI<Message[]>(`/messages?limit=${limit}&unread_only=${unreadOnly}`);
}

export async function getUnreadCount(): Promise<{ unread_count: number }> {
  return fetchAPI<{ unread_count: number }>('/messages/unread/count');
}

export async function markMessageRead(id: string): Promise<Message> {
  return fetchAPI<Message>(`/messages/${id}/read`, { method: 'PATCH' });
}

// Import
export async function importOreadFile(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/import/oread`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Import failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function importFhirBundle(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/import/fhir`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Import failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function importCCDA(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/import/ccda`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Import failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function getImportHistory(): Promise<any[]> {
  return fetchAPI<any[]>('/import/history');
}

// Generated Encounters (Syrinx integration)

export interface GenerateEncounterRequest {
  patient_id: string;
  chief_complaint: string;
  encounter_type: 'acute' | 'well-child' | 'mental-health' | 'follow-up';
  duration: 'short' | 'medium' | 'long';
  error_type?: 'clinical' | 'communication' | null;
}

export interface ScriptLine {
  speaker: string;
  direction?: string;
  line: string;
}

export interface GeneratedEncounter {
  id: string;
  patient_id: string;
  patient_name: string;
  chief_complaint: string;
  metadata: {
    encounter_type: string;
    duration: string;
    clinical_focus?: string;
    speakers?: { name: string; role: string }[];
  };
  script: ScriptLine[];
  audio_url?: string;
}

export interface SavedEncounter {
  id: string;
  patient_id: string;
  syrinx_id: string;
  encounter_type: string;
  chief_complaint: string;
  metadata: any;
  script: ScriptLine[];
  audio_url?: string;
  created_at: string;
}

export async function generateEncounter(request: GenerateEncounterRequest): Promise<GeneratedEncounter> {
  return fetchAPI<GeneratedEncounter>('/encounters/generate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function saveEncounter(encounter: {
  patient_id: string;
  syrinx_id: string;
  encounter_type: string;
  chief_complaint: string;
  metadata: any;
  script: ScriptLine[];
}): Promise<{ id: string; status: string }> {
  return fetchAPI('/encounters/save', {
    method: 'POST',
    body: JSON.stringify(encounter),
  });
}

export async function getGeneratedEncounters(patientId: string): Promise<SavedEncounter[]> {
  return fetchAPI<SavedEncounter[]>(`/encounters/${patientId}/generated`);
}

// Learning Sessions

import type {
  LearningSession,
  SessionSummary,
  StartSessionRequest,
  LearnerAction,
  ActionResponse,
  AdvancePhaseRequest,
  CompleteSessionRequest,
  UpdateSessionRequest,
  DebriefResult,
  SessionTranscript,
} from '../types/learning';

export async function startLearningSession(request: StartSessionRequest): Promise<LearningSession> {
  return fetchAPI<LearningSession>('/learning/sessions', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getLearningSession(sessionId: string): Promise<LearningSession> {
  return fetchAPI<LearningSession>(`/learning/sessions/${sessionId}`);
}

export async function listLearningSessions(
  status?: string,
  patientId?: string,
  limit?: number
): Promise<SessionSummary[]> {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (patientId) params.set('patient_id', patientId);
  if (limit) params.set('limit', limit.toString());
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchAPI<SessionSummary[]>(`/learning/sessions${query}`);
}

export async function getActiveLearningSessions(): Promise<SessionSummary[]> {
  return fetchAPI<SessionSummary[]>('/learning/sessions/active');
}

export async function updateLearningSession(
  sessionId: string,
  request: UpdateSessionRequest
): Promise<LearningSession> {
  return fetchAPI<LearningSession>(`/learning/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(request),
  });
}

export async function submitLearnerAction(
  sessionId: string,
  action: LearnerAction
): Promise<ActionResponse> {
  return fetchAPI<ActionResponse>(`/learning/sessions/${sessionId}/action`, {
    method: 'POST',
    body: JSON.stringify(action),
  });
}

export async function advanceLearningPhase(
  sessionId: string,
  request?: AdvancePhaseRequest
): Promise<LearningSession> {
  return fetchAPI<LearningSession>(`/learning/sessions/${sessionId}/advance`, {
    method: 'POST',
    body: JSON.stringify(request || {}),
  });
}

export async function completeLearningSession(
  sessionId: string,
  request: CompleteSessionRequest
): Promise<DebriefResult> {
  return fetchAPI<DebriefResult>(`/learning/sessions/${sessionId}/complete`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getSessionTranscript(sessionId: string): Promise<SessionTranscript> {
  return fetchAPI<SessionTranscript>(`/learning/sessions/${sessionId}/transcript`);
}
