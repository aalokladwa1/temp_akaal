import { Component, Input, HostBinding } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ActiveMigration } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-active-migrations',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between gap-6 shadow-xs h-full flex-1">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-200">
        <div class="flex items-center gap-3">
          <app-lucide-icon name="arrow-left-right" [size]="20" class="text-slate-700 dark:text-slate-300"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Active Migrations</h2>
        </div>
        <button
          type="button"
          (click)="goToMigration()"
          class="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1 cursor-pointer select-none">
          <span>View all</span>
          <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
        </button>
      </div>

      <!-- Migrations Table / Empty State -->
      @if (migrations.length === 0) {
        <div class="py-10 flex flex-col items-center justify-center text-center gap-2.5 my-auto">
          <div class="w-10 h-10 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-400 dark:text-slate-500">
            <app-lucide-icon name="database" [size]="20"></app-lucide-icon>
          </div>
          <span class="text-xs font-bold text-slate-800">No active migrations</span>
          <p class="text-[11px] text-slate-500 font-medium max-w-sm">Running migrations will appear here when the engine executes pipelines.</p>
          <button
            type="button"
            (click)="createMigration()"
            class="mt-1 h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer flex items-center gap-2 select-none">
            <app-lucide-icon name="plus" [size]="14"></app-lucide-icon>
            <span>Create Migration</span>
          </button>
        </div>
      } @else {
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse table-fixed">
            <thead>
              <tr class="border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider select-none bg-slate-50/70">
                <th class="py-2.5 px-4 w-48">Migration</th>
                <th class="py-2.5 px-3 w-32">Mode</th>
                <th class="py-2.5 px-3 w-28">State</th>
                <th class="py-2.5 px-3">Telemetry</th>
                <th class="py-2.5 px-4 w-24 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200/80 text-xs font-medium">
              @for (m of migrations; track m.id; let even = $even) {
                <tr class="h-14 hover:bg-blue-50/30 transition-colors" [class.bg-slate-50]="!even">
                  <td class="px-4 py-3 truncate">
                    <div class="flex flex-col gap-0.5">
                      <span class="font-bold text-slate-900 hover:text-blue-600 cursor-pointer truncate" (click)="goToCockpit(m.id)">{{ m.name }}</span>
                      <span class="text-[11px] text-slate-500">{{ m.sourceEngine }} &rarr; {{ m.targetEngine }}</span>
                    </div>
                  </td>
                  <td class="px-3 py-3">
                    <span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 select-none">
                      {{ formatMode(m.mode) }}
                    </span>
                  </td>
                  <td class="px-3 py-3">
                    <span 
                      class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold border select-none"
                      [ngClass]="getStateBadgeClasses(m.state)">
                      <span class="w-1.5 h-1.5 rounded-full" [ngClass]="getStateDotClasses(m.state)"></span>
                      <span>{{ getStateLabel(m.state) }}</span>
                    </span>
                  </td>
                  <td class="px-3 py-3">
                    @if (m.mode === 'M1_BULK' || m.mode === 'M2_BULK_CDC' || m.mode === 'M7_DATA_ONLY') {
                      <div class="flex flex-col gap-1 max-w-[200px]">
                        <div class="flex justify-between text-[11px] text-slate-600 font-medium">
                          <span>Progress: {{ m.progressPercent !== null && m.progressPercent !== undefined ? m.progressPercent + '%' : '—' }}</span>
                          <span class="tabular-nums">{{ formatNumber(m.throughputRowsSec) }} r/s</span>
                        </div>
                        <div class="w-full h-1.5 rounded-full bg-slate-100 overflow-hidden">
                          <div class="h-full bg-blue-600 rounded-full" [style.width.%]="m.progressPercent ?? 0"></div>
                        </div>
                      </div>
                    } @else if (m.mode === 'M3_CDC_CONTINUOUS') {
                      <div class="flex items-center gap-2.5 text-[11px]">
                        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        <span class="text-emerald-700 font-bold tabular-nums">Lag: {{ m.cdcLagMs !== null && m.cdcLagMs !== undefined ? m.cdcLagMs + 'ms' : '—' }}</span>
                        <span class="text-slate-300">&bull;</span>
                        <span class="text-slate-600 tabular-nums">{{ formatNumber(m.cdcBacklogEvents) }} evts</span>
                      </div>
                    } @else if (m.mode === 'M4_INCREMENTAL' || m.mode === 'M5_STATE_SYNC') {
                      <div class="flex items-center gap-2 text-[11px] text-slate-600">
                        <span class="text-slate-500 truncate max-w-[150px]">WM: {{ m.lastWatermark || 'None' }}</span>
                        @if (m.reconciliationState) {
                          <span class="text-slate-300">&bull;</span>
                          <span class="text-slate-700 font-medium">{{ m.reconciliationState }}</span>
                        }
                      </div>
                    } @else {
                      <span class="text-[11px] text-slate-500">Pipeline active</span>
                    }
                  </td>
                  <td class="px-4 py-3 text-right">
                    <button
                      type="button"
                      (click)="goToCockpit(m.id)"
                      class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs shadow-2xs transition-colors cursor-pointer select-none">
                      Manage
                    </button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }

    </div>
  `
})
export class ActiveMigrationsComponent {
  @HostBinding('class') public hostClass = 'flex flex-col h-full flex-1';
  @Input() public migrations: ActiveMigration[] = [];

  constructor(private router: Router) {}

  public goToCockpit(id: string): void {
    if (id) {
      this.router.navigate(['/cockpit', id]);
    } else {
      this.goToMigration();
    }
  }

  public goToMigration(): void {
    this.router.navigate(['/migration']);
  }

  public createMigration(): void {
    this.router.navigate(['/migration/create']);
  }

  public formatMode(mode: string): string {
    switch (mode) {
      case 'M1_BULK': return 'M1 Bulk';
      case 'M2_BULK_CDC': return 'M2 Bulk + CDC';
      case 'M3_CDC_CONTINUOUS': return 'M3 CDC';
      case 'M4_INCREMENTAL': return 'M4 Incremental';
      case 'M5_STATE_SYNC': return 'M5 State-Based Sync';
      case 'M6_SCHEMA_ONLY': return 'M6 Schema Only';
      case 'M7_DATA_ONLY': return 'M7 Data Only';
      case 'M8_VALIDATION_ONLY': return 'Validation Assurance';
      default:
        if (!mode) return 'Standard';
        return mode.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase());
    }
  }

  public getStateLabel(state: string): string {
    switch (state) {
      case 'RUNNING': return 'Running';
      case 'PAUSED': return 'Paused';
      case 'BLOCKED': return 'Blocked';
      case 'COMPLETED': return 'Completed';
      case 'FAILED': return 'Failed';
      case 'QUEUED': return 'Queued';
      case 'VALIDATING': return 'Validating';
      case 'CATCHING_UP': return 'Catching Up';
      case 'UNKNOWN': return 'Unknown';
      default:
        if (!state) return 'Unknown';
        return state.charAt(0).toUpperCase() + state.slice(1).toLowerCase().replace(/_/g, ' ');
    }
  }

  public getStateBadgeClasses(state: string): string {
    switch (state) {
      case 'RUNNING':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'COMPLETED':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'FAILED':
      case 'BLOCKED':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'PAUSED':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'CATCHING_UP':
        return 'bg-teal-50 text-teal-700 border-teal-200';
      case 'VALIDATING':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'QUEUED':
      case 'UNKNOWN':
      default:
        return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  }

  public getStateDotClasses(state: string): string {
    switch (state) {
      case 'RUNNING':
        return 'bg-emerald-500';
      case 'COMPLETED':
        return 'bg-blue-500';
      case 'FAILED':
      case 'BLOCKED':
        return 'bg-rose-500';
      case 'PAUSED':
        return 'bg-amber-500';
      case 'CATCHING_UP':
        return 'bg-teal-500';
      case 'VALIDATING':
        return 'bg-indigo-500';
      case 'QUEUED':
      case 'UNKNOWN':
      default:
        return 'bg-slate-400';
    }
  }

  public formatNumber(num: number | null | undefined): string {
    if (num === undefined || num === null) return '0';
    return num.toLocaleString();
  }
}
