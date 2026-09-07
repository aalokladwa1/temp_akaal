/**
 * validation-discrepancies.models.ts
 * =====================================
 * Canonical models and UI view contracts for the Discrepancies & Reconciliation workspace.
 * Strictly non-mutating (M8 Validation authority).
 */

export type DiscrepancyCategory =
  | 'VALUE_DIFFERENCE'
  | 'MISSING_ON_TARGET'
  | 'EXTRA_ON_TARGET'
  | 'STRUCTURAL_DIFFERENCE'
  | 'CARDINALITY_DIFFERENCE'
  | 'PARTITION_FINGERPRINT'
  | 'UNRESOLVED_CORRESPONDENCE'
  | 'INCONCLUSIVE';

export type DiscrepancyProofTier =
  | 'TIER_1_STRUCTURAL'
  | 'TIER_2_CARDINALITY'
  | 'TIER_3_PARTITION'
  | 'TIER_4_ATTRIBUTE';

export type ReconciliationState =
  | 'UNRESOLVED'
  | 'CONFIRMED_DISCREPANCY'
  | 'EXPECTED_DIFFERENCE'
  | 'EXPLAINED_BY_TRANSFORMATION'
  | 'EXCLUDED_BY_SCOPE'
  | 'INCONCLUSIVE';

export type AttributeDifferenceType =
  | 'MATCH'
  | 'DIFFERENT'
  | 'SOURCE_ONLY'
  | 'TARGET_ONLY'
  | 'TYPE_MISMATCH';

export type AttributeValueKind =
  | 'SCALAR'
  | 'NULL'
  | 'EMPTY_STRING'
  | 'WHITESPACE'
  | 'PROTECTED'
  | 'LOB_TRUNCATED'
  | 'ABSENT';

export interface AttributeComparisonItem {
  attributeName: string;
  sourceValue: any;
  sourceValueKind: AttributeValueKind;
  sourceType?: string;
  targetValue: any;
  targetValueKind: AttributeValueKind;
  targetType?: string;
  diffType: AttributeDifferenceType;
  isKey?: boolean;
  isSensitive?: boolean;
  transformationNote?: string;
  lobMetadata?: {
    byteLength: number;
    mimeType: string;
    digest?: string;
  };
}

export interface CardinalitySummary {
  sourceCount: number;
  targetCount: number;
  delta: number;
  localizationStatus: 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE';
  boundaryFilter?: string;
}

export interface FingerprintSummary {
  sourceHash: string;
  targetHash: string;
  partitionRange?: string;
  localizationStatus: 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE';
  hostileXorNote?: string;
}

export interface StructuralSummary {
  sourceSchemaDetails: string;
  targetSchemaDetails: string;
  differenceDetail: string;
}

export interface TransformationContext {
  sourceAttributeMapped: string;
  targetAttributeMapped: string;
  ruleName: string;
  transformationType?: string;
  filterPredicate?: string;
  dedupPolicy?: string;
  maskingApplied?: boolean;
}

export interface DiscrepancyBaselineContext {
  baselineId: string;
  baselineStatus: 'VALID' | 'STALE' | 'NOT_AVAILABLE';
  snapshotTimestamp: string;
  baselineHash?: string;
}

export interface GovernanceHandoff {
  requiresGovernedRepair: boolean;
  repairEligible: boolean;
  repairPolicyNote: string;
  linkedRepairPlanId?: string;
}

export interface DiscrepancyItem {
  id: string;
  objectName: string;
  partitionId?: string;
  recordKey: string;
  category: DiscrepancyCategory;
  proofTier: DiscrepancyProofTier;
  reconciliationState: ReconciliationState;
  differenceSummary: string;
  affectedAttributes: string[];
  totalAttributesCompared: number;
  attributes: AttributeComparisonItem[];
  sourceEndpoint: {
    provider: string;
    label: string;
    location: string;
  };
  targetEndpoint: {
    provider: string;
    label: string;
    location: string;
  };
  cardinalitySummary?: CardinalitySummary;
  fingerprintSummary?: FingerprintSummary;
  structuralSummary?: StructuralSummary;
  transformationContext?: TransformationContext;
  baselineContext?: DiscrepancyBaselineContext;
  governanceHandoff?: GovernanceHandoff;
  timestamp?: string;
}

export interface DiscrepanciesSummaryModel {
  totalDiscrepancies: number | null;
  totalDiscrepanciesFormatted: string;
  affectedObjectsCount: number | null;
  evaluatedScopeCount: number | null;
  localizationStatus: 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE';
  baselineStatus: 'VALID' | 'STALE' | 'NOT_AVAILABLE';
  unresolvedCount: number | null;
  explainedCount: number | null;
  isLargeAggregate: boolean;
  boundedPageSize: number;
  totalKnownPages: number | null;
  currentPage: number;
}

export interface ScopePartitionItem {
  partitionId: string;
  findingsCount: number;
  status: string;
}

export interface ScopeNavigatorItem {
  objectName: string;
  totalFindings: number;
  categoryCounts: Record<string, number>;
  partitions: ScopePartitionItem[];
  localizationAvailable: boolean;
}

export type DiscrepancyViewStatus =
  | 'READY'
  | 'LOADING'
  | 'EMPTY'
  | 'NOT_EVALUATED'
  | 'UNAVAILABLE'
  | 'ERROR';

export interface DiscrepanciesWorkspaceModel {
  summary: DiscrepanciesSummaryModel;
  navigator: ScopeNavigatorItem[];
  items: DiscrepancyItem[];
  selectedDiscrepancyId: string | null;
  selectedObjectFilter: string | null;
  selectedPartitionFilter: string | null;
  selectedCategoryFilter: DiscrepancyCategory | 'ALL';
  selectedProofTierFilter: DiscrepancyProofTier | 'ALL';
  selectedReconciliationFilter: ReconciliationState | 'ALL';
  searchQuery: string;
  showDifferencesOnly: boolean;
  pagination: {
    currentPage: number;
    pageSize: number;
    totalItems: number | null;
    isServerBacked: boolean;
  };
  viewStatus: DiscrepancyViewStatus;
  errorMessage?: string;
  isHistorical?: boolean;
}
