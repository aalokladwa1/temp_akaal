/**
 * AKAAL Administration — 5.6 Connector & Plugin Center and 5.7 Cloud & Infrastructure Configuration Unit Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { ConnectorsPluginsService } from './services/connectors-plugins.service';
import { InfrastructureService } from './services/infrastructure.service';

describe('5.6 Connector & Plugin Center Service & Workflows', () => {
  let connectorService: ConnectorsPluginsService;

  beforeEach(() => {
    connectorService = new ConnectorsPluginsService();
  });

  it('should initialize with authoritative built-in connectors catalog', () => {
    const connectors = connectorService.connectors();
    expect(connectors.length).toBeGreaterThanOrEqual(4);
    
    // Validate canonical connectors
    const pg = connectors.find(c => c.providerId === 'postgresql');
    expect(pg).toBeDefined();
    expect(pg?.capabilities.supportsCdc).toBe(true);
    expect(pg?.certificationLevel).toBe('LIVE_PROVEN');
    expect(pg?.isBuiltIn).toBe(true);
  });

  it('should retrieve a connector by its unique identifier', () => {
    const pg = connectorService.getConnectorById('conn-pg-01');
    expect(pg).toBeDefined();
    expect(pg?.name).toContain('PostgreSQL');
    expect(pg?.driverVersion).toBe('pgjdbc-42.7.2');
  });

  it('should register an external custom connector with UNIT_PROVEN proof level', () => {
    connectorService.registerExternalConnector({
      name: 'Custom In-House FinTech Ledger Connector',
      providerIdentifier: 'custom-fintech-ledger',
      binaryPath: '/opt/akaal/connectors/libfintech-ledger.so',
      protocolVersion: 'v2.4',
      sha256Checksum: 'abc1234567890defabc1234567890defabc1234567890defabc1234567890def'
    });

    const externalList = connectorService.externalConnectors();
    const registered = externalList.find(c => c.name === 'Custom In-House FinTech Ledger Connector');
    expect(registered).toBeDefined();
    expect(registered?.certificationLevel).toBe('UNIT_PROVEN');
    expect(registered?.status).toBe('ACTIVE');
    expect(registered?.id).toContain('ext-conn-');
  });

  it('should toggle plugin active/disabled state cleanly', () => {
    const plugins = connectorService.plugins();
    expect(plugins.length).toBeGreaterThanOrEqual(1);

    const firstPluginId = plugins[0].id;
    const initialStatus = plugins[0].status;

    connectorService.togglePluginStatus(firstPluginId);
    let updated = connectorService.getPluginById(firstPluginId);
    expect(updated?.status).toBe(initialStatus === 'ACTIVE' ? 'DISABLED' : 'ACTIVE');

    // Toggle back
    connectorService.togglePluginStatus(firstPluginId);
    updated = connectorService.getPluginById(firstPluginId);
    expect(updated?.status).toBe(initialStatus);
  });

  it('should maintain strict SDK configuration with sandboxing and modern runtimes', () => {
    const sdk = connectorService.sdkConfig();
    expect(sdk.sandboxingEnforced).toBe(true);
    expect(sdk.wasmRuntimeEngine).toContain('Wasmtime');
    expect(sdk.supportedRuntimes).toContain('Go 1.23+');
    expect(sdk.grpcSocketPath).toBeDefined();
  });
});

describe('5.7 Cloud & Infrastructure Configuration Service & Workflows', () => {
  let infraService: InfrastructureService;

  beforeEach(() => {
    infraService = new InfrastructureService();
  });

  it('should initialize with multi-cloud environments across AWS, Azure, GCP, and OCI', () => {
    const envs = infraService.cloudEnvironments();
    expect(envs.length).toBeGreaterThanOrEqual(4);

    const providers = envs.map(e => e.provider);
    expect(providers).toContain('AWS');
    expect(providers).toContain('AZURE');
    expect(providers).toContain('GCP');
    expect(providers).toContain('OCI');

    // Ensure all credentials are references (no plaintext secrets)
    for (const env of envs) {
      expect(env.credentialRef).toMatch(/^vault:\/\//);
    }
  });

  it('should create and register a new cloud environment', () => {
    infraService.createCloudEnvironment({
      name: 'GCP DR Secondary Project',
      provider: 'GCP',
      accountIdOrTenant: 'gcp-dr-secondary-1002',
      defaultRegion: 'europe-west1',
      credentialRef: 'vault://secret/cloud/gcp/dr-workload-id',
      configuredRegions: ['europe-west1'],
      executionSiteIds: [],
      tags: ['Disaster-Recovery', 'GCP']
    });

    const envs = infraService.cloudEnvironments();
    const created = envs.find(e => e.name === 'GCP DR Secondary Project');
    expect(created).toBeDefined();
    expect(created?.status).toBe('ACTIVE');
    expect(created?.id).toContain('cenv-gcp-');
  });

  it('should retrieve cloud environment by ID', () => {
    const env = infraService.getEnvironmentById('cenv-aws-01');
    expect(env).toBeDefined();
    expect(env?.provider).toBe('AWS');
    expect(env?.defaultRegion).toBe('us-east-1');
  });

  it('should register a Kubernetes cluster with UNIT_PROVEN proof level', () => {
    infraService.createKubernetesConfig({
      name: 'OKE Edge Compute Cluster',
      clusterName: 'akaal-edge-oke-ashburn',
      apiEndpoint: 'https://oke.us-ashburn-1.oraclecloud.com',
      authType: 'OIDC_FEDERATED',
      credentialRef: 'vault://secret/k8s/oke-edge-token',
      defaultNamespace: 'akaal-edge',
      clusterCidr: '10.240.0.0/16',
      associatedCloudEnvId: 'cenv-oci-01'
    });

    const clusters = infraService.kubernetesConfigs();
    const registered = clusters.find(c => c.name === 'OKE Edge Compute Cluster');
    expect(registered).toBeDefined();
    expect(registered?.proofLevel).toBe('UNIT_PROVEN');
    expect(registered?.status).toBe('REGISTERED');
  });

  it('should register an Execution Site and retrieve by ID', () => {
    infraService.createExecutionSite({
      name: 'Tokyo Colocation Direct Gateway Site',
      siteType: 'ON_PREMISES_DATACENTER',
      providerOrDatacenter: 'Equinix TY2',
      region: 'ap-northeast-1',
      maxParallelJobs: 16
    });

    const sites = infraService.executionSites();
    const created = sites.find(s => s.name === 'Tokyo Colocation Direct Gateway Site');
    expect(created).toBeDefined();
    expect(created?.siteType).toBe('ON_PREMISES_DATACENTER');

    const retrieved = infraService.getSiteById(created!.id);
    expect(retrieved?.id).toBe(created!.id);
  });

  it('should establish a Private Connectivity Link', () => {
    infraService.createPrivateLink({
      name: 'Direct AWS PrivateLink to Ingestion Gateway',
      mechanism: 'AWS_PRIVATELINK',
      endpointServiceDns: 'vpce-0192837465aabbccdd.vpce.us-east-1.vpce.amazonaws.com',
      cidrBlock: '10.100.0.0/16',
      targetVpcOrVnet: 'vpc-0112233445566',
      credentialRef: 'vault://secret/cloud/aws/privatelink-token'
    });

    const links = infraService.privateLinks();
    const created = links.find(l => l.name === 'Direct AWS PrivateLink to Ingestion Gateway');
    expect(created).toBeDefined();
    expect(created?.status).toBe('ESTABLISHED');
    expect(created?.mechanism).toBe('AWS_PRIVATELINK');
  });

  it('should create and record a Network Route configuration', () => {
    infraService.createNetworkRoute({
      name: 'Corporate Forward Proxy Route',
      routeType: 'FORWARD_PROXY',
      targetHost: 'proxy.corp.internal',
      targetPort: 8080,
      bypassList: ['127.0.0.1', 'localhost', '169.254.169.254']
    });

    const routes = infraService.networkRoutes();
    const created = routes.find(r => r.name === 'Corporate Forward Proxy Route');
    expect(created).toBeDefined();
    expect(created?.targetHost).toBe('proxy.corp.internal');
  });

  it('should enforce data sovereignty policies and catalog regions', () => {
    const policies = infraService.sovereigntyPolicies();
    expect(policies.length).toBeGreaterThanOrEqual(2);

    const gdprPolicy = policies.find(p => p.jurisdiction === 'EU_EEA');
    expect(gdprPolicy).toBeDefined();
    expect(gdprPolicy?.enforceStrictBoundary).toBe(true);
    expect(gdprPolicy?.deniedRegions).toContain('us-east-1');

    const regions = infraService.regionsCatalog();
    expect(regions.length).toBeGreaterThanOrEqual(6);
    expect(regions.some(r => r.complianceZone === 'EU_EEA')).toBe(true);
    expect(regions.some(r => r.complianceZone === 'US_DOMESTIC')).toBe(true);
  });

  it('should verify IaC and GitOps configuration signals', () => {
    const iac = infraService.iacConfigs();
    expect(iac.length).toBeGreaterThanOrEqual(1);
    expect(iac[0].toolType).toBe('OPEN_TOFU');
    expect(iac[0].stateStorageBackend).toContain('S3');

    const gitops = infraService.gitOpsConfigs();
    expect(gitops.length).toBeGreaterThanOrEqual(1);
    expect(gitops[0].targetBranch).toBe('main');
    expect(gitops[0].credentialRef).toMatch(/^vault:\/\//);
  });
});
