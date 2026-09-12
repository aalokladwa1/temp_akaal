import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { GovernanceService } from '../../services/governance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-privileged-ops-list',
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
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Privileged Operations Registry</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Critical infrastructure operations mandating step-up authorization, four-eyes quorum, or break-glass access.
          </p>
        </div>
      </div>

      <!-- Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Operation Name & Code</th>
                <th class="py-3 px-4">Risk Tier</th>
                <th class="py-3 px-4">Approval Chain</th>
                <th class="py-3 px-4">Four-Eyes</th>
                <th class="py-3 px-4">Break-Glass Eligible</th>
                <th class="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              <tr *ngFor="let p of govService.privilegedOps()" class="hover:bg-slate-50/50 transition-colors">
                <td class="py-3 px-4">
                  <div class="flex flex-col">
                    <span class="font-bold text-slate-900">{{ p.operationName }}</span>
                    <span class="text-[11px] text-slate-500 font-mono">{{ p.operationCode }}</span>
                  </div>
                </td>
                <td class="py-3 px-4">
                  <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-rose-50 text-rose-700">
                    {{ p.riskTier }}
                  </span>
                </td>
                <td class="py-3 px-4 font-medium text-slate-800">
                  {{ p.approvalChainName }}
                </td>
                <td class="py-3 px-4">
                  <span class="font-semibold text-emerald-700">{{ p.fourEyesRequired ? 'Mandatory' : 'None' }}</span>
                </td>
                <td class="py-3 px-4 font-medium text-slate-700">
                  {{ p.breakGlassEligible ? 'Eligible' : 'Prohibited' }}
                </td>
                <td class="py-3 px-4">
                  <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700">
                    {{ p.status }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class PrivilegedOpsListComponent {
  public govService = inject(GovernanceService);
}