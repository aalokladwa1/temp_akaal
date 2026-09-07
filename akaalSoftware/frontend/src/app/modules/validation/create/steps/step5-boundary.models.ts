/**
 * Step 5 — Boundary & Consistency Baseline Models
 *
 * Defines frontend wizard intent identifiers and presentation models.
 * NOTE: These are wizard/draft intent models, NOT canonical backend boundary-policy enums.
 */

export type OperatorBaselineIntent =
  | 'INHERITED_MIGRATION'
  | 'CURRENT_OPERATIONAL'
  | 'MAINTENANCE_COORDINATED'
  | 'EXTERNAL_REPLICATION'
  | 'STATIC_IMMUTABLE';

export type OperatorMaintenanceCondition =
  | 'WRITES_STOPPED_DECLARED'
  | 'EXTERNAL_COORDINATION_DECLARED';

export interface Step5BoundaryDraftState {
  baselineIntent?: OperatorBaselineIntent;
  maintenanceCondition?: OperatorMaintenanceCondition;
  operatorNotes?: string;
}

export interface BaselineConceptOption {
  id: OperatorBaselineIntent;
  title: string;
  description: string;
  icon: string;
  isSupported: boolean;
  unsupportedNotice?: string;
}

export interface TechnicalDetailItem {
  key?: string;
  label: string;
  value: string;
  provenance: string;
  icon?: string;
}

