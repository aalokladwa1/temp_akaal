import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ValidationUiService } from '../../core/services/validation-ui.service';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';
import { StatusBadgeComponent } from '../migration/components/status-badge.component';

@Component({
  selector: 'app-validation-portfolio',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, TableModule, TagModule, LucideIconComponent, StatusBadgeComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto pb-16 font-sans select-none animate-in fade-in duration-150">
      
      <!-- Header (35) -->
      <div class="flex items-center justify-between gap-4 pb-4 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <span class="text-xs font-semibold text-slate-500">Data Synchronization Assurance</span>
          <h1 class="text-2xl font-bold font-heading text-slate-900 tracking-tight">Validation Operations</h1>
          <p class="text-xs text-slate-600 font-medium">Independent parity verification, Merkle difference funnels, and governed target repairs.</p>
        </div>

        <a
          routerLink="/migration/validation/new"
          class="h-9 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs flex items-center gap-2 transition-colors cursor-pointer">
          <app-lucide-icon name="plus" [size]="15"></app-lucide-icon>
          <span>New Validation Run</span>
        </a>
      </div>

      <!-- 4 Primary Status Cards (36) -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
        
        <div
          (click)="vs.filterVerdict.set(vs.filterVerdict() === 'ACTIVE' ? 'ALL' : 'ACTIVE')"
          class="p-4 rounded-2xl bg-white border-2 cursor-pointer transition-all shadow-2xs flex flex-col gap-1"
          [class.border-blue-600]="vs.filterVerdict() === 'ACTIVE'"
          [class.border-slate-200]="vs.filterVerdict() !== 'ACTIVE'">
          <span class="text-[11px] font-bold text-slate-500 uppercase">Active Runs</span>
          <span class="text-2xl font-bold text-slate-900">1</span>
        </div>

        <div
          (click)="vs.filterVerdict.set(vs.filterVerdict() === 'NOT_SYNCED' ? 'ALL' : 'NOT_SYNCED')"
          class="p-4 rounded-2xl bg-white border-2 cursor-pointer transition-all shadow-2xs flex flex-col gap-1"
          [class.border-rose-600]="vs.filterVerdict() === 'NOT_SYNCED'"
          [class.border-slate-200]="vs.filterVerdict() !== 'NOT_SYNCED'">
          <span class="text-[11px] font-bold text-rose-700 uppercase">Not Synced (Divergent)</span>
          <span class="text-2xl font-bold text-rose-700">1</span>
        </div>

        <div
          (click)="vs.filterVerdict.set(vs.filterVerdict() === 'SYNCED' ? 'ALL' : 'SYNCED')"
          class="p-4 rounded-2xl bg-white border-2 cursor-pointer transition-all shadow-2xs flex flex-col gap-1"
          [class.border-emerald-600]="vs.filterVerdict() === 'SYNCED'"
          [class.border-slate-200]="vs.filterVerdict() !== 'SYNCED'">
          <span class="text-[11px] font-bold text-emerald-700 uppercase">Synced Runs</span>
          <span class="text-2xl font-bold text-emerald-700">1</span>
        </div>

        <div
          (click)="vs.filterVerdict.set(vs.filterVerdict() === 'CERTIFIED' ? 'ALL' : 'CERTIFIED')"
          class="p-4 rounded-2xl bg-white border-2 cursor-pointer transition-all shadow-2xs flex flex-col gap-1"
          [class.border-emerald-600]="vs.filterVerdict() === 'CERTIFIED'"
          [class.border-slate-200]="vs.filterVerdict() !== 'CERTIFIED'">
          <span class="text-[11px] font-bold text-emerald-700 uppercase">Certified Runs</span>
          <span class="text-2xl font-bold text-emerald-700">1</span>
        </div>

      </div>

      <!-- Validations Table -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        <h2 class="text-sm font-bold text-slate-900">Validation Fleet Ledger</h2>

        <p-table [value]="vs.filteredValidations()" [paginator]="true" [rows]="10" styleClass="p-datatable-sm">
          <ng-template #header>
            <tr class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              <th>Validation Name</th>
              <th>Reference &rarr; Comparison</th>
              <th>Verdict</th>
              <th>Profile</th>
              <th>Rows Validated</th>
              <th>Differences</th>
              <th class="text-right">Actions</th>
            </tr>
          </ng-template>

          <ng-template #body let-v>
            <tr class="h-16 hover:bg-slate-50 text-xs font-medium">
              <td>
                <div class="flex flex-col">
                  <a [routerLink]="['/validation', v.id]" class="font-bold text-slate-900 hover:text-blue-600 cursor-pointer">{{ v.name }}</a>
                  <span class="text-[11px] text-slate-500">{{ v.purpose }}</span>
                </div>
              </td>

              <td>
                <span class="font-semibold text-slate-800">{{ v.sourceEngine }} &rarr; {{ v.targetEngine }}</span>
              </td>

              <td>
                <app-status-badge [verdict]="v.verdict"></app-status-badge>
              </td>

              <td>
                <span class="px-2 py-0.5 rounded bg-slate-100 font-bold text-[10px] text-slate-700">{{ v.profile }}</span>
              </td>

              <td>
                <span class="font-mono text-xs text-slate-900 font-bold">{{ v.rowsValidated | number }}</span>
              </td>

              <td>
                @if (v.cellDifferencesCount > 0) {
                  <span class="font-mono font-bold text-rose-700">{{ v.cellDifferencesCount }} cells ({{ v.rowsMismatched }} rows)</span>
                } @else {
                  <span class="font-mono text-emerald-700 font-bold">0 differences</span>
                }
              </td>

              <td class="text-right">
                <a
                  [routerLink]="['/validation', v.id]"
                  class="px-3.5 py-1.5 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-xs inline-flex items-center gap-1">
                  <span>Open Workspace</span>
                  <app-lucide-icon name="arrow-right" [size]="13"></app-lucide-icon>
                </a>
              </td>
            </tr>
          </ng-template>
        </p-table>
      </div>

    </div>
  `
})
export class ValidationPortfolioComponent {
  public vs = inject(ValidationUiService);
}
