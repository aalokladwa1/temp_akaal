import { TemplateDetail, TemplateVersionItem } from './template-workspace.models';

/**
 * Pre-P7D Presentation Fixtures for Template Workspace (Part C)
 * Isolated presentation data covering M1–M7 modes, lifecycles, versions, usages, and activities.
 * NOTE: M8 is STRICTLY FORBIDDEN. Zero Plaintext Secrets guaranteed.
 */
export const TEMPLATE_WORKSPACE_FIXTURES: Record<string, TemplateDetail> = {
  'tmpl-ora-pg-m2': {
    id: 'tmpl-ora-pg-m2',
    name: 'Oracle to PostgreSQL Continuous Migration',
    description: 'Bulk table copy with transactional log change data capture for core database re-platforming and cloud migration.',
    mode: 'M2_BULK_CDC',
    applicability: {
      sourceProviderName: 'Oracle',
      targetProviderName: 'PostgreSQL'
    },
    scope: 'ORGANIZATION',
    versionLabel: 'v2.1.0',
    revisionNumber: 3,
    lifecycle: 'PUBLISHED',
    createdAt: '2026-01-15T09:00:00Z',
    updatedAt: '2026-08-28T14:30:00Z',
    createdBy: 'Aalok Ladwa (Chief Data Architect)',
    lastUpdatedBy: 'Aalok Ladwa (Chief Data Architect)',
    configuration: {
      definition: {
        name: 'Oracle to PostgreSQL Continuous Migration',
        description: 'Bulk table copy with transactional log change data capture for core database re-platforming and cloud migration.',
        scope: 'ORGANIZATION',
        sourceProvider: 'oracle',
        targetProvider: 'postgresql',
        mode: 'M2_BULK_CDC'
      },
      migrationDefaults: {
        migrationNamePattern: 'MIG-ORA-PG-{{PROJECT}}-{{ENV}}-{{SEQ}}',
        executionPriority: 'HIGH',
        sourceConnectionPolicy: 'REQUIRE_AT_CREATION',
        sourceConnectionTag: 'oracle-prod-pool',
        targetConnectionPolicy: 'PROJECT_POOL',
        targetConnectionTag: 'pg-aurora-pool',
        requiredAtUse: {
          targetDatabaseRequired: true,
          scheduleRequired: true,
          secretBindingsRequired: true,
          workspaceSelectionRequired: true,
          notificationChannelsRequired: false
        }
      },
      scopeMapping: {
        objectScopeRules: [
          { id: 'rule-1', ruleType: 'INCLUDE', objectType: 'TABLE', pattern: 'HR.*', description: 'Include human resources schema' },
          { id: 'rule-2', ruleType: 'INCLUDE', objectType: 'TABLE', pattern: 'FINANCE.*', description: 'Include general ledger and balances' },
          { id: 'rule-3', ruleType: 'EXCLUDE', objectType: 'TABLE', pattern: '*_TEMP', description: 'Exclude ephemeral scratch tables' },
          { id: 'rule-4', ruleType: 'EXCLUDE', objectType: 'TABLE', pattern: '*_BAK', description: 'Exclude local manual backups' }
        ],
        schemaMappings: [
          { id: 'sm-1', sourceSchema: 'HR', targetSchema: 'hr_core' },
          { id: 'sm-2', sourceSchema: 'FINANCE', targetSchema: 'fin_analytics' }
        ],
        tableCaseTransformation: 'LOWERCASE',
        nullabilityPolicy: 'PRESERVE',
        columnTypeOverrides: [
          { id: 'ct-1', sourceType: 'NUMBER(1,0)', targetType: 'BOOLEAN' },
          { id: 'ct-2', sourceType: 'VARCHAR2(255)', targetType: 'VARCHAR(255)' },
          { id: 'ct-3', sourceType: 'CLOB', targetType: 'TEXT' },
          { id: 'ct-4', sourceType: 'BLOB', targetType: 'BYTEA' }
        ],
        maskingRules: [
          { id: 'mr-1', targetPattern: '*_SSN', maskingType: 'PII_REDACT', note: 'Redact social security numbers' },
          { id: 'mr-2', targetPattern: '*_CARD_NUM', maskingType: 'TOKENIZE', note: 'Tokenize credit card numbers' },
          { id: 'mr-3', targetPattern: '*_EMAIL', maskingType: 'MASK_EMAIL', note: 'Mask email addresses' }
        ],
        cleansing: {
          trimWhitespace: true,
          emptyStringToNull: true,
          deduplicateOnPrimaryKey: true
        }
      },
      enterpriseConfig: {
        performance: {
          extractThreads: 8,
          batchSize: 10000,
          bufferMemoryMb: 2048,
          maxThroughputMbps: 250
        },
        checkpointRecovery: {
          commitIntervalRows: 25000,
          commitIntervalSec: 60,
          retryCount: 5,
          errorHandlingPolicy: 'SKIP_AND_LOG_DLQ',
          maxSkippedErrors: 50
        },
        cdcConfig: {
          cdcEngine: 'DATABASE_LOG_MINER',
          snapshotToStreamHandoff: 'SEAMLESS_LOCKLESS',
          heartbeatTracking: true,
          maxLagAlertSec: 15
        },
        incrementalConfig: {
          watermarkColumn: 'updated_at',
          pollingIntervalSec: 60,
          lookbackWindowMinutes: 5
        },
        stateSyncConfig: {
          biDirectionalEnabled: false,
          conflictResolution: 'SOURCE_WINS'
        },
        schemaOnlyConfig: {
          createForeignKeys: 'POST_LOAD',
          includeIndexes: true,
          dropTargetObjectsFirst: false
        },
        dataOnlyConfig: {
          requireTargetTableExists: true,
          truncateTargetBeforeLoad: false,
          disableForeignKeysDuringLoad: true
        },
        validationPresets: {
          rowCountReconciliation: true,
          schemaChecksumCheck: true,
          sampleDataHashRate: 'SAMPLE_10_PCT'
        }
      },
      governance: {
        overridability: {
          performanceSettings: 'RESTRICTED',
          mappingRules: 'LOCKED',
          scopeObjects: 'SUBSET_ONLY'
        },
        requiredCapabilities: {
          sourcePrivileges: ['SELECT ANY TABLE', 'LOGMINER', 'EXECUTE_CATALOG_ROLE'],
          targetPrivileges: ['CREATE TABLE', 'INSERT', 'UPDATE', 'DELETE'],
          networkRequirements: ['TLS 1.3 Mandated', 'VPC Peering or PrivateLink']
        },
        approvalAndPolicy: {
          requirePeerReview: true,
          enforceChangeFreezeWindow: true,
          auditLogLevel: 'VERBOSE'
        },
        secretReferenceRules: {
          vaultProvider: 'HASHICORP_VAULT',
          keyPathPrefix: 'secret/data/akaal/migration/oracle-pg/',
          guidanceNote: 'Store source and target database credentials under secret/data/akaal/migration/.'
        }
      }
    },
    applicabilityDetails: {
      sourceDialect: 'Oracle 11g, 12c, 19c, 21c (Enterprise & Standard Edition)',
      sourceFamily: 'Relational Database Management System',
      targetDialect: 'PostgreSQL 13, 14, 15, 16 (Self-Hosted, Amazon Aurora, RDS, Cloud SQL)',
      targetFamily: 'Relational Database Management System',
      compatibility: {
        sourceProvider: 'Oracle',
        targetProvider: 'PostgreSQL',
        status: 'VERIFIED',
        statusLabel: 'Officially Certified Provider Pair',
        certifiedVersionRange: 'Oracle 12c+ → PostgreSQL 14+',
        notes: 'Full schema conversion, initial bulk load, and CDC continuous streaming verified under enterprise workloads.'
      },
      requiredCapabilities: {
        sourcePrivileges: [
          'SELECT ANY TABLE / SELECT on migrated schemas',
          'DBMS_LOGMNR package execution permissions',
          'Supplemental logging enabled at database or table level'
        ],
        targetPrivileges: [
          'CREATE SCHEMA, CREATE TABLE, CREATE INDEX on target database',
          'INSERT, UPDATE, DELETE, TRUNCATE permissions',
          'ALTER SESSION / REPLICATION privileges if WAL2JSON or replication slot is used'
        ],
        networkRequirements: [
          'Direct TCP connectivity on port 1521 (Oracle) and port 5432 (PostgreSQL)',
          'mTLS 1.3 encrypted transport mandatory across boundary',
          'Bandwidth capacity >= 250 Mbps for full saturation'
        ]
      },
      requiredAtUse: {
        targetDatabaseRequired: true,
        scheduleRequired: true,
        secretBindingsRequired: true,
        workspaceSelectionRequired: true,
        notificationChannelsRequired: false
      },
      connectionExpectations: {
        tlsMandatory: true,
        zeroSecretsEnforced: true,
        logicalTaggingSupported: true,
        vaultReferencePattern: 'vault://secret/data/akaal/migration/oracle-pg/*'
      },
      environmentConstraints: [
        'Production Oracle databases require archivelog mode enabled for CDC streaming.',
        'PostgreSQL target requires max_connections >= 50 for worker pool allocation.',
        'Cross-region network latency must be under 35ms for real-time synchronization.'
      ],
      knownLimitations: [
        'Oracle BFILE and LONG raw data types require manual handling or binary conversion override.',
        'Oracle proprietary stored procedures (PL/SQL) require manual refactoring to PL/pgSQL before activation.'
      ]
    },
    versions: [
      {
        versionLabel: 'v2.1.0',
        revisionNumber: 3,
        createdAt: '2026-08-28T14:30:00Z',
        createdBy: 'Aalok Ladwa (Chief Data Architect)',
        lifecycle: 'PUBLISHED',
        changeSummary: 'Added data masking rules for PII (SSN, Email, Card numbers) and increased extract concurrency to 8 threads.',
        usageCount: 4,
        supersedesVersion: 'v2.0.0',
        isCurrent: true,
        configurationSnapshot: {
          definition: {
            name: 'Oracle to PostgreSQL Continuous Migration',
            description: 'Bulk table copy with transactional log change data capture for core database re-platforming and cloud migration.',
            scope: 'ORGANIZATION',
            sourceProvider: 'oracle',
            targetProvider: 'postgresql',
            mode: 'M2_BULK_CDC'
          },
          migrationDefaults: {
            migrationNamePattern: 'MIG-ORA-PG-{{PROJECT}}-{{ENV}}-{{SEQ}}',
            executionPriority: 'HIGH',
            sourceConnectionPolicy: 'REQUIRE_AT_CREATION',
            sourceConnectionTag: 'oracle-prod-pool',
            targetConnectionPolicy: 'PROJECT_POOL',
            targetConnectionTag: 'pg-aurora-pool',
            requiredAtUse: {
              targetDatabaseRequired: true,
              scheduleRequired: true,
              secretBindingsRequired: true,
              workspaceSelectionRequired: true,
              notificationChannelsRequired: false
            }
          },
          scopeMapping: {
            objectScopeRules: [
              { id: 'rule-1', ruleType: 'INCLUDE', objectType: 'TABLE', pattern: 'HR.*' },
              { id: 'rule-2', ruleType: 'INCLUDE', objectType: 'TABLE', pattern: 'FINANCE.*' },
              { id: 'rule-3', ruleType: 'EXCLUDE', objectType: 'TABLE', pattern: '*_TEMP' },
              { id: 'rule-4', ruleType: 'EXCLUDE', objectType: 'TABLE', pattern: '*_BAK' }
            ],
            schemaMappings: [
              { id: 'sm-1', sourceSchema: 'HR', targetSchema: 'hr_core' },
              { id: 'sm-2', sourceSchema: 'FINANCE', targetSchema: 'fin_analytics' }
            ],
            tableCaseTransformation: 'LOWERCASE',
            nullabilityPolicy: 'PRESERVE',
            columnTypeOverrides: [
              { id: 'ct-1', sourceType: 'NUMBER(1,0)', targetType: 'BOOLEAN' },
              { id: 'ct-2', sourceType: 'VARCHAR2(255)', targetType: 'VARCHAR(255)' }
            ],
            maskingRules: [
              { id: 'mr-1', targetPattern: '*_SSN', maskingType: 'PII_REDACT' },
              { id: 'mr-2', targetPattern: '*_CARD_NUM', maskingType: 'TOKENIZE' }
            ],
            cleansing: { trimWhitespace: true, emptyStringToNull: true, deduplicateOnPrimaryKey: true }
          },
          enterpriseConfig: {
            performance: { extractThreads: 8, batchSize: 10000, bufferMemoryMb: 2048, maxThroughputMbps: 250 },
            checkpointRecovery: { commitIntervalRows: 25000, commitIntervalSec: 60, retryCount: 5, errorHandlingPolicy: 'SKIP_AND_LOG_DLQ', maxSkippedErrors: 50 },
            cdcConfig: { cdcEngine: 'DATABASE_LOG_MINER', snapshotToStreamHandoff: 'SEAMLESS_LOCKLESS', heartbeatTracking: true, maxLagAlertSec: 15 },
            incrementalConfig: { watermarkColumn: 'updated_at', pollingIntervalSec: 60, lookbackWindowMinutes: 5 },
            stateSyncConfig: { biDirectionalEnabled: false, conflictResolution: 'SOURCE_WINS' },
            schemaOnlyConfig: { createForeignKeys: 'POST_LOAD', includeIndexes: true, dropTargetObjectsFirst: false },
            dataOnlyConfig: { requireTargetTableExists: true, truncateTargetBeforeLoad: false, disableForeignKeysDuringLoad: true },
            validationPresets: { rowCountReconciliation: true, schemaChecksumCheck: true, sampleDataHashRate: 'SAMPLE_10_PCT' }
          },
          governance: {
            overridability: { performanceSettings: 'RESTRICTED', mappingRules: 'LOCKED', scopeObjects: 'SUBSET_ONLY' },
            requiredCapabilities: {
              sourcePrivileges: ['SELECT ANY TABLE', 'LOGMINER'],
              targetPrivileges: ['CREATE TABLE', 'INSERT'],
              networkRequirements: ['TLS 1.3']
            },
            approvalAndPolicy: { requirePeerReview: true, enforceChangeFreezeWindow: true, auditLogLevel: 'VERBOSE' },
            secretReferenceRules: { vaultProvider: 'HASHICORP_VAULT', keyPathPrefix: 'secret/data/akaal/migration/oracle-pg/', guidanceNote: 'Vault secrets' }
          }
        }
      },
      {
        versionLabel: 'v2.0.0',
        revisionNumber: 2,
        createdAt: '2026-05-10T11:00:00Z',
        createdBy: 'Pratham Pathak',
        lifecycle: 'PUBLISHED',
        changeSummary: 'Upgraded CDC engine to LogMiner seamless catchup and enabled peer review policy.',
        usageCount: 18,
        supersedesVersion: 'v1.0.0',
        isCurrent: false,
        configurationSnapshot: {
          definition: {
            name: 'Oracle to PostgreSQL Continuous Migration',
            description: 'Legacy bulk snapshot and CDC migration baseline.',
            scope: 'ORGANIZATION',
            sourceProvider: 'oracle',
            targetProvider: 'postgresql',
            mode: 'M2_BULK_CDC'
          },
          migrationDefaults: {
            migrationNamePattern: 'MIG-ORA-PG-{{PROJECT}}-{{ENV}}-{{SEQ}}',
            executionPriority: 'NORMAL',
            sourceConnectionPolicy: 'REQUIRE_AT_CREATION',
            sourceConnectionTag: '',
            targetConnectionPolicy: 'REQUIRE_AT_CREATION',
            targetConnectionTag: '',
            requiredAtUse: {
              targetDatabaseRequired: true,
              scheduleRequired: false,
              secretBindingsRequired: true,
              workspaceSelectionRequired: false,
              notificationChannelsRequired: false
            }
          },
          scopeMapping: {
            objectScopeRules: [{ id: 'rule-1', ruleType: 'INCLUDE', objectType: 'TABLE', pattern: 'HR.*' }],
            schemaMappings: [{ id: 'sm-1', sourceSchema: 'HR', targetSchema: 'hr_core' }],
            tableCaseTransformation: 'PRESERVE',
            nullabilityPolicy: 'PRESERVE',
            columnTypeOverrides: [],
            maskingRules: [],
            cleansing: { trimWhitespace: true, emptyStringToNull: false, deduplicateOnPrimaryKey: false }
          },
          enterpriseConfig: {
            performance: { extractThreads: 4, batchSize: 5000, bufferMemoryMb: 1024, maxThroughputMbps: 100 },
            checkpointRecovery: { commitIntervalRows: 10000, commitIntervalSec: 60, retryCount: 3, errorHandlingPolicy: 'ABORT_IMMEDIATELY', maxSkippedErrors: 0 },
            cdcConfig: { cdcEngine: 'DATABASE_LOG_MINER', snapshotToStreamHandoff: 'QUIESCE_REQUIRED', heartbeatTracking: true, maxLagAlertSec: 30 },
            incrementalConfig: { watermarkColumn: 'updated_at', pollingIntervalSec: 120, lookbackWindowMinutes: 10 },
            stateSyncConfig: { biDirectionalEnabled: false, conflictResolution: 'SOURCE_WINS' },
            schemaOnlyConfig: { createForeignKeys: 'POST_LOAD', includeIndexes: false, dropTargetObjectsFirst: false },
            dataOnlyConfig: { requireTargetTableExists: true, truncateTargetBeforeLoad: false, disableForeignKeysDuringLoad: false },
            validationPresets: { rowCountReconciliation: true, schemaChecksumCheck: false, sampleDataHashRate: 'SAMPLE_1_PCT' }
          },
          governance: {
            overridability: { performanceSettings: 'FULL_OVERRIDE', mappingRules: 'ALLOWED', scopeObjects: 'UNRESTRICTED' },
            requiredCapabilities: {
              sourcePrivileges: ['SELECT ANY TABLE'],
              targetPrivileges: ['CREATE TABLE', 'INSERT'],
              networkRequirements: ['TLS 1.2']
            },
            approvalAndPolicy: { requirePeerReview: false, enforceChangeFreezeWindow: false, auditLogLevel: 'STANDARD' },
            secretReferenceRules: { vaultProvider: 'HASHICORP_VAULT', keyPathPrefix: 'secret/data/akaal/migration/oracle-pg/', guidanceNote: 'Vault secrets' }
          }
        }
      },
      {
        versionLabel: 'v1.0.0',
        revisionNumber: 1,
        createdAt: '2026-01-15T09:00:00Z',
        createdBy: 'Aalok Ladwa',
        lifecycle: 'ARCHIVED',
        changeSummary: 'Initial template baseline creation with standard defaults.',
        usageCount: 6,
        isCurrent: false,
        configurationSnapshot: {
          definition: {
            name: 'Oracle to PostgreSQL Continuous Migration',
            description: 'Initial template release.',
            scope: 'WORKSPACE',
            sourceProvider: 'oracle',
            targetProvider: 'postgresql',
            mode: 'M2_BULK_CDC'
          },
          migrationDefaults: {
            migrationNamePattern: 'MIG-{{PROJECT}}-{{SEQ}}',
            executionPriority: 'NORMAL',
            sourceConnectionPolicy: 'REQUIRE_AT_CREATION',
            sourceConnectionTag: '',
            targetConnectionPolicy: 'REQUIRE_AT_CREATION',
            targetConnectionTag: '',
            requiredAtUse: {
              targetDatabaseRequired: true,
              scheduleRequired: false,
              secretBindingsRequired: true,
              workspaceSelectionRequired: false,
              notificationChannelsRequired: false
            }
          },
          scopeMapping: {
            objectScopeRules: [{ id: 'rule-1', ruleType: 'INCLUDE', objectType: 'TABLE', pattern: '*' }],
            schemaMappings: [],
            tableCaseTransformation: 'PRESERVE',
            nullabilityPolicy: 'PRESERVE',
            columnTypeOverrides: [],
            maskingRules: [],
            cleansing: { trimWhitespace: false, emptyStringToNull: false, deduplicateOnPrimaryKey: false }
          },
          enterpriseConfig: {
            performance: { extractThreads: 2, batchSize: 2000, bufferMemoryMb: 512, maxThroughputMbps: 50 },
            checkpointRecovery: { commitIntervalRows: 5000, commitIntervalSec: 60, retryCount: 2, errorHandlingPolicy: 'ABORT_IMMEDIATELY', maxSkippedErrors: 0 },
            cdcConfig: { cdcEngine: 'DATABASE_LOG_MINER', snapshotToStreamHandoff: 'QUIESCE_REQUIRED', heartbeatTracking: false, maxLagAlertSec: 60 },
            incrementalConfig: { watermarkColumn: '', pollingIntervalSec: 300, lookbackWindowMinutes: 0 },
            stateSyncConfig: { biDirectionalEnabled: false, conflictResolution: 'SOURCE_WINS' },
            schemaOnlyConfig: { createForeignKeys: 'NONE', includeIndexes: false, dropTargetObjectsFirst: false },
            dataOnlyConfig: { requireTargetTableExists: true, truncateTargetBeforeLoad: false, disableForeignKeysDuringLoad: false },
            validationPresets: { rowCountReconciliation: false, schemaChecksumCheck: false, sampleDataHashRate: 'NONE' }
          },
          governance: {
            overridability: { performanceSettings: 'FULL_OVERRIDE', mappingRules: 'ALLOWED', scopeObjects: 'UNRESTRICTED' },
            requiredCapabilities: {
              sourcePrivileges: ['SELECT ANY TABLE'],
              targetPrivileges: ['CREATE TABLE'],
              networkRequirements: []
            },
            approvalAndPolicy: { requirePeerReview: false, enforceChangeFreezeWindow: false, auditLogLevel: 'STANDARD' },
            secretReferenceRules: { vaultProvider: 'ENVIRONMENT_VAULT', keyPathPrefix: '', guidanceNote: '' }
          }
        }
      }
    ],
    usage: {
      isUsageKnown: true,
      referencedProjectCount: 3,
      migrationCount: 28,
      lastUsedAt: '2026-09-08T10:14:00Z',
      projects: [
        {
          projectId: 'proj-fin-modernization',
          projectName: 'Financial Services Re-Platforming',
          environment: 'Production & Staging',
          scope: 'ORGANIZATION',
          referencingMigrationCount: 14,
          lastUsedAt: '2026-09-08T10:14:00Z'
        },
        {
          projectId: 'proj-hr-cloud',
          projectName: 'Global HR ERP Migration',
          environment: 'Production',
          scope: 'ORGANIZATION',
          referencingMigrationCount: 8,
          lastUsedAt: '2026-08-25T16:20:00Z'
        },
        {
          projectId: 'proj-supply-chain-analytics',
          projectName: 'Supply Chain Data Hub',
          environment: 'UAT',
          scope: 'ORGANIZATION',
          referencingMigrationCount: 6,
          lastUsedAt: '2026-07-19T08:45:00Z'
        }
      ],
      migrations: [
        {
          migrationId: 'mig-ora-pg-001',
          migrationName: 'MIG-ORA-PG-FIN-PROD-001',
          projectId: 'proj-fin-modernization',
          projectName: 'Financial Services Re-Platforming',
          versionUsedAtInstantiation: 'v2.1.0',
          lifecycleState: 'RUNNING',
          appliedAt: '2026-09-08T10:14:00Z',
          overridesCount: 0,
          isIndependentMaterialization: true
        },
        {
          migrationId: 'mig-ora-pg-002',
          migrationName: 'MIG-ORA-PG-HR-PROD-004',
          projectId: 'proj-hr-cloud',
          projectName: 'Global HR ERP Migration',
          versionUsedAtInstantiation: 'v2.0.0',
          lifecycleState: 'RUNNING',
          appliedAt: '2026-08-25T16:20:00Z',
          overridesCount: 2,
          isIndependentMaterialization: true
        },
        {
          migrationId: 'mig-ora-pg-003',
          migrationName: 'MIG-ORA-PG-SC-UAT-009',
          projectId: 'proj-supply-chain-analytics',
          projectName: 'Supply Chain Data Hub',
          versionUsedAtInstantiation: 'v2.1.0',
          lifecycleState: 'COMPLETED',
          appliedAt: '2026-08-12T09:00:00Z',
          overridesCount: 1,
          isIndependentMaterialization: true
        },
        {
          migrationId: 'mig-ora-pg-004',
          migrationName: 'MIG-ORA-PG-FIN-STG-002',
          projectId: 'proj-fin-modernization',
          projectName: 'Financial Services Re-Platforming',
          versionUsedAtInstantiation: 'v1.0.0',
          lifecycleState: 'ARCHIVED',
          appliedAt: '2026-02-14T12:00:00Z',
          overridesCount: 0,
          isIndependentMaterialization: true
        }
      ]
    },
    activities: [
      {
        id: 'act-001',
        timestamp: '2026-08-28T14:30:00Z',
        actor: { name: 'Aalok Ladwa', email: 'aalok@akaal.enterprise', role: 'Chief Data Architect' },
        eventType: 'VERSION_PUBLISHED',
        category: 'VERSIONS',
        summary: 'Published template revision v2.1.0 with masking rules & 8-thread extract concurrency',
        details: 'Added PII masking transforms on SSN, Card numbers, and emails. Increased extract concurrency from 4 to 8 workers.',
        affectedVersion: 'v2.1.0'
      },
      {
        id: 'act-002',
        timestamp: '2026-08-28T13:45:00Z',
        actor: { name: 'Pratham Pathak', email: 'pratham@akaal.enterprise', role: 'Lead Data Engineer' },
        eventType: 'GOVERNANCE_UPDATED',
        category: 'GOVERNANCE',
        summary: 'Enforced dual peer-review sign-off on migration launch from this template',
        affectedVersion: 'v2.1.0'
      },
      {
        id: 'act-003',
        timestamp: '2026-08-20T11:00:00Z',
        actor: { name: 'DevOps Automation', email: 'system@akaal.enterprise', role: 'System Service' },
        eventType: 'MIGRATION_INSTANTIATED',
        category: 'MIGRATION_APPLICATION',
        summary: 'Instantiated new migration MIG-ORA-PG-HR-PROD-004 using template v2.0.0',
        details: 'Project: Global HR ERP Migration (proj-hr-cloud)'
      },
      {
        id: 'act-004',
        timestamp: '2026-05-10T11:00:00Z',
        actor: { name: 'Pratham Pathak', email: 'pratham@akaal.enterprise', role: 'Lead Data Engineer' },
        eventType: 'VERSION_PUBLISHED',
        category: 'VERSIONS',
        summary: 'Published template revision v2.0.0 with LogMiner CDC support',
        affectedVersion: 'v2.0.0'
      },
      {
        id: 'act-005',
        timestamp: '2026-01-15T09:00:00Z',
        actor: { name: 'Aalok Ladwa', email: 'aalok@akaal.enterprise', role: 'Chief Data Architect' },
        eventType: 'TEMPLATE_CREATED',
        category: 'LIFECYCLE',
        summary: 'Created initial template definition v1.0.0 for Oracle to PostgreSQL Continuous Migration',
        affectedVersion: 'v1.0.0'
      }
    ],
    p7bContext: {
      localityRequirements: [
        'Dedicated secure compute enclave',
        'In-memory transformation buffer zero-disk persistence',
        'Direct VPC private networking'
      ],
      sovereigntyConstraints: [
        'Data remains within corporate boundary at all stages',
        'Audit compliance exportable for SOX/GDPR regulatory inspections'
      ],
      recoveryPreference: 'Checkpoint commit every 25,000 rows with dead-letter queue exception routing',
      zeroSecretsAttestation: true
    },
    p7cContext: {
      isAvailable: true,
      advisorySummary: 'Oracle LogMiner stream CDC performs best when redo log buffer is sized >= 64MB and PGA aggregate limit is configured.',
      recommendations: [
        'Verify supplemental logging is enabled before scheduling bulk snapshot handoff.',
        'Target PostgreSQL work_mem can be tuned to 64MB per worker during initial copy.'
      ],
      confidenceNote: 'Derived from historical execution telemetry of 28 production migrations.'
    },
    referenceProtection: {
      isProtected: true,
      reason: 'Template is actively referenced by 2 running enterprise migrations (MIG-ORA-PG-FIN-PROD-001, MIG-ORA-PG-HR-PROD-004). Direct deletion is blocked until active dependencies complete or are detached.',
      activeMigrationCount: 2,
      deletionPermitted: false
    }
  },

  'tmpl-pg-snow-m1': {
    id: 'tmpl-pg-snow-m1',
    name: 'PostgreSQL to Snowflake Analytics Warehouse Load',
    description: 'Historical bulk snapshot migration for dimensional schemas with Parquet staging and warehouse table auto-generation.',
    mode: 'M1_BULK',
    applicability: {
      sourceProviderName: 'PostgreSQL',
      targetProviderName: 'Snowflake'
    },
    scope: 'WORKSPACE',
    versionLabel: 'v1.4.0',
    revisionNumber: 2,
    lifecycle: 'PUBLISHED',
    createdAt: '2026-02-10T10:00:00Z',
    updatedAt: '2026-09-02T11:15:00Z',
    createdBy: 'Data Platform Team',
    lastUpdatedBy: 'Aalok Ladwa',
    configuration: {
      definition: {
        name: 'PostgreSQL to Snowflake Analytics Warehouse Load',
        description: 'Historical bulk snapshot migration for dimensional schemas.',
        scope: 'WORKSPACE',
        sourceProvider: 'postgresql',
        targetProvider: 'snowflake',
        mode: 'M1_BULK'
      },
      migrationDefaults: {
        migrationNamePattern: 'MIG-PG-SNOW-{{PROJECT}}-{{DATE}}',
        executionPriority: 'NORMAL',
        sourceConnectionPolicy: 'PROJECT_POOL',
        sourceConnectionTag: 'pg-prod',
        targetConnectionPolicy: 'PROJECT_POOL',
        targetConnectionTag: 'snow-wh',
        requiredAtUse: {
          targetDatabaseRequired: true,
          scheduleRequired: false,
          secretBindingsRequired: true,
          workspaceSelectionRequired: false,
          notificationChannelsRequired: false
        }
      },
      scopeMapping: {
        objectScopeRules: [
          { id: 'r1', ruleType: 'INCLUDE', objectType: 'TABLE', pattern: 'analytics.*' },
          { id: 'r2', ruleType: 'EXCLUDE', objectType: 'TABLE', pattern: '*_staging' }
        ],
        schemaMappings: [{ id: 'sm1', sourceSchema: 'analytics', targetSchema: 'ANALYTICS_CORE' }],
        tableCaseTransformation: 'UPPERCASE',
        nullabilityPolicy: 'PRESERVE',
        columnTypeOverrides: [{ id: 'ct1', sourceType: 'JSONB', targetType: 'VARIANT' }],
        maskingRules: [],
        cleansing: { trimWhitespace: true, emptyStringToNull: true, deduplicateOnPrimaryKey: true }
      },
      enterpriseConfig: {
        performance: { extractThreads: 16, batchSize: 50000, bufferMemoryMb: 4096, maxThroughputMbps: 500 },
        checkpointRecovery: { commitIntervalRows: 100000, commitIntervalSec: 120, retryCount: 3, errorHandlingPolicy: 'SKIP_AND_LOG_DLQ', maxSkippedErrors: 100 },
        cdcConfig: { cdcEngine: 'WAL2JSON', snapshotToStreamHandoff: 'QUIESCE_REQUIRED', heartbeatTracking: false, maxLagAlertSec: 60 },
        incrementalConfig: { watermarkColumn: 'updated_at', pollingIntervalSec: 300, lookbackWindowMinutes: 15 },
        stateSyncConfig: { biDirectionalEnabled: false, conflictResolution: 'SOURCE_WINS' },
        schemaOnlyConfig: { createForeignKeys: 'NONE', includeIndexes: false, dropTargetObjectsFirst: false },
        dataOnlyConfig: { requireTargetTableExists: true, truncateTargetBeforeLoad: true, disableForeignKeysDuringLoad: false },
        validationPresets: { rowCountReconciliation: true, schemaChecksumCheck: true, sampleDataHashRate: 'SAMPLE_10_PCT' }
      },
      governance: {
        overridability: { performanceSettings: 'FULL_OVERRIDE', mappingRules: 'ALLOWED', scopeObjects: 'UNRESTRICTED' },
        requiredCapabilities: {
          sourcePrivileges: ['SELECT'],
          targetPrivileges: ['CREATE TABLE', 'INSERT', 'STAGE ACCESS'],
          networkRequirements: ['TLS 1.3']
        },
        approvalAndPolicy: { requirePeerReview: false, enforceChangeFreezeWindow: false, auditLogLevel: 'STANDARD' },
        secretReferenceRules: { vaultProvider: 'AWS_SECRETS_MANAGER', keyPathPrefix: 'akaal/pg-snow/', guidanceNote: 'AWS Secrets Manager' }
      }
    },
    applicabilityDetails: {
      sourceDialect: 'PostgreSQL 12, 13, 14, 15, 16',
      sourceFamily: 'Relational Database',
      targetDialect: 'Snowflake Standard & Enterprise Cloud Data Warehouse',
      targetFamily: 'Cloud Data Warehouse',
      compatibility: {
        sourceProvider: 'PostgreSQL',
        targetProvider: 'Snowflake',
        status: 'VERIFIED',
        statusLabel: 'Dialects Certified for Bulk Copy',
        certifiedVersionRange: 'PostgreSQL 13+ → Snowflake 2024+',
        notes: 'High-throughput COPY INTO stage interfaces verified with compressed Parquet intermediate format.'
      },
      requiredCapabilities: {
        sourcePrivileges: ['SELECT'],
        targetPrivileges: ['CREATE TABLE', 'INSERT', 'STAGE ACCESS'],
        networkRequirements: ['TLS 1.3']
      },
      requiredAtUse: {
        targetDatabaseRequired: true,
        scheduleRequired: false,
        secretBindingsRequired: true,
        workspaceSelectionRequired: false,
        notificationChannelsRequired: false
      },
      connectionExpectations: {
        tlsMandatory: true,
        zeroSecretsEnforced: true,
        logicalTaggingSupported: true,
        vaultReferencePattern: 'akaal/pg-snow/*'
      },
      environmentConstraints: ['Snowflake stage bucket must reside in the same cloud region as source PostgreSQL database.'],
      knownLimitations: ['Snowflake does not enforce primary key uniqueness constraints on ingestion.']
    },
    versions: [
      {
        versionLabel: 'v1.4.0',
        revisionNumber: 2,
        createdAt: '2026-09-02T11:15:00Z',
        createdBy: 'Aalok Ladwa',
        lifecycle: 'PUBLISHED',
        changeSummary: 'Tuned batch size to 50k rows and extract concurrency to 16 threads for bulk Parquet COPY INTO.',
        usageCount: 7,
        isCurrent: true,
        configurationSnapshot: {
          definition: {
            name: 'PostgreSQL to Snowflake Analytics Warehouse Load',
            description: 'Historical bulk snapshot migration for dimensional schemas.',
            scope: 'WORKSPACE',
            sourceProvider: 'postgresql',
            targetProvider: 'snowflake',
            mode: 'M1_BULK'
          },
          migrationDefaults: {
            migrationNamePattern: 'MIG-PG-SNOW-{{PROJECT}}-{{DATE}}',
            executionPriority: 'NORMAL',
            sourceConnectionPolicy: 'PROJECT_POOL',
            sourceConnectionTag: 'pg-prod',
            targetConnectionPolicy: 'PROJECT_POOL',
            targetConnectionTag: 'snow-wh',
            requiredAtUse: {
              targetDatabaseRequired: true,
              scheduleRequired: false,
              secretBindingsRequired: true,
              workspaceSelectionRequired: false,
              notificationChannelsRequired: false
            }
          },
          scopeMapping: {
            objectScopeRules: [{ id: 'r1', ruleType: 'INCLUDE', objectType: 'TABLE', pattern: 'analytics.*' }],
            schemaMappings: [{ id: 'sm1', sourceSchema: 'analytics', targetSchema: 'ANALYTICS_CORE' }],
            tableCaseTransformation: 'UPPERCASE',
            nullabilityPolicy: 'PRESERVE',
            columnTypeOverrides: [{ id: 'ct1', sourceType: 'JSONB', targetType: 'VARIANT' }],
            maskingRules: [],
            cleansing: { trimWhitespace: true, emptyStringToNull: true, deduplicateOnPrimaryKey: true }
          },
          enterpriseConfig: {
            performance: { extractThreads: 16, batchSize: 50000, bufferMemoryMb: 4096, maxThroughputMbps: 500 },
            checkpointRecovery: { commitIntervalRows: 100000, commitIntervalSec: 120, retryCount: 3, errorHandlingPolicy: 'SKIP_AND_LOG_DLQ', maxSkippedErrors: 100 },
            cdcConfig: { cdcEngine: 'WAL2JSON', snapshotToStreamHandoff: 'QUIESCE_REQUIRED', heartbeatTracking: false, maxLagAlertSec: 60 },
            incrementalConfig: { watermarkColumn: 'updated_at', pollingIntervalSec: 300, lookbackWindowMinutes: 15 },
            stateSyncConfig: { biDirectionalEnabled: false, conflictResolution: 'SOURCE_WINS' },
            schemaOnlyConfig: { createForeignKeys: 'NONE', includeIndexes: false, dropTargetObjectsFirst: false },
            dataOnlyConfig: { requireTargetTableExists: true, truncateTargetBeforeLoad: true, disableForeignKeysDuringLoad: false },
            validationPresets: { rowCountReconciliation: true, schemaChecksumCheck: true, sampleDataHashRate: 'SAMPLE_10_PCT' }
          },
          governance: {
            overridability: { performanceSettings: 'FULL_OVERRIDE', mappingRules: 'ALLOWED', scopeObjects: 'UNRESTRICTED' },
            requiredCapabilities: {
              sourcePrivileges: ['SELECT'],
              targetPrivileges: ['CREATE TABLE', 'INSERT'],
              networkRequirements: ['TLS 1.3']
            },
            approvalAndPolicy: { requirePeerReview: false, enforceChangeFreezeWindow: false, auditLogLevel: 'STANDARD' },
            secretReferenceRules: { vaultProvider: 'AWS_SECRETS_MANAGER', keyPathPrefix: 'akaal/pg-snow/', guidanceNote: 'AWS Secrets Manager' }
          }
        }
      }
    ],
    usage: {
      isUsageKnown: true,
      referencedProjectCount: 1,
      migrationCount: 7,
      lastUsedAt: '2026-09-02T11:15:00Z',
      projects: [
        {
          projectId: 'proj-dw-marts',
          projectName: 'Analytics Data Marts',
          environment: 'Production',
          scope: 'WORKSPACE',
          referencingMigrationCount: 7,
          lastUsedAt: '2026-09-02T11:15:00Z'
        }
      ],
      migrations: [
        {
          migrationId: 'mig-pg-snow-01',
          migrationName: 'MIG-PG-SNOW-CORE-20260902',
          projectId: 'proj-dw-marts',
          projectName: 'Analytics Data Marts',
          versionUsedAtInstantiation: 'v1.4.0',
          lifecycleState: 'COMPLETED',
          appliedAt: '2026-09-02T11:15:00Z',
          overridesCount: 1,
          isIndependentMaterialization: true
        }
      ]
    },
    activities: [
      {
        id: 'act-p1',
        timestamp: '2026-09-02T11:15:00Z',
        actor: { name: 'Aalok Ladwa', email: 'aalok@akaal.enterprise', role: 'Chief Data Architect' },
        eventType: 'VERSION_PUBLISHED',
        category: 'VERSIONS',
        summary: 'Published revision v1.4.0 with 50k batch size',
        affectedVersion: 'v1.4.0'
      }
    ],
    p7bContext: {
      localityRequirements: ['US-East AWS Region'],
      sovereigntyConstraints: ['Internal analytics domain only'],
      recoveryPreference: 'Re-run snapshot from beginning if interrupted',
      zeroSecretsAttestation: true
    },
    p7cContext: {
      isAvailable: true,
      advisorySummary: 'Snowflake warehouse auto-suspend settings should be configured to 60 seconds during bulk loading windows.',
      recommendations: ['Utilize X-Large virtual warehouse for initial large dimensional table loads'],
      confidenceNote: 'Advisory insight based on Snowflake cost-optimization heuristics.'
    },
    referenceProtection: {
      isProtected: false,
      activeMigrationCount: 0,
      deletionPermitted: true
    }
  }
};
