/**
 * AKAAL Administration — 5.9 Administrative Audit Trail
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuditService } from '../../services/audit.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-audit-trail-list',
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
              <span class="text-xs font-medium text-slate-500">ADMINISTRATIVE LOG</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Administrative Audit Trail</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Immutable log of control plane mutations, privileged role delegations, authentication changes, and system operations.
          </p>
        </div>
      </div>

      <!-- Audit Trail Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Timestamp</th>
              <th class="py-3.5 px-4">Actor</th>
              <th class="py-3.5 px-4">Role</th>
              <th class="py-3.5 px-4">Action</th>
              <th class="py-3.5 px-4">Target Resource</th>
              <th class="py-3.5 px-4">Outcome</th>
              <th class="py-3.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (evt of auditService.auditTrail(); track evt.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px] whitespace-nowrap">{{ evt.timestamp }}</td>
                <td class="py-3.5 px-4 font-bold text-slate-900">{{ evt.actor }}</td>
                <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px]">{{ evt.actorRole }}</td>
                <td class="py-3.5 px-4 font-mono font-bold text-blue-600">{{ evt.action }}</td>
                <td class="py-3.5 px-4">
                  <div class="flex items-center gap-1.5 font-mono text-[11px] text-slate-700">
                    <span>{{ evt.resourceType }}</span>
                    <span class="text-slate-400">:</span>
                    <span class="text-slate-900 font-bold">{{ evt.resourceId }}</span>
                  </div>
                </td>
                <td class="py-3.5 px-4">
                  <span 
                    class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border"
                    [ngClass]="{
                      'bg-emerald-50 text-emerald-700 border-emerald-200': evt.outcome === 'SUCCESS',
                      'bg-rose-50 text-rose-700 border-rose-200': evt.outcome === 'FAILURE',
                      'bg-amber-50 text-amber-700 border-amber-200': evt.outcome === 'DENIED'
                    }">
                    {{ evt.outcome }}
                  </span>
                </td>
                <td class="py-3.5 px-4 text-right">
                  <a
                    [routerLink]="['/administration/audit/trail/detail', evt.id]"
                    class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs">
                    Inspect
                  </a>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class AuditTrailListComponent {
  public auditService = inject(AuditService);
}
