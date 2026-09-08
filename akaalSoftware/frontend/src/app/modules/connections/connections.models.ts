/**
 * AKAAL Connections Domain & Presentation Models
 * Governs Connection Inventory, 49 physical providers across 8 families,
 * 4 managed-cloud profile resolvers, and truthful point-in-time verification states.
 */

export type ConnectionFamily =
  | 'RELATIONAL'
  | 'WAREHOUSE_LAKE'
  | 'NOSQL_GRAPH'
  | 'STREAMING'
  | 'OBJECT_STORAGE'
  | 'TIME_SERIES'
  | 'APPLICATION'
  | 'MANAGED_CLOUD';

export type ConnectionRoleApplicability =
  | 'SOURCE_AND_TARGET'
  | 'SOURCE_ONLY'
  | 'TARGET_ONLY';

export type ConnectionVerificationState =
  | 'VERIFIED_RECENT'             // Verified recently within expected freshness window
  | 'VERIFIED_POINT_IN_TIME'       // Point-in-time test succeeded in the past
  | 'VERIFIED_STALE'              // Verification exceeds freshness threshold
  | 'CONFIG_CHANGED_SINCE_TEST'   // Configuration/credentials mutated since last successful probe
  | 'PARTIAL_VERIFIED'            // L1/L2 Connectivity succeeded, L3/L4 schema/permission unprobed
  | 'TESTING'                     // Active probe in progress
  | 'NEVER_TESTED'                // Newly authored, never verified
  | 'VERIFICATION_FAILED'         // Most recent probe encountered an error
  | 'UNAVAILABLE'                 // Verification authority or network bridge unreachable
  | 'UNAUTHORIZED'                // Operator lacks RBAC/ABAC permission to view/trigger verification
  | 'UNKNOWN';                    // Remote engine state undetermined

export type EntityAvailabilityState =
  | 'READY'
  | 'LOADING'
  | 'EMPTY'
  | 'FILTERED_EMPTY'
  | 'UNAVAILABLE'
  | 'NOT_CONNECTED'
  | 'UNAUTHORIZED'
  | 'ERROR';

export type ConnectionSortField =
  | 'name'
  | 'provider'
  | 'family'
  | 'lastVerified'
  | 'updatedAt'
  | 'usageCount';

export type SortDirection = 'asc' | 'desc';

export interface ConnectionUsageContext {
  referencedProjectCount: number;
  activeMigrationCount: number;
  activeValidationCount: number;
  projectNames?: string[];
  migrationNames?: string[];
  isUnused: boolean;
  usageAvailable: boolean; // false when backend usage authority is unprobed/partial
}

export interface ConnectionFabricContext {
  site?: string;
  locality?: string;
  privateRoute?: string;
  transitVpc?: string;
  datacenterZone?: string;
}

export interface ConnectionIntelligenceAdvisory {
  type: 'ANOMALY' | 'REVIEW_RECOMMENDED' | 'COST_EFFICIENCY';
  headline: string;
  description?: string;
}

export interface ConnectionRecord {
  id: string;
  name: string;
  description?: string;
  providerId: string;
  providerName: string;
  family: ConnectionFamily;
  environment: 'Production' | 'Staging' | 'Development' | 'Disaster Recovery';
  workspaceId: string;
  workspaceName?: string;
  organizationId?: string;
  
  // Safe endpoint summary - tailored by system type (NEVER includes passwords/tokens/keys)
  endpointDisplay: string;
  safeRouteInfo?: string;
  tlsMode?: 'TLS_1_3' | 'TLS_1_2' | 'MUTUAL_TLS' | 'DISABLED' | 'UNKNOWN';
  authMethodDisplay: string; // e.g. "Vault IAM Token", "Kerberos Keytab", "mTLS Certificate", "IAM Role ARN"
  
  roleApplicability: ConnectionRoleApplicability;
  verificationState: ConnectionVerificationState;
  lastVerifiedAt: string | null;
  lastVerifiedDetails?: string;
  verificationFailureReason?: string;
  configChangedSinceTest?: boolean;
  
  usage: ConnectionUsageContext;
  fabric?: ConnectionFabricContext;
  advisory?: ConnectionIntelligenceAdvisory;
  
  tags?: string[];
  createdAt: string;
  updatedAt: string;
}

export interface ConnectionFilterState {
  searchQuery: string;
  family: ConnectionFamily | 'ALL';
  verificationState: ConnectionVerificationState | 'ALL' | 'VERIFIED_GROUP' | 'ATTENTION_GROUP';
  usageFilter: 'ALL' | 'IN_USE' | 'REFERENCED_PROJECTS' | 'UNUSED' | 'UNKNOWN';
  environment: 'ALL' | 'Production' | 'Staging' | 'Development';
  role: 'ALL' | ConnectionRoleApplicability;
  sortBy: ConnectionSortField;
  sortDirection: SortDirection;
}

export interface ConnectionSummaryCounters {
  total: number;
  verified: number;
  needsAttention: number; // failed, stale, config changed
  unused: number;
  testing: number;
}
