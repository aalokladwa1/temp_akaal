import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { StatusBadgeComponent } from '../../components/status-badge.component';

@Component({
  selector: 'app-validation-view',
  standalone: true,
  imports: [CommonModule, RouterLink, StatusBadgeComponent],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150">
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        <div class="flex items-center justify-between">
          <div class="flex flex-col gap-1">
            <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider">Associated M8 Validation Gate</h3>
            <span class="text-xs text-slate-500">Post-migration continuous verification run</span>
          </div>
          <app-status-badge gateStatus="PASSED"></app-status-badge>
        </div>

        <div class="grid grid-cols-3 gap-4 text-xs">
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
            <span class="text-slate-500">Total Rows Verified:</span>
            <span class="text-base font-bold text-slate-900">148,200,000</span>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
            <span class="text-slate-500">Discrepancies:</span>
            <span class="text-base font-bold text-emerald-700">0 Differences</span>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
            <span class="text-slate-500">Certificate Seal:</span>
            <span class="text-xs font-mono text-slate-700">sha256:val001pass</span>
          </div>
        </div>

        <div class="flex justify-end pt-2">
          <a
            routerLink="/migration/validation"
            class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs">
            Open in Validation Operations
          </a>
        </div>
      </div>
    </div>
  `
})
export class ValidationViewComponent {
  public ms = inject(MigrationUiService);
}
