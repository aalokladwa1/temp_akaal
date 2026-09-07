import { Injectable, signal, computed } from '@angular/core';
import { MigrationDevFixturesAdapter } from '../fixtures/migration-dev-fixtures.adapter';
import {
  ValidationItem,
  ValidationPurpose,
  ValidationProfile,
  PhysicalProviderId,
  DifferenceFunnelLevel,
  SchemaDiffItem,
  PartitionHeatmapCell,
  MerkleNodeItem,
  DisputedRowItem,
  GovernedRepairPlan,
  ConnectionItem,
  SourceVerificationResult,
  NetworkRouteType
} from '../models/migration-view.models';
import {
  ScopedComparisonPair,
  ComparisonUnit,
  Step4Pathway
} from '../../modules/validation/create/steps/step4-scope.models';
import {
  OperatorBaselineIntent,
  OperatorMaintenanceCondition
} from '../../modules/validation/create/steps/step5-boundary.models';
import {
  AssuranceLevel,
  TemporalCadence,
  CoveragePolicy,
  AssuranceExceptionGroup,
  AdvancedCoverageConfig
} from '../../modules/validation/create/steps/step6-strategy.models';
import { TimingChoice } from '../../modules/validation/create/steps/step8-review.models';

export type ValidationContextType = 'INDEPENDENT' | 'EXISTING_PROJECT';

export interface NewValidationDraftState {
  name: string;
  environment: 'Production' | 'Non-Production';
  validationContext: ValidationContextType;
  projectId?: string;
  projectName?: string;
  
  currentStep: number;
  isReadOnlyEnforced: boolean;
  isDirty?: boolean;

  // Step 4: Scope & Correspondence
  step4Pathway?: Step4Pathway;
  comparisonUnits?: ComparisonUnit[];
  selectedScopeNamespaces?: string[];
  selectedCorrespondenceRule?: string;
  selectedSourceNodeIds?: string[];
  scopedPairs?: ScopedComparisonPair[];

  // Step 5: Boundary & Consistency Baseline (Operator Intent Draft)
  baselineIntent?: OperatorBaselineIntent;
  maintenanceCondition?: OperatorMaintenanceCondition;
  operatorNotes?: string;

  // Step 6: Validation Strategy & Assurance (Operator Intent Draft)
  assuranceLevel?: AssuranceLevel;
  temporalCadence?: TemporalCadence;
  coveragePolicy?: CoveragePolicy;
  assuranceExceptions?: AssuranceExceptionGroup[];
  advancedCoverage?: AdvancedCoverageConfig;

  // Step 7: Governance & Readiness (Operator Draft State)
  step7AcknowledgedIds?: string[];

  // Step 8: Review, Schedule & Initialize (Operator Draft State)
  step8TimingChoice?: TimingChoice;
  step8ScheduledDate?: string;
  step8ScheduledTime?: string;
  step8ScheduledTimezone?: string;
  step8RecurringFrequency?: 'HOURLY' | 'DAILY' | 'WEEKLY' | 'MONTHLY';

  // Step 2: Source Instance & Connectivity
  sourceConnectionMode?: 'SAVED' | 'NEW';
  sourceConnectionId?: string;
  sourceProvider?: PhysicalProviderId;
  sourceHost?: string;
  sourcePort?: number;
  sourceDatabase?: string;
  sourceUsername?: string;
  sourceSecretRef?: string;
  sourceTls?: boolean;
  sourceTlsMode?: string;
  sourceNetworkRoute?: NetworkRouteType;
  sourceBastionHost?: string;
  sourceParams?: Record<string, any>;
  sourceVerified?: boolean;
  sourceVerificationResult?: SourceVerificationResult;
  sourceSaveToVault?: boolean;

  // Step 3: Target Instance & Compatibility
  targetConnectionMode?: 'SAVED' | 'NEW';
  targetConnectionId?: string;
  targetProvider?: PhysicalProviderId;
  targetHost?: string;
  targetPort?: number;
  targetDatabase?: string;
  targetUsername?: string;
  targetSecretRef?: string;
  targetTls?: boolean;
  targetTlsMode?: string;
  targetNetworkRoute?: NetworkRouteType;
  targetBastionHost?: string;
  targetParams?: Record<string, any>;
  targetVerified?: boolean;
  targetVerificationResult?: SourceVerificationResult;
  targetSaveToVault?: boolean;

  // Preserved for future phases
  purpose?: ValidationPurpose;
  owner?: string;
  priority?: 'NORMAL' | 'HIGH' | 'CRITICAL';
  referenceConnectionId?: string;
  referenceProvider?: PhysicalProviderId;
  comparisonConnectionId?: string;
  comparisonProvider?: PhysicalProviderId;
  scopeType?: 'FULL' | 'PARTITIONED' | 'SAMPLED';
  profile?: ValidationProfile;
  selectedObjects?: string[];
  numericToleranceAbsolute?: number;
  floatingEpsilon?: number;
  timestampTolerateTimezone?: boolean;
  stringTrimWhitespace?: boolean;
  nullEmptyStringEquivalent?: boolean;
  differencePolicy?: 'REPORT_ONLY' | 'LOCALIZE_DIFF' | 'BUILD_RECON_PLAN' | 'GOVERNED_REPAIR';
}

const INITIAL_DRAFT: NewValidationDraftState = {
  name: '',
  environment: 'Production',
  validationContext: 'INDEPENDENT',
  projectId: undefined,
  projectName: undefined,
  currentStep: 1,
  isReadOnlyEnforced: true,
  isDirty: false,
  step4Pathway: 'CHOICE',
  comparisonUnits: [],
  selectedScopeNamespaces: [],
  selectedCorrespondenceRule: 'EXACT_IDENTIFIER_MATCH',
  selectedSourceNodeIds: [],
  scopedPairs: [],
  baselineIntent: undefined,
  maintenanceCondition: undefined,
  operatorNotes: undefined,
  assuranceLevel: 'PARTITION_FINGERPRINT',
  temporalCadence: 'CONSISTENT_STATE',
  coveragePolicy: 'EXHAUSTIVE',
  assuranceExceptions: [],
  advancedCoverage: undefined,
  step7AcknowledgedIds: [],
  step8TimingChoice: 'INITIALIZATION',
  step8ScheduledDate: '',
  step8ScheduledTime: '00:00',
  step8ScheduledTimezone: 'UTC',
  step8RecurringFrequency: 'DAILY',
  sourceConnectionMode: undefined,
  sourceConnectionId: undefined,
  sourceProvider: undefined,
  sourceHost: '',
  sourcePort: 0,
  sourceDatabase: '',
  sourceUsername: '',
  sourceSecretRef: '',
  sourceTls: true,
  sourceTlsMode: 'VERIFY_FULL',
  sourceNetworkRoute: 'DIRECT',
  sourceBastionHost: '',
  sourceParams: {},
  sourceVerified: false,
  sourceVerificationResult: undefined,
  sourceSaveToVault: false,
  targetConnectionMode: undefined,
  targetConnectionId: undefined,
  targetProvider: undefined,
  targetHost: '',
  targetPort: 0,
  targetDatabase: '',
  targetUsername: '',
  targetSecretRef: '',
  targetTls: true,
  targetTlsMode: 'VERIFY_FULL',
  targetNetworkRoute: 'DIRECT',
  targetBastionHost: '',
  targetParams: {},
  targetVerified: false,
  targetVerificationResult: undefined,
  targetSaveToVault: false,
  purpose: 'POST_MIGRATION_VERIFICATION',
  owner: 'Aalok Ladwa',
  priority: 'HIGH',
  referenceConnectionId: '',
  referenceProvider: 'Oracle',
  comparisonConnectionId: '',
  comparisonProvider: 'PostgreSQL',
  scopeType: 'PARTITIONED',
  profile: 'DEEP',
  selectedObjects: [],
  numericToleranceAbsolute: 0,
  floatingEpsilon: 0.0001,
  timestampTolerateTimezone: true,
  stringTrimWhitespace: true,
  nullEmptyStringEquivalent: false,
  differencePolicy: 'GOVERNED_REPAIR'
};

@Injectable({
  providedIn: 'root'
})
export class ValidationUiService {
  private fixtures: MigrationDevFixturesAdapter = new MigrationDevFixturesAdapter();

  // Zero fake data by default
  public validationItems = signal<ValidationItem[]>([]);
  public filterVerdict = signal<string>('ALL');
  public connections = signal<ConnectionItem[]>([]);

  public filteredValidations = computed<ValidationItem[]>(() => {
    const list = this.validationItems();
    const v = this.filterVerdict();
    if (v === 'ALL') return list;
    if (v === 'SYNCED') return list.filter(item => item.verdict === 'SYNCED' || item.verdict === 'SYNCED_CERTIFIED');
    if (v === 'NOT_SYNCED') return list.filter(item => item.verdict === 'NOT_SYNCED');
    if (v === 'ACTIVE') return list.filter(item => item.verdict === 'VALIDATING' || item.verdict === 'RECONCILING' || item.verdict === 'REPAIRING');
    if (v === 'CERTIFIED') return list.filter(item => item.isCertified);
    return list;
  });

  public selectedValidationId = signal<string>('val-002');
  public activeValidation = computed<ValidationItem | null>(() => {
    const id = this.selectedValidationId();
    return this.validationItems().find(v => v.id === id) || null;
  });

  public differenceFunnel = computed<DifferenceFunnelLevel[]>(() => {
    return this.fixtures.getDifferenceFunnel(this.selectedValidationId());
  });

  public schemaDiff = computed<SchemaDiffItem[]>(() => {
    return this.fixtures.getSchemaDiff(this.selectedValidationId());
  });

  public partitionHeatmap = computed<PartitionHeatmapCell[]>(() => {
    return this.fixtures.getPartitionHeatmap(this.selectedValidationId());
  });

  public merkleTree = computed<MerkleNodeItem>(() => {
    return this.fixtures.getMerkleTree(this.selectedValidationId());
  });

  public disputedRows = computed<DisputedRowItem[]>(() => {
    return this.fixtures.getDisputedRows(this.selectedValidationId());
  });

  public governedRepairPlan = computed<GovernedRepairPlan>(() => {
    return this.fixtures.getGovernedRepairPlan(this.selectedValidationId());
  });

  public isRepairModalOpen = signal<boolean>(false);
  public activeDifferenceTab = signal<'funnel' | 'schema' | 'heatmap' | 'merkle' | 'rows' | 'repair'>('funnel');

  public newValidationDraft = signal<NewValidationDraftState>({ ...INITIAL_DRAFT });

  public isStep1Valid = computed<boolean>(() => {
    const draft = this.newValidationDraft();
    const hasName = !!draft.name && draft.name.trim().length > 0;
    if (!hasName) return false;
    if (draft.validationContext === 'EXISTING_PROJECT') {
      return !!draft.projectId;
    }
    return true;
  });

  public isStep2Valid = computed<boolean>(() => {
    const draft = this.newValidationDraft();
    if (!draft.sourceConnectionMode) return false;
    if (draft.sourceConnectionMode === 'SAVED') {
      return !!draft.sourceConnectionId && !!draft.sourceVerified;
    }
    if (draft.sourceConnectionMode === 'NEW') {
      if (!draft.sourceProvider) return false;
      return !!draft.sourceVerified;
    }
    return false;
  });

  public isStep3Valid = computed<boolean>(() => {
    const draft = this.newValidationDraft();
    if (!draft.targetConnectionMode) return false;
    if (draft.targetConnectionMode === 'SAVED') {
      return !!draft.targetConnectionId && !!draft.targetVerified;
    }
    if (draft.targetConnectionMode === 'NEW') {
      if (!draft.targetProvider) return false;
      return !!draft.targetVerified;
    }
    return false;
  });

  public isStep4Valid = computed<boolean>(() => {
    const draft = this.newValidationDraft();
    const units = (draft.comparisonUnits && draft.comparisonUnits.length > 0)
      ? draft.comparisonUnits
      : (draft.scopedPairs || []);

    if (units.length === 0) return false;

    const included = units.filter(u => u.disposition !== 'EXCLUDED');
    if (included.length === 0) return false;

    // Pathway A: Inherited Migration Scope (EXISTING_PROJECT)
    if (draft.validationContext === 'EXISTING_PROJECT') {
      // Law 6: Missing targets do NOT block validation
      // Zero unresolved operator decisions required
      const hasUnresolvedDecisions = included.some(u => u.isDecisionRequired);
      if (hasUnresolvedDecisions) return false;
      return included.every(u => !!u.expectedTargetName || !!u.targetName || u.targetStatus === 'CONFIRMED' || u.targetStatus === 'INHERITED_CONFIRMED');
    }

    // Independent Validation Context
    const pathway = draft.step4Pathway || 'CHOICE';
    if (pathway === 'CHOICE' || pathway === 'IMPORT') {
      return false;
    }

    if (pathway === 'DEFINE') {
      const hasUnresolvedDecisions = included.some(u => u.isDecisionRequired);
      if (hasUnresolvedDecisions) return false;
      return included.every(u => !!u.expectedTargetName || !!u.targetName || u.targetStatus === 'CONFIRMED' || u.targetStatus === 'INHERITED_CONFIRMED');
    }

    return false;
  });

  public isStep5Valid = computed<boolean>(() => {
    const draft = this.newValidationDraft();

    // 1. Existing Project (Pathway A)
    if (draft.validationContext === 'EXISTING_PROJECT') {
      // Truthful invariant: Usable canonical migration context must exist (projectId must be present)
      if (!draft.projectId) return false;
      const intent = draft.baselineIntent || 'INHERITED_MIGRATION';
      return intent === 'INHERITED_MIGRATION';
    }

    // 2. Independent Validation Context (Pathway C)
    const intent = draft.baselineIntent;
    if (!intent) return false;

    switch (intent) {
      case 'CURRENT_OPERATIONAL':
      case 'STATIC_IMMUTABLE':
        return true;
      case 'MAINTENANCE_COORDINATED':
        // Must have an explicit operator-declared operational condition
        return !!draft.maintenanceCondition;
      case 'EXTERNAL_REPLICATION':
        // Truthfully fail-closed: external migration baseline integration is not currently available
        return false;
      default:
        return false;
    }
  });

  public isStep6Valid = computed<boolean>(() => {
    const draft = this.newValidationDraft();
    if (!draft.assuranceLevel) return false;
    if (!draft.temporalCadence) return false;

    // Continuous validation is currently unavailable (P7D runtime deferred)
    if (draft.temporalCadence === 'CONTINUOUS') {
      return false;
    }

    // If exceptions exist, each group must have valid non-empty reason, target level, and >= 1 object
    if (draft.assuranceExceptions && draft.assuranceExceptions.length > 0) {
      const hasInvalidException = draft.assuranceExceptions.some(e =>
        !e.reason || e.reason.trim().length === 0 || !e.objectIds || e.objectIds.length === 0 || !e.targetAssuranceLevel
      );
      if (hasInvalidException) return false;
    }

    // If limited sample coverage is selected, percentage must be valid
    if (draft.coveragePolicy === 'LIMITED_SAMPLE' && draft.advancedCoverage) {
      const pct = draft.advancedCoverage.samplePercentage;
      if (pct === undefined || pct <= 0 || pct >= 100) return false;
    }

    return true;
  });

  public isStep7Valid = computed<boolean>(() => {
    // Mandate 1: Angular is NOT the canonical readiness authority.
    // Production default NOT_EVALUATED / READINESS_NOT_CONNECTED does NOT block proceeding to Step 8.
    // Step 7 validates local draft completeness: Are the required inputs from steps 1-6 present and structurally valid?
    return this.isStep1Valid() &&
           this.isStep2Valid() &&
           this.isStep3Valid() &&
           this.isStep4Valid() &&
           this.isStep5Valid() &&
           this.isStep6Valid();
  });

  public isStep8Valid = computed<boolean>(() => {
    if (!this.isStep7Valid()) return false;
    const draft = this.newValidationDraft();
    if (draft.step8TimingChoice === 'SCHEDULE_LATER') {
      return !!draft.step8ScheduledDate && !!draft.step8ScheduledTime;
    }
    return true;
  });

  constructor(fixtures?: MigrationDevFixturesAdapter) {
    if (fixtures) {
      this.fixtures = fixtures;
    }
  }

  public updateDraft(patch: Partial<NewValidationDraftState>): void {
    this.newValidationDraft.update(curr => {
      const next = {
        ...curr,
        ...patch,
        isDirty: true
      };

      // Bidirectional sync between comparisonUnits and legacy scopedPairs
      if (patch.comparisonUnits !== undefined && patch.scopedPairs === undefined) {
        next.scopedPairs = patch.comparisonUnits;
      } else if (patch.scopedPairs !== undefined && patch.comparisonUnits === undefined) {
        next.comparisonUnits = patch.scopedPairs;
      }

      // Invalidation Law: If Source Connection/Provider changes, invalidate Step 4 scope
      const sourceChanged = (patch.sourceProvider !== undefined && patch.sourceProvider !== curr.sourceProvider) ||
                            (patch.sourceHost !== undefined && patch.sourceHost !== curr.sourceHost) ||
                            (patch.sourceConnectionId !== undefined && patch.sourceConnectionId !== curr.sourceConnectionId);
      if (sourceChanged && patch.comparisonUnits === undefined && patch.scopedPairs === undefined) {
        next.selectedSourceNodeIds = [];
        next.scopedPairs = [];
        next.comparisonUnits = [];
        if (next.validationContext === 'INDEPENDENT') {
          next.baselineIntent = undefined;
          next.maintenanceCondition = undefined;
        }
      }

      // Invalidation Law: If Target Connection/Provider changes, invalidate Target confirmation on scoped pairs
      const targetChanged = (patch.targetProvider !== undefined && patch.targetProvider !== curr.targetProvider) ||
                            (patch.targetHost !== undefined && patch.targetHost !== curr.targetHost) ||
                            (patch.targetConnectionId !== undefined && patch.targetConnectionId !== curr.targetConnectionId);
      if (targetChanged && patch.comparisonUnits === undefined && patch.scopedPairs === undefined) {
        if (next.validationContext === 'INDEPENDENT') {
          next.baselineIntent = undefined;
          next.maintenanceCondition = undefined;
        }
        if (next.comparisonUnits && next.comparisonUnits.length > 0) {
          next.comparisonUnits = next.comparisonUnits.map(p => ({
            ...p,
            expectedTargetId: undefined,
            expectedTargetName: undefined,
            targetId: undefined,
            targetName: undefined,
            targetStatus: 'UNRESOLVED' as const,
            isDecisionRequired: true,
            decisionReason: 'Target endpoint was changed; confirmation required'
          }));
          next.scopedPairs = next.comparisonUnits;
        } else if (next.scopedPairs && next.scopedPairs.length > 0) {
          next.scopedPairs = next.scopedPairs.map(p => ({
            ...p,
            targetId: undefined,
            targetName: undefined,
            targetStatus: 'UNRESOLVED' as const,
            isDecisionRequired: true,
            statusNote: 'Target endpoint was changed; confirmation required'
          }));
          next.comparisonUnits = next.scopedPairs;
        }
      }

      return next;
    });
  }

  public setValidationContext(type: ValidationContextType): void {
    this.newValidationDraft.update(curr => ({
      ...curr,
      validationContext: type,
      projectId: type === 'INDEPENDENT' ? undefined : curr.projectId,
      projectName: type === 'INDEPENDENT' ? undefined : curr.projectName,
      step4Pathway: type === 'EXISTING_PROJECT' ? 'INHERIT' : 'CHOICE',
      baselineIntent: type === 'EXISTING_PROJECT' ? 'INHERITED_MIGRATION' : undefined,
      maintenanceCondition: undefined,
      isDirty: true
    }));
  }

  public isStepValid(step: number): boolean {
    if (step === 1) {
      return this.isStep1Valid();
    }
    if (step === 2) {
      return this.isStep2Valid();
    }
    if (step === 3) {
      return this.isStep3Valid();
    }
    if (step === 4) {
      return this.isStep4Valid();
    }
    if (step === 5) {
      return this.isStep5Valid();
    }
    if (step === 6) {
      return this.isStep6Valid();
    }
    if (step === 7) {
      return this.isStep7Valid();
    }
    if (step === 8) {
      return this.isStep8Valid();
    }
    return true;
  }

  public resetDraft(): void {
    this.newValidationDraft.set({ ...INITIAL_DRAFT });
  }

  public loadDemoFixtures(): void {
    this.validationItems.set(this.fixtures.getValidationItems());
  }

  public openRepairModal(): void {
    this.isRepairModalOpen.set(true);
  }

  public closeRepairModal(): void {
    this.isRepairModalOpen.set(false);
  }
}
