/**
 * akaalSoftware - Validation Studio - Step 6 Models
 * =================================================
 * Domain models and contracts for Step 6: Validation Strategy & Assurance.
 * Decouples operator assurance intent from backend execution mechanics.
 */

export type AssuranceLevel =
  | 'STRUCTURAL'
  | 'CARDINALITY'
  | 'PARTITION_FINGERPRINT'
  | 'COMPLETE_ATTRIBUTE';

export type TemporalCadence =
  | 'CONSISTENT_STATE'
  | 'CONTINUOUS';

export type CoveragePolicy =
  | 'EXHAUSTIVE'
  | 'TARGETED_EXCEPTIONS'
  | 'LIMITED_SAMPLE';

export type CapabilityStatus =
  | 'AVAILABLE'
  | 'AVAILABLE_WITH_LIMITATIONS'
  | 'UNAVAILABLE'
  | 'CAPABILITY_NOT_DETERMINED';

export type ExceptionScopeType =
  | 'ESCALATED'
  | 'REDUCED';

export interface AssuranceTierCard {
  level: AssuranceLevel;
  stepNumber: '01' | '02' | '03' | '04';
  title: string;
  subtitle: string;
  progressionLabel: string;
  capability: CapabilityStatus;
  capabilityReason?: string;
  establishes: string[];
  doesNotEstablish: string[];
  limitations: string[];
}

export interface AssuranceExceptionGroup {
  id: string;
  type: ExceptionScopeType;
  targetAssuranceLevel: AssuranceLevel;
  reason: string;
  objectIds: string[];
  objectNames: string[];
  namespace?: string;
}

export interface AdvancedCoverageConfig {
  mode: 'EXHAUSTIVE' | 'STATISTICAL_SAMPLE';
  samplePercentage?: number;
  deterministicSeed?: number;
  disclaimer: string;
}

export interface ContextualIntelligenceFinding {
  id: string;
  title: string;
  body: string;
  severity: 'INFO' | 'ADVISORY' | 'WARNING';
  recommendedAssuranceLevel?: AssuranceLevel;
  affectedObjectsCount?: number;
  isDismissed: boolean;
  isAccepted: boolean;
}

export interface TemporalOption {
  id: TemporalCadence;
  title: string;
  description: string;
  icon: string;
  capability: CapabilityStatus;
  capabilityNotice?: string;
}
