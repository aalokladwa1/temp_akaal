import { PhysicalProviderId, MigrationMode, DiscoveryDepthTier } from '../../../../core/models/migration-view.models';

export type Step4LifecycleState = 'DEPTH_SELECTION' | 'DISCOVERING' | 'FAILURE' | 'SCOPE_WORKBENCH';

export type ResourceEligibilityStatus = 'READY' | 'ADVISORY' | 'BLOCKED';

export type DiscoveredNodeType =
  | 'INSTANCE'
  | 'DATABASE'
  | 'SCHEMA'
  | 'OBJECT_GROUP'
  | 'TABLE'
  | 'VIEW'
  | 'PROCEDURE'
  | 'FUNCTION'
  | 'PACKAGE'
  | 'TRIGGER'
  | 'SEQUENCE'
  | 'COLLECTION'
  | 'TOPIC'
  | 'PARTITION'
  | 'BUCKET'
  | 'PREFIX'
  | 'OBJECT'
  | 'PATH';

export type CountAccuracy = 'EXACT_ROW_COUNT' | 'CATALOG_ESTIMATE' | 'STATISTICAL_SAMPLE' | 'UNAVAILABLE';

export interface DiscoveredResourceNode {
  id: string;
  name: string;
  type: DiscoveredNodeType;
  typeLabel: string;
  namespace?: string;
  database?: string;
  estimatedRows?: number | null;
  countAccuracy?: CountAccuracy;
  estimatedSizeBytes?: number | null;
  status: ResourceEligibilityStatus;
  statusReason?: string;
  secondaryTraits?: string[];
  isSelected: boolean;
  isDependencyReference?: boolean;
  isMigratable: boolean;
  parentId?: string;
  children?: DiscoveredResourceNode[];
}

export interface FlattenedTreeNode {
  node: DiscoveredResourceNode;
  level: number;
  isExpanded: boolean;
  isVisible: boolean;
  hasChildren: boolean;
  isIndeterminate: boolean;
}

export interface DiscoveryStageEvent {
  id: string;
  label: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  durationMs?: number;
  itemsCount?: number;
  detail?: string;
}

export interface ScopeSummaryMetrics {
  schemasSelected: number;
  schemasTotal: number;
  objectsSelected: number;
  objectsTotal: number;
  primaryTypeLabel: string;
  primarySelected: number;
  volumeSelectedBytes: number;
  volumeFormatted: string;
  isVolumeApplicable: boolean;
  selectedBlockersCount: number;
  selectedAdvisoriesCount: number;
  excludedReferencedCount: number;
}

export interface DiscoveryDepthCardOption {
  depth: DiscoveryDepthTier;
  title: string;
  badge?: string;
  tag: string;
  description: string;
}

export interface HierarchyFilterLabels {
  level1Label: string; // e.g. "Instance" / "Database" / "Cluster" / "Endpoint"
  level2Label: string; // e.g. "Schema" / "Database" / "Namespace" / "Bucket"
  primaryObjectLabel: string; // e.g. "Tables" / "Collections" / "Topics" / "Objects"
}
