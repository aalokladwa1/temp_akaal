import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-governance-view',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150">
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider">Four-Eyes Governance &amp; Approval Gates</h3>
        
        <div class="p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start justify-between gap-4">
          <div class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center shrink-0">
              <app-lucide-icon name="lock" [size]="16"></app-lucide-icon>
            </div>
            <div class="flex flex-col gap-1 text-xs">
              <span class="font-bold text-slate-900">Cutover Approval Barrier (Pending 1 of 2 Sign-offs)</span>
              <span class="text-slate-600">Requires Lead Architect &amp; Security Administrator sign-offs before source quiescence.</span>
            </div>
          </div>

          <button type="button" class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs">
            Authorize Cutover
          </button>
        </div>
      </div>
    </div>
  `
})
export class GovernanceViewComponent {
  public ms = inject(MigrationUiService);
}
