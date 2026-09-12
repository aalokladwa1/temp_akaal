import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { GovernanceService } from '../../services/governance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-governance-history',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/governance-centre" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Governance Centre
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Governance Audit History</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Cryptographically sealed timeline of policy decisions, approvals, emergency elevations, and waivers.
          </p>
        </div>
      </div>

      <!-- Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Timestamp</th>
                <th class="py-3 px-4">Event Type</th>
                <th class="py-3 px-4">Principal Actor</th>
                <th class="py-3 px-4">Target Resource</th>
                <th class="py-3 px-4">Decision</th>
                <th class="py-3 px-4">Details</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              <tr *ngFor="let h of govService.auditHistory()" class="hover:bg-slate-50/50 transition-colors">
                <td class="py-3 px-4 font-mono text-slate-500">
                  {{ h.timestamp | date:'short' }}
                </td>
                <td class="py-3 px-4 font-bold text-slate-900">
                  {{ h.eventType }}
                </td>
                <td class="py-3 px-4">
                  <div class="flex flex-col">
                    <span class="font-medium text-slate-800">{{ h.principalName }}</span>
                    <span class="text-[11px] text-slate-500 font-mono">{{ h.principalEmail }}</span>
                  </div>
                </td>
                <td class="py-3 px-4 font-medium text-slate-800">
                  {{ h.targetResource }}
                </td>
                <td class="py-3 px-4">
                  <span
                    class="rounded px-2 py-0.5 text-[11px] font-semibold"
                    [ngClass]="{
                      'bg-emerald-50 text-emerald-700': h.decision === 'APPROVED' || h.decision === 'ENFORCED',
                      'bg-rose-50 text-rose-700': h.decision === 'REJECTED',
                      'bg-amber-50 text-amber-700': h.decision === 'ELEVATED' || h.decision === 'WAIVED'
                    }">
                    {{ h.decision }}
                  </span>
                </td>
                <td class="py-3 px-4 text-slate-600">
                  {{ h.details }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class GovernanceHistoryComponent {
  public govService = inject(GovernanceService);
}