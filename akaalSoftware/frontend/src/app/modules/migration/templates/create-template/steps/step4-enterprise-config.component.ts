import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateTemplateService } from '../create-template.service';
import {
  ErrorHandlingPolicy,
  CdcEngineType,
  StreamHandoffPolicy,
  ConflictResolutionPolicy,
  ForeignKeyOrderPolicy,
  SampleHashRate
} from '../create-template.models';
import { TEMPLATE_MODE_DESCRIPTORS } from '../../templates.models';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-step4-enterprise-config',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="space-y-6 animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- Top Section Header -->
      <div class="flex flex-col gap-1 border-b border-slate-200 pb-3">
        <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">Enterprise Configuration</h2>
        <p class="text-xs text-slate-500 font-normal">
          Configure runtime performance concurrency, fault-tolerant checkpointing, mode-specific engine tuning, and migration-side verification presets.
        </p>
      </div>

      <!-- SECTION 1: PERFORMANCE & CONCURRENCY -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3.5 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <span class="font-bold text-slate-900">Performance & Concurrency Tuning</span>
          <span class="text-[10px] text-slate-400">Worker resource limits</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          
          <!-- Parallel Extract Threads -->
          <div class="flex flex-col gap-1.5">
            <label for="extract-threads" class="font-semibold text-slate-800">Parallel Extract Threads</label>
            <input
              id="extract-threads"
              type="number"
              min="1"
              max="32"
              [ngModel]="ts.enterpriseConfig().performance.extractThreads"
              (ngModelChange)="updatePerformance({ extractThreads: +$event })"
              class="h-9 px-3 bg-slate-50 border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 focus:outline-none" />
            <span class="text-[10px] text-slate-400">Concurrent table extract workers (1–32)</span>
          </div>

          <!-- Batch Size -->
          <div class="flex flex-col gap-1.5">
            <label for="batch-size" class="font-semibold text-slate-800">Batch Size (Rows)</label>
            <input
              id="batch-size"
              type="number"
              min="100"
              max="100000"
              step="1000"
              [ngModel]="ts.enterpriseConfig().performance.batchSize"
              (ngModelChange)="updatePerformance({ batchSize: +$event })"
              class="h-9 px-3 bg-slate-50 border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 focus:outline-none" />
            <span class="text-[10px] text-slate-400">Rows committed per chunk</span>
          </div>

          <!-- Buffer Memory Allocation -->
          <div class="flex flex-col gap-1.5">
            <label for="buffer-mem" class="font-semibold text-slate-800">Buffer Memory (MB)</label>
            <input
              id="buffer-mem"
              type="number"
              min="256"
              max="16384"
              step="256"
              [ngModel]="ts.enterpriseConfig().performance.bufferMemoryMb"
              (ngModelChange)="updatePerformance({ bufferMemoryMb: +$event })"
              class="h-9 px-3 bg-slate-50 border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 focus:outline-none" />
            <span class="text-[10px] text-slate-400">In-memory ring buffer threshold</span>
          </div>

          <!-- Max Throughput Limit -->
          <div class="flex flex-col gap-1.5">
            <label for="max-throughput" class="font-semibold text-slate-800">Max Throughput Cap</label>
            <input
              id="max-throughput"
              type="number"
              min="0"
              max="10000"
              step="50"
              [ngModel]="ts.enterpriseConfig().performance.maxThroughputMbps"
              (ngModelChange)="updatePerformance({ maxThroughputMbps: +$event })"
              class="h-9 px-3 bg-slate-50 border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 focus:outline-none" />
            <span class="text-[10px] text-slate-400">MB/s rate limit (0 = Unlimited)</span>
          </div>

        </div>
      </div>

      <!-- SECTION 2: CHECKPOINTING & FAULT RECOVERY (Using GDS Custom Select) -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3.5 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <span class="font-bold text-slate-900">Checkpointing & Fault Recovery</span>
          <span class="text-[10px] text-slate-400">Idempotency & Retry</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          <!-- Checkpoint Frequency -->
          <div class="flex flex-col gap-1.5">
            <label for="commit-interval-rows" class="font-semibold text-slate-800">Commit Frequency (Rows)</label>
            <input
              id="commit-interval-rows"
              type="number"
              min="1000"
              max="500000"
              step="5000"
              [ngModel]="ts.enterpriseConfig().checkpointRecovery.commitIntervalRows"
              (ngModelChange)="updateCheckpoint({ commitIntervalRows: +$event })"
              class="h-9 px-3 bg-slate-50 border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 focus:outline-none" />
            <span class="text-[10px] text-slate-400">Commit and checkpoint state every N rows</span>
          </div>

          <!-- Automatic Retry Count -->
          <div class="flex flex-col gap-1.5">
            <label for="retry-count" class="font-semibold text-slate-800">Auto Retry Attempts</label>
            <input
              id="retry-count"
              type="number"
              min="0"
              max="10"
              [ngModel]="ts.enterpriseConfig().checkpointRecovery.retryCount"
              (ngModelChange)="updateCheckpoint({ retryCount: +$event })"
              class="h-9 px-3 bg-slate-50 border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 focus:outline-none" />
            <span class="text-[10px] text-slate-400">Exponential backoff retries on network drops</span>
          </div>

          <!-- Error Handling Policy (GDS Custom Select) -->
          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-800">Error Handling Policy</label>
            <app-custom-select
              [options]="errorHandlingOptions"
              [ngModel]="ts.enterpriseConfig().checkpointRecovery.errorHandlingPolicy"
              (ngModelChange)="updateCheckpoint({ errorHandlingPolicy: $event })">
            </app-custom-select>
            <span class="text-[10px] text-slate-400">Dead-letter queue isolation policy</span>
          </div>

        </div>
      </div>

      <!-- SECTION 3: MODE-SPECIFIC DYNAMIC CONFIGURATION -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3.5 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex items-center gap-2">
            <span class="font-bold text-slate-900">Mode-Specific Engine Tuning</span>
            <span class="px-2 py-0.5 text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 rounded-md">
              {{ currentModeLabel() }}
            </span>
          </div>
          <span class="text-[10px] text-slate-400">Adapts to Step 1 mode selection</span>
        </div>

        <!-- M2 (Bulk + CDC) or M3 (CDC Only) -->
        @if (ts.definition().mode === 'M2_BULK_CDC' || ts.definition().mode === 'M3_CDC') {
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-in fade-in duration-100">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-800">CDC Extraction Engine</label>
              <app-custom-select
                [options]="cdcEngineOptions"
                [ngModel]="ts.enterpriseConfig().cdcConfig.cdcEngine"
                (ngModelChange)="updateCdc({ cdcEngine: $event })">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1.5">
              <label for="max-lag-alert" class="font-semibold text-slate-800">Max Replication Lag Alert</label>
              <input
                id="max-lag-alert"
                type="number"
                min="5"
                max="3600"
                step="5"
                [ngModel]="ts.enterpriseConfig().cdcConfig.maxLagAlertSec"
                (ngModelChange)="updateCdc({ maxLagAlertSec: +$event })"
                class="h-9 px-3 bg-slate-50 border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 focus:outline-none" />
              <span class="text-[10px] text-slate-400">Seconds before raising latency alert</span>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-800">Snapshot-to-Stream Handoff</label>
              <app-custom-select
                [options]="handoffOptions"
                [ngModel]="ts.enterpriseConfig().cdcConfig.snapshotToStreamHandoff"
                (ngModelChange)="updateCdc({ snapshotToStreamHandoff: $event })">
              </app-custom-select>
            </div>

            <div class="flex flex-col justify-end">
              <label class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  [checked]="ts.enterpriseConfig().cdcConfig.heartbeatTracking"
                  (change)="toggleCdcHeartbeat()"
                  class="rounded text-blue-600 focus:ring-0" />
                <div class="flex flex-col">
                  <span class="font-bold text-slate-800">Heartbeat Table</span>
                  <span class="text-[10px] text-slate-500">Inject LSN heartbeat signals</span>
                </div>
              </label>
            </div>
          </div>
        }

        <!-- M4 (Incremental / Polling) -->
        @if (ts.definition().mode === 'M4_INCREMENTAL') {
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 animate-in fade-in duration-100">
            <div class="flex flex-col gap-1.5">
              <label for="watermark-column" class="font-semibold text-slate-800">Watermark Column Pattern</label>
              <input
                id="watermark-column"
                type="text"
                [ngModel]="ts.enterpriseConfig().incrementalConfig.watermarkColumn"
                (ngModelChange)="updateIncremental({ watermarkColumn: $event })"
                placeholder="e.g., updated_at, modified_time"
                class="h-9 px-3 bg-slate-50 border border-slate-200 focus:border-blue-600 rounded-md text-xs font-mono text-slate-900 focus:outline-none" />
              <span class="text-[10px] text-slate-400">Timestamp column for delta polling</span>
            </div>

            <div class="flex flex-col gap-1.5">
              <label for="polling-interval" class="font-semibold text-slate-800">Polling Interval (Seconds)</label>
              <input
                id="polling-interval"
                type="number"
                min="10"
                max="86400"
                step="30"
                [ngModel]="ts.enterpriseConfig().incrementalConfig.pollingIntervalSec"
                (ngModelChange)="updateIncremental({ pollingIntervalSec: +$event })"
                class="h-9 px-3 bg-slate-50 border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 focus:outline-none" />
              <span class="text-[10px] text-slate-400">Frequency of batch delta queries</span>
            </div>

            <div class="flex flex-col gap-1.5">
              <label for="lookback-window" class="font-semibold text-slate-800">Lookback Overlap (Minutes)</label>
              <input
                id="lookback-window"
                type="number"
                min="0"
                max="1440"
                step="5"
                [ngModel]="ts.enterpriseConfig().incrementalConfig.lookbackWindowMinutes"
                (ngModelChange)="updateIncremental({ lookbackWindowMinutes: +$event })"
                class="h-9 px-3 bg-slate-50 border border-slate-200 focus:border-blue-600 rounded-md text-xs font-medium text-slate-900 focus:outline-none" />
              <span class="text-[10px] text-slate-400">Safety margin to catch out-of-order writes</span>
            </div>
          </div>
        }

        <!-- M5 (State Sync) -->
        @if (ts.definition().mode === 'M5_STATE_SYNC') {
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 animate-in fade-in duration-100">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-800">Conflict Resolution Strategy</label>
              <app-custom-select
                [options]="conflictResolutionOptions"
                [ngModel]="ts.enterpriseConfig().stateSyncConfig.conflictResolution"
                (ngModelChange)="updateStateSync({ conflictResolution: $event })">
              </app-custom-select>
              <span class="text-[10px] text-slate-400">Policy applied when primary keys collide</span>
            </div>

            <div class="flex flex-col justify-end">
              <label class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  [checked]="ts.enterpriseConfig().stateSyncConfig.biDirectionalEnabled"
                  (change)="toggleStateSyncBiDirectional()"
                  class="rounded text-blue-600 focus:ring-0" />
                <div class="flex flex-col">
                  <span class="font-bold text-slate-800">Bi-Directional Synchronization</span>
                  <span class="text-[10px] text-slate-500">Replicate deltas bi-directionally between source and target</span>
                </div>
              </label>
            </div>
          </div>
        }

        <!-- M6 (Schema Only) -->
        @if (ts.definition().mode === 'M6_SCHEMA_ONLY') {
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 animate-in fade-in duration-100">
            <label class="p-3 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                [checked]="ts.enterpriseConfig().schemaOnlyConfig.dropTargetObjectsFirst"
                (change)="toggleSchemaDrop()"
                class="rounded text-blue-600 focus:ring-0" />
              <div class="flex flex-col">
                <span class="font-bold text-slate-800">Drop Target Objects First</span>
                <span class="text-[10px] text-slate-500">Execute DROP TABLE IF EXISTS prior to creation</span>
              </div>
            </label>

            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-800">Foreign Key Creation Order</label>
              <app-custom-select
                [options]="fkOrderOptions"
                [ngModel]="ts.enterpriseConfig().schemaOnlyConfig.createForeignKeys"
                (ngModelChange)="updateSchemaOnly({ createForeignKeys: $event })">
              </app-custom-select>
            </div>

            <label class="p-3 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                [checked]="ts.enterpriseConfig().schemaOnlyConfig.includeIndexes"
                (change)="toggleSchemaIndexes()"
                class="rounded text-blue-600 focus:ring-0" />
              <div class="flex flex-col">
                <span class="font-bold text-slate-800">Generate Secondary Indexes</span>
                <span class="text-[10px] text-slate-500">Include non-primary index DDL scripts</span>
              </div>
            </label>
          </div>
        }

        <!-- M7 (Data Only) -->
        @if (ts.definition().mode === 'M7_DATA_ONLY') {
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 animate-in fade-in duration-100">
            <label class="p-3 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                [checked]="ts.enterpriseConfig().dataOnlyConfig.requireTargetTableExists"
                (change)="toggleDataRequireExists()"
                class="rounded text-blue-600 focus:ring-0" />
              <div class="flex flex-col">
                <span class="font-bold text-slate-800">Enforce Target Exists</span>
                <span class="text-[10px] text-slate-500">Fail immediately if target table is missing</span>
              </div>
            </label>

            <label class="p-3 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                [checked]="ts.enterpriseConfig().dataOnlyConfig.truncateTargetBeforeLoad"
                (change)="toggleDataTruncate()"
                class="rounded text-blue-600 focus:ring-0" />
              <div class="flex flex-col">
                <span class="font-bold text-slate-800">Truncate Target Before Load</span>
                <span class="text-[10px] text-slate-500">Clear existing rows before loading batch payload</span>
              </div>
            </label>

            <label class="p-3 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                [checked]="ts.enterpriseConfig().dataOnlyConfig.disableForeignKeysDuringLoad"
                (change)="toggleDataDisableFk()"
                class="rounded text-blue-600 focus:ring-0" />
              <div class="flex flex-col">
                <span class="font-bold text-slate-800">Disable FKs During Load</span>
                <span class="text-[10px] text-slate-500">Temporarily disable constraints to speed up writes</span>
              </div>
            </label>
          </div>
        }

        <!-- M1 (Bulk Load) -->
        @if (ts.definition().mode === 'M1_BULK') {
          <div class="p-3 bg-slate-50 border border-slate-200 rounded-md text-slate-600 text-xs">
            Standard snapshot extract parameters active. Performance and batching values above will govern direct read/write pipelines.
          </div>
        }

      </div>

      <!-- SECTION 4: MIGRATION-SIDE VALIDATION PRESETS -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3.5 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex flex-col">
            <span class="font-bold text-slate-900">Migration-Side Verification Presets</span>
            <span class="text-[11px] text-slate-500 font-normal">Automated in-flight integrity assertions attached to migrations generated from this template.</span>
          </div>
          <span class="text-[10px] text-slate-400">Post-Migration Checks</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          <label class="p-3 bg-slate-50 border border-slate-200 rounded-md flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              [checked]="ts.enterpriseConfig().validationPresets.rowCountReconciliation"
              (change)="toggleValidationPreset('rowCountReconciliation')"
              class="rounded text-blue-600 focus:ring-0 mt-0.5" />
            <div class="flex flex-col">
              <span class="font-bold text-slate-800">Row Count Reconciliation</span>
              <span class="text-[10px] text-slate-500">Compare source and target object row tallies post-migration</span>
            </div>
          </label>

          <label class="p-3 bg-slate-50 border border-slate-200 rounded-md flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              [checked]="ts.enterpriseConfig().validationPresets.schemaChecksumCheck"
              (change)="toggleValidationPreset('schemaChecksumCheck')"
              class="rounded text-blue-600 focus:ring-0 mt-0.5" />
            <div class="flex flex-col">
              <span class="font-bold text-slate-800">Schema Checksum Verification</span>
              <span class="text-[10px] text-slate-500">Verify column definitions and precision compatibility</span>
            </div>
          </label>

          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-800">Data Hash Sampling Rate</label>
            <app-custom-select
              [options]="validationSamplingOptions"
              [ngModel]="ts.enterpriseConfig().validationPresets.sampleDataHashRate"
              (ngModelChange)="updateValidationSampling($event)">
            </app-custom-select>
          </div>

        </div>
      </div>

    </div>
  `
})
export class Step4EnterpriseConfigComponent {
  public ts = inject(CreateTemplateService);

  public errorHandlingOptions: CustomSelectOption[] = [
    { label: 'Skip Corrupt Records & Log to DLQ', value: 'SKIP_AND_LOG_DLQ', desc: 'Isolates bad rows in dead-letter queue' },
    { label: 'Abort Immediately on Any Error', value: 'ABORT_IMMEDIATELY', desc: 'Fail pipeline on first error' },
    { label: 'Retry with Exponential Backoff', value: 'RETRY_EXPONENTIAL', desc: 'Retry record writes up to 3 times' }
  ];

  public cdcEngineOptions: CustomSelectOption[] = [
    { label: 'Native Database LogMiner / Redo', value: 'DATABASE_LOG_MINER', desc: 'Oracle LogMiner / Database redo stream' },
    { label: 'Debezium Embedded Streaming', value: 'DEBEZIUM_STREAM', desc: 'Low-latency CDC stream reader' },
    { label: 'PostgreSQL WAL2JSON Output', value: 'WAL2JSON', desc: 'Logical decoding plugin' },
    { label: 'MySQL Binlog Direct Replicator', value: 'BINLOG_REPLICATION', desc: 'Binary log replication stream' }
  ];

  public handoffOptions: CustomSelectOption[] = [
    { label: 'Seamless Lockless Transition', value: 'SEAMLESS_LOCKLESS', desc: 'Continuous stream without lock' },
    { label: 'Quiesce / Freeze Required', value: 'QUIESCE_REQUIRED', desc: 'Temporary write freeze at cutover' }
  ];

  public conflictResolutionOptions: CustomSelectOption[] = [
    { label: 'Source Database Wins (Authoritative)', value: 'SOURCE_WINS', desc: 'Source state overwrites target' },
    { label: 'Target Database Wins', value: 'TARGET_WINS', desc: 'Target state is preserved' },
    { label: 'Latest Commit Timestamp Wins', value: 'LATEST_TIMESTAMP', desc: 'Most recent update wins' },
    { label: 'Hold in Manual Conflict Queue', value: 'MANUAL_QUEUE', desc: 'Flag colliding rows for review' }
  ];

  public fkOrderOptions: CustomSelectOption[] = [
    { label: 'Post-Load Constraint Creation', value: 'POST_LOAD', desc: 'Recommended: build FKs after data load' },
    { label: 'Pre-Load Constraint Creation', value: 'PRE_LOAD', desc: 'Create constraints upfront' },
    { label: 'Do Not Generate Foreign Keys', value: 'NONE', desc: 'Omit FK DDL scripts' }
  ];

  public validationSamplingOptions: CustomSelectOption[] = [
    { label: 'None (Fastest)', value: 'NONE' },
    { label: '0.1% Random Sample Hash', value: 'SAMPLE_0_1_PCT' },
    { label: '1.0% Random Sample Hash', value: 'SAMPLE_1_PCT' },
    { label: '10.0% Sample Hash', value: 'SAMPLE_10_PCT' },
    { label: '100% Full Checksum', value: 'FULL_100_PCT' }
  ];

  public currentModeLabel(): string {
    const m = this.ts.definition().mode;
    return TEMPLATE_MODE_DESCRIPTORS[m]?.label || m;
  }

  public updatePerformance(partial: Partial<ReturnType<typeof this.ts.enterpriseConfig>['performance']>): void {
    const curr = this.ts.enterpriseConfig();
    this.ts.updateEnterpriseConfig({
      performance: { ...curr.performance, ...partial }
    });
  }

  public updateCheckpoint(partial: Partial<ReturnType<typeof this.ts.enterpriseConfig>['checkpointRecovery']>): void {
    const curr = this.ts.enterpriseConfig();
    this.ts.updateEnterpriseConfig({
      checkpointRecovery: { ...curr.checkpointRecovery, ...partial }
    });
  }

  public updateCdc(partial: Partial<ReturnType<typeof this.ts.enterpriseConfig>['cdcConfig']>): void {
    const curr = this.ts.enterpriseConfig();
    this.ts.updateEnterpriseConfig({
      cdcConfig: { ...curr.cdcConfig, ...partial }
    });
  }

  public toggleCdcHeartbeat(): void {
    const curr = this.ts.enterpriseConfig().cdcConfig;
    this.updateCdc({ heartbeatTracking: !curr.heartbeatTracking });
  }

  public updateIncremental(partial: Partial<ReturnType<typeof this.ts.enterpriseConfig>['incrementalConfig']>): void {
    const curr = this.ts.enterpriseConfig();
    this.ts.updateEnterpriseConfig({
      incrementalConfig: { ...curr.incrementalConfig, ...partial }
    });
  }

  public updateStateSync(partial: Partial<ReturnType<typeof this.ts.enterpriseConfig>['stateSyncConfig']>): void {
    const curr = this.ts.enterpriseConfig();
    this.ts.updateEnterpriseConfig({
      stateSyncConfig: { ...curr.stateSyncConfig, ...partial }
    });
  }

  public toggleStateSyncBiDirectional(): void {
    const curr = this.ts.enterpriseConfig().stateSyncConfig;
    this.updateStateSync({ biDirectionalEnabled: !curr.biDirectionalEnabled });
  }

  public updateSchemaOnly(partial: Partial<ReturnType<typeof this.ts.enterpriseConfig>['schemaOnlyConfig']>): void {
    const curr = this.ts.enterpriseConfig();
    this.ts.updateEnterpriseConfig({
      schemaOnlyConfig: { ...curr.schemaOnlyConfig, ...partial }
    });
  }

  public toggleSchemaDrop(): void {
    const curr = this.ts.enterpriseConfig().schemaOnlyConfig;
    this.updateSchemaOnly({ dropTargetObjectsFirst: !curr.dropTargetObjectsFirst });
  }

  public toggleSchemaIndexes(): void {
    const curr = this.ts.enterpriseConfig().schemaOnlyConfig;
    this.updateSchemaOnly({ includeIndexes: !curr.includeIndexes });
  }

  public updateDataOnly(partial: Partial<ReturnType<typeof this.ts.enterpriseConfig>['dataOnlyConfig']>): void {
    const curr = this.ts.enterpriseConfig();
    this.ts.updateEnterpriseConfig({
      dataOnlyConfig: { ...curr.dataOnlyConfig, ...partial }
    });
  }

  public toggleDataRequireExists(): void {
    const curr = this.ts.enterpriseConfig().dataOnlyConfig;
    this.updateDataOnly({ requireTargetTableExists: !curr.requireTargetTableExists });
  }

  public toggleDataTruncate(): void {
    const curr = this.ts.enterpriseConfig().dataOnlyConfig;
    this.updateDataOnly({ truncateTargetBeforeLoad: !curr.truncateTargetBeforeLoad });
  }

  public toggleDataDisableFk(): void {
    const curr = this.ts.enterpriseConfig().dataOnlyConfig;
    this.updateDataOnly({ disableForeignKeysDuringLoad: !curr.disableForeignKeysDuringLoad });
  }

  public toggleValidationPreset(key: 'rowCountReconciliation' | 'schemaChecksumCheck'): void {
    const curr = this.ts.enterpriseConfig().validationPresets;
    this.ts.updateEnterpriseConfig({
      validationPresets: {
        ...curr,
        [key]: !curr[key]
      }
    });
  }

  public updateValidationSampling(sampleDataHashRate: SampleHashRate): void {
    const curr = this.ts.enterpriseConfig().validationPresets;
    this.ts.updateEnterpriseConfig({
      validationPresets: {
        ...curr,
        sampleDataHashRate
      }
    });
  }
}
