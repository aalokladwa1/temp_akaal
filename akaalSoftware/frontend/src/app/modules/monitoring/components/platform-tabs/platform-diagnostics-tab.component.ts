/**
 * AKAAL Monitoring — Part 3 of 4: Platform Diagnostics Tab Component
 * Deep technical investigation surface with global correlation context,
 * light-themed bounded runtime logs, diagnostic event stream, and telemetry exporter status.
 */

import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { PlatformMonitoringService } from '../../services/platform-monitoring.service';

@Component({
  selector: 'app-platform-diagnostics-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Scoped Global Correlation Context -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Scoped Global Correlation Context</h3>
          <div class="flex items-center gap-2 text-xs">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span class="font-semibold text-slate-700">Distributed Tracing Active</span>
          </div>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
            <span class="text-[11px] text-slate-500">Global Trace ID</span>
            <span class="font-mono font-bold text-slate-800 truncate" [title]="pms.diagnostics().correlation_context.global_trace_id">
              {{ pms.diagnostics().correlation_context.global_trace_id }}
            </span>
          </div>

          <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
            <span class="text-[11px] text-slate-500">Global Run ID</span>
            <span class="font-mono font-bold text-slate-800 truncate">
              {{ pms.diagnostics().correlation_context.run_id }}
            </span>
          </div>

          <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
            <span class="text-[11px] text-slate-500">Active Session ID</span>
            <span class="font-mono font-bold text-slate-800 truncate">
              {{ pms.diagnostics().correlation_context.session_id }}
            </span>
          </div>

          <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex flex-col gap-0.5">
            <span class="text-[11px] text-slate-500">Engine Fingerprint</span>
            <span class="font-mono font-bold text-slate-800 truncate" [title]="pms.diagnostics().correlation_context.engine_fingerprint">
              {{ pms.diagnostics().correlation_context.engine_fingerprint.substring(0, 16) }}...
            </span>
          </div>
        </div>
      </div>

      <!-- 2. Bounded Runtime Log Viewer (Calm, Light Enterprise Aesthetic) -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-3">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Bounded Runtime Logs</h3>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-700">Bounded Ring Buffer</span>
          </div>

          <!-- Log Search & Level Filter with Global Design System Select -->
          <div class="flex items-center gap-2 text-xs">
            <input
              type="text"
              [ngModel]="logFilterQuery()"
              (ngModelChange)="logFilterQuery.set($event)"
              placeholder="Filter logs..."
              class="h-8 px-2.5 rounded-md border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 bg-white">

            <div class="w-32">
              <app-custom-select
                [options]="logLevelOptions"
                [value]="logLevelFilter()"
                (valueChange)="logLevelFilter.set($event)"
                [placeholder]="'All Levels'"
                [size]="'sm'">
              </app-custom-select>
            </div>
          </div>
        </div>

        <div class="bg-slate-50 border border-slate-200/90 rounded-xl p-3 font-mono text-[11px] max-h-72 overflow-y-auto space-y-1 select-text">
          @for (log of filteredLogs(); track log.id) {
            <div class="flex items-start gap-2.5 hover:bg-white p-1.5 rounded transition-colors border-b border-slate-100 last:border-0">
              <span class="text-slate-400 shrink-0 font-mono text-[10.5px]">{{ log.timestamp | date:'HH:mm:ss.SSS' }}</span>
              <span 
                class="px-1.5 py-0.2 rounded font-bold shrink-0 text-[10px]"
                [ngClass]="{
                  'bg-emerald-50 text-emerald-700 border border-emerald-200/60': log.level === 'INFO',
                  'bg-blue-50 text-blue-700 border border-blue-200/60': log.level === 'DEBUG',
                  'bg-amber-50 text-amber-700 border border-amber-200/60': log.level === 'WARN',
                  'bg-rose-50 text-rose-700 border border-rose-200/60': log.level === 'ERROR'
                }">
                {{ log.level }}
              </span>
              <span class="text-slate-500 font-medium shrink-0 max-w-[180px] truncate" [title]="log.logger">{{ log.logger }}</span>
              <span class="text-slate-800 flex-1 leading-relaxed">{{ log.message }}</span>
            </div>
          }
          @if (filteredLogs().length === 0) {
            <div class="text-slate-400 text-center py-5 text-xs font-sans">No log lines match current filter criteria.</div>
          }
        </div>
      </div>

      <!-- 3. Telemetry Exporters & Collector Seams -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Telemetry Exporters &amp; Collector Seams</h3>
          <span class="text-xs text-slate-500 font-medium">{{ pms.diagnostics().telemetry_exporters.length }} active exporters</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          @for (exp of pms.diagnostics().telemetry_exporters; track exp.exporter_name) {
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between gap-2.5 text-xs">
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-900">{{ exp.exporter_name }}</span>
                <span class="flex items-center gap-1.5 text-slate-700 font-medium">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  {{ exp.status }}
                </span>
              </div>
              <div class="text-[11px] font-mono text-slate-500">{{ exp.protocol }}</div>
              <div class="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-2 border-t border-slate-200/60">
                <span class="truncate max-w-[200px]" [title]="exp.collector_endpoint">{{ exp.collector_endpoint }}</span>
                <span class="font-bold text-emerald-700">{{ exp.delivery_rate_pct }}% Delivery</span>
              </div>
            </div>
          }
        </div>
      </div>

      <!-- 4. Diagnostic Event Stream -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Diagnostic Event Stream</h3>
          <span class="text-xs text-slate-500 font-medium">{{ pms.diagnostics().runtime_events.length }} events recorded</span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-600">
            <thead>
              <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                <th class="py-2.5 px-3">Timestamp</th>
                <th class="py-2.5 px-3">Event Type</th>
                <th class="py-2.5 px-3">Component</th>
                <th class="py-2.5 px-3">Message</th>
                <th class="py-2.5 px-3 text-right">Severity</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (evt of pms.diagnostics().runtime_events; track evt.id) {
                <tr class="hover:bg-slate-50/50 transition-colors">
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-500">{{ evt.timestamp | date:'HH:mm:ss' }}</td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-bold text-slate-900">{{ pms.formatText(evt.event_type) }}</td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-700">{{ evt.component }}</td>
                  <td class="py-2.5 px-3 text-slate-800">{{ evt.message }}</td>
                  <td class="py-2.5 px-3 whitespace-nowrap text-right">
                    <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                      {{ evt.severity }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class PlatformDiagnosticsTabComponent {
  public pms = inject(PlatformMonitoringService);

  public logFilterQuery = signal<string>('');
  public logLevelFilter = signal<string>('ALL');

  public logLevelOptions: CustomSelectOption[] = [
    { label: 'All Levels', value: 'ALL', desc: 'Show all log severity levels' },
    { label: 'DEBUG', value: 'DEBUG', desc: 'Detailed debugging traces' },
    { label: 'INFO', value: 'INFO', desc: 'Informational execution milestones' },
    { label: 'WARN', value: 'WARN', desc: 'Warnings and non-fatal anomalies' },
    { label: 'ERROR', value: 'ERROR', desc: 'Errors and failed operations' }
  ];

  public filteredLogs = computed(() => {
    const list = this.pms.diagnostics().bounded_logs || [];
    const q = this.logFilterQuery().trim().toLowerCase();
    const level = this.logLevelFilter();

    return list.filter(l => {
      if (level !== 'ALL' && l.level !== level) return false;
      if (q && !l.message.toLowerCase().includes(q) && !l.logger.toLowerCase().includes(q)) return false;
      return true;
    });
  });
}
