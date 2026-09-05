import { Injectable } from '@angular/core';
import { PhysicalProviderId, MigrationMode } from '../models/migration-view.models';
import {
  StandardProfileOption,
  ValidationOptionDescriptor,
  AdvancedGroupNavDescriptor,
  AdvancedFieldDescriptor,
  Step6ConfigurationDraft
} from '../../modules/migration/create/steps/step6-configuration.models';

/**
 * Step6ConfigurationAdapterService
 *
 * P7.D INTEGRATION BOUNDARY:
 * Provides declarative configuration descriptors, capability-driven provider options,
 * and canonical defaults for Step 6 Enterprise Configuration Center.
 *
 * When P7.D backend is connected, this service maps live IPC payloads
 * from akaalIPC.GetProposedConfiguration(draftId) into the frontend store.
 */
@Injectable({
  providedIn: 'root'
})
export class Step6ConfigurationAdapterService {

  /**
   * 8 Canonical Advanced Navigation Groups
   */
  public readonly advancedGroups: AdvancedGroupNavDescriptor[] = [
    {
      id: 'EXECUTION_RESOURCES',
      label: 'Execution & Resources',
      description: 'Worker concurrency, memory allocation, and CPU partitioning boundaries',
      icon: 'cpu'
    },
    {
      id: 'TRANSFER_BATCHING',
      label: 'Transfer & Batching',
      description: 'Network bandwidth throttle, chunk sizing, staging storage, and LOBs',
      icon: 'sliders-horizontal'
    },
    {
      id: 'RESILIENCE_RECOVERY',
      label: 'Resilience & Recovery',
      description: 'Checkpoint durable frequency, retry backoff, and error quarantine posture',
      icon: 'shield-check'
    },
    {
      id: 'MODE_CONFIG',
      label: 'Mode Configuration',
      description: 'Execution-mode parameters tailored to the active migration strategy',
      icon: 'activity'
    },
    {
      id: 'VALIDATION_RECON',
      label: 'Validation & Reconciliation',
      description: 'Checksum algorithm, verification coverage depth, and data audit tolerance',
      icon: 'check-circle-2'
    },
    {
      id: 'SCHEMA_ACTIONS',
      label: 'Schema & Execution Actions',
      description: 'Transactional DDL posture, index sequencing, and custom pre/post SQL hooks',
      icon: 'file-code'
    },
    {
      id: 'OBSERVABILITY_WINDOWS',
      label: 'Observability & Windows',
      description: 'Execution schedule window, maintenance blackouts, and telemetry thresholds',
      icon: 'clock'
    },
    {
      id: 'PROVIDER_OPTIONS',
      label: 'Provider Options',
      description: 'Native connector parameters for selected source and target engines',
      icon: 'database'
    }
  ];

  /**
   * Standard 3 Execution Profiles
   */
  public getStandardProfiles(
    mode: MigrationMode,
    source: PhysicalProviderId,
    target: PhysicalProviderId
  ): StandardProfileOption[] {
    return [
      {
        id: 'PROTECTIVE',
        title: 'Source Protective',
        description: 'Minimizes locking and CPU contention on live production database instances.',
        workers: 2,
        sourceImpact: 'Low / Non-blocking queries',
        targetImpact: 'Low / Throttle active',
        batching: 'Adaptive (8 MB chunks)',
        durability: 'Continuous Checkpoint'
      },
      {
        id: 'BALANCED',
        title: 'Balanced',
        badge: 'Recommended',
        description: 'Optimized throughput while maintaining predictable resource limits on both ends.',
        workers: 4,
        sourceImpact: 'Moderate / Balanced read slices',
        targetImpact: 'Moderate / Batched writes',
        batching: 'Adaptive (16 MB chunks)',
        durability: 'Standard Checkpoint'
      },
      {
        id: 'HIGH_THROUGHPUT',
        title: 'High Throughput',
        description: 'Maximizes transfer speed across all available network and disk channels.',
        workers: 8,
        sourceImpact: 'High / Parallel partition extraction',
        targetImpact: 'High / Direct buffer stream',
        batching: 'High-speed (64 MB chunks)',
        durability: 'Asynchronous Ingestion'
      }
    ];
  }

  /**
   * Standard 4 Validation Options
   */
  public getValidationOptions(mode: MigrationMode): ValidationOptionDescriptor[] {
    if (mode === 'M6_SCHEMA_ONLY') {
      return [
        {
          id: 'STRUCTURE_ONLY',
          title: 'Structure Only',
          badge: 'Recommended',
          description: 'Validates DDL syntax, constraint presence, object compilation, and permissions.',
          coverage: '100% schemas, tables, views, and procedural routines',
          relativeImpact: 'Low'
        },
        {
          id: 'FAST_FULL',
          title: 'Structural Checksum',
          description: 'Validates catalog schemas and compares compiled object hash signatures.',
          coverage: '100% catalog definitions',
          relativeImpact: 'Low'
        }
      ];
    }

    return [
      {
        id: 'FAST_FULL',
        title: 'Fast Full',
        badge: 'Recommended',
        description: 'Validates 100% row counts and table CRC32 checksums without reading every byte.',
        coverage: '100% scoped tables & row count parity',
        relativeImpact: 'Low'
      },
      {
        id: 'DETERMINISTIC_SAMPLE',
        title: 'Deterministic Sample',
        badge: 'Balanced',
        description: 'Performs statistical pseudo-random 5% row validation across all partition keys.',
        coverage: '5% sample of all records + boundary keys',
        relativeImpact: 'Moderate'
      },
      {
        id: 'EXACT_FULL',
        title: 'Exact Full',
        badge: 'Deep Audit',
        description: 'Full cryptographic SHA-256 validation across all column values and data types.',
        coverage: '100% data bytes & column values',
        relativeImpact: 'High'
      },
      {
        id: 'STRUCTURE_ONLY',
        title: 'Structure Only',
        description: 'Validates table schema, primary keys, and column data type mapping only.',
        coverage: 'Schema and constraint presence only',
        relativeImpact: 'Low'
      }
    ];
  }

  /**
   * Returns default configuration draft based on wizard context
   */
  public createDefaultDraft(
    mode: MigrationMode,
    source: PhysicalProviderId,
    target: PhysicalProviderId,
    environment: string
  ): Step6ConfigurationDraft {
    const isProd = environment === 'Production';

    return {
      depth: 'STANDARD',
      profile: 'BALANCED',
      bandwidthPolicy: 'UNLIMITED',
      bandwidthLimitValue: 100,
      bandwidthLimitUnit: 'MB/s',
      lobPolicy: 'AUTOMATIC',
      resourceImpact: 'BALANCED',
      recoveryPolicy: 'RESUME_CHECKPOINT',
      transientFailurePolicy: 'RETRY_BACKOFF',
      failedRecordsPolicy: isProd ? 'QUARANTINE_CONTINUE' : 'QUARANTINE_CONTINUE',
      
      modeM1: {
        partitionStrategy: 'AUTOMATIC',
        chunkSizeRows: 50000,
        directLoad: true,
        parallelWriters: 4
      },
      modeM2: {
        catchupLagTargetSec: 2,
        cutoverMaxLagSec: 5,
        conflictPolicy: 'LATEST_WINS',
        quiescenceTimeoutSec: 30,
        enableCdcBufferSpill: true
      },
      modeM3: {
        startPosition: 'IMMEDIATE',
        batchWindowMs: 500,
        applyConcurrency: 4,
        eventBufferMb: 256
      },
      modeM4: {
        watermarkColumn: 'UPDATED_AT',
        pollingIntervalSec: 60,
        lookbackWindowMin: 5,
        cursorPageSize: 10000
      },
      modeM5: {
        reconciliationMode: 'ONE_WAY_ALIGN',
        divergencePosture: 'REPAIR_TARGET',
        syncIntervalSec: 300,
        stateTolerancePercent: 0
      },
      modeM6: {
        transactionalDdl: true,
        fkIndexTiming: 'DEFERRED',
        routineValidation: 'STRICT',
        dropExistingObjects: false
      },
      modeM7: {
        targetReadiness: 'TRUNCATE',
        requireSchemaAttestation: true,
        batchCommitIntervalRows: 25000
      },

      validationDepth: mode === 'M6_SCHEMA_ONLY' ? 'STRUCTURE_ONLY' : 'FAST_FULL',
      executionWindowChoice: 'ANYTIME',
      executionWindowStart: '22:00',
      executionWindowEnd: '06:00',
      executionWindowDays: ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'],

      customActions: [],
      advancedOverrides: {}
    };
  }

  /**
   * Builds the comprehensive list of Advanced Fields partitioned by group.
   * Dynamically filters by migration mode, source provider, target provider, and environment.
   */
  public getAdvancedFieldDescriptors(
    mode: MigrationMode,
    source: PhysicalProviderId,
    target: PhysicalProviderId,
    environment: string,
    overrides: Record<string, any>
  ): AdvancedFieldDescriptor[] {
    const isProd = environment === 'Production';
    const fields: AdvancedFieldDescriptor[] = [];

    // =======================================================================
    // 1. EXECUTION & RESOURCES
    // =======================================================================
    fields.push(
      {
        id: 'workers_max',
        groupId: 'EXECUTION_RESOURCES',
        subGroup: 'Concurrency & Threads',
        label: 'Parallel Worker Count',
        description: 'Maximum number of concurrent migration executor threads for data extraction and loading.',
        type: 'number',
        defaultValue: 4,
        effectiveValue: overrides['workers_max'] ?? 4,
        isOverridden: 'workers_max' in overrides,
        provenance: 'workers_max' in overrides ? 'USER_OVERRIDE' : 'PRESET',
        min: 1,
        max: 32,
        unit: 'workers',
        isMaterialChange: true,
        materialChangeWarning: 'Changing worker thread count impacts parallel chunk partitioning in the compiled execution plan.'
      },
      {
        id: 'memory_max_mb',
        groupId: 'EXECUTION_RESOURCES',
        subGroup: 'Memory Management',
        label: 'Maximum Memory Budget',
        description: 'Total resident heap allocation threshold for staging buffers and transform queues.',
        type: 'number',
        defaultValue: isProd ? 4096 : 2048,
        effectiveValue: isProd ? 4096 : (overrides['memory_max_mb'] ?? 2048),
        isOverridden: !isProd && 'memory_max_mb' in overrides,
        provenance: isProd ? 'INHERITED_POLICY' : ('memory_max_mb' in overrides ? 'USER_OVERRIDE' : 'PRESET'),
        provenanceDetail: isProd ? 'Locked by Production governance policy (4 GB limit)' : 'Organization default',
        isPolicyLocked: isProd,
        policyLockReason: 'Production environment policy limits memory allocation to 4096 MB.',
        min: 512,
        max: 16384,
        unit: 'MB'
      },
      {
        id: 'source_max_connections',
        groupId: 'EXECUTION_RESOURCES',
        subGroup: 'Connection Pools',
        label: 'Source Pool Size',
        description: 'Maximum parallel read connections opened against the source instance.',
        type: 'number',
        defaultValue: 6,
        effectiveValue: overrides['source_max_connections'] ?? 6,
        isOverridden: 'source_max_connections' in overrides,
        provenance: 'source_max_connections' in overrides ? 'USER_OVERRIDE' : 'PRESET',
        min: 1,
        max: 64,
        unit: 'sessions'
      },
      {
        id: 'target_max_connections',
        groupId: 'EXECUTION_RESOURCES',
        subGroup: 'Connection Pools',
        label: 'Target Pool Size',
        description: 'Maximum parallel write connections opened against the target destination.',
        type: 'number',
        defaultValue: 8,
        effectiveValue: overrides['target_max_connections'] ?? 8,
        isOverridden: 'target_max_connections' in overrides,
        provenance: 'target_max_connections' in overrides ? 'USER_OVERRIDE' : 'PRESET',
        min: 1,
        max: 64,
        unit: 'sessions'
      }
    );

    // =======================================================================
    // 2. TRANSFER & BATCHING
    // =======================================================================
    fields.push(
      {
        id: 'batch_target_mb',
        groupId: 'TRANSFER_BATCHING',
        subGroup: 'Batch Sizing',
        label: 'Batch Chunk Buffer Size',
        description: 'Target memory buffer payload size before triggering a flush write to destination.',
        type: 'select',
        options: [
          { label: '8 MB — Low memory footprint', value: 8 },
          { label: '16 MB — Standard balanced', value: 16 },
          { label: '32 MB — High throughput', value: 32 },
          { label: '64 MB — High memory ingestion', value: 64 }
        ],
        defaultValue: 16,
        effectiveValue: overrides['batch_target_mb'] ?? 16,
        isOverridden: 'batch_target_mb' in overrides,
        provenance: 'batch_target_mb' in overrides ? 'USER_OVERRIDE' : 'PRESET'
      },
      {
        id: 'lob_threshold_kb',
        groupId: 'TRANSFER_BATCHING',
        subGroup: 'Large Objects',
        label: 'Inline LOB Threshold',
        description: 'BLOB/CLOB/JSON columns smaller than this limit are transferred inline with rows.',
        type: 'number',
        defaultValue: 64,
        effectiveValue: overrides['lob_threshold_kb'] ?? 64,
        isOverridden: 'lob_threshold_kb' in overrides,
        provenance: 'lob_threshold_kb' in overrides ? 'USER_OVERRIDE' : 'PRESET',
        min: 4,
        max: 1024,
        unit: 'KB'
      },
      {
        id: 'compression_level',
        groupId: 'TRANSFER_BATCHING',
        subGroup: 'Network Stream',
        label: 'Transfer Compression',
        description: 'In-transit payload compression algorithm used across WAN or VPC peer boundaries.',
        type: 'select',
        options: [
          { label: 'None — Raw binary streaming (LAN)', value: 'NONE' },
          { label: 'LZ4 — High speed, low CPU', value: 'LZ4' },
          { label: 'Zstandard (ZSTD) — High compression ratio', value: 'ZSTD' }
        ],
        defaultValue: 'LZ4',
        effectiveValue: overrides['compression_level'] ?? 'LZ4',
        isOverridden: 'compression_level' in overrides,
        provenance: 'compression_level' in overrides ? 'USER_OVERRIDE' : 'PRESET'
      }
    );

    // =======================================================================
    // 3. RESILIENCE & RECOVERY
    // =======================================================================
    fields.push(
      {
        id: 'max_retry_attempts',
        groupId: 'RESILIENCE_RECOVERY',
        subGroup: 'Transient Retries',
        label: 'Transient Error Max Retries',
        description: 'Maximum automated retry attempts for recoverable connection drops or deadlock errors.',
        type: 'number',
        defaultValue: 3,
        effectiveValue: overrides['max_retry_attempts'] ?? 3,
        isOverridden: 'max_retry_attempts' in overrides,
        provenance: 'max_retry_attempts' in overrides ? 'USER_OVERRIDE' : 'PRESET',
        min: 0,
        max: 10,
        unit: 'attempts'
      },
      {
        id: 'checkpoint_interval_sec',
        groupId: 'RESILIENCE_RECOVERY',
        subGroup: 'Durable Checkpointing',
        label: 'Checkpoint Sync Interval',
        description: 'Frequency at which completed row boundaries are persisted to durable WAL storage.',
        type: 'number',
        defaultValue: 10,
        effectiveValue: overrides['checkpoint_interval_sec'] ?? 10,
        isOverridden: 'checkpoint_interval_sec' in overrides,
        provenance: 'checkpoint_interval_sec' in overrides ? 'USER_OVERRIDE' : 'PRESET',
        min: 1,
        max: 60,
        unit: 'seconds'
      },
      {
        id: 'quarantine_max_errors',
        groupId: 'RESILIENCE_RECOVERY',
        subGroup: 'Error Quarantine',
        label: 'Max Quarantined Records',
        description: 'Maximum allowable malformed records quarantined before halting migration execution.',
        type: 'number',
        defaultValue: 1000,
        effectiveValue: overrides['quarantine_max_errors'] ?? 1000,
        isOverridden: 'quarantine_max_errors' in overrides,
        provenance: 'quarantine_max_errors' in overrides ? 'USER_OVERRIDE' : 'PRESET',
        min: 0,
        max: 100000,
        unit: 'records'
      }
    );

    // =======================================================================
    // 4. MODE CONFIGURATION (DYNAMIC BY CANONICAL MODE)
    // =======================================================================
    if (mode === 'M1_BULK') {
      fields.push(
        {
          id: 'm1_partition_strategy',
          groupId: 'MODE_CONFIG',
          subGroup: 'Bulk Partitioning',
          label: 'Table Partition Strategy',
          description: 'Slicing algorithm for dividing large tables across parallel reader workers.',
          type: 'select',
          options: [
            { label: 'Automatic — Provider optimized', value: 'AUTOMATIC' },
            { label: 'Hash Partitioning — Uniform distribution', value: 'HASH' },
            { label: 'Range Slicing — Primary key numerical boundaries', value: 'RANGE' }
          ],
          defaultValue: 'AUTOMATIC',
          effectiveValue: overrides['m1_partition_strategy'] ?? 'AUTOMATIC',
          isOverridden: 'm1_partition_strategy' in overrides,
          provenance: 'm1_partition_strategy' in overrides ? 'USER_OVERRIDE' : 'PRESET'
        },
        {
          id: 'm1_chunk_size',
          groupId: 'MODE_CONFIG',
          subGroup: 'Bulk Partitioning',
          label: 'Partition Chunk Size',
          description: 'Target row count per parallel slice.',
          type: 'number',
          defaultValue: 50000,
          effectiveValue: overrides['m1_chunk_size'] ?? 50000,
          isOverridden: 'm1_chunk_size' in overrides,
          provenance: 'm1_chunk_size' in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 1000,
          max: 1000000,
          unit: 'rows'
        }
      );
    } else if (mode === 'M2_BULK_CDC') {
      fields.push(
        {
          id: 'm2_catchup_lag_target',
          groupId: 'MODE_CONFIG',
          subGroup: 'Catch-up & Cutover',
          label: 'Catch-up Lag Objective',
          description: 'CDC replication latency threshold required before declaring the migration ready for cutover.',
          type: 'number',
          defaultValue: 2,
          effectiveValue: overrides['m2_catchup_lag_target'] ?? 2,
          isOverridden: 'm2_catchup_lag_target' in overrides,
          provenance: 'm2_catchup_lag_target' in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 1,
          max: 60,
          unit: 'seconds',
          isMaterialChange: true,
          materialChangeWarning: 'Cutover SLA objective modifies the readiness barrier gates in Step 8.'
        },
        {
          id: 'm2_conflict_policy',
          groupId: 'MODE_CONFIG',
          subGroup: 'Change Capture Apply',
          label: 'CDC Conflict Resolution',
          description: 'Determines behavior when an incoming CDC event collides with existing destination row state.',
          type: 'select',
          options: [
            { label: 'Latest Timestamp Wins — Source commit timestamp', value: 'LATEST_WINS' },
            { label: 'Source Overwrite — Force overwrite target', value: 'SOURCE_WINS' },
            { label: 'Fail on Conflict — Quarantine and halt', value: 'FAIL_ON_CONFLICT' }
          ],
          defaultValue: 'LATEST_WINS',
          effectiveValue: overrides['m2_conflict_policy'] ?? 'LATEST_WINS',
          isOverridden: 'm2_conflict_policy' in overrides,
          provenance: 'm2_conflict_policy' in overrides ? 'USER_OVERRIDE' : 'PRESET'
        },
        {
          id: 'm2_quiescence_timeout',
          groupId: 'MODE_CONFIG',
          subGroup: 'Catch-up & Cutover',
          label: 'Quiescence Verification Timeout',
          description: 'Maximum time to wait for source transaction silence during final cutover window.',
          type: 'number',
          defaultValue: 30,
          effectiveValue: overrides['m2_quiescence_timeout'] ?? 30,
          isOverridden: 'm2_quiescence_timeout' in overrides,
          provenance: 'm2_quiescence_timeout' in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 5,
          max: 300,
          unit: 'seconds'
        }
      );
    } else if (mode === 'M3_CDC') {
      fields.push(
        {
          id: 'm3_start_pos',
          groupId: 'MODE_CONFIG',
          subGroup: 'Stream Position',
          label: 'CDC Stream Start Position',
          description: 'Point in transaction log history from which replication begins.',
          type: 'select',
          options: [
            { label: 'Immediate — Current live log tail', value: 'IMMEDIATE' },
            { label: 'Current SCN / LSN — Exact log sequence number at launch', value: 'CURRENT_SCN' },
            { label: 'Specific Timestamp — Historical point-in-time replay', value: 'TIMESTAMP' }
          ],
          defaultValue: 'IMMEDIATE',
          effectiveValue: overrides['m3_start_pos'] ?? 'IMMEDIATE',
          isOverridden: 'm3_start_pos' in overrides,
          provenance: 'm3_start_pos' in overrides ? 'USER_OVERRIDE' : 'PRESET'
        },
        {
          id: 'm3_batch_window_ms',
          groupId: 'MODE_CONFIG',
          subGroup: 'Stream Batching',
          label: 'Apply Micro-batch Window',
          description: 'Maximum micro-batch buffering time before committing CDC transactions to target.',
          type: 'number',
          defaultValue: 500,
          effectiveValue: overrides['m3_batch_window_ms'] ?? 500,
          isOverridden: 'm3_batch_window_ms' in overrides,
          provenance: 'm3_batch_window_ms' in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 50,
          max: 5000,
          unit: 'ms'
        }
      );
    } else if (mode === 'M4_INCREMENTAL') {
      fields.push(
        {
          id: 'm4_polling_interval_sec',
          groupId: 'MODE_CONFIG',
          subGroup: 'Query Polling',
          label: 'Incremental Query Polling Interval',
          description: 'Interval between periodic query executions checking for modified watermark timestamps.',
          type: 'number',
          defaultValue: 60,
          effectiveValue: overrides['m4_polling_interval_sec'] ?? 60,
          isOverridden: 'm4_polling_interval_sec' in overrides,
          provenance: 'm4_polling_interval_sec' in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 5,
          max: 3600,
          unit: 'seconds'
        },
        {
          id: 'm4_lookback_min',
          groupId: 'MODE_CONFIG',
          subGroup: 'Query Polling',
          label: 'Late-Arrival Lookback Window',
          description: 'Time window subtracted from high watermark to guarantee capture of out-of-order commits.',
          type: 'number',
          defaultValue: 5,
          effectiveValue: overrides['m4_lookback_min'] ?? 5,
          isOverridden: 'm4_lookback_min' in overrides,
          provenance: 'm4_lookback_min' in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 0,
          max: 120,
          unit: 'minutes'
        }
      );
    } else if (mode === 'M5_STATE_SYNC') {
      fields.push(
        {
          id: 'm5_reconciliation_mode',
          groupId: 'MODE_CONFIG',
          subGroup: 'State Sync Policy',
          label: 'State Synchronization Mode',
          description: 'Reconciliation strategy when hash tree comparison discovers discrepancies.',
          type: 'select',
          options: [
            { label: 'One-Way Align — Target reconciled to match source state', value: 'ONE_WAY_ALIGN' },
            { label: 'Bidirectional Audit — Report divergence without auto-repair', value: 'BIDIRECTIONAL_REPORT' }
          ],
          defaultValue: 'ONE_WAY_ALIGN',
          effectiveValue: overrides['m5_reconciliation_mode'] ?? 'ONE_WAY_ALIGN',
          isOverridden: 'm5_reconciliation_mode' in overrides,
          provenance: 'm5_reconciliation_mode' in overrides ? 'USER_OVERRIDE' : 'PRESET'
        },
        {
          id: 'm5_sync_interval_sec',
          groupId: 'MODE_CONFIG',
          subGroup: 'State Sync Policy',
          label: 'Periodic Re-comparison Cadence',
          description: 'Frequency of automated Merkle-tree state comparison rounds.',
          type: 'number',
          defaultValue: 300,
          effectiveValue: overrides['m5_sync_interval_sec'] ?? 300,
          isOverridden: 'm5_sync_interval_sec' in overrides,
          provenance: 'm5_sync_interval_sec' in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 30,
          max: 86400,
          unit: 'seconds'
        }
      );
    } else if (mode === 'M6_SCHEMA_ONLY') {
      fields.push(
        {
          id: 'm6_transactional_ddl',
          groupId: 'MODE_CONFIG',
          subGroup: 'DDL Safety',
          label: 'Transactional DDL Execution',
          description: 'Wraps schema object creation inside atomic transactions where target engine permits.',
          type: 'select',
          options: [
            { label: 'Enabled — Atomic rollback on DDL failure', value: 'true' },
            { label: 'Disabled — Continue on non-fatal object warning', value: 'false' }
          ],
          defaultValue: 'true',
          effectiveValue: overrides['m6_transactional_ddl'] ?? 'true',
          isOverridden: 'm6_transactional_ddl' in overrides,
          provenance: 'm6_transactional_ddl' in overrides ? 'USER_OVERRIDE' : 'PRESET'
        },
        {
          id: 'm6_fk_timing',
          groupId: 'MODE_CONFIG',
          subGroup: 'DDL Safety',
          label: 'Foreign Key & Index Creation Timing',
          description: 'Timing of secondary constraint creation relative to primary table definitions.',
          type: 'select',
          options: [
            { label: 'Deferred — Build constraints after all tables exist', value: 'DEFERRED' },
            { label: 'Inline — Build constraints concurrently with table creation', value: 'INLINE' }
          ],
          defaultValue: 'DEFERRED',
          effectiveValue: overrides['m6_fk_timing'] ?? 'DEFERRED',
          isOverridden: 'm6_fk_timing' in overrides,
          provenance: 'm6_fk_timing' in overrides ? 'USER_OVERRIDE' : 'PRESET'
        }
      );
    } else if (mode === 'M7_DATA_ONLY') {
      fields.push(
        {
          id: 'm7_target_readiness',
          groupId: 'MODE_CONFIG',
          subGroup: 'Data Load Posture',
          label: 'Target Pre-existing Data Policy',
          description: 'Behavior when writing into existing destination tables with pre-existing rows.',
          type: 'select',
          options: [
            { label: 'Truncate — Clean target tables before loading', value: 'TRUNCATE' },
            { label: 'Append — Retain existing records and insert incoming', value: 'APPEND' },
            { label: 'Upsert / Merge — Update matching primary keys', value: 'UPSERT' }
          ],
          defaultValue: 'TRUNCATE',
          effectiveValue: overrides['m7_target_readiness'] ?? 'TRUNCATE',
          isOverridden: 'm7_target_readiness' in overrides,
          provenance: 'm7_target_readiness' in overrides ? 'USER_OVERRIDE' : 'PRESET'
        },
        {
          id: 'm7_schema_attestation',
          groupId: 'MODE_CONFIG',
          subGroup: 'Data Load Posture',
          label: 'Pre-load Schema Verification',
          description: 'Validates target column types and table presence before initiating bulk payload transfer.',
          type: 'select',
          options: [
            { label: 'Strict — Require exact 1-to-1 schema matching', value: 'true' },
            { label: 'Permissive — Coerce compatible column types', value: 'false' }
          ],
          defaultValue: 'true',
          effectiveValue: overrides['m7_schema_attestation'] ?? 'true',
          isOverridden: 'm7_schema_attestation' in overrides,
          provenance: 'm7_schema_attestation' in overrides ? 'USER_OVERRIDE' : 'PRESET'
        }
      );
    }

    // =======================================================================
    // 5. VALIDATION & RECONCILIATION
    // =======================================================================
    fields.push(
      {
        id: 'validation_checksum_algo',
        groupId: 'VALIDATION_RECON',
        subGroup: 'Hash & Checksum',
        label: 'Checksum Algorithm',
        description: 'Cryptographic hashing algorithm utilized for row and block parity verification.',
        type: 'select',
        options: [
          { label: 'CRC32 — High speed, hardware accelerated', value: 'CRC32' },
          { label: 'XXH64 (xxHash) — Extremely fast 64-bit hash', value: 'XXH64' },
          { label: 'SHA-256 — Cryptographic compliance standard', value: 'SHA256' }
        ],
        defaultValue: 'CRC32',
        effectiveValue: overrides['validation_checksum_algo'] ?? 'CRC32',
        isOverridden: 'validation_checksum_algo' in overrides,
        provenance: 'validation_checksum_algo' in overrides ? 'USER_OVERRIDE' : 'PRESET'
      },
      {
        id: 'validation_sample_pct',
        groupId: 'VALIDATION_RECON',
        subGroup: 'Sampling Policy',
        label: 'Deterministic Sample Percentage',
        description: 'Percentage of rows audited during sample-based assurance runs.',
        type: 'number',
        defaultValue: 5,
        effectiveValue: overrides['validation_sample_pct'] ?? 5,
        isOverridden: 'validation_sample_pct' in overrides,
        provenance: 'validation_sample_pct' in overrides ? 'USER_OVERRIDE' : 'PRESET',
        min: 1,
        max: 50,
        unit: '%'
      }
    );

    // =======================================================================
    // 6. SCHEMA & EXECUTION ACTIONS
    // =======================================================================
    fields.push(
      {
        id: 'disable_indexes_bulk',
        groupId: 'SCHEMA_ACTIONS',
        subGroup: 'Index Optimization',
        label: 'Drop Secondary Indexes During Bulk',
        description: 'Temporarily drops non-unique secondary indexes on target and rebuilds them after bulk load completes.',
        type: 'select',
        options: [
          { label: 'Enabled — Recommended for 3x-5x faster bulk ingestion', value: 'true' },
          { label: 'Disabled — Keep indexes intact during loading', value: 'false' }
        ],
        defaultValue: 'true',
        effectiveValue: overrides['disable_indexes_bulk'] ?? 'true',
        isOverridden: 'disable_indexes_bulk' in overrides,
        provenance: 'disable_indexes_bulk' in overrides ? 'USER_OVERRIDE' : 'PRESET'
      },
      {
        id: 'defer_foreign_keys',
        groupId: 'SCHEMA_ACTIONS',
        subGroup: 'Foreign Key Timing',
        label: 'Defer Foreign Key Constraints',
        description: 'Disables foreign key verification during bulk data transport and validates referential integrity in batch.',
        type: 'select',
        options: [
          { label: 'Enabled — Allows out-of-order parallel table transfer', value: 'true' },
          { label: 'Disabled — Strict parent-first hierarchical transfer', value: 'false' }
        ],
        defaultValue: 'true',
        effectiveValue: overrides['defer_foreign_keys'] ?? 'true',
        isOverridden: 'defer_foreign_keys' in overrides,
        provenance: 'defer_foreign_keys' in overrides ? 'USER_OVERRIDE' : 'PRESET'
      }
    );

    // =======================================================================
    // 7. OBSERVABILITY & WINDOWS
    // =======================================================================
    fields.push(
      {
        id: 'telemetry_metrics_interval',
        groupId: 'OBSERVABILITY_WINDOWS',
        subGroup: 'Telemetry & Progress',
        label: 'Metrics Reporting Frequency',
        description: 'Interval for publishing live throughput (rows/sec) and CDC replication lag metrics.',
        type: 'number',
        defaultValue: 5,
        effectiveValue: overrides['telemetry_metrics_interval'] ?? 5,
        isOverridden: 'telemetry_metrics_interval' in overrides,
        provenance: 'telemetry_metrics_interval' in overrides ? 'USER_OVERRIDE' : 'PRESET',
        min: 1,
        max: 60,
        unit: 'seconds'
      },
      {
        id: 'stall_detection_timeout',
        groupId: 'OBSERVABILITY_WINDOWS',
        subGroup: 'Stall Detection',
        label: 'Stall Alert Threshold',
        description: 'Time elapsed without pipeline forward progress before raising a stalled health warning.',
        type: 'number',
        defaultValue: 180,
        effectiveValue: overrides['stall_detection_timeout'] ?? 180,
        isOverridden: 'stall_detection_timeout' in overrides,
        provenance: 'stall_detection_timeout' in overrides ? 'USER_OVERRIDE' : 'PRESET',
        min: 30,
        max: 1800,
        unit: 'seconds'
      }
    );

    // =======================================================================
    // 8. PROVIDER OPTIONS (DYNAMIC FOR SOURCE & TARGET ENGINES)
    // =======================================================================
    // Source Provider Options
    this.appendProviderFields(fields, source, 'SOURCE', overrides);
    // Target Provider Options
    this.appendProviderFields(fields, target, 'TARGET', overrides);

    return fields;
  }

  /**
   * Appends provider-specific native parameters cleanly without hardcoding 28 huge components.
   */
  private appendProviderFields(
    fields: AdvancedFieldDescriptor[],
    provider: PhysicalProviderId,
    endpoint: 'SOURCE' | 'TARGET',
    overrides: Record<string, any>
  ): void {
    const prefix = `${endpoint.toLowerCase()}_${provider.toLowerCase().replace(/[^a-z0-9]/g, '_')}`;

    if (provider === 'Oracle' || provider === 'Oracle Database') {
      fields.push(
        {
          id: `${prefix}_logminer_batch`,
          groupId: 'PROVIDER_OPTIONS',
          providerEndpoint: endpoint,
          providerName: 'Oracle Database',
          subGroup: `${endpoint} · Oracle Specifics`,
          label: endpoint === 'SOURCE' ? 'LogMiner Event Batch Size' : 'Direct Path Load Batch',
          description: endpoint === 'SOURCE'
            ? 'Number of redo log records parsed per LogMiner dictionary session batch.'
            : 'Number of rows sent in single OCI direct-path insert array.',
          type: 'number',
          defaultValue: 10000,
          effectiveValue: overrides[`${prefix}_logminer_batch`] ?? 10000,
          isOverridden: `${prefix}_logminer_batch` in overrides,
          provenance: `${prefix}_logminer_batch` in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 1000,
          max: 100000,
          unit: 'rows'
        },
        {
          id: `${prefix}_scn_headroom`,
          groupId: 'PROVIDER_OPTIONS',
          providerEndpoint: endpoint,
          providerName: 'Oracle Database',
          subGroup: `${endpoint} · Oracle Specifics`,
          label: 'Flashback Query SCN Retention',
          description: 'Retention tolerance for Flashback consistent snapshot queries during active DML.',
          type: 'number',
          defaultValue: 180,
          effectiveValue: overrides[`${prefix}_scn_headroom`] ?? 180,
          isOverridden: `${prefix}_scn_headroom` in overrides,
          provenance: `${prefix}_scn_headroom` in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 15,
          max: 1440,
          unit: 'minutes'
        }
      );
    } else if (provider === 'PostgreSQL' || provider === 'CockroachDB' || provider === 'YugabyteDB') {
      fields.push(
        {
          id: `${prefix}_session_repl_role`,
          groupId: 'PROVIDER_OPTIONS',
          providerEndpoint: endpoint,
          providerName: 'PostgreSQL',
          subGroup: `${endpoint} · PostgreSQL Specifics`,
          label: 'Session Replication Role',
          description: 'Controls trigger and rule firing during table write operations.',
          type: 'select',
          options: [
            { label: 'replica — Bypass user triggers and foreign key triggers during import', value: 'replica' },
            { label: 'origin — Normal operation (all triggers active)', value: 'origin' }
          ],
          defaultValue: 'replica',
          effectiveValue: overrides[`${prefix}_session_repl_role`] ?? 'replica',
          isOverridden: `${prefix}_session_repl_role` in overrides,
          provenance: `${prefix}_session_repl_role` in overrides ? 'USER_OVERRIDE' : 'PRESET'
        },
        {
          id: `${prefix}_copy_batch_size`,
          groupId: 'PROVIDER_OPTIONS',
          providerEndpoint: endpoint,
          providerName: 'PostgreSQL',
          subGroup: `${endpoint} · PostgreSQL Specifics`,
          label: 'COPY Protocol Batch Rows',
          description: 'Streaming batch buffer size for binary PostgreSQL COPY ingestion API.',
          type: 'number',
          defaultValue: 25000,
          effectiveValue: overrides[`${prefix}_copy_batch_size`] ?? 25000,
          isOverridden: `${prefix}_copy_batch_size` in overrides,
          provenance: `${prefix}_copy_batch_size` in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 1000,
          max: 100000,
          unit: 'rows'
        }
      );
    } else if (provider === 'MongoDB') {
      fields.push(
        {
          id: `${prefix}_oplog_batch_size`,
          groupId: 'PROVIDER_OPTIONS',
          providerEndpoint: endpoint,
          providerName: 'MongoDB',
          subGroup: `${endpoint} · MongoDB Specifics`,
          label: 'Change Stream / Oplog Batch Size',
          description: 'BSON document buffer window for change stream watcher cursor.',
          type: 'number',
          defaultValue: 1000,
          effectiveValue: overrides[`${prefix}_oplog_batch_size`] ?? 1000,
          isOverridden: `${prefix}_oplog_batch_size` in overrides,
          provenance: `${prefix}_oplog_batch_size` in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 100,
          max: 10000,
          unit: 'docs'
        }
      );
    } else if (provider === 'Apache Kafka') {
      fields.push(
        {
          id: `${prefix}_max_poll_records`,
          groupId: 'PROVIDER_OPTIONS',
          providerEndpoint: endpoint,
          providerName: 'Apache Kafka',
          subGroup: `${endpoint} · Kafka Specifics`,
          label: 'Max Poll Records',
          description: 'Maximum records returned in a single consumer poll loop invocation.',
          type: 'number',
          defaultValue: 500,
          effectiveValue: overrides[`${prefix}_max_poll_records`] ?? 500,
          isOverridden: `${prefix}_max_poll_records` in overrides,
          provenance: `${prefix}_max_poll_records` in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 50,
          max: 10000,
          unit: 'records'
        }
      );
    } else if (provider === 'Amazon S3' || provider === 'Google Cloud Storage' || provider === 'Azure Blob Storage') {
      fields.push(
        {
          id: `${prefix}_multipart_chunk_mb`,
          groupId: 'PROVIDER_OPTIONS',
          providerEndpoint: endpoint,
          providerName: provider,
          subGroup: `${endpoint} · Object Storage Specifics`,
          label: 'Multipart Chunk Size',
          description: 'Part size for parallel multipart uploads to cloud object storage.',
          type: 'number',
          defaultValue: 64,
          effectiveValue: overrides[`${prefix}_multipart_chunk_mb`] ?? 64,
          isOverridden: `${prefix}_multipart_chunk_mb` in overrides,
          provenance: `${prefix}_multipart_chunk_mb` in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 8,
          max: 512,
          unit: 'MB'
        }
      );
    } else {
      // Generic Provider Fallback for other providers in 28-catalog
      fields.push(
        {
          id: `${prefix}_fetch_size`,
          groupId: 'PROVIDER_OPTIONS',
          providerEndpoint: endpoint,
          providerName: provider,
          subGroup: `${endpoint} · ${provider} Specifics`,
          label: `${provider} Ingestion Buffer`,
          description: `Native batch row allocation for ${provider} connector interface.`,
          type: 'number',
          defaultValue: 10000,
          effectiveValue: overrides[`${prefix}_fetch_size`] ?? 10000,
          isOverridden: `${prefix}_fetch_size` in overrides,
          provenance: `${prefix}_fetch_size` in overrides ? 'USER_OVERRIDE' : 'PRESET',
          min: 1000,
          max: 100000,
          unit: 'rows'
        }
      );
    }
  }
}
