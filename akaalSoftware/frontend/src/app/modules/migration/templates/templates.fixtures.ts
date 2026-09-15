import { TemplateItem } from './templates.models';

/**
 * Pre-P7D Presentation Fixtures for Migration Templates.
 * Provides realistic, calm enterprise template fixtures covering M1 through M7.
 *
 * NOTE: Isolated development presentation data only.
 * No fake backend authority, no synthetic certification stamps.
 */
export const TEMPLATE_FIXTURES: TemplateItem[] = [
  {
    id: 'tmpl-ora-pg-m2',
    name: 'Oracle to PostgreSQL Continuous Migration',
    description: 'Bulk table copy with transactional log change data capture for core database re-platforming.',
    mode: 'M2_BULK_CDC',
    applicability: {
      sourceProviderName: 'Oracle',
      targetProviderName: 'PostgreSQL'
    },
    scope: 'ORGANIZATION',
    versionLabel: 'v2.1.0',
    lifecycle: 'PUBLISHED',
    usage: {
      referencedProjectCount: 14,
      migrationCount: 42,
      lastUsedAt: '2026-08-28T14:30:00Z',
      isUsageKnown: true,
      isUnused: false
    },
    createdAt: '2026-01-15T09:00:00Z',
    updatedAt: '2026-08-28T14:30:00Z'
  },
  {
    id: 'tmpl-pg-snow-m1',
    name: 'PostgreSQL to Snowflake Analytics Warehouse Load',
    description: 'Historical bulk snapshot migration for dimensional schemas and reporting marts.',
    mode: 'M1_BULK',
    applicability: {
      sourceProviderName: 'PostgreSQL',
      targetProviderName: 'Snowflake'
    },
    scope: 'WORKSPACE',
    versionLabel: 'v1.4.0',
    lifecycle: 'PUBLISHED',
    usage: {
      referencedProjectCount: 8,
      migrationCount: 19,
      lastUsedAt: '2026-09-02T11:15:00Z',
      isUsageKnown: true,
      isUnused: false
    },
    createdAt: '2026-02-10T10:00:00Z',
    updatedAt: '2026-09-02T11:15:00Z'
  },
  {
    id: 'tmpl-mssql-pg-m2',
    name: 'SQL Server to PostgreSQL Re-platforming',
    description: 'Schema conversion with initial table loading and ongoing SQL Server CDC streaming.',
    mode: 'M2_BULK_CDC',
    applicability: {
      sourceProviderName: 'SQL Server',
      targetProviderName: 'PostgreSQL'
    },
    scope: 'ORGANIZATION',
    versionLabel: 'v1.8.2',
    lifecycle: 'PUBLISHED',
    usage: {
      referencedProjectCount: 6,
      migrationCount: 15,
      lastUsedAt: '2026-08-19T16:45:00Z',
      isUsageKnown: true,
      isUnused: false
    },
    createdAt: '2026-03-01T08:30:00Z',
    updatedAt: '2026-08-19T16:45:00Z'
  },
  {
    id: 'tmpl-kafka-bq-m3',
    name: 'Kafka Topic to BigQuery Event Stream Ingestion',
    description: 'Continuous real-time event streaming pipeline from Kafka broker partitions to BigQuery tables.',
    mode: 'M3_CDC',
    applicability: {
      sourceProviderName: 'Kafka',
      targetProviderName: 'BigQuery'
    },
    scope: 'ORGANIZATION',
    versionLabel: 'v2.0.0',
    lifecycle: 'PUBLISHED',
    usage: {
      referencedProjectCount: 5,
      migrationCount: 11,
      lastUsedAt: '2026-09-05T09:20:00Z',
      isUsageKnown: true,
      isUnused: false
    },
    createdAt: '2026-03-20T14:00:00Z',
    updatedAt: '2026-09-05T09:20:00Z'
  },
  {
    id: 'tmpl-mysql-s3-m4',
    name: 'MySQL to S3 Lakehouse Incremental Polling',
    description: 'Timestamp watermark-based batch delta extraction for historical lakehouse staging.',
    mode: 'M4_INCREMENTAL',
    applicability: {
      sourceProviderName: 'MySQL',
      targetProviderName: 'Amazon S3'
    },
    scope: 'WORKSPACE',
    versionLabel: 'v1.1.0',
    lifecycle: 'PUBLISHED',
    usage: {
      referencedProjectCount: 3,
      migrationCount: 7,
      lastUsedAt: '2026-07-30T13:10:00Z',
      isUsageKnown: true,
      isUnused: false
    },
    createdAt: '2026-04-05T12:00:00Z',
    updatedAt: '2026-07-30T13:10:00Z'
  },
  {
    id: 'tmpl-mongo-pg-m5',
    name: 'MongoDB to PostgreSQL Document State Sync',
    description: 'Bi-directional state reconciliation and document-to-relational attribute synchronization.',
    mode: 'M5_STATE_SYNC',
    applicability: {
      sourceProviderName: 'MongoDB',
      targetProviderName: 'PostgreSQL'
    },
    scope: 'PROJECT',
    versionLabel: 'v1.0-draft',
    lifecycle: 'DRAFT',
    usage: {
      referencedProjectCount: 0,
      migrationCount: 0,
      lastUsedAt: null,
      isUsageKnown: true,
      isUnused: true
    },
    createdAt: '2026-08-10T15:00:00Z',
    updatedAt: '2026-08-10T15:00:00Z'
  },
  {
    id: 'tmpl-ora-pg-schema-m6',
    name: 'Oracle to PostgreSQL Schema Extraction & DDL Conversion',
    description: 'DDL schema extraction, sequence translation, constraints mapping, and index provisioning.',
    mode: 'M6_SCHEMA_ONLY',
    applicability: {
      sourceProviderName: 'Oracle',
      targetProviderName: 'PostgreSQL'
    },
    scope: 'ORGANIZATION',
    versionLabel: 'v3.0.1',
    lifecycle: 'PUBLISHED',
    usage: {
      referencedProjectCount: 11,
      migrationCount: 28,
      lastUsedAt: '2026-09-01T17:00:00Z',
      isUsageKnown: true,
      isUnused: false
    },
    createdAt: '2026-02-01T11:00:00Z',
    updatedAt: '2026-09-01T17:00:00Z'
  },
  {
    id: 'tmpl-sfdc-pg-m7',
    name: 'Salesforce CRM to PostgreSQL Data Mart Sync',
    description: 'Object payload extraction and relational table loading for Salesforce CRM entities.',
    mode: 'M7_DATA_ONLY',
    applicability: {
      sourceProviderName: 'Salesforce',
      targetProviderName: 'PostgreSQL'
    },
    scope: 'WORKSPACE',
    versionLabel: 'v1.0.0',
    lifecycle: 'PUBLISHED',
    usage: {
      referencedProjectCount: 2,
      migrationCount: 4,
      lastUsedAt: '2026-08-12T10:00:00Z',
      isUsageKnown: true,
      isUnused: false
    },
    createdAt: '2026-06-15T09:30:00Z',
    updatedAt: '2026-08-12T10:00:00Z'
  },
  {
    id: 'tmpl-pg-bq-m1',
    name: 'PostgreSQL to BigQuery Cold Data Migration',
    description: 'Bulk snapshot partition export for historical archive datasets and compliance reporting.',
    mode: 'M1_BULK',
    applicability: {
      sourceProviderName: 'PostgreSQL',
      targetProviderName: 'BigQuery'
    },
    scope: 'WORKSPACE',
    versionLabel: 'v1.3.0',
    lifecycle: 'DEPRECATED',
    usage: {
      referencedProjectCount: 4,
      migrationCount: 8,
      lastUsedAt: '2026-05-20T14:00:00Z',
      isUsageKnown: true,
      isUnused: false
    },
    createdAt: '2026-01-20T10:00:00Z',
    updatedAt: '2026-05-20T14:00:00Z'
  },
  {
    id: 'tmpl-redis-pg-m4',
    name: 'Redis Cache to PostgreSQL State Persistence',
    description: 'Periodic key-value snapshot polling into structured relational target tables.',
    mode: 'M4_INCREMENTAL',
    applicability: {
      sourceProviderName: 'Redis',
      targetProviderName: 'PostgreSQL'
    },
    scope: 'PROJECT',
    versionLabel: 'v0.9.0',
    lifecycle: 'DRAFT',
    usage: {
      referencedProjectCount: 0,
      migrationCount: 0,
      lastUsedAt: null,
      isUsageKnown: false, // Telemetry unprobed state
      isUnused: false
    },
    createdAt: '2026-08-25T16:00:00Z',
    updatedAt: '2026-08-25T16:00:00Z'
  }
];
