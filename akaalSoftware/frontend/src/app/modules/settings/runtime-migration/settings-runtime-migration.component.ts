import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../shared/components/custom-select.component';
import { SettingsService } from '../services/settings.service';
import {
  ExecutionProfileOption,
  ExecutionGraphOption,
  TablePartitionStrategy,
  ConflictResolutionOption,
  ValidationAssuranceLevel,
  RecoveryStrategyOption
} from '../models/settings.models';

interface SubSectionNav {
  id: string;
  label: string;
  icon: string;
}

@Component({
  selector: 'app-settings-runtime-migration',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="space-y-8">
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div class="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider font-mono">Operational Defaults</div>
          <h2 class="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">Runtime &amp; Migration Defaults</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Configure pipeline worker parallelism, transaction batching, ingest queues, CDC buffers, and recovery strategies for future migrations.
          </p>
        </div>
        <div class="flex items-center gap-3">
          <button
            type="button"
            (click)="resetDefaults()"
            class="px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg transition-colors flex items-center gap-2">
            <app-lucide-icon name="rotate-ccw" [size]="14"></app-lucide-icon>
            Reset Defaults
          </button>
        </div>
      </div>

      <!-- Scope Notice Banner -->
      <div class="bg-blue-50/60 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/40 rounded-xl p-4 flex items-start gap-3">
        <div class="w-7 h-7 rounded-lg bg-blue-100/80 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 mt-0.5">
          <app-lucide-icon name="info" [size]="16"></app-lucide-icon>
        </div>
        <div class="text-xs leading-relaxed text-slate-700 dark:text-slate-300">
          <span class="font-bold text-slate-900 dark:text-slate-100">Future Migration Defaults:</span>
          Parameters configured here initialize execution plans during migration creation. Modifying these values does not mutate active, paused, or queued pipeline executions. Platform resource ceilings are enforced authoritatively by Domain 5.10 Platform Administration.
        </div>
      </div>

      <!-- Main Layout with Secondary Vertical Sub-Navigation -->
      <div class="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
        
        <!-- Left Sub-Navigation Rail (Sticky) -->
        <nav class="xl:col-span-3 bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-3 space-y-1 xl:sticky xl:top-6 shadow-sm">
          <div class="px-3 py-2 text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
            Subsections
          </div>
          @for (sub of subsections; track sub.id) {
            <button
              type="button"
              (click)="scrollToSection(sub.id)"
              [class.bg-blue-50]="activeSection() === sub.id"
              [class.text-blue-600]="activeSection() === sub.id"
              [class.dark:bg-blue-950]="activeSection() === sub.id"
              [class.dark:text-blue-400]="activeSection() === sub.id"
              [class.text-slate-700]="activeSection() !== sub.id"
              [class.dark:text-slate-300]="activeSection() !== sub.id"
              class="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-semibold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors text-left">
              <app-lucide-icon [name]="sub.icon" [size]="14"></app-lucide-icon>
              <span>{{ sub.label }}</span>
            </button>
          }
        </nav>

        <!-- Right Content Column: 11 Spacious Sections -->
        <div class="xl:col-span-9 space-y-8">

          <!-- 1. Runtime -->
          <section id="section-runtime" class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <app-lucide-icon name="workflow" [size]="18"></app-lucide-icon>
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">1. Runtime</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">Baseline execution profile and DAG dependency resolution strategy.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Execution Profile Default
                </label>
                <app-custom-select
                  [options]="executionProfileOptions"
                  [ngModel]="settings().executionProfile"
                  (ngModelChange)="updateSetting('executionProfile', $event)">
                </app-custom-select>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Sets initial CPU/RAM priority weights for execution steps.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Task Execution Timeout (seconds)
                </label>
                <input
                  type="number"
                  min="60"
                  max="86400"
                  step="60"
                  [ngModel]="settings().taskTimeoutSeconds"
                  (ngModelChange)="updateSetting('taskTimeoutSeconds', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Maximum permitted runtime before a work task is marked expired (default 3600s).</p>
              </div>

              <div class="md:col-span-2">
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Execution Graph Strategy
                </label>
                <app-custom-select
                  [options]="graphStrategyOptions"
                  [ngModel]="settings().graphStrategy"
                  (ngModelChange)="updateSetting('graphStrategy', $event)">
                </app-custom-select>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Dynamic DAG schedules task dependencies adaptively based on table chunk readiness.</p>
              </div>
            </div>
          </section>

          <!-- 2. Workers / Parallelism -->
          <section id="section-workers" class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <app-lucide-icon name="cpu" [size]="18"></app-lucide-icon>
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">2. Workers / Parallelism</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">Default worker thread pool bounds and adaptive concurrency scaling.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Default Starting Workers
                </label>
                <input
                  type="number"
                  min="1"
                  max="32"
                  [ngModel]="settings().defaultStartingWorkers"
                  (ngModelChange)="updateSetting('defaultStartingWorkers', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Initial worker thread pool launched at plan initiation.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Minimum Concurrency Floor
                </label>
                <input
                  type="number"
                  min="1"
                  max="16"
                  [ngModel]="settings().minConcurrencyFloor"
                  (ngModelChange)="updateSetting('minConcurrencyFloor', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Guaranteed minimum workers during high system throttle.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Preferred Max Workers
                </label>
                <input
                  type="number"
                  min="4"
                  max="64"
                  [ngModel]="settings().preferredMaxWorkers"
                  (ngModelChange)="updateSetting('preferredMaxWorkers', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Maximum workers target for high-throughput phases.</p>
              </div>
            </div>

            <!-- Governed Platform Policy Banner -->
            <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div class="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <app-lucide-icon name="shield" [size]="14" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
                  Maximum Worker Ceiling: 64 Threads
                </div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Managed by enterprise platform policy (5.10 Platform Administration). Workstation settings cannot exceed this cluster limit.
                </div>
              </div>
              <div class="text-xs font-bold text-slate-600 dark:text-slate-300 px-2.5 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shrink-0">
                Enforced Read-Only
              </div>
            </div>

            <!-- Adaptive Concurrency Toggle -->
            <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
              <div>
                <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Adaptive Concurrency Controller</div>
                <div class="text-xs text-slate-500 dark:text-slate-400">Dynamically scales worker threads within min/max bounds based on live target latency.</div>
              </div>
              <button
                type="button"
                (click)="updateSetting('adaptiveConcurrencyEnabled', !settings().adaptiveConcurrencyEnabled)"
                [class.bg-blue-600]="settings().adaptiveConcurrencyEnabled"
                [class.bg-slate-300]="!settings().adaptiveConcurrencyEnabled"
                [class.dark:bg-slate-700]="!settings().adaptiveConcurrencyEnabled"
                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
                <span
                  [class.translate-x-5]="settings().adaptiveConcurrencyEnabled"
                  [class.translate-x-0]="!settings().adaptiveConcurrencyEnabled"
                  class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
              </button>
            </div>
          </section>

          <!-- 3. Batching -->
          <section id="section-batching" class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <app-lucide-icon name="layers" [size]="18"></app-lucide-icon>
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">3. Batching</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">Row transaction chunk sizes, in-flight memory boundaries, and LOB streaming thresholds.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Default Row Batch Size
                </label>
                <input
                  type="number"
                  min="500"
                  max="50000"
                  step="500"
                  [ngModel]="settings().defaultBatchSize"
                  (ngModelChange)="updateSetting('defaultBatchSize', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Number of records committed in a single transaction frame (default 10,000).</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Max Memory Per Batch (MiB)
                </label>
                <input
                  type="number"
                  min="16"
                  max="256"
                  step="16"
                  [ngModel]="settings().maxMemoryPerBatchMb"
                  (ngModelChange)="updateSetting('maxMemoryPerBatchMb', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Memory ceiling before a batch flushes ahead of row target (default 64 MiB).</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  LOB Streaming Threshold (KiB)
                </label>
                <input
                  type="number"
                  min="64"
                  max="16384"
                  step="64"
                  [ngModel]="settings().lobStreamingThresholdKb"
                  (ngModelChange)="updateSetting('lobStreamingThresholdKb', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">LOB fields exceeding this size stream out-of-line (default 1024 KiB).</p>
              </div>
            </div>

            <!-- Adaptive Batching Toggle -->
            <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
              <div>
                <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Adaptive Batch Sizing</div>
                <div class="text-xs text-slate-500 dark:text-slate-400">Dynamically adjusts batch row counts to prevent transaction log saturation during wide column loads.</div>
              </div>
              <button
                type="button"
                (click)="updateSetting('adaptiveBatchingEnabled', !settings().adaptiveBatchingEnabled)"
                [class.bg-blue-600]="settings().adaptiveBatchingEnabled"
                [class.bg-slate-300]="!settings().adaptiveBatchingEnabled"
                [class.dark:bg-slate-700]="!settings().adaptiveBatchingEnabled"
                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
                <span
                  [class.translate-x-5]="settings().adaptiveBatchingEnabled"
                  [class.translate-x-0]="!settings().adaptiveBatchingEnabled"
                  class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
              </button>
            </div>
          </section>

          <!-- 4. Queues -->
          <section id="section-queues" class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <app-lucide-icon name="activity" [size]="18"></app-lucide-icon>
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">4. Queues</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">In-memory pipeline work queues and backpressure saturation thresholds.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Default Queue Capacity (items)
                </label>
                <input
                  type="number"
                  min="5000"
                  max="200000"
                  step="5000"
                  [ngModel]="settings().defaultQueueCapacity"
                  (ngModelChange)="updateSetting('defaultQueueCapacity', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Buffer slot capacity between reader tasks and writer stages.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Backpressure High Watermark (%)
                </label>
                <input
                  type="number"
                  min="60"
                  max="95"
                  [ngModel]="settings().highWatermarkPercent"
                  (ngModelChange)="updateSetting('highWatermarkPercent', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Queue saturation level that signals upstream reader tasks to pause.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Backpressure Low Watermark (%)
                </label>
                <input
                  type="number"
                  min="20"
                  max="60"
                  [ngModel]="settings().lowWatermarkPercent"
                  (ngModelChange)="updateSetting('lowWatermarkPercent', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Queue drain level that signals upstream reader tasks to resume.</p>
              </div>
            </div>
          </section>

          <!-- 5. Resource Limits -->
          <section id="section-resources" class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <app-lucide-icon name="server" [size]="18"></app-lucide-icon>
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">5. Resource Limits</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">Cluster compute quotas and worker process scheduling priority.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3.5">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Governed Max Memory</div>
                <div class="text-base font-bold text-slate-900 dark:text-slate-100 mt-1">8,192 MiB (8 GiB)</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1 flex items-center gap-1">
                  <app-lucide-icon name="shield" [size]="12" class="text-blue-600"></app-lucide-icon>
                  Managed by Platform Service Specification
                </div>
              </div>

              <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3.5">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Governed Max CPU</div>
                <div class="text-base font-bold text-slate-900 dark:text-slate-100 mt-1">4,000 Millicores (4 vCPU)</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1 flex items-center gap-1">
                  <app-lucide-icon name="shield" [size]="12" class="text-blue-600"></app-lucide-icon>
                  Managed by Platform Service Specification
                </div>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Worker Process Priority
                </label>
                <input
                  type="text"
                  readonly
                  value="Normal (0)"
                  class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Standard OS execution priority scheduled by container daemon.</p>
              </div>
            </div>
          </section>

          <!-- 6. Bulk -->
          <section id="section-bulk" class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <app-lucide-icon name="database" [size]="18"></app-lucide-icon>
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">6. Bulk Migration Defaults</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">Defaults for M1 and M2 bulk historical table extraction and loading.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Partition Strategy Default
                </label>
                <app-custom-select
                  [options]="partitionStrategyOptions"
                  [ngModel]="settings().partitionStrategy"
                  (ngModelChange)="updateSetting('partitionStrategy', $event)">
                </app-custom-select>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Default partitioning algorithm applied to candidate tables.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Parallel Chunks per Table
                </label>
                <input
                  type="number"
                  min="1"
                  max="16"
                  [ngModel]="settings().parallelChunksPerTable"
                  (ngModelChange)="updateSetting('parallelChunksPerTable', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Parallel reader slices per partitioned physical table.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Read Fetch Buffer Size (rows)
                </label>
                <input
                  type="number"
                  min="1000"
                  max="20000"
                  step="1000"
                  [ngModel]="settings().readFetchBufferSize"
                  (ngModelChange)="updateSetting('readFetchBufferSize', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Source driver cursor batch fetch allocation.</p>
              </div>
            </div>

            <!-- Direct Path Insert Toggle -->
            <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
              <div>
                <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Direct-Path Bulk Insert Loading</div>
                <div class="text-xs text-slate-500 dark:text-slate-400">Bypasses transaction redo/undo logging on supported targets when writing unindexed tables.</div>
              </div>
              <button
                type="button"
                (click)="updateSetting('directPathBulkInsert', !settings().directPathBulkInsert)"
                [class.bg-blue-600]="settings().directPathBulkInsert"
                [class.bg-slate-300]="!settings().directPathBulkInsert"
                [class.dark:bg-slate-700]="!settings().directPathBulkInsert"
                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
                <span
                  [class.translate-x-5]="settings().directPathBulkInsert"
                  [class.translate-x-0]="!settings().directPathBulkInsert"
                  class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
              </button>
            </div>
          </section>

          <!-- 7. CDC -->
          <section id="section-cdc" class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <app-lucide-icon name="refresh-cw" [size]="18"></app-lucide-icon>
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">7. CDC (Change Data Capture)</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">Continuous replication ingest buffers, spill thresholds, and transaction batching.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  CDC Stream Buffer Memory (MiB)
                </label>
                <input
                  type="number"
                  min="32"
                  max="512"
                  step="32"
                  [ngModel]="settings().cdcBufferMemoryMb"
                  (ngModelChange)="updateSetting('cdcBufferMemoryMb', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">In-memory buffer capacity before durability spill frames are written (default 64 MiB).</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Spill-to-Durability Threshold (%)
                </label>
                <input
                  type="number"
                  min="50"
                  max="95"
                  [ngModel]="settings().spillThresholdPercent"
                  (ngModelChange)="updateSetting('spillThresholdPercent', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Memory saturation watermark that initiates spill to Authority #5 storage.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  CDC Poll Frequency / Heartbeat (ms)
                </label>
                <input
                  type="number"
                  min="50"
                  max="2000"
                  step="50"
                  [ngModel]="settings().cdcPollFrequencyMs"
                  (ngModelChange)="updateSetting('cdcPollFrequencyMs', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Poll frequency for connector replication streams (default 250 ms).</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Transaction Grouping Window (ms)
                </label>
                <input
                  type="number"
                  min="100"
                  max="5000"
                  step="100"
                  [ngModel]="settings().transactionGroupingWindowMs"
                  (ngModelChange)="updateSetting('transactionGroupingWindowMs', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Window for grouping micro-transactions to reduce target write amplification.</p>
              </div>
            </div>
          </section>

          <!-- 8. Incremental / Polling -->
          <section id="section-incremental" class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <app-lucide-icon name="clock" [size]="18"></app-lucide-icon>
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">8. Incremental / Polling (M4)</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">Timestamp watermark polling intervals, clock-skew margins, and fetch limits.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Default Polling Interval (seconds)
                </label>
                <input
                  type="number"
                  min="1"
                  max="300"
                  [ngModel]="settings().pollingIntervalSeconds"
                  (ngModelChange)="updateSetting('pollingIntervalSeconds', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Interval between delta query sweeps (default 10s).</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Lookback Safety Margin (seconds)
                </label>
                <input
                  type="number"
                  min="5"
                  max="600"
                  [ngModel]="settings().lookbackSafetyMarginSeconds"
                  (ngModelChange)="updateSetting('lookbackSafetyMarginSeconds', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Overlap window to protect against clock skew and concurrent uncommitted inserts.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  High-Watermark Column Strategy
                </label>
                <input
                  type="text"
                  readonly
                  value="Auto-Detect (updated_at, mtime, sequence)"
                  class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Identifies monotonic or temporal column for incremental capture.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Max Records per Poll Cycle
                </label>
                <input
                  type="number"
                  min="1000"
                  max="50000"
                  step="1000"
                  [ngModel]="settings().maxRecordsPerPoll"
                  (ngModelChange)="updateSetting('maxRecordsPerPoll', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Limits transaction batch size on high-velocity tables.</p>
              </div>
            </div>
          </section>

          <!-- 9. State Synchronization -->
          <section id="section-sync" class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <app-lucide-icon name="git-fork" [size]="18"></app-lucide-icon>
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">9. State Synchronization (M5)</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">Continuous state comparison algorithms, drift sensitivity, and conflict resolution defaults.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Comparison Algorithm
                </label>
                <input
                  type="text"
                  readonly
                  value="Two-Way Keyset Diff"
                  class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Evaluates divergence between authoritative source and replicas.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  State Drift Sensitivity
                </label>
                <input
                  type="text"
                  readonly
                  value="Strict (0-Tolerance)"
                  class="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 cursor-not-allowed" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Emits divergence alerts on any row value or checksum mismatch.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Conflict Resolution Preference
                </label>
                <app-custom-select
                  [options]="conflictResolutionOptions"
                  [ngModel]="settings().conflictResolutionPreference"
                  (ngModelChange)="updateSetting('conflictResolutionPreference', $event)">
                </app-custom-select>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Determines precedence when simultaneous updates occur.</p>
              </div>
            </div>
          </section>

          <!-- 10. Validation -->
          <section id="section-validation" class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <app-lucide-icon name="check-circle" [size]="18"></app-lucide-icon>
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">10. Validation Defaults</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">Post-migration data integrity verification levels and sampling rates.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Default Assurance Level
                </label>
                <app-custom-select
                  [options]="validationAssuranceOptions"
                  [ngModel]="settings().validationAssuranceLevel"
                  (ngModelChange)="updateSetting('validationAssuranceLevel', $event)">
                </app-custom-select>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Level 2 calculates cryptographic SHA-256 batch checksums and row counts.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Sample Verification Rate (%)
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  [ngModel]="settings().sampleVerificationRatePercent"
                  (ngModelChange)="updateSetting('sampleVerificationRatePercent', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">100% performs exhaustive verification across all migrated tables.</p>
              </div>
            </div>

            <!-- Post-Migration Auto-Validation Toggle -->
            <div class="flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
              <div>
                <div class="text-xs font-bold text-slate-800 dark:text-slate-200">Automatic Post-Migration Verification</div>
                <div class="text-xs text-slate-500 dark:text-slate-400">Executes an M8 non-mutating validation job immediately upon bulk load completion.</div>
              </div>
              <button
                type="button"
                (click)="updateSetting('postMigrationAutoValidation', !settings().postMigrationAutoValidation)"
                [class.bg-blue-600]="settings().postMigrationAutoValidation"
                [class.bg-slate-300]="!settings().postMigrationAutoValidation"
                [class.dark:bg-slate-700]="!settings().postMigrationAutoValidation"
                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-lg transition-colors duration-200 ease-in-out p-0.5">
                <span
                  [class.translate-x-5]="settings().postMigrationAutoValidation"
                  [class.translate-x-0]="!settings().postMigrationAutoValidation"
                  class="inline-block h-5 w-5 rounded-md bg-white shadow transform transition duration-200 ease-in-out"></span>
              </button>
            </div>
          </section>

          <!-- 11. Recovery -->
          <section id="section-recovery" class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div class="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <app-lucide-icon name="shield-check" [size]="18"></app-lucide-icon>
              </div>
              <div>
                <h3 class="text-base font-bold text-slate-900 dark:text-slate-100">11. Recovery Defaults</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">Automatic failure recovery strategies, restart retry counts, and durability safety invariants.</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Default Recovery Strategy
                </label>
                <app-custom-select
                  [options]="recoveryStrategyOptions"
                  [ngModel]="settings().recoveryStrategy"
                  (ngModelChange)="updateSetting('recoveryStrategy', $event)">
                </app-custom-select>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Resumes execution from last confirmed FencingToken checkpoint.</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Max Automatic Restart Retries
                </label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  [ngModel]="settings().maxAutomaticRetries"
                  (ngModelChange)="updateSetting('maxAutomaticRetries', +$event)"
                  class="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Number of automated recovery attempts before pausing plan for operator inspection.</p>
              </div>
            </div>

            <!-- Governed Invariant: Fencing Epoch Barrier -->
            <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div class="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <app-lucide-icon name="lock" [size]="14" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
                  Monotonic Fencing Epoch Rollback Barrier: Permanently Enforced
                </div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Strictly prohibits rolling back to an earlier fencing epoch. Enforced authoritatively by Durability Authority #5 to prevent split-brain execution.
                </div>
              </div>
              <div class="text-xs font-bold text-blue-700 dark:text-blue-400 px-2.5 py-1 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded-md shrink-0">
                Safety Invariant Active
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  `
})
export class SettingsRuntimeMigrationComponent {
  private settingsService = inject(SettingsService);

  public settings = this.settingsService.runtimeMigrationSettings;
  public activeSection = signal<string>('section-runtime');

  public subsections: SubSectionNav[] = [
    { id: 'section-runtime', label: '1. Runtime', icon: 'workflow' },
    { id: 'section-workers', label: '2. Workers / Parallelism', icon: 'cpu' },
    { id: 'section-batching', label: '3. Batching', icon: 'layers' },
    { id: 'section-queues', label: '4. Queues', icon: 'activity' },
    { id: 'section-resources', label: '5. Resource Limits', icon: 'server' },
    { id: 'section-bulk', label: '6. Bulk Defaults', icon: 'database' },
    { id: 'section-cdc', label: '7. CDC Ingestion', icon: 'refresh-cw' },
    { id: 'section-incremental', label: '8. Incremental (M4)', icon: 'clock' },
    { id: 'section-sync', label: '9. State Sync (M5)', icon: 'git-fork' },
    { id: 'section-validation', label: '10. Validation', icon: 'check-circle' },
    { id: 'section-recovery', label: '11. Recovery', icon: 'shield-check' }
  ];

  public executionProfileOptions: SelectOption[] = [
    { label: 'Standard Balanced (Nominal Workloads)', value: 'BALANCED' },
    { label: 'High Throughput (Dedicated Hardware)', value: 'HIGH_THROUGHPUT' },
    { label: 'Memory Constrained (Low RAM Footprint)', value: 'MEMORY_CONSTRAINED' },
    { label: 'Low Impact (Background Execution)', value: 'LOW_IMPACT' }
  ];

  public graphStrategyOptions: SelectOption[] = [
    { label: 'Dynamic DAG (Adaptive Task Dependencies)', value: 'DYNAMIC_DAG' },
    { label: 'Fixed Linear (Sequential Stage Gating)', value: 'FIXED_LINEAR' }
  ];

  public partitionStrategyOptions: SelectOption[] = [
    { label: 'Auto-Detect (Primary Key / Keyset Analysis)', value: 'AUTO_DETECT' },
    { label: 'Primary Key Range Slicing', value: 'PRIMARY_KEY_RANGE' },
    { label: 'Modulo Hash Partitioning', value: 'MODULO_HASH' },
    { label: 'Keyset Paging (Ordered Cursor)', value: 'KEYSET_PAGING' }
  ];

  public conflictResolutionOptions: SelectOption[] = [
    { label: 'Source-Wins (Authoritative Source Precedence)', value: 'SOURCE_WINS' },
    { label: 'Target-Wins (Replica State Retained)', value: 'TARGET_WINS' },
    { label: 'Manual Hold (Halt on Conflict Drift)', value: 'MANUAL_HOLD' }
  ];

  public validationAssuranceOptions: SelectOption[] = [
    { label: 'Level 1: Fast Row Count Only', value: 'LEVEL_1_ROW_COUNT' },
    { label: 'Level 2: Checksum & Row Count (Recommended)', value: 'LEVEL_2_CHECKSUM' },
    { label: 'Level 3: Full Deep Cell-by-Cell Diff', value: 'LEVEL_3_FULL_DIFF' }
  ];

  public recoveryStrategyOptions: SelectOption[] = [
    { label: 'Resume from Last Confirmed Checkpoint (Recommended)', value: 'RESUME_CHECKPOINT' },
    { label: 'Restart Failed Step from Beginning', value: 'RESTART_STEP' },
    { label: 'Fail-Closed (Immediate Halt for Investigation)', value: 'FAIL_CLOSED' }
  ];

  public scrollToSection(sectionId: string): void {
    this.activeSection.set(sectionId);
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  public updateSetting(key: string, value: any): void {
    this.settingsService.updateRuntimeMigration({ [key]: value });
  }

  public resetDefaults(): void {
    this.settingsService.resetRuntimeMigration();
  }
}
