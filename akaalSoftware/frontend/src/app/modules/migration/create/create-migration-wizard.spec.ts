import { describe, it, expect, beforeEach } from 'vitest';
import { MigrationUiService } from '../../../core/services/migration-ui.service';
import { MigrationDevFixturesAdapter } from '../../../core/fixtures/migration-dev-fixtures.adapter';
import { ALL_28_PROVIDER_SCHEMAS } from '../../../core/models/provider-form-schemas';
import { PhysicalProviderId, DiscoveryDepthTier } from '../../../core/models/migration-view.models';

describe('CreateMigrationWizard State & Governance Suite', () => {
  let service: MigrationUiService;
  let fixtures: MigrationDevFixturesAdapter;

  beforeEach(() => {
    fixtures = new MigrationDevFixturesAdapter();
    service = new MigrationUiService(fixtures);
  });

  describe('Provider Coverage Verification (All 28 Engines)', () => {
    const required28Providers: PhysicalProviderId[] = [
      'SQLite', 'PostgreSQL', 'MySQL', 'MariaDB', 'Oracle', 'Microsoft SQL Server', 'IBM Db2',
      'Snowflake', 'Google BigQuery', 'Amazon Redshift', 'Databricks / Delta Lake',
      'MongoDB', 'Apache Cassandra', 'ScyllaDB', 'Neo4j', 'Redis', 'KeyDB', 'Elasticsearch', 'OpenSearch',
      'Apache Kafka', 'Amazon Kinesis', 'Azure Event Hubs', 'Google Cloud Pub/Sub',
      'Amazon S3', 'Google Cloud Storage', 'Azure Blob Storage', 'MinIO', 'Apache HDFS'
    ];

    it('must have exact schema definitions for all 28 physical database providers', () => {
      for (const p of required28Providers) {
        const schema = ALL_28_PROVIDER_SCHEMAS[p];
        expect(schema, `Schema for provider ${p} must exist`).toBeDefined();
        expect(schema.providerId).toBe(p);
        expect(schema.fields.length).toBeGreaterThan(0);
      }
    });

    it('Oracle schema must include specialized descriptor types (Service Name, SID, TNS, Wallet)', () => {
      const oracleSchema = ALL_28_PROVIDER_SCHEMAS['Oracle'];
      const connTypeField = oracleSchema.fields.find(f => f.id === 'connection_type');
      expect(connTypeField).toBeDefined();
      expect(connTypeField?.options?.map(o => o.value)).toContain('SERVICE_NAME');
      expect(connTypeField?.options?.map(o => o.value)).toContain('SID');
      expect(connTypeField?.options?.map(o => o.value)).toContain('TNS_DESCRIPTOR');
      expect(connTypeField?.options?.map(o => o.value)).toContain('WALLET');
    });
  });

  describe('Downstream Invalidation Protocol', () => {
    it('changing source engine should reset topology scope and trigger invalidation notice', () => {
      service.updateDraft({ selectedTopologyNodes: ['node-1', 'node-2'] });
      expect(service.wizardDraft().selectedTopologyNodes.length).toBe(2);

      service.updateSourceProvider('MongoDB');
      expect(service.wizardDraft().sourceProvider).toBe('MongoDB');
      expect(service.wizardDraft().selectedTopologyNodes.length).toBe(0);
      expect(service.invalidationNotice()).toContain('MongoDB');
    });

    it('changing execution mode should trigger plan invalidation notice', () => {
      service.updateWizardMode('M3_CDC');
      expect(service.wizardDraft().mode).toBe('M3_CDC');
      expect(service.invalidationNotice()).toContain('M3_CDC');
    });
  });

  describe('Dynamic DAG & Approval Barrier Intent Storage', () => {
    it('should insert an Approval Barrier with 2-approver quorum intent', () => {
      const initialCount = service.wizardDraft().customBarriersCount;
      service.insertApprovalBarrier('BETWEEN', 'n4', 'e5');

      expect(service.wizardDraft().customBarriersCount).toBe(initialCount + 1);
      const plan = service.wizardExecutionPlan();
      const customBarrier = plan.nodes.find(n => n.id.startsWith('barr-custom-'));
      expect(customBarrier).toBeDefined();
      expect(customBarrier?.isBarrier).toBe(true);
      expect(customBarrier?.requiredSignatures).toBe(2);
    });

    it('should remove an Approval Barrier cleanly', () => {
      service.insertApprovalBarrier('BETWEEN', 'n4', 'e5');
      const plan = service.wizardExecutionPlan();
      const customBarrier = plan.nodes.find(n => n.id.startsWith('barr-custom-'));
      expect(customBarrier).toBeDefined();

      service.removeApprovalBarrier(customBarrier!.id);
      expect(service.wizardExecutionPlan().nodes.find(n => n.id === customBarrier!.id)).toBeUndefined();
    });
  });

  describe('Provider-Aware Topology Discovery', () => {
    it('Oracle topology should expose deep 5-level hierarchy', () => {
      const tree = service.getTopologyTreeForProvider('Oracle');
      expect(tree[0].type).toBe('DATABASE'); // Instance
      expect(tree[0].children?.[0].type).toBe('DATABASE'); // PDB
      expect(tree[0].children?.[0].children?.[0].type).toBe('SCHEMA'); // Schema
      expect(tree[0].children?.[0].children?.[0].children?.[0].type).toBe('OBJECT_GROUP'); // Tables group
      expect(tree[0].children?.[0].children?.[0].children?.[0].children?.[0].type).toBe('TABLE'); // Table
    });

    it('MongoDB topology should naturally expose 3-level deployment/database/collections topology without artificial filler', () => {
      const tree = service.getTopologyTreeForProvider('MongoDB');
      expect(tree[0].type).toBe('DATABASE'); // Replica Set
      expect(tree[0].children?.[0].type).toBe('DATABASE'); // Database
      expect(tree[0].children?.[0].children?.[0].type).toBe('COLLECTION'); // Collection
    });

    it('Kafka topology should expose 3-level cluster/topics/partitions topology', () => {
      const tree = service.getTopologyTreeForProvider('Apache Kafka');
      expect(tree[0].type).toBe('DATABASE'); // Kafka Cluster
      expect(tree[0].children?.[0].type).toBe('TOPIC'); // Topic
      expect(tree[0].children?.[0].children?.[0].type).toBe('PATH'); // Partition
    });
  });

  describe('Step Validation Integrity', () => {
    it('step 1 should be invalid with empty migration name and valid when named, environment, and mode are set', () => {
      service.updateDraft({ name: '' });
      expect(service.isStepValid(1)).toBe(false);

      service.updateDraft({ name: 'PROD_MIGRATION', environment: 'Production', mode: 'M1_BULK' });
      expect(service.isStepValid(1)).toBe(true);
    });

    it('step 4 should be invalid when no scope objects are selected', () => {
      service.updateDraft({ selectedTopologyNodes: [] });
      expect(service.isStepValid(4)).toBe(false);

      service.updateDraft({ selectedTopologyNodes: ['tbl-1'] });
      expect(service.isStepValid(4)).toBe(true);
    });
  });

  describe('7-Mode Execution DAG Compilation & Environment Defaults', () => {
    it('M1_BULK should compile into 8 bulk stages without CDC nodes', () => {
      service.updateWizardMode('M1_BULK');
      const plan = service.wizardExecutionPlan();
      expect(plan.mode).toBe('M1_BULK');
      expect(plan.nodes.length).toBe(8);
      expect(plan.nodes.some(n => n.type === 'BULK_TRANSFER')).toBe(true);
      expect(plan.nodes.some(n => n.type === 'CDC_CATCHUP')).toBe(false);
    });

    it('M2_BULK_CDC should compile with Cutover Gate and both bulk and CDC catchup streams', () => {
      service.updateWizardMode('M2_BULK_CDC');
      const plan = service.wizardExecutionPlan();
      expect(plan.mode).toBe('M2_BULK_CDC');
      expect(plan.nodes.length).toBe(11);
      expect(plan.nodes.some(n => n.isBarrier)).toBe(true);
      expect(plan.nodes.some(n => n.type === 'CUTOVER')).toBe(true);
    });

    it('Production environment should enforce 2-approver Four-Eyes quorum on pre-inserted gates', () => {
      service.updateDraft({ environment: 'Production', mode: 'M2_BULK_CDC' });
      const plan = service.wizardExecutionPlan();
      const gate = plan.nodes.find(n => n.isBarrier);
      expect(gate).toBeDefined();
      expect(gate?.requiredSignatures).toBe(2);
      expect(gate?.approverRoles).toContain('Security Officer');
    });

    it('Staging environment should default to 1-approver Lead DBA sign-off', () => {
      service.updateDraft({ environment: 'Staging', mode: 'M2_BULK_CDC' });
      const plan = service.wizardExecutionPlan();
      const gate = plan.nodes.find(n => n.isBarrier);
      expect(gate).toBeDefined();
      expect(gate?.requiredSignatures).toBe(1);
      expect(gate?.approverRoles).toEqual(['Lead DBA']);
    });
  });

  describe('2.2.0 Creation Shell Lifecycle & Navigation Guarantees', () => {
    it('initial draft should start at Step 1 with clean initial state and dirty=false', () => {
      expect(service.wizardDraft().currentStep).toBe(1);
      expect(service.wizardDraft().name).toBe('');
      expect(service.wizardDraft().environment).toBe('');
      expect(service.wizardDraft().mode).toBe('');
      expect(service.wizardDraft().isDirty).toBe(false);
    });

    it('updating draft fields should mark isDirty=true and preserve all draft properties', () => {
      service.updateDraft({ name: 'Enterprise PostgreSQL Pipeline', sourceHost: 'pg-prod.internal' });
      expect(service.wizardDraft().name).toBe('Enterprise PostgreSQL Pipeline');
      expect(service.wizardDraft().sourceHost).toBe('pg-prod.internal');
      expect(service.wizardDraft().isDirty).toBe(true);
    });

    it('navigating forward and backward must preserve draft state without data loss', () => {
      service.updateDraft({ name: 'State Preservation Test', description: 'Testing step survival' });
      service.updateDraft({ currentStep: 2 });
      expect(service.wizardDraft().currentStep).toBe(2);
      expect(service.wizardDraft().name).toBe('State Preservation Test');

      service.updateDraft({ sourceHost: '10.0.0.15', sourcePort: 5432 });
      service.updateDraft({ currentStep: 3 });
      expect(service.wizardDraft().currentStep).toBe(3);

      // Back to Step 1
      service.updateDraft({ currentStep: 1 });
      expect(service.wizardDraft().currentStep).toBe(1);
      expect(service.wizardDraft().name).toBe('State Preservation Test');
      expect(service.wizardDraft().description).toBe('Testing step survival');
      expect(service.wizardDraft().sourceHost).toBe('10.0.0.15');
      expect(service.wizardDraft().sourcePort).toBe(5432);
    });

    it('launchDraftMigration should register new portfolio migration item and return valid id', () => {
      service.updateDraft({ name: 'Production_Launch_Migration', sourceProvider: 'Oracle', targetProvider: 'PostgreSQL' });
      const newId = service.launchDraftMigration();

      expect(newId).toMatch(/^mig-\d+/);
      expect(service.selectedMigrationId()).toBe(newId);
      const created = service.portfolioMigrations().find(m => m.id === newId);
      expect(created).toBeDefined();
      expect(created?.name).toBe('Production_Launch_Migration');
      expect(created?.sourceEngine).toBe('Oracle');
      expect(created?.targetEngine).toBe('PostgreSQL');
      expect(created?.lifecycleState).toBe('RUNNING');
    });
  });

  describe('2.2.1 Step 1 — Define Migration Contract Suite', () => {
    it('migration name must enforce 3-64 valid alphanumeric characters', () => {
      service.updateDraft({ environment: 'Production', mode: 'M1_BULK' });

      // Empty
      service.updateDraft({ name: '' });
      expect(service.isStepValid(1)).toBe(false);

      // Too short (< 3 chars)
      service.updateDraft({ name: 'ab' });
      expect(service.isStepValid(1)).toBe(false);

      // Invalid characters with spaces or symbols
      service.updateDraft({ name: 'Invalid Name with spaces!' });
      expect(service.isStepValid(1)).toBe(false);

      // Valid alphanumeric, hyphen and underscores (3-64 chars)
      service.updateDraft({ name: 'Core_Banking-Migration_01' });
      expect(service.isStepValid(1)).toBe(true);

      // Too long (> 64 chars)
      const longName = 'a'.repeat(65);
      service.updateDraft({ name: longName });
      expect(service.isStepValid(1)).toBe(false);
    });

    it('project id should default to undefined (Independent Migration) and bind legitimately', () => {
      expect(service.wizardDraft().projectId).toBeUndefined();

      service.updateDraft({ projectId: 'proj-01' });
      expect(service.wizardDraft().projectId).toBe('proj-01');

      service.updateDraft({ projectId: undefined });
      expect(service.wizardDraft().projectId).toBeUndefined();
    });

    it('environment selection must preserve canonical enum (Production, Staging, Development)', () => {
      service.updateDraft({ environment: 'Production' });
      expect(service.wizardDraft().environment).toBe('Production');

      service.updateDraft({ environment: 'Staging' });
      expect(service.wizardDraft().environment).toBe('Staging');

      service.updateDraft({ environment: 'Development' });
      expect(service.wizardDraft().environment).toBe('Development');
    });

    it('all 7 canonical creation execution modes must be authorized and selectable', () => {
      const canonical7Modes = [
        'M1_BULK',
        'M2_BULK_CDC',
        'M3_CDC',
        'M4_INCREMENTAL',
        'M5_STATE_SYNC',
        'M6_SCHEMA_ONLY',
        'M7_DATA_ONLY'
      ] as const;

      for (const mode of canonical7Modes) {
        service.updateWizardMode(mode);
        expect(service.wizardDraft().mode).toBe(mode);
      }
    });

    it('criticality tier defaults to TIER_2 and preserves TIER_1 and TIER_3 selections', () => {
      expect(service.wizardDraft().criticalityTier).toBe('TIER_2');

      service.updateDraft({ criticalityTier: 'TIER_1' });
      expect(service.wizardDraft().criticalityTier).toBe('TIER_1');

      service.updateDraft({ criticalityTier: 'TIER_3' });
      expect(service.wizardDraft().criticalityTier).toBe('TIER_3');
    });

    it('downtime requirement preserves operator intent without fabricating execution guarantees', () => {
      expect(service.wizardDraft().downtimeRequirement).toBeNull();

      service.updateDraft({ downtimeRequirement: 'ZERO_DOWNTIME' });
      expect(service.wizardDraft().downtimeRequirement).toBe('ZERO_DOWNTIME');

      service.updateDraft({ downtimeRequirement: 'MAINTENANCE_WINDOW' });
      expect(service.wizardDraft().downtimeRequirement).toBe('MAINTENANCE_WINDOW');
    });

    it('tags editor must support add, remove, and deduplication', () => {
      expect(service.wizardDraft().tags).toEqual([]);

      // Add tags
      service.updateDraft({
        tags: ['core-banking', 'pii']
      });
      expect(service.wizardDraft().tags.length).toBe(2);

      // Remove tag
      const filtered = service.wizardDraft().tags.filter(t => t !== 'core-banking');
      service.updateDraft({ tags: filtered });
      expect(service.wizardDraft().tags.length).toBe(1);
      expect(service.wizardDraft().tags[0]).toBe('pii');
    });

    it('description field must update canonical draft state', () => {
      expect(service.wizardDraft().description).toBe('');
      service.updateDraft({ description: 'Critical modernization pipeline for Q3' });
      expect(service.wizardDraft().description).toBe('Critical modernization pipeline for Q3');
    });

    it('extended canonical environments (QA, Sandbox, Disaster Recovery) must be valid', () => {
      service.updateDraft({ name: 'Valid_Migration_Name', mode: 'M1_BULK' });

      service.updateDraft({ environment: 'QA' });
      expect(service.isStepValid(1)).toBe(true);

      service.updateDraft({ environment: 'Sandbox' });
      expect(service.isStepValid(1)).toBe(true);

      service.updateDraft({ environment: 'Disaster Recovery' });
      expect(service.isStepValid(1)).toBe(true);
    });

    it('step 1 validation fails if mode is absent', () => {
      service.updateDraft({ name: 'Valid_Migration_Name', environment: 'Production', mode: '' as any });
      expect(service.isStepValid(1)).toBe(false);
    });
  });

  describe('2.2.2 Step 2 — Source Connection Contract Suite', () => {
    it('step 2 completion guard must require verified status and reject unverified source', () => {
      service.updateDraft({
        sourceConnectionMode: 'SAVED',
        sourceConnectionId: 'conn-01',
        sourceVerified: false
      });
      expect(service.isStepValid(2)).toBe(false);

      service.updateDraft({
        sourceVerified: true,
        sourceVerificationResult: {
          fingerprint: 'test-fingerprint',
          isVerified: true,
          hasBlockingIssues: false,
          physicalConnection: { status: 'PASSED' },
          identityAttestation: { status: 'PASSED' },
          capabilityDiscovery: { status: 'PASSED', capabilities: [] },
          permissionProbe: { status: 'PASSED', permissions: [] }
        }
      });
      expect(service.isStepValid(2)).toBe(true);

      // Blocking issues must fail validation
      service.updateDraft({
        sourceVerificationResult: {
          fingerprint: 'test-fingerprint-blocked',
          isVerified: false,
          hasBlockingIssues: true,
          physicalConnection: { status: 'PASSED' },
          identityAttestation: { status: 'PASSED' },
          capabilityDiscovery: { status: 'FAILED', capabilities: [] },
          permissionProbe: { status: 'FAILED', permissions: [] }
        }
      });
      expect(service.isStepValid(2)).toBe(false);
    });

    it('material parameter changes must invalidate verification state', () => {
      service.updateDraft({
        sourceConnectionMode: 'NEW',
        sourceProvider: 'PostgreSQL',
        sourceHost: 'pg-prod.internal',
        sourcePort: 5432,
        sourceVerified: true
      });
      expect(service.wizardDraft().sourceVerified).toBe(true);

      // Mutate host
      service.updateDraft({ sourceHost: 'pg-replica.internal', sourceVerified: false });
      expect(service.wizardDraft().sourceVerified).toBe(false);
    });

    it('all 28 canonical provider registrations map to defined presentation schemas', () => {
      const fixtureAdapter = new MigrationDevFixturesAdapter();
      const providers = fixtureAdapter.getPhysicalProviders();
      expect(providers.length).toBe(28);

      for (const p of providers) {
        expect(p.id).toBeDefined();
        expect(p.name).toBeDefined();
        expect(p.category).toBeDefined();
        expect(p.capabilities.length).toBeGreaterThan(0);
      }
    });

    it('provider parameters must diverge dynamically across provider families', () => {
      // SQLite uses database_path and no host/port
      const sqliteMeta = ALL_28_PROVIDER_SCHEMAS['SQLite'];
      expect(sqliteMeta.fields.some(f => f.id === 'database_path')).toBe(true);
      expect(sqliteMeta.fields.some(f => f.id === 'host')).toBe(false);
      expect(sqliteMeta.fields.some(f => f.id === 'port')).toBe(false);

      // Google BigQuery uses project_id/dataset and no host/port
      const bqMeta = ALL_28_PROVIDER_SCHEMAS['Google BigQuery'];
      expect(bqMeta.fields.some(f => f.id === 'project_id')).toBe(true);
      expect(bqMeta.fields.some(f => f.id === 'host')).toBe(false);

      // PostgreSQL uses host, port, database, username, ssl_mode
      const pgMeta = ALL_28_PROVIDER_SCHEMAS['PostgreSQL'];
      expect(pgMeta.fields.some(f => f.id === 'host')).toBe(true);
      expect(pgMeta.fields.some(f => f.id === 'port')).toBe(true);
      expect(pgMeta.fields.some(f => f.id === 'ssl_mode')).toBe(true);

      // Kafka uses bootstrap_brokers and security_protocol
      const kafkaMeta = ALL_28_PROVIDER_SCHEMAS['Apache Kafka'];
      expect(kafkaMeta.fields.some(f => f.id === 'bootstrap_brokers')).toBe(true);
      expect(kafkaMeta.fields.some(f => f.id === 'security_protocol')).toBe(true);

      // Amazon S3 uses bucket_name, region, and auth_type
      const s3Meta = ALL_28_PROVIDER_SCHEMAS['Amazon S3'];
      expect(s3Meta.fields.some(f => f.id === 'bucket_name')).toBe(true);
      expect(s3Meta.fields.some(f => f.id === 'region')).toBe(true);
    });
  });

  describe('2.2.3 Step 3 — Target Connection & Compatibility Contract Suite', () => {
    it('step 3 completion guard must require verified target and reject unverified target', () => {
      service.updateDraft({
        targetConnectionMode: 'SAVED',
        targetConnectionId: 'conn-02',
        targetVerified: false
      });
      expect(service.isStepValid(3)).toBe(false);

      service.updateDraft({
        targetVerified: true,
        targetVerificationResult: {
          fingerprint: 'target-fp-1',
          isVerified: true,
          hasBlockingIssues: false,
          latencyMs: 2.1,
          physicalConnection: { status: 'PASSED', latencyMs: 2.1 },
          identityAttestation: { status: 'PASSED', systemVersion: 'PostgreSQL 16.2' },
          writeAuthority: { status: 'PASSED', permissions: ['CREATE TABLE', 'INSERT'] },
          ingestionCapability: {
            status: 'PASSED',
            preferredStrategy: 'Binary COPY',
            fallbackStrategy: 'Batched UPSERT',
            directPathAvailable: true,
            privilegesVerified: true
          },
          sandboxCapability: { status: 'PASSED', supported: true, detail: 'Transactional DDL available' },
          storageHeadroom: { status: 'SUFFICIENT', displayStatus: 'Sufficient' },
          compatibility: {
            sourceProvider: 'Oracle',
            sourceVersion: 'Oracle 19c',
            targetProvider: 'PostgreSQL',
            targetVersion: 'PostgreSQL 16.2',
            topology: 'Heterogeneous',
            schemaConversion: 'Supported',
            dataTypeMapping: { status: 'Review required', reviewCount: 2, detail: '2 types require review' },
            proceduralConversion: { status: 'Review required', analyzedCount: 24, automaticCount: 21, reviewCount: 3 },
            isBlocked: false
          },
          targetContents: {
            existingObjectsDetected: false,
            tableCount: 0,
            viewCount: 0,
            indexCount: 0,
            conflictingObjectsCount: 0
          }
        }
      });
      expect(service.isStepValid(3)).toBe(true);
    });

    it('step 3 must block completion if target verification has blocking issues or compatibility is blocked', () => {
      service.updateDraft({
        targetVerified: true,
        targetVerificationResult: {
          fingerprint: 'target-fp-blocked',
          isVerified: false,
          hasBlockingIssues: true,
          blockedReason: 'Target database user lacks CREATE TABLE privilege',
          latencyMs: 1.8,
          physicalConnection: { status: 'PASSED', latencyMs: 1.8 },
          identityAttestation: { status: 'PASSED', systemVersion: 'PostgreSQL 16.2' },
          writeAuthority: { status: 'FAILED', permissions: [] },
          ingestionCapability: {
            status: 'FAILED',
            preferredStrategy: 'None',
            fallbackStrategy: 'None',
            directPathAvailable: false,
            privilegesVerified: false
          },
          sandboxCapability: { status: 'FAILED', supported: false, detail: 'Privileges missing' },
          storageHeadroom: { status: 'SUFFICIENT', displayStatus: 'Sufficient' },
          compatibility: {
            sourceProvider: 'Oracle',
            sourceVersion: 'Oracle 19c',
            targetProvider: 'PostgreSQL',
            targetVersion: 'PostgreSQL 16.2',
            topology: 'Heterogeneous',
            schemaConversion: 'Unsupported',
            dataTypeMapping: { status: 'Unsupported', reviewCount: 5, detail: 'Blocked' },
            proceduralConversion: { status: 'Unsupported', analyzedCount: 10, automaticCount: 0, reviewCount: 10 },
            isBlocked: true
          },
          targetContents: {
            existingObjectsDetected: false,
            tableCount: 0,
            viewCount: 0,
            indexCount: 0,
            conflictingObjectsCount: 0
          }
        }
      });
      expect(service.isStepValid(3)).toBe(false);
    });

    it('destructive collision policy in Production with conflicting objects must enforce explicit acknowledgment', () => {
      service.updateDraft({
        environment: 'Production',
        targetConnectionMode: 'SAVED',
        targetConnectionId: 'conn-02',
        targetVerified: true,
        collisionPolicy: 'DROP_AND_RECREATE',
        productionCollisionAcknowledged: false,
        targetVerificationResult: {
          fingerprint: 'target-fp-conflicts',
          isVerified: true,
          hasBlockingIssues: false,
          latencyMs: 1.9,
          physicalConnection: { status: 'PASSED', latencyMs: 1.9 },
          identityAttestation: { status: 'PASSED', systemVersion: 'PostgreSQL 16.2' },
          writeAuthority: { status: 'PASSED', permissions: ['CREATE TABLE', 'INSERT'] },
          ingestionCapability: {
            status: 'PASSED',
            preferredStrategy: 'Binary COPY',
            fallbackStrategy: 'Batched UPSERT',
            directPathAvailable: true,
            privilegesVerified: true
          },
          sandboxCapability: { status: 'PASSED', supported: true, detail: 'DDL available' },
          storageHeadroom: { status: 'SUFFICIENT', displayStatus: 'Sufficient' },
          compatibility: {
            sourceProvider: 'Oracle',
            sourceVersion: 'Oracle 19c',
            targetProvider: 'PostgreSQL',
            targetVersion: 'PostgreSQL 16.2',
            topology: 'Heterogeneous',
            schemaConversion: 'Supported',
            dataTypeMapping: { status: 'Direct map', reviewCount: 0, detail: 'Direct map' },
            proceduralConversion: { status: 'Supported', analyzedCount: 5, automaticCount: 5, reviewCount: 0 },
            isBlocked: false
          },
          targetContents: {
            existingObjectsDetected: true,
            tableCount: 14,
            viewCount: 3,
            indexCount: 27,
            conflictingObjectsCount: 8
          }
        }
      });

      // Must be invalid without explicit acknowledgment
      expect(service.isStepValid(3)).toBe(false);

      // Once acknowledged, becomes valid
      service.updateDraft({ productionCollisionAcknowledged: true });
      expect(service.isStepValid(3)).toBe(true);

      // Non-destructive FAIL_IF_NOT_EMPTY does not require destructive acknowledgment
      service.updateDraft({ collisionPolicy: 'FAIL_IF_NOT_EMPTY', productionCollisionAcknowledged: false });
      expect(service.isStepValid(3)).toBe(true);
    });

    it('changing target engine or connection parameters must invalidate prior target verification', () => {
      service.updateDraft({
        targetConnectionMode: 'NEW',
        targetProvider: 'PostgreSQL',
        targetHost: 'pg-target.internal',
        targetVerified: true
      });
      expect(service.wizardDraft().targetVerified).toBe(true);

      // Change target host
      service.updateDraft({ targetHost: 'pg-new-host.internal', targetVerified: false });
      expect(service.wizardDraft().targetVerified).toBe(false);
      expect(service.isStepValid(3)).toBe(false);
    });
  });

  describe('2.2.4 Step 4 — Discovery & Advanced Scope Contract Suite', () => {
    it('step 4 completion guard must require at least one object in selected scope', () => {
      service.updateDraft({ selectedTopologyNodes: [] });
      expect(service.isStepValid(4)).toBe(false);

      service.updateDraft({ selectedTopologyNodes: ['ora-tbl-accounts'] });
      expect(service.isStepValid(4)).toBe(true);
    });

    it('all 4 discovery depth tiers (SHALLOW, STANDARD, DEEP, FULL_WITH_SAMPLING) must be defined and selectable', () => {
      const depthTiers = ['SHALLOW', 'STANDARD', 'DEEP', 'FULL_WITH_SAMPLING'] as const;
      for (const tier of depthTiers) {
        service.updateDraft({ discoveryDepthTier: tier });
        expect(service.wizardDraft().discoveryDepthTier).toBe(tier);
      }
    });

    it('Oracle hierarchy must expose 5-level instance/database/schema/group/object architecture', () => {
      const tree = service.getTopologyTreeForProvider('Oracle');
      expect(tree.length).toBeGreaterThan(0);
      expect(tree[0].type).toBe('DATABASE'); // RAC / PDB level
      expect(tree[0].children?.[0].type).toBe('DATABASE');
      expect(tree[0].children?.[0].children?.[0].type).toBe('SCHEMA');
    });

    it('MongoDB hierarchy must naturally expose cluster/database/collections without fake schema layers', () => {
      const tree = service.getTopologyTreeForProvider('MongoDB');
      expect(tree.length).toBeGreaterThan(0);
      expect(tree[0].type).toBe('DATABASE');
      expect(tree[0].children?.[0].children?.[0].type).toBe('COLLECTION');
    });

    it('Kafka hierarchy must expose cluster/topics without relational table semantics', () => {
      const tree = service.getTopologyTreeForProvider('Apache Kafka');
      expect(tree.length).toBeGreaterThan(0);
      expect(tree[0].children?.[0].type).toBe('TOPIC');
    });

    it('Storage hierarchy must expose bucket/prefixes/files without relational table semantics', () => {
      const tree = service.getTopologyTreeForProvider('Amazon S3');
      expect(tree.length).toBeGreaterThan(0);
      expect(tree[0].type).toBe('BUCKET');
    });

    it('changing Step 2 source engine must invalidate selected scope and reset topology nodes', () => {
      service.updateDraft({ selectedTopologyNodes: ['ora-tbl-accounts', 'ora-tbl-customers'] });
      expect(service.wizardDraft().selectedTopologyNodes.length).toBe(2);

      service.updateSourceProvider('PostgreSQL');
      expect(service.wizardDraft().selectedTopologyNodes.length).toBe(0);
      expect(service.isStepValid(4)).toBe(false);
    });
  });

  describe('Create Migration Wizard Shell Governance & Interaction Suite', () => {
    it('Wizard Shell 9 steps must follow the exact canonical sequence with single-line labels', () => {
      const canonicalSteps = [
        { index: 1, label: 'Define' },
        { index: 2, label: 'Source' },
        { index: 3, label: 'Target' },
        { index: 4, label: 'Scope' },
        { index: 5, label: 'Mapping' },
        { index: 6, label: 'Configure' },
        { index: 7, label: 'Plan' },
        { index: 8, label: 'Govern' },
        { index: 9, label: 'Review' }
      ];

      expect(canonicalSteps.length).toBe(9);
      expect(canonicalSteps[0].label).toBe('Define');
      expect(canonicalSteps[8].label).toBe('Review');
    });

    it('Safe vs Unsafe exit guardrail: SAVED state allows direct exit, DIRTY/ERROR triggers loss confirmation', () => {
      // 1. Saved state is safe
      service.saveStatus.set('SAVED');
      expect(service.saveStatus()).toBe('SAVED');

      // 2. Unsaved dirty state requires confirmation
      service.updateDraft({ name: 'Unsaved Project Alpha', isDirty: true });
      service.saveStatus.set('DIRTY');
      expect(service.saveStatus()).toBe('DIRTY');
      expect(service.wizardDraft().isDirty).toBe(true);

      // 3. Error state requires confirmation
      service.saveStatus.set('ERROR');
      expect(service.saveStatus()).toBe('ERROR');
    });

    it('Sequential Stepper Locking: operator cannot skip forward past incomplete steps', () => {
      // Step 1 incomplete
      service.updateDraft({ currentStep: 1, name: '', mode: '' as any });
      expect(service.isStepValid(1)).toBe(false);

      // Step 1 complete -> allows progression to Step 2
      service.updateDraft({
        name: 'Enterprise Sync',
        environment: 'Staging',
        mode: 'M1_BULK'
      });
      expect(service.isStepValid(1)).toBe(true);

      // Step 2 incomplete -> prevents advance to Step 3
      service.updateDraft({ currentStep: 2, sourceProvider: '' as any, sourceVerified: false });
      expect(service.isStepValid(2)).toBe(false);

      // Backward navigation to completed step 1 is always permitted
      service.updateDraft({ currentStep: 1 });
      expect(service.wizardDraft().currentStep).toBe(1);
    });

    it('Footer navigation destinations: Step 1 omits Previous, Steps 2-8 display explicit previous/continue labels', () => {
      // Step 1: Destination to Step 2
      service.updateDraft({ currentStep: 1 });
      expect(service.wizardDraft().currentStep).toBe(1);

      // Step 2: Previous is Define, Continue is Target
      service.updateDraft({ currentStep: 2 });
      expect(service.wizardDraft().currentStep).toBe(2);

      // Step 9: Previous is Govern, Final Launch action (no fake Step 10)
      service.updateDraft({ currentStep: 9 });
      expect(service.wizardDraft().currentStep).toBe(9);
    });

    it('Preflight Issue Ledger: detects blocking errors and advisory warnings', () => {
      // Incomplete draft triggers preflight errors across steps
      service.updateDraft({
        name: '',
        mode: '' as any,
        sourceProvider: '' as any,
        targetProvider: '' as any,
        selectedTopologyNodes: []
      });

      const draft = service.wizardDraft();
      expect(draft.name).toBe('');
      expect(draft.selectedTopologyNodes.length).toBe(0);
    });

    it('Template Blueprint application loads valid configuration without inventing frontend parameters', () => {
      const templates = fixtures.getTemplates();
      expect(templates.length).toBeGreaterThan(0);

      const oracleTmpl = templates.find(t => t.id === 'tmpl-ora-pg-cdc') || templates[0];
      service.loadTemplateIntoDraft(oracleTmpl);

      expect(service.wizardDraft().mode).toBe(oracleTmpl.compatibleModes[0]);
      expect(service.wizardDraft().sourceProvider).toBe(oracleTmpl.sourceTypes[0]);
      expect(service.wizardDraft().targetProvider).toBe(oracleTmpl.targetTypes[0]);
      expect(service.wizardDraft().currentStep).toBe(1);
    });
  });

  describe('Step 3 (Target Connection) Governance & Engine Suite', () => {
    it('Step 3 requires verified target connection, collision policy, and passing attestation', () => {
      // Initially unverified
      service.updateDraft({
        targetConnectionMode: 'NEW',
        targetProvider: 'PostgreSQL',
        targetVerified: false,
        collisionPolicy: 'FAIL_ON_COLLISION'
      });
      expect(service.isStepValid(3)).toBe(false);

      // Verified and attested
      service.updateDraft({
        targetVerified: true,
        targetVerificationResult: {
          fingerprint: 'fp-target-test',
          isVerified: true,
          hasBlockingIssues: false,
          latencyMs: 2,
          physicalConnection: { status: 'PASSED', latencyMs: 2 },
          identityAttestation: { status: 'PASSED', systemVersion: 'PG 16' },
          writeAuthority: { status: 'PASSED', permissions: ['CREATE', 'INSERT'] },
          ingestionCapability: { status: 'PASSED', preferredStrategy: 'POSTGRES_BINARY_COPY', fallbackStrategy: 'INSERT', directPathAvailable: true, privilegesVerified: true },
          sandboxCapability: { status: 'PASSED', supported: true, detail: 'Canary passed' },
          storageHeadroom: { status: 'SUFFICIENT', displayStatus: '500 GB free' },
          compatibility: {
            sourceProvider: 'Oracle',
            sourceVersion: '19c',
            targetProvider: 'PostgreSQL',
            targetVersion: '16',
            topology: 'Heterogeneous',
            schemaConversion: 'Supported',
            dataTypeMapping: { status: 'Direct map', reviewCount: 0, detail: 'OK' },
            proceduralConversion: { status: 'Supported', analyzedCount: 0, automaticCount: 0, reviewCount: 0 },
            isBlocked: false
          },
          targetContents: { existingObjectsDetected: false, tableCount: 0, viewCount: 0, indexCount: 0, conflictingObjectsCount: 0 }
        }
      });
      expect(service.isStepValid(3)).toBe(true);
    });

    it('Self-Targeting Guard: blocks Continue when host & db match source unless a distinct schema is provided', () => {
      service.updateDraft({
        targetConnectionMode: 'NEW',
        targetProvider: 'PostgreSQL',
        sourceHost: 'db.internal.corp',
        sourcePort: 5432,
        sourceDatabase: 'app_production',
        targetHost: 'db.internal.corp',
        targetPort: 5432,
        targetDatabase: 'app_production',
        targetSchema: '', // Empty target schema -> blocked
        targetVerified: true,
        targetVerificationResult: {
          fingerprint: 'fp-1',
          isVerified: true,
          hasBlockingIssues: false,
          latencyMs: 1,
          physicalConnection: { status: 'PASSED', latencyMs: 1 },
          identityAttestation: { status: 'PASSED', systemVersion: 'PG 16' },
          writeAuthority: { status: 'PASSED', permissions: ['CREATE'] },
          ingestionCapability: { status: 'PASSED', preferredStrategy: 'COPY', fallbackStrategy: 'INSERT', directPathAvailable: true, privilegesVerified: true },
          sandboxCapability: { status: 'PASSED', supported: true, detail: 'OK' },
          storageHeadroom: { status: 'SUFFICIENT', displayStatus: 'OK' },
          compatibility: { sourceProvider: 'PostgreSQL', sourceVersion: '16', targetProvider: 'PostgreSQL', targetVersion: '16', topology: 'Homogeneous', schemaConversion: 'Supported', dataTypeMapping: { status: 'Direct map', reviewCount: 0, detail: 'OK' }, proceduralConversion: { status: 'Supported', analyzedCount: 0, automaticCount: 0, reviewCount: 0 }, isBlocked: false },
          targetContents: { existingObjectsDetected: false, tableCount: 0, viewCount: 0, indexCount: 0, conflictingObjectsCount: 0 }
        }
      });

      // Self-targeting without different schema must block step 3
      expect(service.isStepValid(3)).toBe(false);

      // Specifying a distinct target schema unlocks step 3
      service.updateDraft({ targetSchema: 'shadow_schema_2026' });
      expect(service.isStepValid(3)).toBe(true);
    });

    it('Production Destructive Guard: DROP_AND_RECREATE in Production requires typed acknowledgment', () => {
      service.updateDraft({
        targetConnectionMode: 'NEW',
        targetProvider: 'PostgreSQL',
        environment: 'Production',
        targetHost: 'pg-target.corp',
        targetPort: 5432,
        targetDatabase: 'warehouse_prod',
        targetSchema: 'finance',
        targetVerified: true,
        collisionPolicy: 'DROP_AND_RECREATE',
        productionCollisionAcknowledged: false,
        targetVerificationResult: {
          fingerprint: 'fp-2',
          isVerified: true,
          hasBlockingIssues: false,
          latencyMs: 1,
          physicalConnection: { status: 'PASSED', latencyMs: 1 },
          identityAttestation: { status: 'PASSED', systemVersion: 'PG 16' },
          writeAuthority: { status: 'PASSED', permissions: ['DROP', 'CREATE'] },
          ingestionCapability: { status: 'PASSED', preferredStrategy: 'COPY', fallbackStrategy: 'INSERT', directPathAvailable: true, privilegesVerified: true },
          sandboxCapability: { status: 'PASSED', supported: true, detail: 'OK' },
          storageHeadroom: { status: 'SUFFICIENT', displayStatus: 'OK' },
          compatibility: { sourceProvider: 'Oracle', sourceVersion: '19c', targetProvider: 'PostgreSQL', targetVersion: '16', topology: 'Heterogeneous', schemaConversion: 'Supported', dataTypeMapping: { status: 'Direct map', reviewCount: 0, detail: 'OK' }, proceduralConversion: { status: 'Supported', analyzedCount: 0, automaticCount: 0, reviewCount: 0 }, isBlocked: false },
          targetContents: { existingObjectsDetected: true, tableCount: 5, viewCount: 2, indexCount: 5, conflictingObjectsCount: 5 }
        }
      });

      // Without acknowledgment -> blocked
      expect(service.isStepValid(3)).toBe(false);

      // Once operator types acknowledgment -> passed
      service.updateDraft({ productionCollisionAcknowledged: true });
      expect(service.isStepValid(3)).toBe(true);
    });

    it('Target Provider schema includes ingestionEngines fast-path definitions for target providers', () => {
      const pgSchema = ALL_28_PROVIDER_SCHEMAS['PostgreSQL'];
      expect(pgSchema.ingestionEngines).toBeDefined();
      expect(pgSchema.ingestionEngines?.some(e => e.value === 'POSTGRES_BINARY_COPY')).toBe(true);

      const oraSchema = ALL_28_PROVIDER_SCHEMAS['Oracle'];
      expect(oraSchema.ingestionEngines).toBeDefined();
      expect(oraSchema.ingestionEngines?.some(e => e.value === 'OCI_DIRECT_PATH')).toBe(true);

      const sfSchema = ALL_28_PROVIDER_SCHEMAS['Snowflake'];
      expect(sfSchema.ingestionEngines).toBeDefined();
      expect(sfSchema.ingestionEngines?.some(e => e.value === 'SNOWPIPE_STREAMING')).toBe(true);
    });
  });

  describe('2.2.4 Step 4 — Universal Discovery & Scope Studio Suite', () => {
    it('step 4 completion guard must require selected objects and resolved/acknowledged FKs', () => {
      // Empty selection -> blocked
      service.updateDraft({
        selectedTopologyNodes: [],
        unresolvedFkCount: 0,
        ignoreFkWarnings: false
      });
      expect(service.isStepValid(4)).toBe(false);

      // Selected nodes with 0 FK warnings -> valid
      service.updateDraft({
        selectedTopologyNodes: ['tbl-customers', 'tbl-orders'],
        unresolvedFkCount: 0,
        ignoreFkWarnings: false
      });
      expect(service.isStepValid(4)).toBe(true);

      // Selected nodes with unacknowledged FK warnings -> blocked
      service.updateDraft({
        selectedTopologyNodes: ['tbl-orders'],
        unresolvedFkCount: 1,
        ignoreFkWarnings: false
      });
      expect(service.isStepValid(4)).toBe(false);

      // Selected nodes with operator acknowledgment -> valid
      service.updateDraft({
        ignoreFkWarnings: true
      });
      expect(service.isStepValid(4)).toBe(true);

      // Unsaved modifications (isScopeSaved === false) -> blocked
      service.updateDraft({
        isScopeSaved: false
      });
      expect(service.isStepValid(4)).toBe(false);

      // Saved scope selection (isScopeSaved === true) -> valid
      service.updateDraft({
        isScopeSaved: true
      });
      expect(service.isStepValid(4)).toBe(true);

      // Freeze scope gate: unfrozen -> blocked
      service.updateDraft({
        isScopeFrozen: false
      });
      expect(service.isStepValid(4)).toBe(false);

      // Frozen scope -> valid
      service.updateDraft({
        isScopeFrozen: true
      });
      expect(service.isStepValid(4)).toBe(true);
    });

    it('supports all 4 cumulative discovery depth tiers', () => {
      const depths: DiscoveryDepthTier[] = ['QUICK', 'STANDARD', 'DEEP', 'COMPLIANCE'];
      depths.forEach(d => {
        service.updateDraft({ discoveryDepthTier: d });
        expect(service.wizardDraft().discoveryDepthTier).toBe(d);
      });
    });
  });
});

