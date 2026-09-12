/**
 * AKAAL Administration — 5.7 Cloud & Infrastructure Service
 * Authoritative presentation service for Cloud Environments, Compute, Connectivity, Placement, and Automation.
 */

import { Injectable, signal } from '@angular/core';
import {
  CloudEnvironment,
  KubernetesClusterConfig,
  ExecutionSite,
  PrivateConnectivityConfig,
  NetworkRouteConfig,
  HybridEnvironment,
  RegionEntry,
  DataSovereigntyPolicy,
  IacConfig,
  GitOpsConfig,
  CloudProviderType
} from '../models/infrastructure.models';

@Injectable({
  providedIn: 'root'
})
export class InfrastructureService {
  // Cloud Environments
  public cloudEnvironments = signal<CloudEnvironment[]>([
    {
      id: 'cenv-aws-01',
      name: 'AWS Global Production Estate',
      provider: 'AWS',
      accountIdOrTenant: '112233445566',
      defaultRegion: 'us-east-1',
      credentialRef: 'vault://secret/cloud/aws/prod-role-arn',
      status: 'ACTIVE',
      configuredRegions: ['us-east-1', 'us-west-2', 'eu-west-1'],
      executionSiteIds: ['site-eks-01', 'site-vpc-02'],
      tags: ['Production', 'Enterprise-Core', 'AWS-GovCloud-Eligible'],
      createdAt: '2025-08-10'
    },
    {
      id: 'cenv-azure-01',
      name: 'Azure Enterprise Hub Subscription',
      provider: 'AZURE',
      accountIdOrTenant: '7f92a104-55cc-4e89-9a22-38b021a88bb3',
      defaultRegion: 'eastus2',
      credentialRef: 'vault://secret/cloud/azure/service-principal-ref',
      status: 'ACTIVE',
      configuredRegions: ['eastus2', 'westeurope'],
      executionSiteIds: ['site-aks-01'],
      tags: ['Azure-Corp', 'Staging-Prod-Mirror'],
      createdAt: '2025-09-15'
    },
    {
      id: 'cenv-gcp-01',
      name: 'GCP Analytics Data Estate Project',
      provider: 'GCP',
      accountIdOrTenant: 'akaal-data-lake-prod-992',
      defaultRegion: 'us-central1',
      credentialRef: 'vault://secret/cloud/gcp/workload-identity-provider',
      status: 'ACTIVE',
      configuredRegions: ['us-central1', 'europe-west3'],
      executionSiteIds: ['site-gke-01'],
      tags: ['BigQuery-Host', 'GCP-Production'],
      createdAt: '2025-10-02'
    },
    {
      id: 'cenv-oci-01',
      name: 'Oracle Cloud ERP Foundation Tenancy',
      provider: 'OCI',
      accountIdOrTenant: 'ocid1.tenancy.oc1..aaaaaaaaxamplecorp99201',
      defaultRegion: 'us-ashburn-1',
      credentialRef: 'vault://secret/cloud/oci/api-signing-key-ref',
      status: 'ACTIVE',
      configuredRegions: ['us-ashburn-1', 'eu-frankfurt-1'],
      executionSiteIds: ['site-oci-oke-01'],
      tags: ['Oracle-EBS-Exadata', 'ERP-Tier-1'],
      createdAt: '2025-11-20'
    }
  ]);

  // Kubernetes Configurations
  public kubernetesConfigs = signal<KubernetesClusterConfig[]>([
    {
      id: 'k8s-01',
      name: 'EKS Primary Migration Compute Cluster',
      clusterName: 'akaal-prod-eks-us-east-1',
      apiEndpoint: 'https://B12809A1E04B4.gr7.us-east-1.eks.amazonaws.com',
      authType: 'PROJECTED_SA',
      credentialRef: 'vault://secret/k8s/eks-prod-token',
      defaultNamespace: 'akaal-workloads',
      clusterCidr: '10.100.0.0/16',
      associatedCloudEnvId: 'cenv-aws-01',
      proofLevel: 'LIVE_PROVEN',
      lastVerifiedAt: '2026-02-18 10:30 UTC',
      status: 'REGISTERED'
    },
    {
      id: 'k8s-02',
      name: 'AKS Europe Secure Transit Cluster',
      clusterName: 'akaal-sec-aks-westeurope',
      apiEndpoint: 'https://akaal-aks-westeurope-dns-3301.hcp.westeurope.azmk8s.io:443',
      authType: 'OIDC_FEDERATED',
      credentialRef: 'vault://secret/k8s/aks-oidc-federation',
      defaultNamespace: 'akaal-transit',
      clusterCidr: '10.244.0.0/16',
      associatedCloudEnvId: 'cenv-azure-01',
      proofLevel: 'INTEGRATION_PROVEN',
      lastVerifiedAt: '2026-02-14 08:15 UTC',
      status: 'REGISTERED'
    }
  ]);

  // Execution Sites
  public executionSites = signal<ExecutionSite[]>([
    {
      id: 'site-eks-01',
      name: 'AWS us-east-1 High-Throughput Worker Fleet',
      siteType: 'CLOUD_HOSTED',
      providerOrDatacenter: 'AWS us-east-1',
      region: 'us-east-1',
      maxParallelJobs: 32,
      egressProxyRef: 'route-proxy-01',
      status: 'ACTIVE',
      registeredAt: '2025-08-14'
    },
    {
      id: 'site-vpc-02',
      name: 'On-Premises Chicago Primary Datacenter Gateway',
      siteType: 'ON_PREMISES_DATACENTER',
      providerOrDatacenter: 'Equinix CH3 Datacenter',
      region: 'us-central-onprem',
      maxParallelJobs: 16,
      status: 'ACTIVE',
      registeredAt: '2025-09-01'
    },
    {
      id: 'site-aks-01',
      name: 'Azure West Europe Isolated Site',
      siteType: 'CUSTOMER_VPC',
      providerOrDatacenter: 'Azure VNet WestEurope-Core',
      region: 'westeurope',
      maxParallelJobs: 24,
      status: 'ACTIVE',
      registeredAt: '2025-09-20'
    }
  ]);

  // Private Connectivity
  public privateLinks = signal<PrivateConnectivityConfig[]>([
    {
      id: 'plink-01',
      name: 'AWS PrivateLink to Snowflake Internal VPC',
      mechanism: 'AWS_PRIVATELINK',
      targetVpcOrVnet: 'vpc-09941a8bb20',
      cidrBlock: '10.0.128.0/20',
      endpointServiceDns: 'com.amazonaws.vpce.us-east-1.vpce-svc-091924aa19',
      credentialRef: 'vault://secret/network/privatelink-auth',
      status: 'ESTABLISHED',
      createdAt: '2025-08-22'
    },
    {
      id: 'plink-02',
      name: 'Azure Private Endpoint to Azure SQL MI',
      mechanism: 'AZURE_PRIVATE_ENDPOINT',
      targetVpcOrVnet: 'vnet-core-transit-01',
      cidrBlock: '10.20.4.0/24',
      endpointServiceDns: 'privatelink.database.windows.net',
      status: 'ESTABLISHED',
      createdAt: '2025-10-12'
    }
  ]);

  // Network Routing / Proxy / Bastion
  public networkRoutes = signal<NetworkRouteConfig[]>([
    {
      id: 'route-proxy-01',
      name: 'Corporate Egress Forward Proxy',
      routeType: 'FORWARD_PROXY',
      targetHost: 'proxy-egress.corp.akaaltech.com',
      targetPort: 8080,
      credentialRef: 'vault://secret/proxy/corp-egress-token',
      bypassList: ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '*.internal.akaal.corp'],
      status: 'ACTIVE',
      createdAt: '2025-08-11'
    },
    {
      id: 'route-bastion-01',
      name: 'Legacy Mainframe SSH Bastion Gateway',
      routeType: 'SSH_BASTION',
      targetHost: 'bastion-chicago.corp.akaaltech.com',
      targetPort: 2222,
      credentialRef: 'vault://secret/ssh/bastion-ed25519-key',
      bypassList: [],
      status: 'ACTIVE',
      createdAt: '2025-09-05'
    }
  ]);

  // Hybrid Environments
  public hybridEnvironments = signal<HybridEnvironment[]>([
    {
      id: 'hybrid-01',
      name: 'Chicago On-Prem to AWS us-east-1 DirectConnect Trunk',
      cloudEnvId: 'cenv-aws-01',
      executionSiteId: 'site-vpc-02',
      interconnectType: 'AWS_DIRECT_CONNECT',
      mtu: 9001,
      bandwidthMbps: 10000,
      status: 'ACTIVE'
    }
  ]);

  // Regions Catalog
  public regionsCatalog = signal<RegionEntry[]>([
    { id: 'reg-01', provider: 'AWS', regionCode: 'us-east-1', displayName: 'US East (N. Virginia)', isAllowedByPolicy: true, complianceZone: 'US_DOMESTIC' },
    { id: 'reg-02', provider: 'AWS', regionCode: 'us-west-2', displayName: 'US West (Oregon)', isAllowedByPolicy: true, complianceZone: 'US_DOMESTIC' },
    { id: 'reg-03', provider: 'AWS', regionCode: 'eu-west-1', displayName: 'Europe (Ireland)', isAllowedByPolicy: true, complianceZone: 'EU_EEA' },
    { id: 'reg-04', provider: 'AZURE', regionCode: 'eastus2', displayName: 'East US 2 (Virginia)', isAllowedByPolicy: true, complianceZone: 'US_DOMESTIC' },
    { id: 'reg-05', provider: 'AZURE', regionCode: 'westeurope', displayName: 'West Europe (Netherlands)', isAllowedByPolicy: true, complianceZone: 'EU_EEA' },
    { id: 'reg-06', provider: 'GCP', regionCode: 'us-central1', displayName: 'US Central (Iowa)', isAllowedByPolicy: true, complianceZone: 'US_DOMESTIC' },
    { id: 'reg-07', provider: 'GCP', regionCode: 'europe-west3', displayName: 'Europe West (Frankfurt)', isAllowedByPolicy: true, complianceZone: 'EU_EEA' },
    { id: 'reg-08', provider: 'OCI', regionCode: 'us-ashburn-1', displayName: 'US East (Ashburn)', isAllowedByPolicy: true, complianceZone: 'US_DOMESTIC' }
  ]);

  // Data Sovereignty Policies
  public sovereigntyPolicies = signal<DataSovereigntyPolicy[]>([
    {
      id: 'sov-01',
      name: 'European Union GDPR Data Residency Boundary',
      jurisdiction: 'EU_EEA',
      allowedRegions: ['eu-west-1', 'westeurope', 'europe-west3', 'eu-frankfurt-1'],
      deniedRegions: ['us-east-1', 'us-west-2', 'eastus2', 'us-central1', 'us-ashburn-1'],
      restrictedDataClasses: ['EU_PII', 'GDPR_CONFIDENTIAL', 'FINANCIAL_TAX'],
      enforceStrictBoundary: true,
      status: 'ENFORCED'
    },
    {
      id: 'sov-02',
      name: 'United States Federal / Commercial Residency Boundary',
      jurisdiction: 'US_FEDERAL',
      allowedRegions: ['us-east-1', 'us-west-2', 'eastus2', 'us-central1', 'us-ashburn-1'],
      deniedRegions: ['eu-west-1', 'westeurope', 'europe-west3'],
      restrictedDataClasses: ['US_PERSON_PII', 'ITAR_RESTRICTED', 'CJIS_CRIMINAL'],
      enforceStrictBoundary: true,
      status: 'ENFORCED'
    }
  ]);

  // Infrastructure as Code (IaC)
  public iacConfigs = signal<IacConfig[]>([
    {
      id: 'iac-01',
      name: 'Enterprise Cloud Landing Zone Terraform Blueprint',
      toolType: 'OPEN_TOFU',
      repositoryRef: 'git@github.com:akaal-corp/cloud-infrastructure-tf.git',
      stateStorageBackend: 'AWS S3 + DynamoDB Lock',
      stateStorageRef: 's3://akaal-prod-tofu-state-useast1/infra/terraform.tfstate',
      lastPlanChecksum: 'sha256-55aa88bb9910cde',
      lastPlanDate: '2026-02-19 14:20 UTC',
      status: 'CONFIGURED'
    }
  ]);

  // GitOps Configuration
  public gitOpsConfigs = signal<GitOpsConfig[]>([
    {
      id: 'gitops-01',
      name: 'Fleet Kubernetes Cluster Workload Manifests',
      repositoryUrl: 'https://github.com/akaal-corp/gitops-cluster-workloads.git',
      targetBranch: 'main',
      manifestsPath: 'clusters/production/environments',
      credentialRef: 'vault://secret/git/deploy-key-ref',
      syncIntervalMinutes: 5,
      status: 'SYNCED',
      lastSyncAt: '5 minutes ago'
    }
  ]);

  public getEnvironmentById(id: string): CloudEnvironment | undefined {
    return this.cloudEnvironments().find(e => e.id === id);
  }

  public getKubernetesById(id: string): KubernetesClusterConfig | undefined {
    return this.kubernetesConfigs().find(k => k.id === id);
  }

  public getSiteById(id: string): ExecutionSite | undefined {
    return this.executionSites().find(s => s.id === id);
  }

  public createCloudEnvironment(env: Omit<CloudEnvironment, 'id' | 'createdAt' | 'status'>): void {
    const newRecord: CloudEnvironment = {
      ...env,
      id: `cenv-${env.provider.toLowerCase()}-${Date.now()}`,
      status: 'ACTIVE',
      createdAt: new Date().toISOString().split('T')[0]
    };
    this.cloudEnvironments.update(list => [newRecord, ...list]);
  }

  public createKubernetesConfig(cfg: Omit<KubernetesClusterConfig, 'id' | 'proofLevel' | 'lastVerifiedAt' | 'status'>): void {
    const newRecord: KubernetesClusterConfig = {
      ...cfg,
      id: `k8s-${Date.now()}`,
      proofLevel: 'UNIT_PROVEN',
      lastVerifiedAt: 'Pending Live External Probe',
      status: 'REGISTERED'
    };
    this.kubernetesConfigs.update(list => [newRecord, ...list]);
  }

  public createExecutionSite(site: Omit<ExecutionSite, 'id' | 'registeredAt' | 'status'>): void {
    const newRecord: ExecutionSite = {
      ...site,
      id: `site-${Date.now()}`,
      registeredAt: new Date().toISOString().split('T')[0],
      status: 'ACTIVE'
    };
    this.executionSites.update(list => [newRecord, ...list]);
  }

  public createPrivateLink(link: Omit<PrivateConnectivityConfig, 'id' | 'createdAt' | 'status'>): void {
    const newRecord: PrivateConnectivityConfig = {
      ...link,
      id: `plink-${Date.now()}`,
      createdAt: new Date().toISOString().split('T')[0],
      status: 'ESTABLISHED'
    };
    this.privateLinks.update(list => [newRecord, ...list]);
  }

  public createNetworkRoute(route: Omit<NetworkRouteConfig, 'id' | 'createdAt' | 'status'>): void {
    const newRecord: NetworkRouteConfig = {
      ...route,
      id: `route-${Date.now()}`,
      createdAt: new Date().toISOString().split('T')[0],
      status: 'ACTIVE'
    };
    this.networkRoutes.update(list => [newRecord, ...list]);
  }
}
