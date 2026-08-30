import { describe, it, expect, beforeEach } from 'vitest';
import { MigrationUiService } from '../../../core/services/migration-ui.service';
import { MigrationDevFixturesAdapter } from '../../../core/fixtures/migration-dev-fixtures.adapter';
import { ALL_28_PROVIDER_SCHEMAS } from '../../../core/models/provider-form-schemas';
import { PhysicalProviderId } from '../../../core/models/migration-view.models';

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
    it('step 1 should be invalid with empty migration name and valid when named', () => {
      service.updateDraft({ name: '' });
      expect(service.isStepValid(1)).toBe(false);

      service.updateDraft({ name: 'PROD_MIGRATION' });
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
});
