import { PatientDetail } from './api';
import { SyrinxScenario } from '../hooks/useSyrinxSession';

export type ParentPersona =
  | 'anxious'
  | 'calm'
  | 'dismissive'
  | 'demanding'
  | 'confused'
  | 'frustrated';

export const PARENT_PERSONAS: { value: ParentPersona; label: string; description: string }[] = [
  {
    value: 'anxious',
    label: 'Anxious First-Time Parent',
    description: 'Worried, asks many questions, needs reassurance',
  },
  {
    value: 'calm',
    label: 'Calm & Experienced',
    description: 'Matter-of-fact, provides clear information',
  },
  {
    value: 'dismissive',
    label: 'Dismissive',
    description: 'Minimizes symptoms, may withhold information',
  },
  {
    value: 'demanding',
    label: 'Demanding',
    description: 'Wants immediate answers, may push for specific treatments',
  },
  {
    value: 'confused',
    label: 'Confused',
    description: 'Unclear about symptoms, gives inconsistent information',
  },
  {
    value: 'frustrated',
    label: 'Frustrated with Healthcare',
    description: 'Has had bad experiences, skeptical of recommendations',
  },
];

export function buildScenario(
  patientData: PatientDetail,
  chiefComplaint: string,
  parentPersona: ParentPersona
): SyrinxScenario {
  const { patient, allergies, medications, conditions } = patientData;

  const fullName = `${patient.given_names.join(' ')} ${patient.family_name}`;

  // Build age string
  let ageString: string;
  if (patient.age_years < 1) {
    // Calculate months for infants
    const dob = new Date(patient.date_of_birth);
    const now = new Date();
    const months = Math.floor((now.getTime() - dob.getTime()) / (1000 * 60 * 60 * 24 * 30));
    ageString = `${months} month${months !== 1 ? 's' : ''}`;
  } else {
    ageString = `${patient.age_years} year${patient.age_years !== 1 ? 's' : ''}`;
  }

  // Extract active items
  const activeAllergies = allergies
    .filter(a => a.display_name)
    .map(a => {
      const reaction = a.reactions?.[0]?.manifestation;
      return reaction ? `${a.display_name} (${reaction})` : a.display_name;
    });

  const activeMedications = medications
    .filter(m => m.status === 'active')
    .map(m => {
      if (m.dose_quantity && m.frequency) {
        return `${m.display_name} ${m.dose_quantity}${m.dose_unit || ''} ${m.frequency}`;
      }
      return m.display_name;
    });

  const activeConditions = conditions
    .filter(c => c.clinical_status === 'active')
    .map(c => c.display_name);

  return {
    description: `${ageString} old ${patient.sex_at_birth || 'child'} named ${fullName} presenting with ${chiefComplaint}`,
    patient: {
      name: fullName,
      age: ageString,
      sex: patient.sex_at_birth || 'unknown',
      allergies: activeAllergies.length > 0 ? activeAllergies : ['None known'],
      medications: activeMedications.length > 0 ? activeMedications : ['None'],
      chronic_conditions: activeConditions.length > 0 ? activeConditions : ['None'],
    },
    parent: {
      style: parentPersona,
    },
    chief_complaint: chiefComplaint,
  };
}

export function getPersonaDescription(persona: ParentPersona): string {
  return PARENT_PERSONAS.find(p => p.value === persona)?.description || '';
}
