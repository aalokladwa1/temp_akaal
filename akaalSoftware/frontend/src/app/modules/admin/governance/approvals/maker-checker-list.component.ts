import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { GovernanceService } from '../../services/governance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-maker-checker-list',
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
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Maker / Checker Dual Authorization</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Four-eyes dual control policies prohibiting self-approval on destructive or schema-altering migrations.
          </p>
        </div>
      </div>

      <!-- Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Entity / Action Type</th>
                <th class="py-3 px-4">Dual Control</th>
                <th class="py-3 px-4">Self-Approval</th>
                <th class="py-3 px-4">Quorum Signers</th>
                <th class="py-3 px-4">Audit Attestation</th>
                <th class="py-3 px-4">Last Updated</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              <tr *ngFor="let m of govService.makerCheckerPolicies()" class="hover:bg-slate-50/50 transition-colors">
                <td class="py-3 px-4 font-bold text-slate-900">
                  {{ m.entityType }}
                </td>
                <td class="py-3 px-4">
                  <span class="rounded px-2 py-0.5 text-[11px] font-semibold" [ngClass]="m.dualControlEnforced ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'">
                    {{ m.dualControlEnforced ? 'Enforced' : 'Disabled' }}
                  </span>
                </td>
                <td class="py-3 px-4 font-semibold text-slate-800">
                  {{ m.selfApprovalProhibited ? 'Prohibited (Strict)' : 'Allowed' }}
                </td>
                <td class="py-3 px-4 font-bold text-indigo-700">
                  {{ m.quorumRequirement }} Approvers
                </td>
                <td class="py-3 px-4">
                  <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-blue-50 text-blue-700">
                    Mandatory
                  </span>
                </td>
                <td class="py-3 px-4 text-slate-600">
                  {{ m.updatedAt | date:'mediumDate' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class MakerCheckerListComponent {
  public govService = inject(GovernanceService);
}