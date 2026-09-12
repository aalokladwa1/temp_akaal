/**
 * AKAAL Administration — 5.8 Control Mapping List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ComplianceService } from '../../services/compliance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-control-mapping-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/compliance"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">COMPLIANCE</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">TECHNICAL CONTROL MAPPINGS</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Control Mapping</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Formal relationships linking external regulatory control requirements to AKAAL platform technical execution controls.
          </p>
        </div>
      </div>

      <!-- Mapping Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Framework Control</th>
              <th class="py-3.5 px-4">Regulatory Framework</th>
              <th class="py-3.5 px-4">AKAAL Technical Control</th>
              <th class="py-3.5 px-4">Safeguard Rationale</th>
              <th class="py-3.5 px-4">Verification Date</th>
              <th class="py-3.5 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (m of complianceService.controlMappings(); track m.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-mono font-bold text-blue-600">{{ m.controlCode }}</td>
                <td class="py-3.5 px-4 text-slate-700 font-medium">{{ m.frameworkName }}</td>
                <td class="py-3.5 px-4">
                  <div class="flex flex-col">
                    <span class="font-bold text-slate-900">{{ m.technicalControlName }}</span>
                    <span class="font-mono text-[10px] text-slate-500">{{ m.akaalTechnicalControlId }}</span>
                  </div>
                </td>
                <td class="py-3.5 px-4 text-slate-600 max-w-md">{{ m.rationale }}</td>
                <td class="py-3.5 px-4 text-slate-500 whitespace-nowrap">{{ m.verifiedAt }}</td>
                <td class="py-3.5 px-4">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {{ m.status }}
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
export class ControlMappingListComponent {
  public complianceService = inject(ComplianceService);
}
