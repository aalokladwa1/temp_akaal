/**
 * AKAAL Administration — 5.9 Legal Hold List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuditService } from '../../services/audit.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-legal-hold-list',
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
              <span class="text-xs font-medium text-slate-500">LEGAL HOLD GOVERNANCE</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Legal Hold</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Consequential preservation orders preventing purge, disposition, or mutation of audit records and execution evidence.
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <a
            routerLink="/administration/audit/legal-hold/create"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs">
            Create Legal Hold
          </a>
        </div>
      </div>

      <!-- Legal Holds Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Matter / Case Name</th>
              <th class="py-3.5 px-4">Case ID</th>
              <th class="py-3.5 px-4">Legal Custodian</th>
              <th class="py-3.5 px-4">Held Items</th>
              <th class="py-3.5 px-4">Hold Created</th>
              <th class="py-3.5 px-4">Status</th>
              <th class="py-3.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (hold of auditService.legalHolds(); track hold.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4">
                  <div class="flex flex-col">
                    <span class="font-bold text-slate-900 font-heading">{{ hold.matterName }}</span>
                    <span class="text-[11px] text-slate-500 mt-0.5 max-w-md line-clamp-1">{{ hold.scopeDescription }}</span>
                  </div>
                </td>
                <td class="py-3.5 px-4 font-mono font-bold text-blue-600">{{ hold.caseId }}</td>
                <td class="py-3.5 px-4 text-slate-700">{{ hold.custodian }}</td>
                <td class="py-3.5 px-4 font-semibold text-slate-900">{{ hold.heldItemsCount }} artifacts</td>
                <td class="py-3.5 px-4 text-slate-600">{{ hold.holdCreatedDate }}</td>
                <td class="py-3.5 px-4">
                  <span 
                    class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border"
                    [ngClass]="hold.status === 'ACTIVE' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-slate-100 text-slate-700 border-slate-200'">
                    {{ hold.status }}
                  </span>
                </td>
                <td class="py-3.5 px-4 text-right">
                  @if (hold.status === 'ACTIVE') {
                    <button
                      type="button"
                      (click)="onRelease(hold.id)"
                      class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
                      Release Hold
                    </button>
                  } @else {
                    <span class="text-[11px] text-slate-400">Released {{ hold.releasedDate }}</span>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class LegalHoldListComponent {
  public auditService = inject(AuditService);

  public onRelease(id: string): void {
    const reason = prompt('Please specify formal reason for releasing this legal hold:');
    if (reason && reason.trim()) {
      this.auditService.releaseLegalHold(id, reason.trim());
    }
  }
}
