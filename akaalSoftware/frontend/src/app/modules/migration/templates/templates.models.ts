/**
 * AKAAL Migration Templates Domain & Presentation Models
 * Governs Template Inventory, M1-M7 migration mode applicability,
 * opaque version display labels, calm usage contexts, and Pre-P7D presentation fixtures.
 *
 * OWNER-FROZEN BOUNDARY:
 * - Templates accelerate canonical Migration Creation (M1-M7).
 * - M8 (Validation Only) is STRICTLY FORBIDDEN anywhere in Templates.
 * - Validation Creation NEVER consumes Templates.
 */

export type TemplateMigrationMode =
  | 'M1_BULK'           // Bulk Load / Snapshot
  | 'M2_BULK_CDC'       // Bulk + CDC (Initial Snapshot + Ongoing Replication)
  | 'M3_CDC'            // CDC Only (Continuous Streaming)
  | 'M4_INCREMENTAL'    // Incremental / Polling
  | 'M5_STATE_SYNC'     // State-Based Sync (Two-way / Multi-directional)
  | 'M6_SCHEMA_ONLY'    // Schema Only (DDL Extraction & Conversion)
  | 'M7_DATA_ONLY';     // Data Only (No Schema Alteration)

export interface ModeDescriptor {
  code: TemplateMigrationMode;
  shortCode: string;   // e.g. "M1", "M2", "M3"
  label: string;       // e.g. "Bulk Load", "Bulk + CDC"
  fullLabel: string;   // e.g. "M2 • Bulk + CDC"
  description: string;
}

export const TEMPLATE_MODE_DESCRIPTORS: Record<TemplateMigrationMode, ModeDescriptor> = {
  M1_BULK: {
    code: 'M1_BULK',
    shortCode: 'M1',
    label: 'Bulk Load',
    fullLabel: 'M1 • Bulk Load',
    description: 'Initial snapshot data migration without continuous replication.'
  },
  M2_BULK_CDC: {
    code: 'M2_BULK_CDC',
    shortCode: 'M2',
    label: 'Bulk + CDC',
    fullLabel: 'M2 • Bulk + CDC',
    description: 'Initial bulk snapshot followed by low-latency CDC replication.'
  },
  M3_CDC: {
    code: 'M3_CDC',
    shortCode: 'M3',
    label: 'CDC Only',
    fullLabel: 'M3 • CDC Only',
    description: 'Continuous change data capture streaming from active transaction logs.'
  },
  M4_INCREMENTAL: {
    code: 'M4_INCREMENTAL',
    shortCode: 'M4',
    label: 'Incremental / Polling',
    fullLabel: 'M4 • Incremental',
    description: 'Timestamp or watermark-based periodic batch delta replication.'
  },
  M5_STATE_SYNC: {
    code: 'M5_STATE_SYNC',
    shortCode: 'M5',
    label: 'State-Based Sync',
    fullLabel: 'M5 • State Sync',
    description: 'State-based reconciliation and multi-directional synchronization.'
  },
  M6_SCHEMA_ONLY: {
    code: 'M6_SCHEMA_ONLY',
    shortCode: 'M6',
    label: 'Schema Only',
    fullLabel: 'M6 • Schema Only',
    description: 'DDL structural extraction, conversion, and target object creation.'
  },
  M7_DATA_ONLY: {
    code: 'M7_DATA_ONLY',
    shortCode: 'M7',
    label: 'Data Only',
    fullLabel: 'M7 • Data Only',
    description: 'Data payload migration into pre-existing target schema objects.'
  }
};

export type TemplateScope = 'ORGANIZATION' | 'WORKSPACE' | 'PROJECT';

export type TemplateLifecycle = 'PUBLISHED' | 'DRAFT' | 'DEPRECATED' | 'ARCHIVED';

export type TemplateAvailabilityState =
  | 'READY'
  | 'LOADING'
  | 'EMPTY'
  | 'UNAVAILABLE'
  | 'ERROR'
  | 'UNAUTHORIZED';

export interface TemplateApplicability {
  sourceProviderName: string;
  targetProviderName: string;
}

export interface TemplateUsageContext {
  referencedProjectCount: number;
  migrationCount: number;
  lastUsedAt: string | null;
  isUsageKnown: boolean; // false when telemetry/backend authority is unprobed
  isUnused: boolean;
}

export interface TemplateItem {
  id: string;
  name: string;
  description: string;
  mode: TemplateMigrationMode;
  applicability: TemplateApplicability;
  scope: TemplateScope;
  versionLabel: string; // Opaque display string, e.g. "v1.2.0", "v2.0-draft"
  lifecycle: TemplateLifecycle;
  usage: TemplateUsageContext;
  createdAt: string;
  updatedAt: string;
}

export type TemplateSortOption = 'name_asc' | 'name_desc' | 'usage_desc' | 'updated_desc';

export interface TemplateFilterState {
  searchQuery: string;
  mode: TemplateMigrationMode | 'ALL';
  applicability: string | 'ALL'; // formatted "Source -> Target" or "ALL"
  sortBy: TemplateSortOption;
}
