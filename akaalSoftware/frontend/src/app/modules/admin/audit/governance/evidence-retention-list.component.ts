/**
 * AKAAL Administration — 5.9 Evidence Retention Policies List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuditService } from '../../services/audit.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-evidence-retention-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/audit"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">AUDIT</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">EVIDENCE RETENTION</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Evidence Retention</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Automated lifecycle rules controlling the preservation, cold archival, and lawful disposition of evidence artifacts.
          </p>
        </div>
      </div>

      <!-- Retention Policies Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Policy Scope</th>
              <th class="py-3.5 px-4">Evidence Classification</th>
              <th class="py-3.5 px-4">Retention Baseline</th>
              <th class="py-3.5 px-4">Disposition Action</th>
              <th class="py-3.5 px-4">Legal Hold Exempt</th>
              <th class="py-3.5 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (ret of auditService.retentionPolicies(); track ret.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900 font-heading">{{ ret.name }}</td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-slate-700">{{ ret.evidenceClass }}</td>
                <td class="py-3.5 px-4 font-semibold text-slate-900">{{ ret.retentionYears }} Years</td>
                <td class="py-3.5 px-4">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                    {{ ret.dispositionAction.replace('_', ' ') }}
                  </span>
                </td>
                <td class="py-3.5 px-4 text-slate-600">
                  {{ ret.legalHoldExempt ? 'Yes (Transient)' : 'No (Protected)' }}
                </td>
                <td class="py-3.5 px-4">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {{ ret.status }}
                  </span>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class EvidenceRetentionListComponent {
  public auditService = inject(AuditService);
}
