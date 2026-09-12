import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MonitoringService } from '../services/monitoring.service';

@Component({
  selector: 'app-monitoring-summary-strip',
  standalone: true,
  imports: [CommonModule],
  template: `
    <!-- Operational Summary (Section 1) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
      
      <!-- 1. Overall Platform State -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between h-34 select-none">
        <div class="flex items-center justify-between gap-2">
          <span class="text-[10px] sm:text-[11px] font-bold text-slate-500 uppercase tracking-wider">Platform</span>
          @if (ms.summary()?.overall_platform_health === 'HEALTHY') {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              <span>Healthy</span>
            </span>
          } @else if (ms.summary()?.overall_platform_health === 'DEGRADED') {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 shrink-0">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
              <span>Degraded</span>
            </span>
          } @else if (ms.summary()?.overall_platform_health === 'UNHEALTHY') {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 shrink-0">
              <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
              <span>Unhealthy</span>
            </span>
          } @else {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 shrink-0">
              <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
              <span>Unknown</span>
            </span>
          }
        </div>
        <div class="flex flex-col gap-0.5">
          <span class="text-2xl font-bold font-mono text-slate-900 tracking-tight leading-none">
            {{ ms.summary()?.overall_platform_health || 'HEALTHY' }}
          </span>
          <span class="text-xs text-slate-500 font-medium truncate mt-1">
            All execution paths nominal
          </span>
        </div>
      </div>

      <!-- 2. Telemetry Confidence / Freshness -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between h-34 select-none">
        <div class="flex items-center justify-between gap-2">
          <span class="text-[10px] sm:text-[11px] font-bold text-slate-500 uppercase tracking-wider">Telemetry</span>
          @if (ms.telemetryConfidence() === 'CURRENT') {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              <span>Current</span>
            </span>
          } @else if (ms.telemetryConfidence() === 'STALE') {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 shrink-0">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
              <span>Stale</span>
            </span>
          } @else {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 shrink-0">
              <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
              <span>No Data</span>
            </span>
          }
        </div>
        <div class="flex flex-col gap-0.5">
          <span class="text-2xl font-bold font-mono text-slate-900 tracking-tight leading-none">
            {{ ms.formatObservationTime(ms.lastObservedAt()) }}
          </span>
          <span class="text-xs text-slate-500 font-mono truncate mt-1" [title]="ms.lastObservedAt() || ''">
            Canonical UTC observation
          </span>
        </div>
      </div>

      <!-- 3. Active Workloads (M1-M7) -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between h-34 select-none">
        <div class="flex items-center justify-between gap-2">
          <span class="text-[10px] sm:text-[11px] font-bold text-slate-500 uppercase tracking-wider">Active Fleet</span>
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 shrink-0">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            <span>Active</span>
          </span>
        </div>
        <div class="flex flex-col gap-0.5">
          <div class="flex items-baseline gap-2">
            <span class="text-2xl font-bold font-mono text-slate-900 tracking-tight leading-none tabular-nums">
              {{ ms.activeMigrationCount() }}
            </span>
            <span class="text-xs font-mono text-slate-500">active</span>
          </div>
          <span class="text-xs text-slate-500 font-medium truncate mt-1">
            {{ ms.activeMigrations().length }} registered migrations
          </span>
        </div>
      </div>

      <!-- 4. Platform Engine Connection -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between h-34 select-none">
        <div class="flex items-center justify-between gap-2">
          <span class="text-[10px] sm:text-[11px] font-bold text-slate-500 uppercase tracking-wider">Engine Bridge</span>
          @if (ms.summary()?.engine_connection_state === 'CONNECTED') {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              <span>Pipe Active</span>
            </span>
          } @else {
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 shrink-0">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
              <span>Disconnected</span>
            </span>
          }
        </div>
        <div class="flex flex-col gap-0.5">
          <span class="text-lg font-bold font-mono text-slate-900 tracking-tight leading-none truncate">
            Named Pipe IPC
          </span>
          <span class="text-xs text-slate-500 font-medium truncate mt-1">
            Decoupled engine daemon
          </span>
        </div>
      </div>

    </div>
  `
})
export class MonitoringSummaryStripComponent {
  public ms = inject(MonitoringService);
}
