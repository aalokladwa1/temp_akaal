/**
 * Step 8 — Review, Schedule & Initialize Models
 *
 * Defines presentation structures for the 5 review groups, draft identity,
 * execution timing choices, and draft configuration inspect modal.
 */

export interface DraftIdentityPresentation {
  validationName: string;
  environment: 'Production' | 'Non-Production';
  validationContext: 'INDEPENDENT' | 'EXISTING_PROJECT';
  projectName?: string;
  draftId: string;
  source: {
    provider: string;
    label: string;
  };
  target: {
    provider: string;
    label: string;
  };
}

export interface ReviewFieldItem {
  label: string;
  value: string;
  badge?: string;
  badgeColor?: string;
  detail?: string;
}

export interface ReviewDocumentGroup {
  id: string;
  title: string;
  subtitle: string;
  upstreamStep: number;
  upstreamStepLabel: string;
  fields: ReviewFieldItem[];
}

export type TimingChoice = 'INITIALIZATION' | 'SCHEDULE_LATER' | 'RECURRING' | 'CONTINUOUS';

export interface TimingState {
  choice: TimingChoice;
  scheduledDate: string;
  scheduledTime: string;
  selectedTimezone: string;
  resolvedLocalDisplay: string;
  resolvedUtcDisplay: string;
  recurrenceFrequency: 'HOURLY' | 'DAILY' | 'WEEKLY' | 'MONTHLY';
}

export interface ConsequenceExplanation {
  title: string;
  primaryActionDescription: string;
  subsequentSteps: string[];
  productionNotice?: string;
}
