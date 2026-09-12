import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { MigrationExecutionDTO, SelectedMigrationHeaderDTO } from '../../models/migration-monitoring.models';
import { formatSnakeToTitle } from '../../models/monitoring.models';
import { ModeBulkSnapshotTelemetryComponent } from '../mode-telemetry/mode-bulk-snapshot-telemetry.component';
import { ModeBulkCdcTelemetryComponent } from '../mode-telemetry/mode-bulk-cdc-telemetry.component';
import { ModeContinuousCdcTelemetryComponent } from '../mode-telemetry/mode-continuous-cdc-telemetry.component';
import { ModeIncrementalTelemetryComponent } from '../mode-telemetry/mode-incremental-telemetry.component';
import { ModeStateSyncTelemetryComponent } from '../mode-telemetry/mode-state-sync-telemetry.component';
import { ModeSchemaTelemetryComponent } from '../mode-telemetry/mode-schema-telemetry.component';
import { ModeRawDataIngestTelemetryComponent } from '../mode-telemetry/mode-raw-data-ingest-telemetry.component';

@Component({
  selector: 'app-migration-execution-tab',
  standalone: true,
  imports: [
    CommonModule,
    LucideIconComponent,
    ModeBulkSnapshotTelemetryComponent,
    ModeBulkCdcTelemetryComponent,
    ModeContinuousCdcTelemetryComponent,
    ModeIncrementalTelemetryComponent,
    ModeStateSyncTelemetryComponent,
    ModeSchemaTelemetryComponent,
    ModeRawDataIngestTelemetryComponent
  ],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Compiled ExecutionPlan & Fingerprint Card -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
          <div class="flex items-center gap-2.5">
            <app-lucide-icon name="file-code" [size]="16" class="text-blue-600"></app-lucide-icon>
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Compiled Execution Plan</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 font-mono">
              {{ execution.plan_info.version }}
            </span>
          </div>

          <div class="flex items-center gap-2 text-xs text-slate-500 font-mono">
            <span class="text-slate-400">Fingerprint:</span>
            <span class="truncate max-w-[220px]" [title]="execution.plan_info.fingerprint">{{ execution.plan_info.fingerprint }}</span>
          </div>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1 p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span class="text-slate-500 font-medium">Compiled At</span>
            <span class="font-semibold text-slate-800 font-mono">{{ execution.plan_info.compiled_at | date:'yyyy-MM-dd HH:mm' }}</span>
          </div>

          <div class="flex flex-col gap-1 p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span class="text-slate-500 font-medium">Stage Completion</span>
            <span class="font-semibold text-slate-800 font-mono">{{ execution.plan_info.completed_nodes }} / {{ execution.plan_info.total_nodes }} stages</span>
          </div>

          <div class="flex flex-col gap-1 p-3 rounded-xl bg-slate-50 border border-slate-100 col-span-2">
            <span class="text-slate-500 font-medium">Active Execution Stage</span>
            <span class="font-semibold text-blue-700 truncate">{{ execution.plan_info.active_node_label }}</span>
          </div>
        </div>
      </div>

      <!-- 2. Dynamic DAG Stage Progression -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Execution DAG Stage Progression</h3>
          <span class="text-xs text-slate-500 font-medium">{{ execution.dag_nodes.length }} execution nodes</span>
        </div>

        <div class="flex flex-col gap-2.5">
          @for (node of execution.dag_nodes; track node.id; let idx = $index) {
            <div 
              class="p-3.5 rounded-xl border flex items-center justify-between gap-4 flex-wrap transition-colors"
              [ngClass]="{
                'bg-white border-slate-200': node.state === 'COMPLETED',
                'bg-blue-50/40 border-blue-200 shadow-2xs': node.state === 'RUNNING',
                'bg-slate-50 border-slate-200/60 opacity-75': node.state === 'WAITING',
                'bg-rose-50 border-rose-200': node.state === 'BLOCKED'
              }">
              
              <!-- Node Info & Status -->
              <div class="flex items-center gap-3 min-w-[260px]">
                <span 
                  class="w-6 h-6 rounded flex items-center justify-center text-xs font-bold shrink-0"
                  [ngClass]="{
                    'bg-emerald-100 text-emerald-800': node.state === 'COMPLETED',
                    'bg-blue-600 text-white': node.state === 'RUNNING',
                    'bg-slate-200 text-slate-600': node.state === 'WAITING',
                    'bg-rose-600 text-white': node.state === 'BLOCKED'
                  }">
                  {{ idx + 1 }}
                </span>

                <div class="flex flex-col">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-bold text-slate-900">{{ node.label }}</span>
                    <span class="px-1.5 py-0.2 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
                      {{ formatText(node.stage_type) }}
                    </span>
                  </div>
                  <span class="text-[11px] text-slate-500">{{ node.duration_label }}</span>
                </div>
              </div>

              <!-- Progress & State Details -->
              <div class="flex items-center gap-6 text-xs">
                @if (node.rows_transferred !== undefined && node.rows_transferred > 0) {
                  <div class="flex flex-col items-end">
                    <span class="text-[11px] text-slate-400">Rows Transferred</span>
                    <span class="font-mono font-semibold text-slate-800">{{ node.rows_transferred | number }}</span>
                  </div>
                }

                @if (node.progress_percent !== undefined && node.progress_percent !== null) {
                  <div class="flex items-center gap-2 min-w-[120px]">
                    <div class="w-20 bg-slate-200 h-1.5 rounded-full overflow-hidden">
                      <div 
                        class="h-full rounded-full transition-all"
                        [ngClass]="node.state === 'COMPLETED' ? 'bg-emerald-500' : 'bg-blue-600'"
                        [style.width.%]="node.progress_percent">
                      </div>
                    </div>
                    <span class="font-mono font-semibold text-slate-700 text-[11px]">{{ node.progress_percent }}%</span>
                  </div>
                }

                <!-- Status Badge -->
                <span 
                  class="px-2.5 py-0.5 rounded text-[11px] font-semibold"
                  [ngClass]="{
                    'bg-emerald-50 text-emerald-700 border border-emerald-200/60': node.state === 'COMPLETED',
                    'bg-blue-600 text-white': node.state === 'RUNNING',
                    'bg-slate-100 text-slate-600': node.state === 'WAITING',
                    'bg-rose-50 text-rose-700 border border-rose-200': node.state === 'BLOCKED'
                  }">
                  {{ node.state }}
                </span>
              </div>

            </div>
          }
        </div>
      </div>

      <!-- 3. Mode-Specific Telemetry (Dynamically Switched for M1-M7) -->
      @if (header.mode === 'M1_BULK' && execution.m1_bulk) {
        <app-mode-bulk-snapshot-telemetry [telemetry]="execution.m1_bulk"></app-mode-bulk-snapshot-telemetry>
      } @else if (header.mode === 'M2_BULK_CDC' && execution.m2_bulk_cdc) {
        <app-mode-bulk-cdc-telemetry [telemetry]="execution.m2_bulk_cdc"></app-mode-bulk-cdc-telemetry>
      } @else if (header.mode === 'M3_CDC' && execution.m3_cdc) {
        <app-mode-continuous-cdc-telemetry [telemetry]="execution.m3_cdc"></app-mode-continuous-cdc-telemetry>
      } @else if (header.mode === 'M4_INCREMENTAL' && execution.m4_incremental) {
        <app-mode-incremental-telemetry [telemetry]="execution.m4_incremental"></app-mode-incremental-telemetry>
      } @else if (header.mode === 'M5_STATE_SYNC' && execution.m5_state_sync) {
        <app-mode-state-sync-telemetry [telemetry]="execution.m5_state_sync"></app-mode-state-sync-telemetry>
      } @else if (header.mode === 'M6_SCHEMA_ONLY' && execution.m6_schema) {
        <app-mode-schema-telemetry [telemetry]="execution.m6_schema"></app-mode-schema-telemetry>
      } @else if (header.mode === 'M7_DATA_ONLY' && execution.m7_data_only) {
        <app-mode-raw-data-ingest-telemetry [telemetry]="execution.m7_data_only"></app-mode-raw-data-ingest-telemetry>
      }

    </div>
  `
})
export class MigrationExecutionTabComponent {
  @Input({ required: true }) execution!: MigrationExecutionDTO;
  @Input({ required: true }) header!: SelectedMigrationHeaderDTO;

  public formatText = formatSnakeToTitle;
}
