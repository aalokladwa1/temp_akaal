/**
 * AKAAL Administration — 5.8 Custom Frameworks List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ComplianceService } from '../../services/compliance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-custom-frameworks-list',
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
              <span class="text-xs font-medium text-slate-500">CUSTOM FRAMEWORKS</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Custom Frameworks</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Enterprise bespoke compliance policies, internal security baseline specifications, and jurisdictional mandates.
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <a
            routerLink="/administration/compliance/frameworks/custom/create"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs">
            Create Custom Framework
          </a>
        </div>
      </div>

      <!-- Custom Frameworks Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Framework Name</th>
              <th class="py-3.5 px-4">Specification Code</th>
              <th class="py-3.5 px-4">Version</th>
              <th class="py-3.5 px-4">Authoritative Owner</th>
              <th class="py-3.5 px-4">Controls Count</th>
              <th class="py-3.5 px-4">Created Date</th>
              <th class="py-3.5 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (fw of complianceService.customFrameworks(); track fw.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4">
                  <div class="flex flex-col">
                    <span class="font-bold text-slate-900 font-heading">{{ fw.name }}</span>
                    <span class="text-[11px] text-slate-500 mt-0.5 max-w-md line-clamp-1">{{ fw.description }}</span>
                  </div>
                </td>
                <td class="py-3.5 px-4 font-mono font-medium text-slate-700">{{ fw.code }}</td>
                <td class="py-3.5 px-4 text-slate-600 font-medium">{{ fw.version }}</td>
                <td class="py-3.5 px-4 text-slate-600">{{ fw.authorityOwner }}</td>
                <td class="py-3.5 px-4 font-semibold text-slate-900">{{ fw.controlsCount }} controls</td>
                <td class="py-3.5 px-4 text-slate-500">{{ fw.createdAt }}</td>
                <td class="py-3.5 px-4">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {{ fw.status }}
                  </span>
                </td>
              </tr>
            }
            @if (complianceService.customFrameworks().length === 0) {
              <tr>
                <td colspan="7" class="py-8 text-center text-slate-500 text-xs">
                  No custom frameworks registered.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class CustomFrameworksListComponent {
  public complianceService = inject(ComplianceService);
}
