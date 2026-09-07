export type Step4Pathway = 'INHERIT' | 'CHOICE' | 'IMPORT' | 'DEFINE';

export type CorrespondenceProvenance =
  | 'MIGRATION_PLAN'
  | 'IMPORTED_METADATA'
  | 'DECLARED_RULE'
  | 'OPERATOR_DEFINED';

export type PhysicalObservationStatus =
  | 'DISCOVERED'
  | 'NOT_DISCOVERED'
  | 'UNAVAILABLE';

export type ScopeDisposition = 'INCLUDED' | 'EXCLUDED';

export interface ColumnCorrespondenceItem {
  sourceColumn: string;
  sourceType: string;
  targetColumn: string;
  targetType: string;
  isPrimaryKey?: boolean;
  isNullable?: boolean;
}

export interface ComparisonUnit {
  id: string;
  // Source side
  sourceId: string;
  sourceName: string;
  sourceNamespace: string;
  sourceType: string; // 'Table' | 'View' | 'Collection' | 'Topic' | 'Dataset'
  sourceTypeIcon?: string;
  sourceKeyFact: string; // e.g. 'PK: ACC_ID' | 'Composite PK (2)' | 'No key discovered'
  sourceVolumeFact: string; // e.g. '18.6M rows (estimate)'
  sourceVolumeBytes?: number;
  sourceEstimatedRows?: number;

  // Expected Target Counterpart
  expectedTargetId?: string;
  expectedTargetName?: string;
  expectedTargetNamespace?: string;
  expectedTargetType?: string;
  expectedTargetKeyFact?: string;
  expectedTargetVolumeFact?: string;

  // The 3 Distinct Dimensions
  disposition: ScopeDisposition;
  provenance: CorrespondenceProvenance;
  provenanceBasis: string; // e.g. 'Migration Plan (Execution Graph)', 'Rule: Exact Identifier Match', 'Operator Selection'
  observationStatus: PhysicalObservationStatus;
  observationNote?: string;

  // Operator Decisions (if ambiguous / unmapped)
  isDecisionRequired?: boolean;
  decisionReason?: string;
  previousDecisionReason?: string;

  // Secondary Column Details
  columns?: ColumnCorrespondenceItem[];

  // Compatibility fields for legacy consumers
  targetId?: string;
  targetName?: string;
  targetNamespace?: string;
  targetType?: string;
  targetTypeIcon?: string;
  targetKeyFact?: string;
  targetVolumeFact?: string;
  targetStatus?: ScopedPairTargetStatus;
  candidateTargetName?: string;
  candidateReason?: string;
}

// Backward compatibility alias for any existing references
export type ScopedComparisonPair = ComparisonUnit;
export type ScopedPairTargetStatus =
  | 'CONFIRMED'
  | 'INHERITED_CONFIRMED'
  | 'UNRESOLVED'
  | 'CANDIDATE_REQUIRES_CONFIRMATION'
  | 'UNAVAILABLE'
  | 'STALE';

export interface MigrationExecutionSummary {
  totalUnits: number;
  completedUnits: number;
  failedUnits: number;
  inProgressUnits: number;
  schemas: string[];
}

export interface OperatorDecisionItem {
  unitId: string;
  sourceName: string;
  sourceNamespace: string;
  sourceKeyFact: string;
  sourceVolumeFact: string;
  issue: string;
  selectedTarget?: string;
  suggestedCandidates?: { id: string; name: string; namespace: string }[];
}

export interface NamespaceScopeItem {
  namespace: string;
  totalUnits: number;
  includedUnits: number;
  isIncluded: boolean;
}

export interface DiscoveredComparisonUnit {
  id: string;
  name: string;
  qualifiedName: string;
  type: string;
  typeLabel: string;
  icon: string;
  namespace?: string;
  database?: string;
  keyFact: string;
  volumeFact: string;
  volumeBytes?: number;
  estimatedRows?: number | null;
  columns?: ColumnCorrespondenceItem[];
}

export interface DiscoveredHierarchyNode {
  id: string;
  name: string;
  type: 'INSTANCE' | 'CLUSTER' | 'DATABASE' | 'SCHEMA' | 'CONTAINER' | 'GROUP' | 'LEAF';
  typeLabel: string;
  icon: string;
  isLeaf: boolean;
  leafData?: DiscoveredComparisonUnit;
  children?: DiscoveredHierarchyNode[];
}

export interface FlattenedScopeNode {
  node: DiscoveredHierarchyNode;
  level: number;
  isExpanded: boolean;
  isVisible: boolean;
  hasChildren: boolean;
  isIndeterminate: boolean;
  isSelected: boolean;
}

export interface HierarchyFilterOption {
  id: string;
  label: string;
  count: number;
}
