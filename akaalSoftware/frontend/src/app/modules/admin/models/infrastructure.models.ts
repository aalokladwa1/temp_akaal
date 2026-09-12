/**
 * AKAAL Administration — 5.7 Cloud & Infrastructure Models
 * Governs Cloud Environments (AWS, Azure, GCP, OCI), Compute (Kubernetes, Execution Sites),
 * Connectivity (Private links, Proxy/Bastion routing, Hybrid topologies),
 * Placement (Regions, Sovereignty), and Automation (IaC, GitOps).
 */

export type CloudProviderType = 'AWS' | 'AZURE' | 'GCP' | 'OCI';

export interface CloudEnvironment {
  id: string;
  name: string;
  provider: CloudProviderType;
  accountIdOrTenant: string;
  defaultRegion: string;
  credentialRef: string; // Vault / KMS secret reference, zero plaintext
  status: 'ACTIVE' | 'PENDING_VERIFICATION' | 'SUSPENDED';
  configuredRegions: string[];
  executionSiteIds: string[];
  tags: string[];
  createdAt: string;
}

export type KubernetesAuthType = 'PROJECTED_SA' | 'OIDC_FEDERATED' | 'KUBECONFIG_ESCROW';

export interface KubernetesClusterConfig {
  id: string;
  name: string;
  clusterName: string;
  apiEndpoint: string;
  authType: KubernetesAuthType;
  credentialRef: string;
  defaultNamespace: string;
  clusterCidr: string;
  associatedCloudEnvId?: string;
  proofLevel: 'LIVE_PROVEN' | 'INTEGRATION_PROVEN' | 'UNIT_PROVEN';
  lastVerifiedAt: string;
  status: 'REGISTERED' | 'UNREACHABLE' | 'DEGRADED';
}

export type ExecutionSiteType = 'CLOUD_HOSTED' | 'CUSTOMER_VPC' | 'ON_PREMISES_DATACENTER';

export interface ExecutionSite {
  id: string;
  name: string;
  siteType: ExecutionSiteType;
  providerOrDatacenter: string;
  region: string;
  maxParallelJobs: number;
  egressProxyRef?: string;
  status: 'ACTIVE' | 'DRAINING' | 'INACTIVE';
  registeredAt: string;
}

export type PrivateConnectivityMechanism =
  | 'AWS_PRIVATELINK'
  | 'AZURE_PRIVATE_ENDPOINT'
  | 'GCP_PSC'
  | 'IPSEC_VPN';

export interface PrivateConnectivityConfig {
  id: string;
  name: string;
  mechanism: PrivateConnectivityMechanism;
  targetVpcOrVnet: string;
  cidrBlock: string;
  endpointServiceDns: string;
  credentialRef?: string;
  status: 'ESTABLISHED' | 'PENDING_ACCEPTANCE' | 'DISCONNECTED';
  createdAt: string;
}

export type NetworkRouteType = 'DIRECT' | 'FORWARD_PROXY' | 'REVERSE_PROXY' | 'SSH_BASTION';

export interface NetworkRouteConfig {
  id: string;
  name: string;
  routeType: NetworkRouteType;
  targetHost: string;
  targetPort: number;
  credentialRef?: string;
  bypassList: string[];
  status: 'ACTIVE' | 'DISABLED';
  createdAt: string;
}

export interface HybridEnvironment {
  id: string;
  name: string;
  cloudEnvId: string;
  executionSiteId: string;
  interconnectType: 'AWS_DIRECT_CONNECT' | 'AZURE_EXPRESSROUTE' | 'GCP_INTERCONNECT' | 'SITE_TO_SITE_VPN';
  mtu: number;
  bandwidthMbps: number;
  status: 'ACTIVE' | 'MAINTENANCE';
}

export interface RegionEntry {
  id: string;
  provider: CloudProviderType;
  regionCode: string;
  displayName: string;
  isAllowedByPolicy: boolean;
  complianceZone: string;
}

export interface DataSovereigntyPolicy {
  id: string;
  name: string;
  jurisdiction: 'EU_EEA' | 'US_FEDERAL' | 'APAC_SG' | 'GLOBAL_RESIDENT';
  allowedRegions: string[];
  deniedRegions: string[];
  restrictedDataClasses: string[];
  enforceStrictBoundary: boolean;
  status: 'ENFORCED' | 'AUDIT_ONLY';
}

export interface IacConfig {
  id: string;
  name: string;
  toolType: 'TERRAFORM' | 'OPEN_TOFU';
  repositoryRef: string;
  stateStorageBackend: string;
  stateStorageRef: string;
  lastPlanChecksum?: string;
  lastPlanDate?: string;
  status: 'CONFIGURED' | 'DRIFT_DETECTED';
}

export interface GitOpsConfig {
  id: string;
  name: string;
  repositoryUrl: string;
  targetBranch: string;
  manifestsPath: string;
  credentialRef: string;
  syncIntervalMinutes: number;
  status: 'SYNCED' | 'PENDING' | 'ERROR';
  lastSyncAt: string;
}
