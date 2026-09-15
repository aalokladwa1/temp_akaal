/**
 * AKAAL Administration — 5.7 Data Sovereignty & Residency Policies
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { InfrastructureService } from '../../services/infrastructure.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-sovereignty-policies',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/infrastructure/placement-hub" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Placement &amp; Governance
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Data Sovereignty &amp; Residency Boundaries</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Technical geographic constraints requiring data to remain within configured regional boundaries during replication and transformation.
            </p>
          </div>
        </div>
      </div>

      <!-- Policy Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        @for (policy of service.sovereigntyPolicies(); track policy.id) {
          <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5">
            <div class="flex flex-col gap-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                  <span class="font-bold text-slate-900 text-base font-heading">{{ policy.name }}</span>
                </div>
                <span class="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {{ policy.status }}
                </span>
              </div>

              <div class="flex flex-col gap-1.5 mt-2">
                <span class="text-xs font-bold text-slate-700 font-heading">Allowed Target Regions:</span>
                <div class="flex flex-wrap gap-1.5">
                  @for (r of policy.allowedRegions; track r) {
                    <span class="px-2 py-0.5 bg-slate-50 border border-slate-200 rounded text-xs font-mono text-slate-800">
                      {{ r }}
                    </span>
                  }
                </div>
              </div>

              <div class="flex flex-col gap-1.5 mt-2">
                <span class="text-xs font-bold text-slate-700 font-heading">Strictly Denied Egress Regions:</span>
                <div class="flex flex-wrap gap-1.5">
                  @for (r of policy.deniedRegions; track r) {
                    <span class="px-2 py-0.5 bg-rose-50 border border-rose-200 rounded text-xs font-mono text-rose-700">
                      {{ r }}
                    </span>
                  }
                </div>
              </div>

              <div class="flex flex-col gap-1.5 mt-2">
                <span class="text-xs font-bold text-slate-700 font-heading">Restricted Classification Classes:</span>
                <div class="flex flex-wrap gap-1.5">
                  @for (c of policy.restrictedDataClasses; track c) {
                    <span class="px-2 py-0.5 bg-slate-100 border border-slate-200 rounded text-xs font-mono text-slate-700">
                      {{ c }}
                    </span>
                  }
                </div>
              </div>
            </div>

            <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Boundary Enforcement: <strong class="text-emerald-700 font-semibold">{{ policy.enforceStrictBoundary ? 'Active Quarantine Barrier' : 'Audit Mode' }}</strong></span>
              <span class="font-mono text-[11px] text-slate-400">Jurisdiction: {{ policy.jurisdiction }}</span>
            </div>
          </div>
        }
      </div>

    </div>
  `
})
export class SovereigntyPoliciesComponent {
  public service = inject(InfrastructureService);
}
