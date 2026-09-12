import { Component, inject, Optional } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HistoryHomeService } from '../history-home.service';
import {
  MigrationHistoryItem,
  HistoryMode,
  HistoryOutcome,
  ValidationReconciliationState,
  HISTORY_MODE_DESCRIPTORS,
  HistoryModeDescriptor
} from '../history-home.models';

@Component({
  selector: 'app-history-table',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="overflow-x-auto overflow-y-visible">
      <table class="w-full text-left border-collapse min-w-[850px]">
        <thead>
          <tr class="border-b border-slate-200 bg-slate-50/80 text-[11px] font-bold text-slate-600 uppercase tracking-wider select-none">
            <th scope="col" class="py-3 px-4 min-w-[300px]">Migration</th>
            <th scope="col" class="py-3 px-4 min-w-[140px]">Mode</th>
            <th scope="col" class="py-3 px-4 min-w-[300px]">Source &rarr; Target</th>
            <th scope="col" class="py-3 px-4 min-w-[120px]">Outcome</th>
            <th scope="col" class="py-3 px-4 text-right min-w-[140px]">Validation Verdict</th>
          </tr>
        </thead>

        <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
          @for (item of hs.filteredHistoryItems(); track item.id) {
            <tr 
              class="hover:bg-slate-50/90 transition-colors group cursor-pointer"
              (click)="onRowClick(item)">
              
              <!-- 1. Migration (Clean Name Only) -->
              <td class="py-3.5 px-4 align-middle">
                <span class="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors text-sm truncate block max-w-[420px]" [title]="item.migrationName">
                  {{ item.migrationName }}
                </span>
              </td>

              <!-- 2. Mode Badge (Clean Name Only, No MX) -->
              <td class="py-3.5 px-4 align-middle whitespace-nowrap">
                <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border"
                  [ngClass]="getModeBadgeClass(item.mode)">
                  {{ getModeDescriptor(item.mode).label }}
                </span>
              </td>

              <!-- 3. Source -> Target (Horizontal Inline Clean) -->
              <td class="py-3.5 px-4 align-middle whitespace-nowrap">
                <div class="text-xs font-medium text-slate-800 flex items-center gap-1.5">
                  <span class="truncate max-w-[240px]" [title]="item.sourceProvider">{{ item.sourceProvider }}</span>
                  <span class="text-slate-400 font-normal">&rarr;</span>
                  <span class="font-semibold text-slate-900 truncate max-w-[240px]" [title]="item.targetProvider">{{ item.targetProvider }}</span>
                </div>
              </td>

              <!-- 4. Outcome Badge (Only Badge, No Text Below) -->
              <td class="py-3.5 px-4 align-middle whitespace-nowrap">
                <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold border"
                  [ngClass]="getOutcomeBadgeClass(item.outcome)">
                  {{ item.outcome }}
                </span>
              </td>

              <!-- 5. Validation Verdict (Clean Tag Only, Zero Numbers) -->
              <td class="py-3.5 px-4 align-middle text-right whitespace-nowrap">
                <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border"
                  [ngClass]="getValidationBadgeClass(item.validationState)">
                  {{ getValidationLabel(item) }}
                </span>
              </td>

            </tr>
          }
        </tbody>
      </table>
    </div>
  `
})
export class HistoryTableComponent {
  public hs: HistoryHomeService;
  private router: Router | null;

  constructor(
    @Optional() hs?: HistoryHomeService,
    @Optional() router?: Router
  ) {
    if (hs) {
      this.hs = hs;
    } else {
      try {
        this.hs = inject(HistoryHomeService);
      } catch {
        this.hs = new HistoryHomeService();
      }
    }

    if (router) {
      this.router = router;
    } else {
      try {
        this.router = inject(Router);
      } catch {
        this.router = null;
      }
    }
  }

  public getModeDescriptor(mode: HistoryMode): HistoryModeDescriptor {
    return HISTORY_MODE_DESCRIPTORS[mode] || {
      code: mode,
      shortCode: mode,
      label: mode,
      fullLabel: mode,
      description: '',
      supportsCutover: false,
      isValidationAssurance: false
    };
  }

  public getModeBadgeClass(mode: HistoryMode): string {
    switch (mode) {
      case 'M1_BULK':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'M2_BULK_CDC':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'M3_CDC':
        return 'bg-cyan-50 text-cyan-800 border-cyan-200';
      case 'M4_INCREMENTAL':
        return 'bg-teal-50 text-teal-800 border-teal-200';
      case 'M5_STATE_SYNC':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'M6_SCHEMA_ONLY':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'M7_DATA_ONLY':
        return 'bg-emerald-50 text-emerald-800 border-emerald-200';
      case 'M8_VALIDATION_ONLY':
        return 'bg-sky-50 text-sky-800 border-sky-300 font-bold';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  }

  public getOutcomeBadgeClass(outcome: HistoryOutcome): string {
    switch (outcome) {
      case 'SUCCEEDED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'FAILED':
      case 'ABORTED':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'RUNNING':
        return 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse';
      case 'STOPPED':
      case 'CANCELLED':
      case 'PAUSED':
      case 'INTERRUPTED':
        return 'bg-slate-100 text-slate-700 border-slate-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  }

  public getValidationBadgeClass(state: ValidationReconciliationState): string {
    switch (state) {
      case 'PASSED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'RECONCILED':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'MISMATCHES_DETECTED':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'FAILED':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'SKIPPED':
      case 'NOT_CONFIGURED':
      case 'PENDING':
      case 'UNAVAILABLE':
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  public getValidationLabel(item: MigrationHistoryItem): string {
    switch (item.validationState) {
      case 'PASSED':
        return 'Passed';
      case 'RECONCILED':
        return 'Reconciled';
      case 'MISMATCHES_DETECTED':
        return 'Mismatch';
      case 'FAILED':
        return 'Failed';
      case 'SKIPPED':
        return 'Skipped';
      case 'NOT_CONFIGURED':
        return 'Not Configured';
      case 'IN_PROGRESS':
        return 'In Progress';
      default:
        return item.validationState;
    }
  }

  public onRowClick(item: MigrationHistoryItem): void {
    const isMigrationPrefix = this.router ? this.router.url.startsWith('/migration') : true;
    const path = isMigrationPrefix
      ? `/migration/history/${item.migrationId}`
      : `/history/${item.migrationId}`;
    this.router?.navigate([path]);
  }
}
