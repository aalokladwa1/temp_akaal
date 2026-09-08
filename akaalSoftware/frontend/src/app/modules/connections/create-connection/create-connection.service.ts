import { Injectable, signal, computed, inject, Optional } from '@angular/core';
import { Router } from '@angular/router';
import { ConnectionsService } from '../connections.service';
import {
  CreateConnectionStepIndex,
  CreateConnectionDraft,
  VerificationFacts,
  ProviderCatalogItem,
  ManagedCloudProfile
} from './create-connection.models';
import { ALL_PROVIDER_CATALOG_ITEMS, MANAGED_CLOUD_PROFILES } from './create-connection.schemas';
import { ConnectionRecord } from '../connections.models';

export const INITIAL_DRAFT_STATE: CreateConnectionDraft = {
  // Step 1
  selectedProviderId: null,
  isManagedCloud: false,
  managedCloudId: null,
  managedResourceType: null,
  isFileDataset: false,
  fileDatasetFormat: null,

  // Step 2
  name: '',
  description: '',
  environment: 'Production',
  workspaceId: 'ws-enterprise-default',
  parameters: {},

  // Extensions
  oracleAddressingMode: 'HOST_SERVICE',
  oracleHost: '',
  oraclePort: 1521,
  oracleServiceName: '',
  oracleSid: '',
  oracleTnsName: '',
  oracleTnsAdminPath: '',
  oracleDriverMode: 'THIN',
  oracleClientLibPath: '',
  oraclePrivilegeMode: 'NORMAL',
  oracleWalletPath: '',

  bigqueryProjectId: '',
  bigqueryDataset: '',
  bigqueryLocation: 'US',
  bigqueryBillingProject: '',
  bigqueryUseStorageReadApi: true,
  bigqueryRequestTimeoutSec: 60,

  spannerProjectId: '',
  spannerInstanceId: '',
  spannerDatabaseId: '',
  spannerEmulatorHost: '',
  spannerChannelPoolSize: 4,
  spannerPriority: 'MEDIUM',

  salesforceInstanceUrl: '',
  salesforceAuthFlow: 'OAUTH',
  salesforceApiVersion: 'v59.0',
  salesforceClientId: '',
  salesforceSubject: '',

  servicenowInstanceUrl: '',
  servicenowAuthMode: 'BASIC',
  servicenowPageSize: 1000,

  sapConnectionMode: 'RFC_BAPI',
  sapServerMode: 'APPLICATION_SERVER',
  sapAppServerHost: '',
  sapSystemNumber: '00',
  sapClient: '100',
  sapMessageServerHost: '',
  sapGroup: 'PUBLIC',
  sapSystemId: '',
  sapLanguage: 'EN',
  sapSncEnabled: false,
  sapSncPartnerName: '',
  sapOdataServiceUrl: '',

  // Step 3
  authMethod: 'PASSWORD',
  authUsername: '',
  authSecretRef: '',
  authSecretValue: '',
  authRoleArn: '',
  authPrincipal: '',
  authKeyId: '',
  authTenantId: '',

  tlsMode: 'REQUIRED',
  minTlsVersion: 'TLS_1_2',
  caCertificateRef: '',
  serverNameOverride: '',
  allowSelfSigned: false,

  clientCertRef: '',
  clientPrivateKeyRef: '',
  clientPrivateKeyPassphraseRef: '',

  networkRoute: 'DIRECT',
  sshBastionHost: '',
  sshBastionPort: 22,
  sshBastionUsername: '',
  sshBastionAuthMethod: 'PRIVATE_KEY',
  sshBastionKeyRef: '',
  sshBastionPasswordRef: '',
  sshHostKeyFingerprint: '',
  allowUnverifiedSshHost: false,

  proxyHost: '',
  proxyPort: 8080,
  proxyAuthMethod: 'NONE',
  proxyUsername: '',
  proxyPasswordRef: '',

  privateEndpointUrl: '',
  fabricSite: 'primary-dc-01',
  fabricLocality: 'us-east-1a',
  fabricTransitVpc: 'vpc-transit-prod',

  dnsTimeoutMs: 5000,
  connectTimeoutMs: 15000,
  socketTimeoutMs: 30000,
  tcpKeepaliveEnabled: true,
  keepaliveIdleSec: 60,
  keepaliveIntervalSec: 15,
  keepaliveProbes: 5,

  // Step 4
  verificationFacts: {
    testedAt: null,
    overallStatus: 'UNTESTED',
    connectivity: [],
    permissions: [],
    capabilities: [],
    sourceEligibility: 'UNKNOWN',
    targetEligibility: 'UNKNOWN',
    discoveryCapability: 'UNKNOWN',
    cdcCapability: {
      type: 'NONE',
      label: 'Unverified',
      description: 'Run Test Connection to evaluate CDC capability.'
    },
    validationCapability: {
      supported: false,
      rowHashChecksum: false,
      columnProfile: false,
      sampleReconciliation: false,
      nonMutatingGuaranteed: true
    },
    limitations: [],
    warnings: []
  },
  isStaleVerification: false,
  isTesting: false,
  isTestingPermissions: false,
  isTestingCapabilities: false
};

@Injectable({
  providedIn: 'root'
})
export class CreateConnectionService {
  private router: Router;
  private connService: ConnectionsService;

  constructor(
    @Optional() router?: Router,
    @Optional() connService?: ConnectionsService
  ) {
    if (router) {
      this.router = router;
    } else {
      try {
        this.router = inject(Router, { optional: true }) || ({ navigate: () => Promise.resolve(true) } as any);
      } catch {
        this.router = { navigate: () => Promise.resolve(true) } as any;
      }
    }

    if (connService) {
      this.connService = connService;
    } else {
      try {
        this.connService = inject(ConnectionsService, { optional: true }) || new ConnectionsService();
      } catch {
        this.connService = new ConnectionsService();
      }
    }
  }

  public currentStep = signal<CreateConnectionStepIndex>(1);
  public draft = signal<CreateConnectionDraft>(JSON.parse(JSON.stringify(INITIAL_DRAFT_STATE)));

  public providerCatalog = signal<ProviderCatalogItem[]>(ALL_PROVIDER_CATALOG_ITEMS);
  public cloudProfiles = signal<ManagedCloudProfile[]>(MANAGED_CLOUD_PROFILES);

  public selectedProvider = computed<ProviderCatalogItem | null>(() => {
    const d = this.draft();
    if (!d.selectedProviderId) return null;
    return this.providerCatalog().find(p => p.id === d.selectedProviderId) || null;
  });

  public isStep1Valid = computed<boolean>(() => {
    const d = this.draft();
    return !!d.selectedProviderId;
  });

  public isStep2Valid = computed<boolean>(() => {
    const d = this.draft();
    if (!d.name.trim()) return false;
    const p = this.selectedProvider();
    if (!p) return false;

    // Custom Extension Provider Checks
    if (p.id === 'oracle') {
      if (d.oracleAddressingMode === 'HOST_SERVICE') return !!d.oracleHost && !!d.oraclePort && !!d.oracleServiceName;
      if (d.oracleAddressingMode === 'HOST_SID') return !!d.oracleHost && !!d.oraclePort && !!d.oracleSid;
      if (d.oracleAddressingMode === 'TNS_ENTRY') return !!d.oracleTnsName;
      if (d.oracleAddressingMode === 'ORACLE_WALLET') return !!d.oracleWalletPath;
      return true;
    }
    if (p.id === 'bigquery') return !!d.bigqueryProjectId;
    if (p.id === 'spanner') return !!d.spannerProjectId && !!d.spannerInstanceId && !!d.spannerDatabaseId;
    if (p.id === 'salesforce') return !!d.salesforceInstanceUrl;
    if (p.id === 'servicenow') return !!d.servicenowInstanceUrl;
    if (p.id === 'sap_application') {
      if (d.sapConnectionMode === 'RFC_BAPI') {
        if (d.sapServerMode === 'APPLICATION_SERVER') return !!d.sapAppServerHost && !!d.sapSystemNumber;
        if (d.sapServerMode === 'MESSAGE_SERVER') return !!d.sapMessageServerHost && !!d.sapSystemId;
      }
      if (d.sapConnectionMode === 'ODATA') return !!d.sapOdataServiceUrl;
      return true;
    }

    // Generic schema validation
    if (p.id === 'sqlite') return !!(d.parameters['database_path'] || d.parameters['host']);
    if (p.id === 's3' || p.id === 'gcs' || p.id === 'minio') return !!d.parameters['bucket'];
    if (p.id === 'kafka') return !!(d.parameters['bootstrap_servers'] || d.parameters['host']);
    if (p.id === 'azure_blob') return !!(d.parameters['account_name'] || d.parameters['container_name']);

    // Default generic host check
    return !!(d.parameters['host'] || d.parameters['database'] || d.parameters['account'] || true);
  });

  public isStep3Valid = computed<boolean>(() => {
    const d = this.draft();
    if (!d.authMethod) return false;
    if (d.networkRoute === 'SSH_BASTION') {
      if (!d.sshBastionHost || !d.sshBastionUsername) return false;
    }
    if (d.networkRoute === 'HTTP_PROXY' || d.networkRoute === 'SOCKS5_PROXY') {
      if (!d.proxyHost) return false;
    }
    return true;
  });

  public isStep4Valid = computed<boolean>(() => {
    return true; // Step 4 can be viewed and verified or skipped to review
  });

  public canProceed = computed<boolean>(() => {
    const s = this.currentStep();
    switch (s) {
      case 1: return this.isStep1Valid();
      case 2: return this.isStep2Valid();
      case 3: return this.isStep3Valid();
      case 4: return this.isStep4Valid();
      case 5: return true;
      default: return false;
    }
  });

  // =========================================================================
  // STEP NAVIGATION ACTIONS
  // =========================================================================

  public goToStep(step: CreateConnectionStepIndex): void {
    if (step < this.currentStep() || this.canProceed()) {
      this.currentStep.set(step);
    }
  }

  public nextStep(): void {
    const s = this.currentStep();
    if (s < 5 && this.canProceed()) {
      this.currentStep.set((s + 1) as CreateConnectionStepIndex);
    }
  }

  public prevStep(): void {
    const s = this.currentStep();
    if (s > 1) {
      this.currentStep.set((s - 1) as CreateConnectionStepIndex);
    }
  }

  public cancel(): void {
    this.router.navigate(['/connections']);
  }

  // =========================================================================
  // PROVIDER SELECTION & STATE RESET
  // =========================================================================

  public selectProvider(providerId: string): void {
    const current = this.draft().selectedProviderId;
    if (current === providerId) return;

    const catalogItem = this.providerCatalog().find(p => p.id === providerId);
    if (!catalogItem) return;

    // Reset draft fields to ensure clean cross-step state with no leftover stale fields
    this.draft.update(d => ({
      ...d,
      selectedProviderId: providerId,
      isManagedCloud: false,
      managedCloudId: null,
      managedResourceType: null,
      isFileDataset: providerId === 'file_dataset',
      fileDatasetFormat: providerId === 'file_dataset' ? 'CSV' : null,
      
      // Defaults
      name: d.name || `${catalogItem.name} Connection`,
      parameters: {
        host: catalogItem.defaultPort ? 'db.prod.corp.internal' : '',
        port: catalogItem.defaultPort || '',
        database: 'finance_prod',
        schema: 'public',
        username: 'akaal_admin',
        secret_ref: 'vault://secret/prod/db_pass'
      },
      authMethod: catalogItem.defaultAuthMethod,
      tlsMode: catalogItem.supportsTls ? 'REQUIRED' : 'DISABLED',
      
      // Invalidate previous verification
      verificationFacts: {
        testedAt: null,
        overallStatus: 'UNTESTED',
        connectivity: [],
        permissions: [],
        capabilities: [],
        sourceEligibility: 'UNKNOWN',
        targetEligibility: 'UNKNOWN',
        discoveryCapability: 'UNKNOWN',
        cdcCapability: {
          type: 'NONE',
          label: 'Unverified',
          description: 'Run Test Connection to evaluate CDC capability.'
        },
        validationCapability: {
          supported: false,
          rowHashChecksum: false,
          columnProfile: false,
          sampleReconciliation: false,
          nonMutatingGuaranteed: true
        },
        limitations: [],
        warnings: []
      },
      isStaleVerification: false
    }));
  }

  public selectManagedCloudResource(profileId: ManagedCloudProfile['id'], resourceType: string, physicalProviderId: string): void {
    this.selectProvider(physicalProviderId);
    this.draft.update(d => ({
      ...d,
      isManagedCloud: true,
      managedCloudId: profileId,
      managedResourceType: resourceType,
      name: `${resourceType.replace(/_/g, ' ')} Connection`
    }));
  }

  public selectFileDataset(format: 'CSV' | 'JSONL' | 'PARQUET'): void {
    this.selectProvider('file_dataset');
    this.draft.update(d => ({
      ...d,
      isFileDataset: true,
      fileDatasetFormat: format,
      name: `Local ${format} Dataset`
    }));
  }

  // =========================================================================
  // UPSTREAM FIELD MUTATION TRACKING
  // =========================================================================

  public markConfigurationMutated(): void {
    const d = this.draft();
    if (d.verificationFacts.overallStatus !== 'UNTESTED') {
      this.draft.update(curr => ({
        ...curr,
        isStaleVerification: true
      }));
    }
  }

  // =========================================================================
  // STEP 4: VERIFICATION PROBE SIMULATION (Point-in-Time Pre-P7D Fixture)
  // =========================================================================

  public runTestConnection(): void {
    this.draft.update(d => ({ ...d, isTesting: true }));

    setTimeout(() => {
      const d = this.draft();
      const p = this.selectedProvider();
      const nowIso = new Date().toISOString();

      const connectivity: VerificationFacts['connectivity'] = [
        {
          key: 'config_validation',
          label: 'Configuration & Schemas',
          status: 'PASSED',
          value: 'Valid Syntax & Parameters',
          latencyMs: 1
        },
        {
          key: 'dns_resolution',
          label: 'DNS Resolution',
          status: 'PASSED',
          value: p?.id === 'sqlite' ? 'N/A (Local File)' : 'Resolved to 10.14.28.92',
          latencyMs: 3
        },
        {
          key: 'tcp_socket',
          label: 'Socket Connectivity',
          status: 'PASSED',
          value: p?.id === 'sqlite' ? 'File Descriptor Open (0.2ms)' : `TCP Port ${p?.defaultPort || 443} Open`,
          latencyMs: 7
        },
        {
          key: 'tls_handshake',
          label: 'Transport Security',
          status: p?.supportsTls && d.tlsMode !== 'DISABLED' ? 'PASSED' : 'SKIPPED',
          value: p?.supportsTls && d.tlsMode !== 'DISABLED' ? `${d.minTlsVersion} · TLS_AES_256_GCM_SHA384` : 'Plaintext / Local Transport',
          latencyMs: 12
        },
        {
          key: 'authentication',
          label: 'Authentication Attestation',
          status: 'PASSED',
          value: `Principal Authenticated (${d.authMethod})`,
          latencyMs: 18
        },
        {
          key: 'server_attestation',
          label: 'Server & Catalog Attestation',
          status: 'PASSED',
          value: `${p?.name || 'Engine'} v16.2 Enterprise Edition`,
          latencyMs: 24
        }
      ];

      // CDC & Validation Capability Mapping
      let cdcCap: VerificationFacts['cdcCapability'] = {
        type: 'NONE',
        label: 'No CDC Support',
        description: 'Batch/bulk migration and incremental query sync only.'
      };

      if (['postgresql', 'mysql', 'mariadb', 'oracle', 'mssql', 'mongodb'].includes(p?.id || '')) {
        cdcCap = {
          type: 'NATIVE_DATABASE_CDC',
          label: 'Native Database CDC Available',
          description: `${p?.name} engine transaction log stream verified (M2 Bulk+CDC / M3 Continuous CDC ready).`
        };
      } else if (['kafka', 'pulsar', 'kinesis', 'eventhubs', 'pubsub'].includes(p?.id || '')) {
        cdcCap = {
          type: 'STREAM_OFFSET_CONSUMPTION',
          label: 'Stream Offset Consumption',
          description: 'Continuous consumer partition offset ingestion (Stream sync mode).'
        };
      } else if (['s3', 'gcs', 'azure_blob', 'oci_object_storage'].includes(p?.id || '')) {
        cdcCap = {
          type: 'OBJECT_EVENT_NOTIFICATION',
          label: 'Bucket Event Ingestion',
          description: 'Object creation/modification event notification ingestion.'
        };
      }

      const limitations: string[] = [];
      const warnings: string[] = [];

      if (d.allowSelfSigned) {
        warnings.push('Self-signed TLS certificates permitted (Security warning).');
      }
      if (d.tlsMode === 'PREFERRED') {
        warnings.push('TLS mode PREFERRED allows fallback to unencrypted connection if server rejects TLS.');
      }
      if (p?.id === 'salesforce') {
        limitations.push('Salesforce is supported in Source role only (CRM object extraction).');
      }
      if (p?.id === 'sqlite') {
        limitations.push('Concurrent writes restricted by SQLite file-level locking.');
      }

      this.draft.update(curr => ({
        ...curr,
        isTesting: false,
        isStaleVerification: false,
        verificationFacts: {
          ...curr.verificationFacts,
          testedAt: nowIso,
          overallStatus: 'PASSED',
          connectivity,
          sourceEligibility: 'AVAILABLE',
          targetEligibility: p?.roleApplicability === 'SOURCE_ONLY' ? 'UNAVAILABLE' : 'AVAILABLE',
          discoveryCapability: 'SUPPORTED',
          cdcCapability: cdcCap,
          validationCapability: {
            supported: true,
            rowHashChecksum: true,
            columnProfile: true,
            sampleReconciliation: true,
            nonMutatingGuaranteed: true
          },
          limitations,
          warnings
        }
      }));
    }, 500);
  }

  public runPermissionProbe(): void {
    this.draft.update(d => ({ ...d, isTestingPermissions: true }));

    setTimeout(() => {
      const p = this.selectedProvider();
      const isSourceOnly = p?.roleApplicability === 'SOURCE_ONLY';

      const permissions: VerificationFacts['permissions'] = [
        { privilege: 'SELECT / READ', status: 'VERIFIED', scope: 'TABLES & VIEWS' },
        { privilege: 'INSERT / WRITE', status: isSourceOnly ? 'UNSUPPORTED' : 'VERIFIED', scope: 'TABLES' },
        { privilege: 'UPDATE', status: isSourceOnly ? 'UNSUPPORTED' : 'VERIFIED', scope: 'TABLES' },
        { privilege: 'DELETE', status: isSourceOnly ? 'UNSUPPORTED' : 'VERIFIED', scope: 'TABLES' },
        { privilege: 'CREATE TABLE / DDL', status: isSourceOnly ? 'UNSUPPORTED' : 'VERIFIED', scope: 'SCHEMA' },
        { privilege: 'ALTER TABLE / METADATA', status: isSourceOnly ? 'UNSUPPORTED' : 'VERIFIED', scope: 'SCHEMA' },
        { privilege: 'TRANSACTION LOG READ (CDC)', status: 'VERIFIED', scope: 'LOGMINER / REPLICATION' }
      ];

      this.draft.update(curr => ({
        ...curr,
        isTestingPermissions: false,
        verificationFacts: {
          ...curr.verificationFacts,
          permissions
        }
      }));
    }, 400);
  }

  public runCapabilityProbe(): void {
    this.draft.update(d => ({ ...d, isTestingCapabilities: true }));

    setTimeout(() => {
      const p = this.selectedProvider();

      const capabilities: VerificationFacts['capabilities'] = [
        { capability: 'Transaction Log Level (wal_level/binlog/archivelog)', status: 'VERIFIED', category: 'CDC', detail: 'Sufficient replication privileges' },
        { capability: 'High-Throughput Bulk Partition Streaming', status: 'VERIFIED', category: 'STORAGE', detail: 'Parallel worker chunks supported' },
        { capability: 'Savepoints & Read Consistency Snapshots', status: 'VERIFIED', category: 'TRANSACTION', detail: 'Snapshot isolation verified' },
        { capability: 'Catalog Schema & Primary Key Introspection', status: 'VERIFIED', category: 'DISCOVERY', detail: 'Full DDL schema parser verified' },
        { capability: 'Validation #11 Non-Mutating Checksum', status: 'VERIFIED', category: 'VALIDATION', detail: 'MD5/SHA-256 block hashing supported' }
      ];

      this.draft.update(curr => ({
        ...curr,
        isTestingCapabilities: false,
        verificationFacts: {
          ...curr.verificationFacts,
          capabilities
        }
      }));
    }, 400);
  }

  // =========================================================================
  // STEP 5: CREATE CONNECTION & REGISTRATION
  // =========================================================================

  public createConnection(): void {
    const d = this.draft();
    const p = this.selectedProvider();
    if (!p) return;

    const nowIso = new Date().toISOString();
    const id = `conn-${p.id}-${Date.now().toString(36)}`;

    let endpointDisplay = '';
    if (p.id === 'oracle') {
      endpointDisplay = d.oracleAddressingMode === 'HOST_SERVICE'
        ? `${d.oracleHost || 'oracle-db'}:${d.oraclePort || 1521}/${d.oracleServiceName || 'PDB1'}`
        : `${d.oracleTnsName || d.oracleSid || 'ORCL'}`;
    } else if (p.id === 'bigquery') {
      endpointDisplay = `gcp://${d.bigqueryProjectId || 'project'}/${d.bigqueryDataset || 'all_datasets'}`;
    } else if (p.id === 'spanner') {
      endpointDisplay = `spanner://${d.spannerProjectId || 'project'}/${d.spannerInstanceId || 'instance'}/${d.spannerDatabaseId || 'db'}`;
    } else if (p.id === 'salesforce') {
      endpointDisplay = d.salesforceInstanceUrl || 'company.my.salesforce.com';
    } else if (p.id === 'servicenow') {
      endpointDisplay = d.servicenowInstanceUrl || 'company.service-now.com';
    } else if (p.id === 'sap_application') {
      endpointDisplay = d.sapConnectionMode === 'RFC_BAPI'
        ? `sap-rfc://${d.sapAppServerHost || d.sapMessageServerHost || 'sap-host'}:${d.sapSystemNumber || '00'}`
        : (d.sapOdataServiceUrl || 'sap-odata');
    } else if (p.id === 'sqlite') {
      endpointDisplay = (d.parameters['database_path'] as string) || '/var/data/app.db';
    } else if (p.id === 's3' || p.id === 'gcs' || p.id === 'minio') {
      endpointDisplay = `s3://${d.parameters['bucket'] || 'enterprise-data-lake'}`;
    } else {
      endpointDisplay = `${d.parameters['host'] || 'db.prod.corp.internal'}:${d.parameters['port'] || p.defaultPort || '5432'}/${d.parameters['database'] || 'finance_prod'}`;
    }

    const newRecord: ConnectionRecord = {
      id,
      name: d.name || `${p.name} Connection`,
      description: d.description || `Configured via Create Connection Wizard (${p.categoryLabel})`,
      providerId: p.id,
      providerName: p.name,
      family: p.family,
      environment: d.environment,
      workspaceId: d.workspaceId,
      workspaceName: 'Enterprise Production Vault',
      endpointDisplay,
      safeRouteInfo: d.networkRoute === 'SSH_BASTION' ? `SSH Bastion (${d.sshBastionHost || 'bastion'})` : `${d.networkRoute.replace(/_/g, ' ')}`,
      tlsMode: d.tlsMode === 'DISABLED' ? 'DISABLED' : (d.minTlsVersion === 'TLS_1_3' ? 'TLS_1_3' : 'TLS_1_2'),
      authMethodDisplay: d.authMethod.replace(/_/g, ' '),
      roleApplicability: p.roleApplicability,
      verificationState: d.verificationFacts.overallStatus === 'PASSED' ? 'VERIFIED_RECENT' : 'NEVER_TESTED',
      lastVerifiedAt: d.verificationFacts.testedAt,
      lastVerifiedDetails: d.verificationFacts.overallStatus === 'PASSED'
        ? 'Verified via Create Connection Wizard · All connectivity and authentication probes passed'
        : undefined,
      usage: {
        referencedProjectCount: 0,
        activeMigrationCount: 0,
        activeValidationCount: 0,
        isUnused: true,
        usageAvailable: true
      },
      fabric: {
        site: d.fabricSite,
        locality: d.fabricLocality,
        transitVpc: d.fabricTransitVpc
      },
      createdAt: nowIso,
      updatedAt: nowIso
    };

    // Add connection into store
    this.connService.connections.update(list => [newRecord, ...list]);

    // Reset draft
    this.resetDraft();

    // Navigate to /connections and open inspect drawer
    this.router.navigate(['/connections']).then(() => {
      this.connService.openInspectDrawer(newRecord);
    });
  }

  public resetDraft(): void {
    this.draft.set(JSON.parse(JSON.stringify(INITIAL_DRAFT_STATE)));
    this.currentStep.set(1);
  }
}
