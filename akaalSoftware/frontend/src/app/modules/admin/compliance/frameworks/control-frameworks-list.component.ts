/**
 * AKAAL Administration — 5.8 Control Frameworks List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ComplianceService } from '../../services/compliance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-control-frameworks-list',
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
              <span class="text-xs font-medium text-slate-500">FRAMEWORKS CATALOG</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Control Frameworks</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Authoritative regulatory and security specifications with verified technical safeguard mappings.
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <a
            routerLink="/administration/compliance/frameworks/views"
            class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs">
            Framework Views
          </a>
        </div>
      </div>

      <!-- Frameworks Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Framework</th>
              <th class="py-3.5 px-4">Standard Code</th>
              <th class="py-3.5 px-4">Version</th>
              <th class="py-3.5 px-4">Governing Authority</th>
              <th class="py-3.5 px-4">Mapped Controls</th>
              <th class="py-3.5 px-4">Status</th>
              <th class="py-3.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (fw of complianceService.frameworks(); track fw.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4">
                  <div class="flex flex-col">
                    <span class="font-bold text-slate-900 font-heading">{{ fw.name }}</span>
                    <span class="text-[11px] text-slate-500 mt-0.5 max-w-md line-clamp-1">{{ fw.description }}</span>
                  </div>
                </td>
                <td class="py-3.5 px-4 font-mono font-medium text-slate-700">{{ fw.code }}</td>
                <td class="py-3.5 px-4 text-slate-600 font-medium">{{ fw.version }}</td>
                <td class="py-3.5 px-4 text-slate-600">{{ fw.authorityBody }}</td>
                <td class="py-3.5 px-4">
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-slate-900">{{ fw.mappedControlsCount }}</span>
                    <span class="text-slate-400">/</span>
                    <span class="text-slate-600">{{ fw.totalControls }} controls</span>
                  </div>
                </td>
                <td class="py-3.5 px-4">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {{ fw.status }}
                  </span>
                </td>
                <td class="py-3.5 px-4 text-right">
                  <a
                    [routerLink]="['/administration/compliance/frameworks/detail', fw.id]"
                    class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs">
                    View Controls
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
export class ControlFrameworksListComponent {
  public complianceService = inject(ComplianceService);
}
