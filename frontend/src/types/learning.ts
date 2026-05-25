/**
 * TypeScript types for the Learning Visit system.
 */

// Action types
export type ActionType =
  | 'question'
  | 'exam_request'
  | 'lab_order'
  | 'imaging_order'
  | 'add_differential'
  | 'remove_differential'
  | 'rank_differential'
  | 'make_diagnosis'
  | 'make_disposition'
  | 'ask_echo';

export type SessionStatus = 'active' | 'paused' | 'completed' | 'abandoned';

export type Phase =
  | 'chief_complaint'
  | 'hpi'
  | 'ros'
  | 'exam'
  | 'assessment'
  | 'plan'
  | 'debrief';

export type LearnerLevel =
  | 'student'
  | 'resident'
  | 'np_student'
  | 'fellow'
  | 'attending';

export type EncounterType =
  | 'acute'
  | 'well-child'
  | 'mental-health'
  | 'follow-up';

// Embedded types
export interface ActionRecord {
  id: string;
  timestamp: string;
  action_type: ActionType;
  content: string;
  target?: string;
  phase: Phase;
  echo_response_id?: string;
}

export interface DifferentialEntry {
  diagnosis: string;
  rank: number;
  added_at: string;
  confidence?: string;
  reasoning?: string;
}

export interface OrderRecord {
  id: string;
  order_type: 'lab' | 'imaging' | 'medication' | 'referral';
  item: string;
  rationale?: string;
  timestamp: string;
  result_id?: string;
  status: 'pending' | 'resulted' | 'cancelled';
}

export interface EchoMessage {
  id: string;
  role: 'learner' | 'echo';
  content: string;
  timestamp: string;
  triggered_by?: string;
  is_proactive: boolean;
}

export interface TeachingMoment {
  id: string;
  timestamp: string;
  trigger: string;
  trigger_type: string;
  message: string;
  acknowledged: boolean;
}

export interface DecisionPoint {
  id: string;
  timestamp: string;
  branch_id: string;
  trigger: Record<string, any>;
  consequence: string;
  new_findings: Record<string, any>[];
}

export interface RevealedData {
  chief_complaint?: string;
  hpi_elements: Array<{ key: string; content: any }>;
  ros_findings: Array<{ key: string; content: any }>;
  pmh_details: Array<{ key: string; content: any }>;
  family_history: Array<{ key: string; content: any }>;
  social_history: Array<{ key: string; content: any }>;
  vital_signs?: Record<string, any>;
  exam_findings: Array<{ key: string; finding: any }>;
  lab_results: Array<Record<string, any>>;
  imaging_results: Array<Record<string, any>>;
}

// Request types
export interface StartSessionRequest {
  patient_id: string;
  encounter_type: EncounterType;
  chief_complaint: string;
  appointment_id?: string;
  case_id?: string;
  learner_level?: LearnerLevel;
}

export interface LearnerAction {
  action_type: ActionType;
  content: string;
  target?: string;
}

export interface AdvancePhaseRequest {
  to_phase?: Phase;
}

export interface CompleteSessionRequest {
  final_diagnosis: string;
  final_disposition: string;
}

export interface UpdateSessionRequest {
  status: 'paused' | 'active' | 'abandoned';
}

// Response types
export interface ActionResponse {
  success: boolean;
  action_id: string;
  revealed_data?: Record<string, any>;
  echo_feedback?: EchoMessage;
  phase_changed: boolean;
  new_phase?: Phase;
  teaching_moment?: TeachingMoment;
  branch_triggered?: DecisionPoint;
  order_result?: Record<string, any>;
}

export interface SessionSummary {
  id: string;
  patient_id: string;
  patient_name?: string;
  status: SessionStatus;
  current_phase: Phase;
  encounter_type: EncounterType;
  chief_complaint: string;
  started_at: string;
  completed_at?: string;
}

export interface LearningSession {
  id: string;
  patient_id: string;
  appointment_id?: string;
  case_id?: string;

  // Metadata
  status: SessionStatus;
  started_at: string;
  paused_at?: string;
  completed_at?: string;

  // Context
  encounter_type: EncounterType;
  chief_complaint: string;
  learner_level: LearnerLevel;

  // Phase
  current_phase: Phase;

  // Clinical data
  revealed_data: RevealedData;
  locked_data: Record<string, any>;

  // Learner state
  actions: ActionRecord[];
  differential: DifferentialEntry[];
  orders_placed: OrderRecord[];

  // Echo
  echo_messages: EchoMessage[];
  teaching_moments: TeachingMoment[];

  // Branching
  active_branch: string;
  branch_history: string[];
  decision_points: DecisionPoint[];

  // Final assessment
  final_diagnosis?: string;
  final_disposition?: string;
  correct_diagnosis?: string;
  correct_disposition?: string;

  // Metrics
  time_in_phase: Record<string, number>;
  questions_asked: number;
  exams_performed: number;

  created_at?: string;
  updated_at?: string;
}

export interface DebriefResult {
  summary: string;
  score?: {
    total: number;
    breakdown: Record<string, number>;
  };
  strengths: string[];
  areas_for_improvement: string[];
  missed_items: string[];
  teaching_points: string[];
  follow_up_resources: string[];
  correct_diagnosis: string;
  correct_disposition: string;
  was_correct: boolean;
}

// Transcript types
export interface TranscriptEvent {
  type: 'action' | 'echo_message' | 'teaching_moment' | 'decision_point';
  timestamp: string;
  data: ActionRecord | EchoMessage | TeachingMoment | DecisionPoint;
}

export interface SessionTranscript {
  session_id: string;
  patient_id: string;
  encounter_type: EncounterType;
  chief_complaint: string;
  started_at: string;
  completed_at?: string;
  final_diagnosis?: string;
  final_disposition?: string;
  events: TranscriptEvent[];
}

// Phase display info
export const PHASE_LABELS: Record<Phase, string> = {
  chief_complaint: 'Chief Complaint',
  hpi: 'History of Present Illness',
  ros: 'Review of Systems',
  exam: 'Physical Exam',
  assessment: 'Assessment',
  plan: 'Plan',
  debrief: 'Debrief',
};

export const PHASE_ORDER: Phase[] = [
  'chief_complaint',
  'hpi',
  'ros',
  'exam',
  'assessment',
  'plan',
  'debrief',
];
