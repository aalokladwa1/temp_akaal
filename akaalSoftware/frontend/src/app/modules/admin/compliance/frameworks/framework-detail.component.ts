/**
 * AKAAL Administration — 5.8 Framework Detail View
 */

import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ComplianceService } from '../../services/compliance.service';
import { ControlFramework, FrameworkControl } from '../../models/compliance.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-framework-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/compliance/frameworks/catalog"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back to Catalog</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">FRAMEWORK SPECIFICATION</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-mono font-bold text-blue-600">{{ framework()?.code || 'FRAMEWORK' }}</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">
            {{ framework()?.name || 'Framework Details' }}
          </h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            {{ framework()?.description }}
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <a
            routerLink="/administration/compliance/controls/mapping"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs">
            Manage Control Mappings
          </a>
        </div>
      </div>

      <!-- Framework Properties Card -->
      @if (framework(); as fw) {
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs grid grid-cols-1 md:grid-cols-4 gap-6">
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Authority Body</span>
            <span class="text-xs font-semibold text-slate-900">{{ fw.authorityBody }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Specification Version</span>
            <span class="text-xs font-semibold text-slate-900">{{ fw.version }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Control Coverage</span>
            <span class="text-xs font-semibold text-slate-900">{{ fw.mappedControlsCount }} of {{ fw.totalControls }} Mapped</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Governance Status</span>
            <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 w-fit">
              {{ fw.status }}
            </span>
          </div>
        </div>

        <!-- Framework Controls Section -->
        <div class="flex flex-col gap-3">
          <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider font-heading">
            Framework Control Requirements
          </h2>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
                  <th class="py-3.5 px-4">Control Code</th>
                  <th class="py-3.5 px-4">Requirement Title</th>
                  <th class="py-3.5 px-4">Regulatory Domain</th>
                  <th class="py-3.5 px-4">Mapping State</th>
                  <th class="py-3.5 px-4">Mapped Technical Safeguards</th>
                  <th class="py-3.5 px-4 text-right">Evidence Items</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-200 text-xs">
                @for (ctrl of controls(); track ctrl.id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono font-bold text-blue-600">{{ ctrl.controlCode }}</td>
                    <td class="py-3.5 px-4">
                      <div class="flex flex-col">
                        <span class="font-bold text-slate-900">{{ ctrl.title }}</span>
                        <span class="text-[11px] text-slate-500 mt-0.5 max-w-md line-clamp-1">{{ ctrl.description }}</span>
                      </div>
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">{{ ctrl.domain }}</td>
                    <td class="py-3.5 px-4">
                      <span 
                        class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border"
                        [ngClass]="{
                          'bg-emerald-50 text-emerald-700 border-emerald-200': ctrl.mappingState === 'FULLY_MAPPED',
                          'bg-blue-50 text-blue-700 border-blue-200': ctrl.mappingState === 'PARTIALLY_MAPPED',
                          'bg-amber-50 text-amber-700 border-amber-200': ctrl.mappingState === 'EXCEPTION_RECORDED',
                          'bg-slate-100 text-slate-700 border-slate-200': ctrl.mappingState === 'UNMAPPED'
                        }">
                        {{ ctrl.mappingState.replace('_', ' ') }}
                      </span>
                    </td>
                    <td class="py-3.5 px-4">
                      <div class="flex flex-wrap gap-1.5">
                        @for (tech of ctrl.mappedTechnicalControls; track tech) {
                          <span class="inline-flex items-center px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[10px] border border-slate-200">
                            {{ tech }}
                          </span>
                        }
                      </div>
                    </td>
                    <td class="py-3.5 px-4 text-right font-semibold text-slate-900">
                      <a 
                        routerLink="/administration/compliance/evidence"
                        class="text-blue-600 hover:underline">
                        {{ ctrl.evidenceCount }} artifacts
                      </a>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }
    </div>
  `
})
export class FrameworkDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private complianceService = inject(ComplianceService);

  public framework = signal<ControlFramework | undefined>(undefined);
  public controls = signal<FrameworkControl[]>([]);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      const fw = this.complianceService.getFrameworkById(id);
      this.framework.set(fw);
      if (fw) {
        this.controls.set(this.complianceService.getControlsForFramework(fw.id));
      }
    }
  }
}
