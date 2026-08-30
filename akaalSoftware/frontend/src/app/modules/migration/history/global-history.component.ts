import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { DialogModule } from 'primeng/dialog';
import { HistoryUiService } from '../../../core/services/history-ui.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { StatusBadgeComponent } from '../components/status-badge.component';

@Component({
  selector: 'app-global-history',
  standalone: true,
  imports: [CommonModule, FormsModule, TableModule, TagModule, DialogModule, LucideIconComponent, StatusBadgeComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto pb-16 font-sans select-none animate-in fade-in duration-150">
      
      <!-- Header (49) -->
      <div class="flex items-center justify-between gap-4 pb-4 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <span class="text-xs font-semibold text-slate-500">Forensic Audit &amp; Lineage</span>
          <h1 class="text-2xl font-bold font-heading text-slate-900 tracking-tight">History &amp; Evidence Ledger</h1>
          <p class="text-xs text-slate-600 font-medium">Immutable audit trail with 3 separate truth dimensions: Lifecycle, Validation, and Evidence Sealing.</p>
        </div>

        <button
          type="button"
          (click)="hs.isComparisonModalOpen.set(true)"
          class="h-9 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs flex items-center gap-2 transition-colors cursor-pointer">
          <app-lucide-icon name="git-branch" [size]="15"></app-lucide-icon>
          <span>Compare Selected Runs ({{ hs.selectedExecutionIds().length }})</span>
        </button>
      </div>

      <!-- Ledger Table (50) -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        
        <div class="flex items-center justify-between gap-4 flex-wrap pb-3 border-b border-slate-100">
          <span class="text-xs font-bold text-slate-800">Historical Executions ({{ hs.ledgerItems().length }})</span>
          
          <div class="relative w-80">
            <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <app-lucide-icon name="search" [size]="15"></app-lucide-icon>
            </div>
            <input
              type="text"
              [ngModel]="hs.filterSearch()"
              (ngModelChange)="hs.filterSearch.set($event)"
              placeholder="Search execution ID, operator..."
              class="w-full h-10 pl-10 pr-3.5 rounded-xl bg-slate-50 hover:bg-slate-100/70 border border-slate-200 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs" />
          </div>
        </div>

        <p-table [value]="hs.filteredLedgerItems()" [paginator]="true" [rows]="10" styleClass="p-datatable-sm">
          <ng-template #header>
            <tr class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              <th>Execution ID &amp; Migration</th>
              <th>Source &rarr; Target</th>
              <th>Mode</th>
              <th>Lifecycle State</th>
              <th>Validation Verdict</th>
              <th>Evidence State</th>
              <th>Duration</th>
              <th>Operator</th>
            </tr>
          </ng-template>

          <ng-template #body let-item>
            <tr class="h-16 hover:bg-slate-50 text-xs font-medium">
              <td>
                <div class="flex flex-col">
                  <span class="font-bold text-slate-900">{{ item.migrationName }}</span>
                  <span class="font-mono text-[11px] text-slate-500">{{ item.executionId }}</span>
                </div>
              </td>

              <td>
                <span class="font-semibold text-slate-800">{{ item.sourceEngine }} &rarr; {{ item.targetEngine }}</span>
              </td>

              <td>
                <app-status-badge [mode]="item.mode"></app-status-badge>
              </td>

              <td>
                <app-status-badge [lifecycle]="item.lifecycleState"></app-status-badge>
              </td>

              <td>
                <app-status-badge [verdict]="item.validationVerdict"></app-status-badge>
              </td>

              <td>
                <span class="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-blue-50 text-blue-700 border border-blue-200">{{ item.evidenceState }}</span>
              </td>

              <td>
                <span class="font-mono text-slate-700">{{ item.durationString }}</span>
              </td>

              <td>
                <span class="text-slate-800 font-semibold">{{ item.operator }}</span>
              </td>
            </tr>
          </ng-template>
        </p-table>

      </div>

      <!-- Multi-Run Comparison Modal (52) -->
      <p-dialog
        [(visible)]="hs.isComparisonModalOpen"
        [modal]="true"
        [closable]="true"
        [draggable]="false"
        [style]="{ width: '90vw', maxWidth: '820px' }">
        
        <ng-template #header>
          <div class="flex items-center gap-2">
            <app-lucide-icon name="git-branch" [size]="18" class="text-blue-600"></app-lucide-icon>
            <h3 class="text-sm font-bold text-slate-900">Multi-Run Comparison Workbench (2–5 Executions)</h3>
          </div>
        </ng-template>

        <div class="flex flex-col gap-3 text-xs">
          @for (m of hs.comparisonMetrics(); track m.dimension) {
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <span class="font-bold text-slate-800">{{ m.dimension }}</span>
              <div class="flex items-center gap-4 font-mono text-slate-900 font-semibold">
                @for (val of m.runValues | keyvalue; track val.key) {
                  <span>{{ val.key }}: <strong class="text-blue-700">{{ val.value }}</strong></span>
                }
              </div>
            </div>
          }
        </div>

        <ng-template #footer>
          <button type="button" (click)="hs.isComparisonModalOpen.set(false)" class="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-bold">Close</button>
        </ng-template>
      </p-dialog>

    </div>
  `
})
export class GlobalHistoryComponent {
  public hs = inject(HistoryUiService);
}
