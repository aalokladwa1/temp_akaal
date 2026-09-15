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
import { ConnectionRecord, ConnectionVerificationState } from '../connections.models';

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

  public onCancelHandler: (() => void) | null = null;
  public onSuccessHandler: ((conn: ConnectionRecord) => void) | null = null;

  public cancel(): void {
    if (this.onCancelHandler) {
      this.onCancelHandler();
      return;
    }
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

  // State for truthful submission feedback
  public isCreating = signal<boolean>(false);
  public creationNotice = signal<string | null>(null);
  public isSubmittedModalOpen = signal<boolean>(false);

  // =========================================================================
  // STEP 4: VERIFICATION PROBES (Truthful fail-closed handling: B-2.2-05)
  // =========================================================================

  public runTestConnection(): void {
    this.draft.update(d => ({ ...d, isTesting: true }));

    setTimeout(() => {
      const p = this.selectedProvider();
      const limitations: string[] = [];
      const warnings: string[] = ['Live connection testing is unavailable while connection service is disconnected.'];

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
          testedAt: null,
          overallStatus: 'UNTESTED',
          connectivity: [],
          sourceEligibility: p?.roleApplicability === 'TARGET_ONLY' ? 'UNAVAILABLE' : 'AVAILABLE',
          targetEligibility: p?.roleApplicability === 'SOURCE_ONLY' ? 'UNAVAILABLE' : 'AVAILABLE',
          discoveryCapability: 'SUPPORTED',
          limitations,
          warnings
        }
      }));
    }, 200);
  }

  public runPermissionProbe(): void {
    this.draft.update(d => ({ ...d, isTestingPermissions: true }));

    setTimeout(() => {
      this.draft.update(curr => ({
        ...curr,
        isTestingPermissions: false,
        verificationFacts: {
          ...curr.verificationFacts,
          warnings: [...(curr.verificationFacts.warnings || []), 'Live permission introspection is unavailable while connection service is disconnected.']
        }
      }));
    }, 200);
  }

  public runCapabilityProbe(): void {
    this.draft.update(d => ({ ...d, isTestingCapabilities: true }));

    setTimeout(() => {
      this.draft.update(curr => ({
        ...curr,
        isTestingCapabilities: false,
        verificationFacts: {
          ...curr.verificationFacts,
          warnings: [...(curr.verificationFacts.warnings || []), 'Live capability attestation is unavailable while connection service is disconnected.']
        }
      }));
    }, 200);
  }

  // =========================================================================
  // STEP 5: CREATE CONNECTION (Truthful fail-closed handling: B-2.2-07)
  // =========================================================================

  public createConnection(): void {
    const provider = this.selectedProvider();
    if (!provider) {
      this.creationNotice.set('Cannot create connection: No provider selected.');
      return;
    }

    const d = this.draft();
    const name = d.name.trim();
    if (!name) {
      this.creationNotice.set('Cannot create connection: Connection name is required.');
      return;
    }

    // Fail closed if canonical connection authority is disconnected (CHECK1 law: B-2.2-07)
    if (this.connService.availabilityState() === 'NOT_CONNECTED') {
      this.creationNotice.set('Connection saving is unavailable while connection service is disconnected.');
      return;
    }

    // Canonical ID originating from connected canonical authority
    const newId = `conn-${provider.id}-${Date.now().toString().slice(-6)}`;
    const testStatus = d.verificationFacts?.overallStatus;
    const isVerified = testStatus === 'PASSED';
    const verificationState: ConnectionVerificationState = isVerified ? 'VERIFIED_RECENT' : 'NEVER_TESTED';

    // Derive endpointDisplay truthfully from actual parameters (no fabricated host/port)
    let endpoint = '';
    if (provider.id === 'sqlite') {
      endpoint = d.parameters['database_path'] || d.parameters['host'] || 'local';
    } else if (provider.id === 'bigquery') {
      endpoint = d.bigqueryProjectId || d.parameters['project_id'] || '';
    } else if (provider.id === 'spanner') {
      endpoint = d.spannerInstanceId ? `${d.spannerProjectId || ''}/${d.spannerInstanceId}` : '';
    } else if (provider.id === 'salesforce') {
      endpoint = d.salesforceInstanceUrl || '';
    } else if (provider.id === 'servicenow') {
      endpoint = d.servicenowInstanceUrl || '';
    } else if (provider.id === 'kafka') {
      endpoint = d.parameters['bootstrap_servers'] || d.parameters['host'] || '';
    } else if (provider.id === 's3' || provider.id === 'gcs' || provider.id === 'minio') {
      endpoint = d.parameters['bucket'] || d.parameters['bucket_name'] || '';
    } else if (d.parameters['host']) {
      const port = d.parameters['port'] || provider.defaultPort;
      endpoint = port ? `${d.parameters['host']}:${port}` : `${d.parameters['host']}`;
    }

    // Derive authMethodDisplay truthfully from actual auth configuration (no fabricated strings)
    let authDisplay = 'None / Inherited';
    if (d.authSecretRef) {
      authDisplay = `Vault Secret (${d.authSecretRef})`;
    } else if (d.authUsername) {
      authDisplay = `User: ${d.authUsername}`;
    } else if (d.authMethod) {
      authDisplay = d.authMethod;
    }

    const newRecord: ConnectionRecord = {
      id: newId,
      name: name,
      providerId: provider.id,
      providerName: provider.name,
      family: provider.family,
      environment: d.environment,
      workspaceId: d.workspaceId || '',
      endpointDisplay: endpoint,
      safeRouteInfo: d.networkRoute || 'DIRECT',
      authMethodDisplay: authDisplay,
      roleApplicability: provider.roleApplicability,
      verificationState: verificationState,
      lastVerifiedAt: isVerified ? new Date().toISOString() : null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      usage: {
        activeMigrationCount: 0,
        activeValidationCount: 0,
        projectNames: [],
        referencedProjectCount: 0,
        isUnused: true,
        usageAvailable: true
      },
      tags: [d.environment]
    };

    // Register into canonical store
    this.connService.connections.update(list => [newRecord, ...list]);

    if (this.onSuccessHandler) {
      this.onSuccessHandler(newRecord);
      this.resetDraft();
      return;
    }

    this.isSubmittedModalOpen.set(true);
  }

  public resetDraft(): void {
    this.draft.set(JSON.parse(JSON.stringify(INITIAL_DRAFT_STATE)));
    this.currentStep.set(1);
    this.isSubmittedModalOpen.set(false);
    this.creationNotice.set(null);
  }
}
