import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Step6ConfigurationStoreService } from '../../../../core/services/step6-configuration-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-configuration-standard',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="w-full flex flex-col gap-6 font-sans text-xs select-none pb-8">

      <!-- ========================================================================= -->
      <!-- 1. EXECUTION PROFILE                                                      -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <div class="flex items-center gap-2">
            <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              1. Execution Profile <span class="text-rose-500">*</span>
            </h2>
            <span class="text-slate-300 font-light">&middot;</span>
            <span class="text-xs text-slate-400 font-normal">
              Choose how AKAAL should balance migration speed against source and target impact.
            </span>
          </div>
          <button
            type="button"
            (click)="store.setDepth('ADVANCED')"
            class="text-[11px] font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1 cursor-pointer transition-colors">
            <span>View in Advanced</span>
            <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
          </button>
        </div>

        <!-- 3 Profile Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          @for (profile of store.standardProfiles(); track profile.id) {
            <div
              (click)="store.selectProfile(profile.id)"
              class="p-3.5 border rounded-lg cursor-pointer bg-white transition-colors select-none flex flex-col justify-between gap-3 min-h-[110px]"
              [class.border-blue-600]="store.draft().profile === profile.id"
              [class.ring-1]="store.draft().profile === profile.id"
              [class.ring-blue-600]="store.draft().profile === profile.id"
              [class.bg-blue-50]="store.draft().profile === profile.id"
              [class.border-slate-200]="store.draft().profile !== profile.id"
              [class.hover:border-slate-300]="store.draft().profile !== profile.id"
              [class.hover:bg-slate-50]="store.draft().profile !== profile.id">
              
              <div class="flex flex-col gap-1">
                <div class="flex items-center justify-between">
                  <span class="text-xs font-bold text-slate-900">{{ profile.title }}</span>
                  @if (profile.badge) {
                    <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-700 border border-blue-200">
                      {{ profile.badge }}
                    </span>
                  }
                </div>
                <p class="text-[11px] text-slate-500 leading-relaxed font-normal">
                  {{ profile.description }}
                </p>
              </div>

              <!-- Selection radio indicator -->
              <div class="flex items-center justify-between pt-2 border-t border-slate-100/80">
                <span class="text-[10px] font-mono text-slate-400 font-medium">
                  {{ profile.workers }} workers &middot; {{ profile.batching }}
                </span>
                <div class="flex items-center gap-1.5">
                  <span
                    class="w-3.5 h-3.5 rounded-full border flex items-center justify-center transition-colors"
                    [class.border-blue-600]="store.draft().profile === profile.id"
                    [class.bg-blue-600]="store.draft().profile === profile.id"
                    [class.border-slate-300]="store.draft().profile !== profile.id">
                    @if (store.draft().profile === profile.id) {
                      <span class="w-1.5 h-1.5 rounded-full bg-white"></span>
                    }
                  </span>
                </div>
              </div>

            </div>
          }
        </div>

        <!-- Effective Settings Preview Bar -->
        <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs text-slate-700">
          <div class="flex items-center divide-x divide-slate-200 text-xs w-full">
            <div class="pr-6 flex items-baseline gap-2">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Workers</span>
              <span class="font-bold text-slate-900 font-mono">{{ store.selectedProfileOption().workers }} parallel</span>
            </div>
            <div class="px-6 flex items-baseline gap-2">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Source Impact</span>
              <span class="font-semibold text-slate-800">{{ store.selectedProfileOption().sourceImpact }}</span>
            </div>
            <div class="px-6 flex items-baseline gap-2">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Target Impact</span>
              <span class="font-semibold text-slate-800">{{ store.selectedProfileOption().targetImpact }}</span>
            </div>
            <div class="pl-6 flex items-baseline gap-2">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Batching</span>
              <span class="font-semibold text-slate-800 font-mono">{{ store.selectedProfileOption().batching }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 2. TRANSFER & RESOURCE POLICY                                             -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            2. Transfer &amp; Resource Policy
          </h2>
          <span class="text-xs text-slate-400 font-normal">Network throttling and large object serialization posture</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Bandwidth Throttle -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3">
            <div class="flex flex-col gap-0.5">
              <span class="text-xs font-bold text-slate-900">Network Bandwidth Limit</span>
              <span class="text-[11px] text-slate-500">Throttle total network egress to protect shared corporate links.</span>
            </div>

            <div class="flex flex-col gap-2">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="bw_policy"
                  [checked]="store.draft().bandwidthPolicy === 'UNLIMITED'"
                  (change)="store.patchDraft({ bandwidthPolicy: 'UNLIMITED' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Automatic / Unlimited</span>
                <span class="text-[10px] text-slate-400">(Use available network throughput)</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="bw_policy"
                  [checked]="store.draft().bandwidthPolicy === 'LIMITED'"
                  (change)="store.patchDraft({ bandwidthPolicy: 'LIMITED' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Limit transfer rate</span>
              </label>

              @if (store.draft().bandwidthPolicy === 'LIMITED') {
                <div class="pl-6 pt-1 flex items-center gap-2 animate-in fade-in duration-100">
                  <input
                    type="number"
                    [ngModel]="store.draft().bandwidthLimitValue"
                    (ngModelChange)="store.patchDraft({ bandwidthLimitValue: $event })"
                    min="1"
                    class="w-24 h-8 px-2 text-xs bg-white border border-slate-200 rounded-md text-slate-900 font-mono focus:outline-none focus:border-blue-600" />
                  
                  <div class="w-24">
                    <app-custom-select
                      [options]="bandwidthUnitOptions"
                      [value]="store.draft().bandwidthLimitUnit"
                      (valueChange)="store.patchDraft({ bandwidthLimitUnit: $event })"
                      size="sm">
                    </app-custom-select>
                  </div>
                </div>
              }
            </div>
          </div>

          <!-- Large Objects (LOB) Policy -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3">
            <div class="flex flex-col gap-0.5">
              <span class="text-xs font-bold text-slate-900">Large Objects (LOB / JSON) Policy</span>
              <span class="text-[11px] text-slate-500">Determines handling of binary blobs, documents, and large text columns.</span>
            </div>

            <div class="flex flex-col gap-2">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="lob_policy"
                  [checked]="store.draft().lobPolicy === 'AUTOMATIC'"
                  (change)="store.patchDraft({ lobPolicy: 'AUTOMATIC' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Automatic</span>
                <span class="text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.2 rounded font-semibold">Recommended</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="lob_policy"
                  [checked]="store.draft().lobPolicy === 'INLINE'"
                  (change)="store.patchDraft({ lobPolicy: 'INLINE' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Inline small LOBs (&lt; 64 KB)</span>
                <span class="text-[10px] text-slate-400">(Faster for mostly compact JSON/text)</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="lob_policy"
                  [checked]="store.draft().lobPolicy === 'STREAMING'"
                  (change)="store.patchDraft({ lobPolicy: 'STREAMING' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Out-of-band streaming</span>
                <span class="text-[10px] text-slate-400">(Dedicated stream for gigabyte binaries)</span>
              </label>
            </div>
          </div>

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 3. RESILIENCE & FAILURE HANDLING                                          -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            3. Resilience &amp; Failure Handling
          </h2>
          <span class="text-xs text-slate-400 font-normal">Automated recovery and quarantine policy</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          
          <!-- Recovery Policy -->
          <div class="p-3.5 bg-white border border-slate-200 rounded-lg flex flex-col gap-2.5">
            <div class="flex flex-col gap-0.5">
              <span class="text-xs font-bold text-slate-900">Interrupted Recovery</span>
              <span class="text-[10px] text-slate-500">Behavior upon system crash or unexpected interruption.</span>
            </div>

            <div class="flex flex-col gap-1.5 pt-1">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="rec_policy"
                  [checked]="store.draft().recoveryPolicy === 'RESUME_CHECKPOINT'"
                  (change)="store.patchDraft({ recoveryPolicy: 'RESUME_CHECKPOINT' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Resume from checkpoint</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="rec_policy"
                  [checked]="store.draft().recoveryPolicy === 'PAUSE_OPERATOR'"
                  (change)="store.patchDraft({ recoveryPolicy: 'PAUSE_OPERATOR' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Pause for confirmation</span>
              </label>
            </div>
          </div>

          <!-- Transient Errors -->
          <div class="p-3.5 bg-white border border-slate-200 rounded-lg flex flex-col gap-2.5">
            <div class="flex flex-col gap-0.5">
              <span class="text-xs font-bold text-slate-900">Transient Failures</span>
              <span class="text-[10px] text-slate-500">Network timeouts or deadlock contention.</span>
            </div>

            <div class="flex flex-col gap-1.5 pt-1">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="trans_policy"
                  [checked]="store.draft().transientFailurePolicy === 'RETRY_BACKOFF'"
                  (change)="store.patchDraft({ transientFailurePolicy: 'RETRY_BACKOFF' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Retry automatically</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="trans_policy"
                  [checked]="store.draft().transientFailurePolicy === 'PAUSE_WORK'"
                  (change)="store.patchDraft({ transientFailurePolicy: 'PAUSE_WORK' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Pause affected work</span>
              </label>
            </div>
            <span class="text-[10px] text-slate-400 font-mono pt-1">3 attempts &middot; managed backoff</span>
          </div>

          <!-- Failed Records -->
          <div class="p-3.5 bg-white border border-slate-200 rounded-lg flex flex-col gap-2.5">
            <div class="flex flex-col gap-0.5">
              <span class="text-xs font-bold text-slate-900">Malformed Records</span>
              <span class="text-[10px] text-slate-500">Data type overflow or constraint rejection.</span>
            </div>

            <div class="flex flex-col gap-1.5 pt-1">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="fail_records_policy"
                  [checked]="store.draft().failedRecordsPolicy === 'QUARANTINE_CONTINUE'"
                  (change)="store.patchDraft({ failedRecordsPolicy: 'QUARANTINE_CONTINUE' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Quarantine &amp; continue</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="fail_records_policy"
                  [checked]="store.draft().failedRecordsPolicy === 'STOP_WORK'"
                  (change)="store.patchDraft({ failedRecordsPolicy: 'STOP_WORK' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Stop affected work</span>
              </label>
            </div>
          </div>

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 4. MODE CONFIGURATION (DYNAMIC BY CANONICAL MODE)                          -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <div class="flex items-center gap-2">
            <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              4. Mode Configuration
            </h2>
            <span class="text-slate-300 font-light">&middot;</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-50 text-blue-700 border border-blue-200">
              {{ store.modeDisplayTitle() }}
            </span>
          </div>
          <span class="text-xs text-slate-400 font-normal">Execution strategy parameters</span>
        </div>

        <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-4">
          
          <!-- M1: Bulk Migration -->
          @if (store.currentMode() === 'M1_BULK') {
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Partition Slicing Strategy</label>
                <app-custom-select
                  [options]="partitionOptions"
                  [value]="store.draft().modeM1.partitionStrategy"
                  (valueChange)="updateModeM1({ partitionStrategy: $event })"
                  size="sm">
                </app-custom-select>
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Partition Chunk Size (Rows)</label>
                <input
                  type="number"
                  [ngModel]="store.draft().modeM1.chunkSizeRows"
                  (ngModelChange)="updateModeM1({ chunkSizeRows: $event })"
                  class="h-7 px-2 text-xs bg-white border border-slate-200 rounded text-slate-900 font-mono focus:outline-none focus:border-blue-600" />
              </div>
              <div class="flex items-center pt-5">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    [checked]="store.draft().modeM1.directLoad"
                    (change)="updateModeM1({ directLoad: !store.draft().modeM1.directLoad })"
                    class="rounded border-slate-300 text-blue-600 focus:ring-0" />
                  <span class="text-xs font-semibold text-slate-800">Use native direct-path loader</span>
                </label>
              </div>
            </div>
          }

          <!-- M2: Bulk + CDC -->
          @if (store.currentMode() === 'M2_BULK_CDC') {
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Catch-up Lag Objective (Seconds)</label>
                <input
                  type="number"
                  [ngModel]="store.draft().modeM2.catchupLagTargetSec"
                  (ngModelChange)="updateModeM2({ catchupLagTargetSec: $event })"
                  min="1"
                  max="60"
                  class="h-7 px-2 text-xs bg-white border border-slate-200 rounded text-slate-900 font-mono focus:outline-none focus:border-blue-600" />
                <span class="text-[10px] text-slate-400">Target replication delay for cutover readiness</span>
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Conflict Policy</label>
                <app-custom-select
                  [options]="conflictPolicyOptions"
                  [value]="store.draft().modeM2.conflictPolicy"
                  (valueChange)="updateModeM2({ conflictPolicy: $event })"
                  size="sm">
                </app-custom-select>
                <span class="text-[10px] text-slate-400">Action on target write collision</span>
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Quiescence Wait (Seconds)</label>
                <input
                  type="number"
                  [ngModel]="store.draft().modeM2.quiescenceTimeoutSec"
                  (ngModelChange)="updateModeM2({ quiescenceTimeoutSec: $event })"
                  min="5"
                  max="300"
                  class="h-7 px-2 text-xs bg-white border border-slate-200 rounded text-slate-900 font-mono focus:outline-none focus:border-blue-600" />
                <span class="text-[10px] text-slate-400">Source silence duration during cutover</span>
              </div>
            </div>
          }

          <!-- M3: CDC Replication -->
          @if (store.currentMode() === 'M3_CDC') {
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Stream Start Position</label>
                <app-custom-select
                  [options]="cdcStartPositionOptions"
                  [value]="store.draft().modeM3.startPosition"
                  (valueChange)="updateModeM3({ startPosition: $event })"
                  size="sm">
                </app-custom-select>
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Micro-batch Window (ms)</label>
                <input
                  type="number"
                  [ngModel]="store.draft().modeM3.batchWindowMs"
                  (ngModelChange)="updateModeM3({ batchWindowMs: $event })"
                  min="50"
                  max="5000"
                  class="h-7 px-2 text-xs bg-white border border-slate-200 rounded text-slate-900 font-mono focus:outline-none focus:border-blue-600" />
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Apply Concurrency</label>
                <input
                  type="number"
                  [ngModel]="store.draft().modeM3.applyConcurrency"
                  (ngModelChange)="updateModeM3({ applyConcurrency: $event })"
                  min="1"
                  max="16"
                  class="h-7 px-2 text-xs bg-white border border-slate-200 rounded text-slate-900 font-mono focus:outline-none focus:border-blue-600" />
              </div>
            </div>
          }

          <!-- M4: Incremental Polling -->
          @if (store.currentMode() === 'M4_INCREMENTAL') {
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Default Watermark Column</label>
                <input
                  type="text"
                  [ngModel]="store.draft().modeM4.watermarkColumn"
                  (ngModelChange)="updateModeM4({ watermarkColumn: $event })"
                  placeholder="e.g. UPDATED_AT, LAST_MODIFIED"
                  class="h-7 px-2 text-xs bg-white border border-slate-200 rounded text-slate-900 font-mono focus:outline-none focus:border-blue-600" />
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Polling Interval (Seconds)</label>
                <input
                  type="number"
                  [ngModel]="store.draft().modeM4.pollingIntervalSec"
                  (ngModelChange)="updateModeM4({ pollingIntervalSec: $event })"
                  min="5"
                  max="3600"
                  class="h-7 px-2 text-xs bg-white border border-slate-200 rounded text-slate-900 font-mono focus:outline-none focus:border-blue-600" />
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Late-Arrival Lookback (Minutes)</label>
                <input
                  type="number"
                  [ngModel]="store.draft().modeM4.lookbackWindowMin"
                  (ngModelChange)="updateModeM4({ lookbackWindowMin: $event })"
                  min="0"
                  max="120"
                  class="h-7 px-2 text-xs bg-white border border-slate-200 rounded text-slate-900 font-mono focus:outline-none focus:border-blue-600" />
              </div>
            </div>
          }

          <!-- M5: State Synchronization -->
          @if (store.currentMode() === 'M5_STATE_SYNC') {
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Reconciliation Strategy</label>
                <app-custom-select
                  [options]="stateSyncReconciliationOptions"
                  [value]="store.draft().modeM5.reconciliationMode"
                  (valueChange)="updateModeM5({ reconciliationMode: $event })"
                  size="sm">
                </app-custom-select>
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Sync Check Cadence (Seconds)</label>
                <input
                  type="number"
                  [ngModel]="store.draft().modeM5.syncIntervalSec"
                  (ngModelChange)="updateModeM5({ syncIntervalSec: $event })"
                  min="30"
                  max="86400"
                  class="h-7 px-2 text-xs bg-white border border-slate-200 rounded text-slate-900 font-mono focus:outline-none focus:border-blue-600" />
              </div>
            </div>
          }

          <!-- M6: Schema Only -->
          @if (store.currentMode() === 'M6_SCHEMA_ONLY') {
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="flex items-center pt-2">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    [checked]="store.draft().modeM6.transactionalDdl"
                    (change)="updateModeM6({ transactionalDdl: !store.draft().modeM6.transactionalDdl })"
                    class="rounded border-slate-300 text-blue-600 focus:ring-0" />
                  <span class="text-xs font-semibold text-slate-800">Atomic transactional DDL execution</span>
                </label>
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Foreign Key &amp; Index Creation Timing</label>
                <app-custom-select
                  [options]="fkTimingOptions"
                  [value]="store.draft().modeM6.fkIndexTiming"
                  (valueChange)="updateModeM6({ fkIndexTiming: $event })"
                  size="sm">
                </app-custom-select>
              </div>
            </div>
          }

          <!-- M7: Data Only -->
          @if (store.currentMode() === 'M7_DATA_ONLY') {
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">Pre-existing Destination Data</label>
                <app-custom-select
                  [options]="dataOnlyTargetReadinessOptions"
                  [value]="store.draft().modeM7.targetReadiness"
                  (valueChange)="updateModeM7({ targetReadiness: $event })"
                  size="sm">
                </app-custom-select>
              </div>

              <div class="flex items-center pt-5">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    [checked]="store.draft().modeM7.requireSchemaAttestation"
                    (change)="updateModeM7({ requireSchemaAttestation: !store.draft().modeM7.requireSchemaAttestation })"
                    class="rounded border-slate-300 text-blue-600 focus:ring-0" />
                  <span class="text-xs font-semibold text-slate-800">Verify schema presence before loading</span>
                </label>
              </div>
            </div>
          }

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 5. VALIDATION & ASSURANCE                                                 -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            5. Validation &amp; Assurance
          </h2>
          <span class="text-xs text-slate-400 font-normal">Data parity and checksum audit depth</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          @for (opt of store.validationOptions(); track opt.id) {
            <div
              (click)="store.patchDraft({ validationDepth: opt.id })"
              class="p-3 border rounded-lg cursor-pointer bg-white transition-colors select-none flex flex-col justify-between gap-2.5 min-h-[90px]"
              [class.border-blue-600]="store.draft().validationDepth === opt.id"
              [class.ring-1]="store.draft().validationDepth === opt.id"
              [class.ring-blue-600]="store.draft().validationDepth === opt.id"
              [class.bg-blue-50]="store.draft().validationDepth === opt.id"
              [class.border-slate-200]="store.draft().validationDepth !== opt.id"
              [class.hover:border-slate-300]="store.draft().validationDepth !== opt.id"
              [class.hover:bg-slate-50]="store.draft().validationDepth !== opt.id">
              
              <div class="flex flex-col gap-1">
                <div class="flex items-center justify-between">
                  <span class="text-xs font-bold text-slate-900">{{ opt.title }}</span>
                  @if (opt.badge) {
                    <span class="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-blue-100 text-blue-700 border border-blue-200">
                      {{ opt.badge }}
                    </span>
                  }
                </div>
                <p class="text-[11px] text-slate-500 leading-normal font-normal">
                  {{ opt.description }}
                </p>
              </div>

              <div class="flex items-center justify-between pt-1.5 border-t border-slate-100/80">
                <span class="text-[10px] text-slate-400 font-mono">Impact: {{ opt.relativeImpact }}</span>
                <span
                  class="w-3.5 h-3.5 rounded-full border flex items-center justify-center transition-colors"
                  [class.border-blue-600]="store.draft().validationDepth === opt.id"
                  [class.bg-blue-600]="store.draft().validationDepth === opt.id"
                  [class.border-slate-300]="store.draft().validationDepth !== opt.id">
                  @if (store.draft().validationDepth === opt.id) {
                    <span class="w-1.5 h-1.5 rounded-full bg-white"></span>
                  }
                </span>
              </div>

            </div>
          }
        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 6. EXECUTION CONSTRAINTS                                                  -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            6. Execution Constraints
          </h2>
          <span class="text-xs text-slate-400 font-normal">Operating windows and custom pre/post action hooks</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Allowed Execution Window -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3">
            <div class="flex flex-col gap-0.5">
              <span class="text-xs font-bold text-slate-900">Allowed Execution Schedule</span>
              <span class="text-[11px] text-slate-500">Define operational hours permitted for heavy data transport.</span>
            </div>

            <div class="flex flex-col gap-2">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="window_choice"
                  [checked]="store.draft().executionWindowChoice === 'ANYTIME'"
                  (change)="store.patchDraft({ executionWindowChoice: 'ANYTIME' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Anytime (No schedule restriction)</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="window_choice"
                  [checked]="store.draft().executionWindowChoice === 'RESTRICTED'"
                  (change)="store.patchDraft({ executionWindowChoice: 'RESTRICTED' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-semibold text-slate-800">Restricted maintenance window</span>
              </label>

              @if (store.draft().executionWindowChoice === 'RESTRICTED') {
                <div class="pl-6 pt-1 flex items-center gap-3 animate-in fade-in duration-100">
                  <div class="flex items-center gap-1.5">
                    <span class="text-[11px] text-slate-500">From:</span>
                    <input
                      type="time"
                      [ngModel]="store.draft().executionWindowStart"
                      (ngModelChange)="store.patchDraft({ executionWindowStart: $event })"
                      class="h-7 px-2 text-xs bg-white border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-600" />
                  </div>
                  <div class="flex items-center gap-1.5">
                    <span class="text-[11px] text-slate-500">To:</span>
                    <input
                      type="time"
                      [ngModel]="store.draft().executionWindowEnd"
                      (ngModelChange)="store.patchDraft({ executionWindowEnd: $event })"
                      class="h-7 px-2 text-xs bg-white border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-600" />
                  </div>
                </div>
              }
            </div>
          </div>

          <!-- Pre/Post Actions & Governance Summary -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col justify-between gap-3">
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-slate-900">Pre / Post Execution Actions</span>
                <button
                  type="button"
                  (click)="store.openAddCustomAction('PRE_MIGRATION')"
                  class="text-[11px] font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1 cursor-pointer">
                  <span>+ Configure SQL Actions</span>
                </button>
              </div>

              @if (store.draft().customActions.length === 0) {
                <p class="text-[11px] text-slate-500 font-normal leading-relaxed">
                  No custom SQL scripts configured. Standard schema and table migration hooks will run directly.
                </p>
              } @else {
                <div class="flex flex-col gap-1 max-h-24 overflow-y-auto">
                  @for (action of store.draft().customActions; track action.id) {
                    <div class="p-1.5 bg-slate-50 border border-slate-200 rounded flex items-center justify-between text-xs">
                      <div class="flex items-center gap-1.5 truncate">
                        <app-lucide-icon name="file-code" [size]="12" class="text-blue-600 shrink-0"></app-lucide-icon>
                        <span class="font-semibold text-slate-800 truncate">{{ action.name }}</span>
                        <span class="text-[10px] text-slate-400">({{ action.hookLabel }})</span>
                      </div>
                      <button
                        type="button"
                        (click)="store.openEditCustomAction(action)"
                        class="text-[10px] font-semibold text-slate-600 hover:text-blue-600 cursor-pointer">
                        Edit
                      </button>
                    </div>
                  }
                </div>
              }
            </div>

            <!-- Inherited Enterprise Requirements -->
            <div class="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
              <div class="flex items-center gap-1.5">
                <app-lucide-icon name="shield" [size]="12" class="text-indigo-600"></app-lucide-icon>
                <span>{{ store.summaryMetrics().inheritedPoliciesCount }} inherited enterprise policies apply</span>
              </div>
              <span class="text-[10px] font-mono text-slate-400">{{ store.environment() }}</span>
            </div>
          </div>

        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 7. CONFIGURATION SUMMARY                                                  -->
      <!-- ========================================================================= -->
      <section class="p-4 bg-slate-50 border border-slate-200 rounded-lg flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="check-circle-2" [size]="14" class="text-emerald-600"></app-lucide-icon>
            <span class="text-xs font-bold text-slate-800">Configuration Summary</span>
          </div>
          @if (store.isCustomized()) {
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
              Customized &middot; {{ store.totalOverridesCount() }} advanced override{{ store.totalOverridesCount() > 1 ? 's' : '' }}
            </span>
          } @else {
            <span class="text-[11px] font-medium text-slate-500">
              Standard Balanced Baseline
            </span>
          }
        </div>

        <p class="text-xs text-slate-600 leading-relaxed font-medium">
          {{ store.summaryMetrics().profileLabel }} execution &middot; {{ store.summaryMetrics().bandwidthSummary }} &middot; {{ store.summaryMetrics().recoverySummary }} &middot; {{ store.summaryMetrics().quarantineSummary }} &middot; {{ store.summaryMetrics().modeSummary }} &middot; {{ store.summaryMetrics().validationSummary }} &middot; {{ store.summaryMetrics().windowSummary }}
        </p>

        <div class="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
          <span>{{ store.summaryMetrics().inheritedPoliciesCount }} inherited values &middot; {{ store.summaryMetrics().customOverridesCount }} custom overrides</span>
          <span class="text-emerald-700 font-semibold flex items-center gap-1">
            <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
            <span>Ready for Plan Compilation</span>
          </span>
        </div>
      </section>

    </div>
  `
})
export class ConfigurationStandardComponent {
  public store = inject(Step6ConfigurationStoreService);

  public readonly bandwidthUnitOptions = [
    { label: 'MB/s', value: 'MB/s' },
    { label: 'Gb/s', value: 'Gb/s' }
  ];

  public readonly partitionOptions = [
    { label: 'Automatic — Provider optimized', value: 'AUTOMATIC' },
    { label: 'Hash Partitioning — Uniform distribution', value: 'HASH' },
    { label: 'Range Slicing — Primary key numerical boundaries', value: 'RANGE' }
  ];

  public readonly conflictPolicyOptions = [
    { label: 'Latest Timestamp Wins', value: 'LATEST_WINS' },
    { label: 'Source Overwrite Target', value: 'SOURCE_WINS' },
    { label: 'Fail on Conflict', value: 'FAIL_ON_CONFLICT' }
  ];

  public readonly cdcStartPositionOptions = [
    { label: 'Immediate — Current live log tail', value: 'IMMEDIATE' },
    { label: 'Current SCN — Exact commit number at launch', value: 'CURRENT_SCN' },
    { label: 'Timestamp — Historical point in time', value: 'TIMESTAMP' }
  ];

  public readonly stateSyncReconciliationOptions = [
    { label: 'One-Way Align — Target matches source', value: 'ONE_WAY_ALIGN' },
    { label: 'Bidirectional Audit — Report divergence only', value: 'BIDIRECTIONAL_REPORT' }
  ];

  public readonly fkTimingOptions = [
    { label: 'Deferred — Build after all tables complete', value: 'DEFERRED' },
    { label: 'Inline — Build concurrently with table', value: 'INLINE' }
  ];

  public readonly dataOnlyTargetReadinessOptions = [
    { label: 'Truncate — Clean target tables first', value: 'TRUNCATE' },
    { label: 'Append — Retain existing records and insert', value: 'APPEND' },
    { label: 'Upsert — Merge on matching primary key', value: 'UPSERT' }
  ];

  public updateModeM1(patch: any): void {
    this.store.patchDraft({ modeM1: { ...this.store.draft().modeM1, ...patch } });
  }

  public updateModeM2(patch: any): void {
    this.store.patchDraft({ modeM2: { ...this.store.draft().modeM2, ...patch } });
  }

  public updateModeM3(patch: any): void {
    this.store.patchDraft({ modeM3: { ...this.store.draft().modeM3, ...patch } });
  }

  public updateModeM4(patch: any): void {
    this.store.patchDraft({ modeM4: { ...this.store.draft().modeM4, ...patch } });
  }

  public updateModeM5(patch: any): void {
    this.store.patchDraft({ modeM5: { ...this.store.draft().modeM5, ...patch } });
  }

  public updateModeM6(patch: any): void {
    this.store.patchDraft({ modeM6: { ...this.store.draft().modeM6, ...patch } });
  }

  public updateModeM7(patch: any): void {
    this.store.patchDraft({ modeM7: { ...this.store.draft().modeM7, ...patch } });
  }
}
