import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';

@Component({
  selector: 'app-mission-control-view',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150">
      
      @if (!ms.activeMigration()) {
        <div class="p-12 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col items-center justify-center text-center gap-2">
          <span class="text-sm font-bold text-slate-800">No active migration in execution</span>
          <p class="text-xs text-slate-500 font-medium max-w-sm">Mission control telemetry activates when a migration workflow is running or staged.</p>
        </div>
      } @else {
        <!-- Top Telemetry Summary Ribbon -->
        <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div class="flex flex-col gap-0.5">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Execution Stage</span>
              <h2 class="text-xl font-bold text-slate-900">{{ ms.activeMigration()?.currentStage }}</h2>
            </div>

            <div class="flex items-center gap-6">
              <div class="flex flex-col text-right">
                <span class="text-xs font-semibold text-slate-500">Estimated Time to Catch-up</span>
                <span class="text-base font-bold text-slate-900">{{ ms.activeMigration()?.etaString }}</span>
              </div>
            </div>
          </div>

          <!-- Stage Progress Bar -->
          <div class="flex flex-col gap-1.5 pt-2">
            <div class="flex justify-between text-xs font-semibold text-slate-700">
              <span>Stage Progress</span>
              <span>{{ ms.activeMigration()?.progressPercent }}%</span>
            </div>
            <div class="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
              <div class="h-full bg-blue-600 rounded-full transition-all duration-300" [style.width.%]="ms.activeMigration()?.progressPercent"></div>
            </div>
          </div>
        </div>

        <!-- Mode-Specific Live Cockpits -->
        @switch (ms.activeMigration()?.mode) {
          
          <!-- M1: BULK ONLY -->
          @case ('M1_BULK') {
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Throughput</span>
                <span class="text-2xl font-bold text-slate-900">{{ ms.activeMigration()?.throughputRowsSec | number }} r/s</span>
                <span class="text-[11px] text-emerald-700 font-semibold">Bulk Stream Verified</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Partition Workers</span>
                <span class="text-2xl font-bold text-slate-900">8 / 8 Active</span>
                <span class="text-[11px] text-slate-500 font-semibold">Zero Thread Starvation</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">State Seal</span>
                <span class="text-2xl font-bold text-blue-700">SHA-256 Armed</span>
                <span class="text-[11px] text-slate-500 font-semibold">Immutable Checkpoints</span>
              </div>
            </div>
          }

          <!-- M2: BULK + CDC -->
          @case ('M2_BULK_CDC') {
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Throughput</span>
                <span class="text-2xl font-bold text-slate-900">{{ ms.activeMigration()?.throughputRowsSec | number }} r/s</span>
                <span class="text-[11px] text-emerald-700 font-semibold">Bulk Stream Verified</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">CDC Replication Lag</span>
                <span class="text-2xl font-bold text-emerald-700">{{ ms.activeMigration()?.cdcLagMs ?? 0 }}ms</span>
                <span class="text-[11px] text-slate-500 font-semibold">Target Catch-up Active</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Memory Ring Buffer</span>
                <span class="text-2xl font-bold text-slate-900">142 MB / 2048 MB</span>
                <span class="text-[11px] text-slate-500 font-semibold">7% Capacity</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-amber-800 uppercase">Cutover Readiness</span>
                <span class="text-2xl font-bold text-amber-800">Ready</span>
                <span class="text-[11px] text-amber-700 font-bold">Awaiting Quorum Approval</span>
              </div>
            </div>
          }

          <!-- M3: CDC ONLY (No Bulk) -->
          @case ('M3_CDC') {
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Real-Time Streaming Lag</span>
                <span class="text-2xl font-bold text-emerald-700">{{ ms.activeMigration()?.cdcLagMs ?? 0 }}ms</span>
                <span class="text-[11px] text-slate-500 font-semibold">LogMiner Transaction Tail</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Event Ingestion</span>
                <span class="text-2xl font-bold text-slate-900">4,280 ev/s</span>
                <span class="text-[11px] text-slate-500 font-semibold">WAL Micro-batches</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Transaction SCN</span>
                <span class="text-2xl font-bold text-blue-700 font-mono text-lg">948,201,489</span>
                <span class="text-[11px] text-slate-500 font-semibold">Sequence Verified</span>
              </div>
            </div>
          }

          <!-- M4: INCREMENTAL WATERMARK -->
          @case ('M4_INCREMENTAL') {
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Watermark Position</span>
                <span class="text-2xl font-bold text-slate-900 font-mono text-sm">2026-08-28 12:40:00 UTC</span>
                <span class="text-[11px] text-slate-500 font-semibold">Column: updated_at</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Lookback Overlap</span>
                <span class="text-2xl font-bold text-blue-700">120 sec</span>
                <span class="text-[11px] text-slate-500 font-semibold">Deduplication Survivor Active</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Next Polling Cycle</span>
                <span class="text-2xl font-bold text-emerald-700">00:34</span>
                <span class="text-[11px] text-slate-500 font-semibold">Scheduled Micro-batch</span>
              </div>
            </div>
          }

          <!-- M5: STATE SYNC -->
          @case ('M5_STATE_SYNC') {
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Merkle Tree Comparison</span>
                <span class="text-2xl font-bold text-slate-900">Depth 8 &bull; XXHash64</span>
                <span class="text-[11px] text-slate-500 font-semibold">256 Partition Leaves</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Mismatched Leaves</span>
                <span class="text-2xl font-bold text-amber-700">2 / 256</span>
                <span class="text-[11px] text-slate-500 font-semibold">0.78% Range Drift</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Auto-Repair Queue</span>
                <span class="text-2xl font-bold text-blue-700">18 Records</span>
                <span class="text-[11px] text-slate-500 font-semibold">Safe Patch Plan Ready</span>
              </div>
            </div>
          }

          <!-- M6: SCHEMA ONLY -->
          @case ('M6_SCHEMA_ONLY') {
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">DDL Objects Translated</span>
                <span class="text-2xl font-bold text-slate-900">482 / 482</span>
                <span class="text-[11px] text-emerald-700 font-semibold">100% Topological Accuracy</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Deferred Foreign Keys</span>
                <span class="text-2xl font-bold text-blue-700">94 Constraints</span>
                <span class="text-[11px] text-slate-500 font-semibold">Deferred for Bulk Speed</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Transaction Status</span>
                <span class="text-2xl font-bold text-emerald-700">COMMITTED</span>
                <span class="text-[11px] text-slate-500 font-semibold">Target Schema Initialized</span>
              </div>
            </div>
          }

          <!-- M7: DATA ONLY -->
          @case ('M7_DATA_ONLY') {
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Binary Stream Volume</span>
                <span class="text-2xl font-bold text-slate-900">1.2B Rows</span>
                <span class="text-[11px] text-emerald-700 font-semibold">Direct Memory Injection</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Throughput</span>
                <span class="text-2xl font-bold text-blue-700">142,000 r/s</span>
                <span class="text-[11px] text-slate-500 font-semibold">Max IOPS Active</span>
              </div>
              <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-500 uppercase">Data Cleansing / Masking</span>
                <span class="text-2xl font-bold text-emerald-700">PCI-DSS Passed</span>
                <span class="text-[11px] text-slate-500 font-semibold">Zero Unmasked Leaks</span>
              </div>
            </div>
          }
        }
      }

    </div>
  `
})
export class MissionControlViewComponent {
  public ms = inject(MigrationUiService);
}
