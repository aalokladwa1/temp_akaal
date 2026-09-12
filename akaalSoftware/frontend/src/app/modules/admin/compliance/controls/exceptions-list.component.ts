/**
 * AKAAL Administration — 5.8 Compliance Exceptions List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ComplianceService } from '../../services/compliance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-exceptions-list',
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
              <span class="text-xs font-medium text-slate-500">EXCEPTIONS GOVERNANCE</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Compliance Exceptions</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Authorized deviations, compensatory security safeguards, and time-bounded control waivers.
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <a
            routerLink="/administration/compliance/controls/exceptions/request"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs">
            Request Exception
          </a>
        </div>
      </div>

      <!-- Exceptions Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Exception Code</th>
              <th class="py-3.5 px-4">Title & Scope</th>
              <th class="py-3.5 px-4">Control Reference</th>
              <th class="py-3.5 px-4">Approved By</th>
              <th class="py-3.5 px-4">Expiration Date</th>
              <th class="py-3.5 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (exc of complianceService.exceptions(); track exc.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-mono font-bold text-blue-600">{{ exc.code }}</td>
                <td class="py-3.5 px-4">
                  <div class="flex flex-col">
                    <span class="font-bold text-slate-900">{{ exc.title }}</span>
                    <span class="text-[11px] text-slate-500 mt-0.5 max-w-md">{{ exc.scope }}</span>
                  </div>
                </td>
                <td class="py-3.5 px-4 font-mono text-slate-700 font-medium">{{ exc.controlCode }}</td>
                <td class="py-3.5 px-4 text-slate-600">{{ exc.approvedBy }}</td>
                <td class="py-3.5 px-4 text-slate-600 whitespace-nowrap">{{ exc.validUntil }}</td>
                <td class="py-3.5 px-4">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {{ exc.status }}
                  </span>
                </td>
              </tr>
            }
            @if (complianceService.exceptions().length === 0) {
              <tr>
                <td colspan="6" class="py-8 text-center text-slate-500 text-xs">
                  No active compliance exceptions registered.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class ExceptionsListComponent {
  public complianceService = inject(ComplianceService);
}
