/**
 * AKAAL Administration — 5.5 Template & Configuration Library Service
 */

import { Injectable, signal, computed } from '@angular/core';
import {
  TemplateAsset,
  AssetFamily,
  AssetFamilySummary,
  PromotionTargetEnv
} from '../models/templates-config.models';

@Injectable({
  providedIn: 'root'
})
export class TemplatesConfigService {
  public readonly assets = signal<TemplateAsset[]>([
    // 1. Migration Templates
    {
      id: 'tmpl-mig-001',
      name: 'PostgreSQL to Snowflake Enterprise Migration Blueprint',
      code: 'PG_SNOWFLAKE_BLUEPRINT',
      family: 'MIGRATION_TEMPLATE',
      category: 'Database Migration',
      description: 'Comprehensive schema ddl translation, CDC replication buffer, and automated index optimization recipe.',
      currentVersion: '2.4.0',
      authorName: 'Marcus Vance',
      authorEmail: 'm.vance@akaaltech.corp',
      environmentTier: 'PRODUCTION',
      status: 'PUBLISHED',
      isSystemProvided: true,
      tags: ['PostgreSQL', 'Snowflake', 'CDC', 'Production-Ready'],
      specPayload: JSON.stringify({
        sourceDialect: 'POSTGRES_15',
        targetDialect: 'SNOWFLAKE_ENTERPRISE',
        concurrencyLimit: 8,
        batchSizeRows: 50000,
        enableCdcStream: true,
        schemaMappingStrategy: 'STRICT_TYPE_CONVERSION'
      }, null, 2),
      versions: [
        {
          version: '2.4.0',
          releaseDate: '2026-02-20',
          authorEmail: 'm.vance@akaaltech.corp',
          commitHash: 'git-cf8812a',
          changelog: 'Added support for JSONB column flattening into Snowflake VARIANT types.',
          breakingChanges: false,
          checksum: 'sha256-4b91ac09e8...'
        },
        {
          version: '2.3.1',
          releaseDate: '2026-01-10',
          authorEmail: 'm.vance@akaaltech.corp',
          commitHash: 'git-a1099bc',
          changelog: 'Optimized chunk partition size for tables > 100M rows.',
          breakingChanges: false,
          checksum: 'sha256-78cc12d001...'
        }
      ],
      usages: [
        {
          id: 'use-001',
          consumerType: 'MIGRATION_JOB',
          consumerName: 'Core Banking Ledger Migration Job #104',
          consumerScope: 'Workspace: Core Banking (eu-west-1)',
          boundVersion: '2.4.0',
          lastExecutionTimestamp: '2026-03-10 18:22 UTC',
          healthStatus: 'HEALTHY'
        }
      ],
      createdAt: '2025-08-12',
      updatedAt: '2026-02-20'
    },
    {
      id: 'tmpl-mig-002',
      name: 'Oracle PL/SQL to BigQuery Stored Proc Migration Pattern',
      code: 'ORACLE_BIGQUERY_PROC',
      family: 'MIGRATION_TEMPLATE',
      category: 'Stored Procedures',
      description: 'Translates legacy Oracle packages, autonomous transactions, and cursors to Google Cloud BigQuery SQL scripts.',
      currentVersion: '1.2.0',
      authorName: 'Priya Patel',
      authorEmail: 'p.patel@akaaltech.corp',
      environmentTier: 'PRODUCTION',
      status: 'PUBLISHED',
      isSystemProvided: false,
      tags: ['Oracle', 'BigQuery', 'SQL Dialect', 'ETL'],
      specPayload: JSON.stringify({
        sourceEngine: 'ORACLE_19C',
        targetEngine: 'BIGQUERY_STANDARD',
        handleExceptions: 'LOG_AND_CONTINUE',
        convertCursorsToLoops: true
      }, null, 2),
      versions: [
        {
          version: '1.2.0',
          releaseDate: '2026-01-15',
          authorEmail: 'p.patel@akaaltech.corp',
          commitHash: 'git-e889104',
          changelog: 'Initial production-hardened release with nested table unnesting.',
          breakingChanges: false,
          checksum: 'sha256-990a12e87c...'
        }
      ],
      usages: [
        {
          id: 'use-002',
          consumerType: 'WORKSPACE',
          consumerName: 'Global Risk Analytics Data Lake',
          consumerScope: 'Org: Global Treasury',
          boundVersion: '1.2.0',
          lastExecutionTimestamp: '2026-03-09 11:00 UTC',
          healthStatus: 'HEALTHY'
        }
      ],
      createdAt: '2025-11-04',
      updatedAt: '2026-01-15'
    },

    // 2. Mapping Templates
    {
      id: 'tmpl-map-001',
      name: 'ISO 20022 Financial Messages to Canonical Trade Model',
      code: 'ISO20022_CANONICAL_TRADE',
      family: 'MAPPING_TEMPLATE',
      category: 'Financial Standard',
      description: 'Standardized attribute-by-attribute schema mapping for pacs.008 and camt.053 payment message models.',
      currentVersion: '3.1.0',
      authorName: 'Aalok Ladwa',
      authorEmail: 'a.ladwa@akaaltech.corp',
      environmentTier: 'PRODUCTION',
      status: 'PUBLISHED',
      isSystemProvided: true,
      tags: ['ISO20022', 'Payments', 'SWIFT', 'Fintech'],
      specPayload: JSON.stringify({
        standard: 'ISO_20022_V3',
        mappings: [
          { source: 'GrpHdr.MsgId', target: 'transaction_reference_id', coercion: 'STRING' },
          { source: 'CdtTrfTxInf.Amt.InstdAmt', target: 'settlement_amount_cents', coercion: 'DECIMAL_TO_INTEGER_CENTS' },
          { source: 'CdtTrfTxInf.Dbtr.Nm', target: 'debtor_legal_name', coercion: 'STRING_TRIM' }
        ]
      }, null, 2),
      versions: [
        {
          version: '3.1.0',
          releaseDate: '2026-03-01',
          authorEmail: 'a.ladwa@akaaltech.corp',
          commitHash: 'git-882ab11',
          changelog: 'Added support for instant SEPA payment message codes.',
          breakingChanges: false,
          checksum: 'sha256-881a9900c4...'
        }
      ],
      usages: [
        {
          id: 'use-003',
          consumerType: 'PIPELINE',
          consumerName: 'Global Real-time Settlement Ingest Pipeline',
          consumerScope: 'Env: Production-EU',
          boundVersion: '3.1.0',
          lastExecutionTimestamp: '2 minutes ago',
          healthStatus: 'HEALTHY'
        }
      ],
      createdAt: '2025-05-18',
      updatedAt: '2026-03-01'
    },

    // 3. Transformation Templates
    {
      id: 'tmpl-trf-001',
      name: 'High-Throughput Parquet Deduplication & Normalizer',
      code: 'PARQUET_DEDUP_NORM',
      family: 'TRANSFORMATION_TEMPLATE',
      category: 'Data Cleansing',
      description: 'Streamed windowed deduplication over composite primary key with UTC timestamp normalization and null coalescing.',
      currentVersion: '1.8.4',
      authorName: 'Marcus Vance',
      authorEmail: 'm.vance@akaaltech.corp',
      environmentTier: 'PRODUCTION',
      status: 'PUBLISHED',
      isSystemProvided: false,
      tags: ['Parquet', 'Deduplication', 'Normalization', 'Streaming'],
      specPayload: JSON.stringify({
        windowSizeMinutes: 15,
        compositeKeyColumns: ['tenant_id', 'entity_uuid', 'event_epoch_ms'],
        timestampColumns: ['created_at', 'updated_at'],
        targetTimezone: 'UTC'
      }, null, 2),
      versions: [
        {
          version: '1.8.4',
          releaseDate: '2026-02-11',
          authorEmail: 'm.vance@akaaltech.corp',
          commitHash: 'git-1090fe3',
          changelog: 'Memory footprint reduced by 40% using Arrow dictionary encoding.',
          breakingChanges: false,
          checksum: 'sha256-1199aacc88...'
        }
      ],
      usages: [
        {
          id: 'use-004',
          consumerType: 'PIPELINE',
          consumerName: 'Clickstream Event Normalization Pipeline',
          consumerScope: 'Workspace: Marketing Analytics',
          boundVersion: '1.8.4',
          lastExecutionTimestamp: '10 minutes ago',
          healthStatus: 'HEALTHY'
        }
      ],
      createdAt: '2025-09-20',
      updatedAt: '2026-02-11'
    },

    // 4. Privacy Policies
    {
      id: 'tmpl-prv-001',
      name: 'GDPR / CCPA PII Tokenization & Format-Preserving Encryption',
      code: 'GDPR_PII_FPE_POLICY',
      family: 'PRIVACY_POLICY',
      category: 'Compliance & Masking',
      description: 'Reversible FPE encryption for SSNs, credit card numbers, and deterministic HMAC-SHA256 hashing for emails.',
      currentVersion: '2.0.0',
      authorName: 'Sarah Jenkins',
      authorEmail: 's.jenkins@akaaltech.corp',
      environmentTier: 'PRODUCTION',
      status: 'PUBLISHED',
      isSystemProvided: true,
      tags: ['GDPR', 'CCPA', 'PII', 'FPE', 'Tokenization'],
      specPayload: JSON.stringify({
        complianceStandards: ['GDPR_ART_32', 'CCPA_2024', 'HIPAA_SAFE_HARBOR'],
        rules: [
          { columnRegex: '.*(ssn|social_security|national_id).*', algorithm: 'AES_256_FPE_BPS' },
          { columnRegex: '.*(credit_card|pan|card_num).*', algorithm: 'LUHN_PRESERVING_MASK' },
          { columnRegex: '.*(email|mail_addr).*', algorithm: 'DETERMINISTIC_HMAC_SHA256' }
        ]
      }, null, 2),
      versions: [
        {
          version: '2.0.0',
          releaseDate: '2026-01-05',
          authorEmail: 's.jenkins@akaaltech.corp',
          commitHash: 'git-772210a',
          changelog: 'Upgraded FPE cipher to FF3-1 specification.',
          breakingChanges: false,
          checksum: 'sha256-4433bb0099...'
        }
      ],
      usages: [
        {
          id: 'use-005',
          consumerType: 'ENVIRONMENT',
          consumerName: 'Stage Non-Production Sandbox Cluster',
          consumerScope: 'Org: Global Retail',
          boundVersion: '2.0.0',
          lastExecutionTimestamp: '1 hour ago',
          healthStatus: 'HEALTHY'
        }
      ],
      createdAt: '2025-04-12',
      updatedAt: '2026-01-05'
    },

    // 5. Data Quality Policies
    {
      id: 'tmpl-dq-001',
      name: 'Strict Financial Ledger Balance & Completeness Assertions',
      code: 'FIN_LEDGER_DQ_ASSERTIONS',
      family: 'DATA_QUALITY_POLICY',
      category: 'Integrity Rules',
      description: 'Zero-null primary key assertions, foreign key referential integrity checks, and debit/credit sum parity validations.',
      currentVersion: '1.4.0',
      authorName: 'Marcus Vance',
      authorEmail: 'm.vance@akaaltech.corp',
      environmentTier: 'PRODUCTION',
      status: 'PUBLISHED',
      isSystemProvided: true,
      tags: ['DataQuality', 'Assertions', 'Finance', 'Completeness'],
      specPayload: JSON.stringify({
        severityThreshold: 'FATAL_ABORT_ON_FAILURE',
        checks: [
          { checkName: 'Debit Credit Equality Check', expression: 'SUM(debit_cents) == SUM(credit_cents)' },
          { checkName: 'No Null Account References', expression: 'account_id IS NOT NULL' },
          { checkName: 'Valid Currency ISO 4217', expression: 'currency_code IN ["USD", "EUR", "GBP", "JPY", "SGD"]' }
        ]
      }, null, 2),
      versions: [
        {
          version: '1.4.0',
          releaseDate: '2026-02-28',
          authorEmail: 'm.vance@akaaltech.corp',
          commitHash: 'git-993344b',
          changelog: 'Added strict currency code ISO 4217 validation enum.',
          breakingChanges: false,
          checksum: 'sha256-99881122aa...'
        }
      ],
      usages: [
        {
          id: 'use-006',
          consumerType: 'PIPELINE',
          consumerName: 'End-of-Day General Ledger Settlement Job',
          consumerScope: 'Workspace: Corporate Finance',
          boundVersion: '1.4.0',
          lastExecutionTimestamp: '2026-03-10 23:59 UTC',
          healthStatus: 'HEALTHY'
        }
      ],
      createdAt: '2025-06-25',
      updatedAt: '2026-02-28'
    },

    // 6. Configuration Profiles
    {
      id: 'tmpl-cfg-001',
      name: 'Ultra-High Throughput Distributed Execution Profile',
      code: 'UHT_DISTRIBUTED_EXEC_PROFILE',
      family: 'CONFIGURATION_PROFILE',
      category: 'Runtime Tuning',
      description: 'Configures JVM off-heap memory, 128 worker parallelism, buffer spill thresholds, and speculative task execution.',
      currentVersion: '2.1.0',
      authorName: 'Marcus Vance',
      authorEmail: 'm.vance@akaaltech.corp',
      environmentTier: 'PRODUCTION',
      status: 'PUBLISHED',
      isSystemProvided: true,
      tags: ['JVM', 'Performance', 'Cluster', 'OffHeap'],
      specPayload: JSON.stringify({
        executorCores: 8,
        executorMemoryMb: 32768,
        offHeapMemoryMb: 8192,
        parallelismFactor: 128,
        speculativeExecution: true,
        compressionCodec: 'ZSTD_LEVEL_3'
      }, null, 2),
      versions: [
        {
          version: '2.1.0',
          releaseDate: '2026-01-20',
          authorEmail: 'm.vance@akaaltech.corp',
          commitHash: 'git-332110c',
          changelog: 'Switched compression to ZSTD Level 3 for 25% faster disk I/O.',
          breakingChanges: false,
          checksum: 'sha256-77884411bb...'
        }
      ],
      usages: [
        {
          id: 'use-007',
          consumerType: 'ENVIRONMENT',
          consumerName: 'Prod EMEA Analytics Compute Cluster',
          consumerScope: 'Org: Global Parent Holding',
          boundVersion: '2.1.0',
          lastExecutionTimestamp: 'Active Right Now',
          healthStatus: 'HEALTHY'
        }
      ],
      createdAt: '2025-10-15',
      updatedAt: '2026-01-20'
    }
  ]);

  // Family Summaries
  public readonly familySummaries = computed<AssetFamilySummary[]>(() => {
    const list = this.assets();
    const families: { family: AssetFamily; title: string; desc: string; icon: string; route: string }[] = [
      {
        family: 'MIGRATION_TEMPLATE',
        title: 'Migration Templates',
        desc: 'DDL blueprints, database conversion rules, and CDC synchronization strategies.',
        icon: 'database',
        route: '/administration/templates-library/migration'
      },
      {
        family: 'MAPPING_TEMPLATE',
        title: 'Mapping Templates',
        desc: 'Field-level transformations, schema translations, and canonical domain mappings.',
        icon: 'git-fork',
        route: '/administration/templates-library/mapping'
      },
      {
        family: 'TRANSFORMATION_TEMPLATE',
        title: 'Transformation Templates',
        desc: 'Cleansing pipelines, regex parsing steps, and stream normalization recipes.',
        icon: 'shuffle',
        route: '/administration/templates-library/transformation'
      },
      {
        family: 'PRIVACY_POLICY',
        title: 'Privacy Policies',
        desc: 'PII masking, format-preserving encryption, tokenization, and hashing rules.',
        icon: 'shield-check',
        route: '/administration/templates-library/privacy'
      },
      {
        family: 'DATA_QUALITY_POLICY',
        title: 'Data Quality Policies',
        desc: 'Assertion tests, integrity gates, null constraints, and statistical anomaly checks.',
        icon: 'check-circle-2',
        route: '/administration/templates-library/quality'
      },
      {
        family: 'CONFIGURATION_PROFILE',
        title: 'Configuration Profiles',
        desc: 'Runtime memory tuning, cluster worker budgets, and execution parameters.',
        icon: 'sliders',
        route: '/administration/templates-library/configuration'
      }
    ];

    return families.map(f => {
      const familyAssets = list.filter(a => a.family === f.family);
      const totalUsages = familyAssets.reduce((acc, a) => acc + a.usages.length, 0);
      return {
        family: f.family,
        title: f.title,
        description: f.desc,
        icon: f.icon,
        routePath: f.route,
        totalAssetsCount: familyAssets.length,
        publishedCount: familyAssets.filter(a => a.status === 'PUBLISHED').length,
        deprecatedCount: familyAssets.filter(a => a.status === 'DEPRECATED').length,
        activeUsagesCount: totalUsages
      };
    });
  });

  public getAssetsByFamily(family: AssetFamily): TemplateAsset[] {
    return this.assets().filter(a => a.family === family);
  }

  public getAssetById(id: string): TemplateAsset | undefined {
    return this.assets().find(a => a.id === id);
  }

  public createAsset(data: Partial<TemplateAsset>): TemplateAsset {
    const newAsset: TemplateAsset = {
      id: 'tmpl-' + Date.now().toString(36),
      name: data.name || 'New Template Asset',
      code: (data.name || 'NEW_ASSET').toUpperCase().replace(/[^A-Z0-9]/g, '_'),
      family: data.family || 'MIGRATION_TEMPLATE',
      category: data.category || 'General',
      description: data.description || '',
      currentVersion: '1.0.0',
      authorName: data.authorName || 'Current Administrator',
      authorEmail: data.authorEmail || 'admin@akaaltech.corp',
      environmentTier: data.environmentTier || 'DEVELOPMENT',
      status: 'PUBLISHED',
      isSystemProvided: false,
      tags: data.tags || ['Custom'],
      specPayload: data.specPayload || '{\n  "version": "1.0.0"\n}',
      versions: [
        {
          version: '1.0.0',
          releaseDate: new Date().toISOString().split('T')[0],
          authorEmail: 'admin@akaaltech.corp',
          commitHash: 'git-init',
          changelog: 'Initial version creation.',
          breakingChanges: false,
          checksum: 'sha256-init'
        }
      ],
      usages: [],
      createdAt: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString().split('T')[0]
    };
    this.assets.update(list => [newAsset, ...list]);
    return newAsset;
  }

  public updateAsset(id: string, data: Partial<TemplateAsset>): void {
    this.assets.update(list =>
      list.map(a => (a.id === id ? { ...a, ...data, updatedAt: new Date().toISOString().split('T')[0] } : a))
    );
  }

  public promoteAsset(id: string, targetTier: PromotionTargetEnv): void {
    this.assets.update(list =>
      list.map(a =>
        a.id === id
          ? {
              ...a,
              environmentTier: targetTier,
              updatedAt: new Date().toISOString().split('T')[0]
            }
          : a
      )
    );
  }

  public deprecateAsset(id: string, reason: string, replacementId?: string): void {
    this.assets.update(list =>
      list.map(a =>
        a.id === id
          ? {
              ...a,
              status: 'DEPRECATED',
              deprecationNotice: {
                reason,
                targetReplacementAssetId: replacementId,
                effectiveEndOfLifeDate: '2026-12-31'
              },
              updatedAt: new Date().toISOString().split('T')[0]
            }
          : a
      )
    );
  }
}
