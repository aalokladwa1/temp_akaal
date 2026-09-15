/**
 * AKAAL Template Workspace Domain & Presentation Models (Part C)
 * Governs the 7-Tab Template Workspace:
 * 1. Overview (Identity, Applicability, Modes, Availability, Config Summary, Version/Lifecycle, Usage, P7B/P7C Context)
 * 2. Configuration (Defaults, Requirements, Discovery, Mapping, Cleansing, Masking, Performance, Mode Tuning, Validation, Governance, Locality)
 * 3. Applicability (Source/Target Providers, M1-M7 Modes, Compatibility Matrix, Required Capabilities, Required-at-Use, Constraints)
 * 4. Versions (Current Revision, History Table, Semantic Diff Engine, Supersession, Read-only Historical View, New Version Modal)
 * 5. Usage (Projects Referencing, Migrations Created, Materialization Boundary, Overrides Context, Reference Protection)
 * 6. Activity (Auditable Event Timeline: Created, Updated, Config, Versions, Lifecycle, Applicability, Governance, Migration Application)
 * 7. Settings (General Metadata, Scope Boundary, Access Context, Lifecycle Actions, Destructive Delete with Confirmation)
 *
 * OWNER-FROZEN BOUNDARY:
 * - Templates accelerate canonical Migration Creation (M1-M7 only).
 * - M8 (Validation Only) is STRICTLY FORBIDDEN anywhere in Templates.
 * - Standalone Validation Creation NEVER consumes Templates.
 * - Zero Plaintext Secrets: Templates never store or expose credentials.
 * - Running Migration Immutability: Template updates never alter initialized/running migrations.
 */

import {
  TemplateMigrationMode,
  TemplateScope,
  TemplateLifecycle,
  TemplateApplicability,
  TemplateUsageContext,
  TEMPLATE_MODE_DESCRIPTORS,
  ModeDescriptor
} from '../templates.models';
import {
  CreateTemplateDraftState,
  INITIAL_CREATE_TEMPLATE_DRAFT,
  ExecutionPriority,
  ConnectionPolicy,
  RequiredAtUseChecklist,
  ObjectScopeRule,
  SchemaMappingRule,
  TableCaseTransformation,
  NullabilityPolicy,
  ColumnTypeOverride,
  MaskingRule,
  CleansingRules,
  PerformanceConfig,
  CheckpointRecoveryConfig,
  CdcModeConfig,
  IncrementalModeConfig,
  StateSyncModeConfig,
  SchemaOnlyModeConfig,
  DataOnlyModeConfig,
  ValidationPresetsConfig,
  OverridabilityRules,
  RequiredCapabilities,
  ApprovalAndPolicy,
  SecretReferenceRules
} from '../create-template/create-template.models';

export type TemplateWorkspaceTab =
  | 'overview'
  | 'configuration'
  | 'applicability'
  | 'versions'
  | 'usage'
  | 'activity'
  | 'settings';

export interface TabNavigationItem {
  key: TemplateWorkspaceTab;
  label: string;
  icon: string;
}

export const TEMPLATE_WORKSPACE_TABS: TabNavigationItem[] = [
  { key: 'overview', label: 'Overview', icon: 'layout-dashboard' },
  { key: 'configuration', label: 'Configuration', icon: 'sliders' },
  { key: 'applicability', label: 'Applicability', icon: 'shield-check' },
  { key: 'versions', label: 'Versions', icon: 'git-branch' },
  { key: 'usage', label: 'Usage', icon: 'folder-git-2' },
  { key: 'activity', label: 'Activity', icon: 'history' },
  { key: 'settings', label: 'Settings', icon: 'settings' }
];

// =========================================================================
// PROVIDER COMPATIBILITY & APPLICABILITY DETAILS
// =========================================================================

export type CompatibilityStatus = 'VERIFIED' | 'NOT_VERIFIED' | 'UNSUPPORTED' | 'UNKNOWN';

export interface ProviderPairCompatibility {
  sourceProvider: string;
  targetProvider: string;
  status: CompatibilityStatus;
  statusLabel: string;
  certifiedVersionRange?: string;
  notes?: string;
}

export interface TemplateApplicabilityDetails {
  sourceDialect: string;
  sourceFamily: string;
  targetDialect: string;
  targetFamily: string;
  compatibility: ProviderPairCompatibility;
  requiredCapabilities: RequiredCapabilities;
  requiredAtUse: RequiredAtUseChecklist;
  connectionExpectations: {
    tlsMandatory: boolean;
    zeroSecretsEnforced: boolean;
    logicalTaggingSupported: boolean;
    vaultReferencePattern: string;
  };
  environmentConstraints: string[];
  knownLimitations: string[];
}

// =========================================================================
// VERSION HISTORY & SEMANTIC DIFF MODELS
// =========================================================================

export interface TemplateVersionItem {
  versionLabel: string;        // e.g. "v2.1.0", "v2.0.0", "v1.0.0"
  revisionNumber: number;      // 1, 2, 3
  createdAt: string;
  createdBy: string;
  lifecycle: TemplateLifecycle;
  changeSummary: string;
  usageCount: number;
  supersedesVersion?: string;
  isCurrent: boolean;
  configurationSnapshot: CreateTemplateDraftState;
}

export type DiffChangeType = 'ADDED' | 'MODIFIED' | 'REMOVED' | 'UNCHANGED';

export interface VersionDiffFieldChange {
  category: string;             // 'Defaults' | 'Scope & Discovery' | 'Mapping' | 'Enterprise Config' | 'Governance'
  fieldLabel: string;
  oldValue: string;
  newValue: string;
  changeType: DiffChangeType;
}

export interface VersionDiffResult {
  baseVersion: string;
  compareVersion: string;
  changes: VersionDiffFieldChange[];
  totalAdded: number;
  totalModified: number;
  totalRemoved: number;
}

// =========================================================================
// USAGE & REFERENCE DEPENDENCY MODELS
// =========================================================================

export interface TemplateProjectUsage {
  projectId: string;
  projectName: string;
  environment: string;
  scope: TemplateScope;
  referencingMigrationCount: number;
  lastUsedAt: string;
}

export interface TemplateMigrationUsage {
  migrationId: string;
  migrationName: string;
  projectId: string;
  projectName: string;
  versionUsedAtInstantiation: string;
  lifecycleState: 'DRAFT' | 'CONFIGURING' | 'INITIALIZED' | 'RUNNING' | 'COMPLETED' | 'ARCHIVED';
  appliedAt: string;
  overridesCount: number;
  isIndependentMaterialization: boolean; // Law: Materialized migrations are independent
}

export interface TemplateReferenceProtection {
  isProtected: boolean;
  reason?: string;
  activeMigrationCount: number;
  deletionPermitted: boolean;
}

// =========================================================================
// ACTIVITY & AUDIT TIMELINE MODELS
// =========================================================================

export type TemplateActivityCategory =
  | 'ALL'
  | 'LIFECYCLE'
  | 'VERSIONS'
  | 'CONFIGURATION'
  | 'APPLICABILITY'
  | 'GOVERNANCE'
  | 'MIGRATION_APPLICATION'
  | 'ADMINISTRATION';

export interface TemplateActivityEvent {
  id: string;
  timestamp: string;
  actor: {
    name: string;
    email: string;
    role: string;
  };
  eventType: string;
  category: TemplateActivityCategory;
  summary: string;
  details?: string;
  affectedVersion?: string;
}

// =========================================================================
// OPERATIONAL CONTEXT (P7B INTENT & P7C ADVISORY)
// =========================================================================

export interface TemplateP7bOperationalIntent {
  localityRequirements: string[];
  sovereigntyConstraints: string[];
  recoveryPreference: string;
  zeroSecretsAttestation: boolean;
}

export interface TemplateP7cAdvisoryContext {
  isAvailable: boolean;
  advisorySummary?: string;
  recommendations?: string[];
  confidenceNote?: string;
}

// =========================================================================
// COMPLETE TEMPLATE DETAIL MODEL (ROOT WORKSPACE AGGREGATE)
// =========================================================================

export interface TemplateDetail {
  id: string;
  name: string;
  description: string;
  mode: TemplateMigrationMode;
  applicability: TemplateApplicability;
  scope: TemplateScope;
  versionLabel: string;
  revisionNumber: number;
  lifecycle: TemplateLifecycle;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  lastUpdatedBy: string;

  // Rich Domain Sub-States
  configuration: CreateTemplateDraftState;
  applicabilityDetails: TemplateApplicabilityDetails;
  versions: TemplateVersionItem[];
  usage: {
    projects: TemplateProjectUsage[];
    migrations: TemplateMigrationUsage[];
    isUsageKnown: boolean;
    referencedProjectCount: number;
    migrationCount: number;
    lastUsedAt: string | null;
  };
  activities: TemplateActivityEvent[];
  p7bContext: TemplateP7bOperationalIntent;
  p7cContext: TemplateP7cAdvisoryContext;
  referenceProtection: TemplateReferenceProtection;
}
