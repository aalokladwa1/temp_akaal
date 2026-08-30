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
  GovernedRepairPlan
} from '../models/migration-view.models';

export interface NewValidationDraftState {
  name: string;
  purpose: ValidationPurpose;
  associatedMigrationId?: string;
  environment: string;
  owner: string;
  priority: 'NORMAL' | 'HIGH' | 'CRITICAL';
  
  referenceConnectionId: string;
  referenceProvider: PhysicalProviderId;
  comparisonConnectionId: string;
  comparisonProvider: PhysicalProviderId;

  scopeType: 'FULL' | 'PARTITIONED' | 'SAMPLED';
  profile: ValidationProfile;
  selectedObjects: string[];

  numericToleranceAbsolute: number;
  floatingEpsilon: number;
  timestampTolerateTimezone: boolean;
  stringTrimWhitespace: boolean;
  nullEmptyStringEquivalent: boolean;
  differencePolicy: 'REPORT_ONLY' | 'LOCALIZE_DIFF' | 'BUILD_RECON_PLAN' | 'GOVERNED_REPAIR';

  currentStep: number;
  isReadOnlyEnforced: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class ValidationUiService {
  private fixtures: MigrationDevFixturesAdapter = new MigrationDevFixturesAdapter();

  // Zero fake data by default
  public validationItems = signal<ValidationItem[]>([]);
  public filterVerdict = signal<string>('ALL');

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

  public newValidationDraft = signal<NewValidationDraftState>({
    name: '',
    purpose: 'POST_MIGRATION_VERIFICATION',
    environment: 'Production',
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
    differencePolicy: 'GOVERNED_REPAIR',
    currentStep: 1,
    isReadOnlyEnforced: true
  });

  constructor(fixtures?: MigrationDevFixturesAdapter) {
    if (fixtures) {
      this.fixtures = fixtures;
    }
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
