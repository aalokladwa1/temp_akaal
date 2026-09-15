/**
 * AKAAL Administration — 5.5 Template & Configuration Library Domain Models
 */

export type AssetFamily = 
  | 'MIGRATION_TEMPLATE'
  | 'MAPPING_TEMPLATE'
  | 'TRANSFORMATION_TEMPLATE'
  | 'PRIVACY_POLICY'
  | 'DATA_QUALITY_POLICY'
  | 'CONFIGURATION_PROFILE';

export type TemplateStatus = 'DRAFT' | 'PUBLISHED' | 'DEPRECATED' | 'ARCHIVED';
export type PromotionTargetEnv = 'DEVELOPMENT' | 'STAGING' | 'PRODUCTION';

export interface VersionHistoryEntry {
  version: string;
  releaseDate: string;
  authorEmail: string;
  commitHash: string;
  changelog: string;
  breakingChanges: boolean;
  checksum: string;
}

export interface DependencyUsageEntry {
  id: string;
  consumerType: 'PIPELINE' | 'WORKSPACE' | 'CONNECTOR' | 'ENVIRONMENT' | 'MIGRATION_JOB';
  consumerName: string;
  consumerScope: string;
  boundVersion: string;
  lastExecutionTimestamp: string;
  healthStatus: 'HEALTHY' | 'WARNING' | 'FAILED';
}

export interface TemplateAsset {
  id: string;
  name: string;
  code: string;
  family: AssetFamily;
  category: string;
  description: string;
  currentVersion: string;
  authorName: string;
  authorEmail: string;
  environmentTier: PromotionTargetEnv;
  status: TemplateStatus;
  isSystemProvided: boolean;
  tags: string[];
  specPayload: string; // JSON / YAML configuration payload
  versions: VersionHistoryEntry[];
  usages: DependencyUsageEntry[];
  deprecationNotice?: {
    reason: string;
    targetReplacementAssetId?: string;
    effectiveEndOfLifeDate: string;
  };
  createdAt: string;
  updatedAt: string;
}

export interface AssetFamilySummary {
  family: AssetFamily;
  title: string;
  description: string;
  icon: string;
  routePath: string;
  totalAssetsCount: number;
  publishedCount: number;
  deprecatedCount: number;
  activeUsagesCount: number;
}
