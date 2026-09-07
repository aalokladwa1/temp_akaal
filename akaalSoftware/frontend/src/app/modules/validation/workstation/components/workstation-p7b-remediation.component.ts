import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationWorkstationService } from '../validation-workstation.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-workstation-p7b-remediation',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      <!-- Card 1: Baseline Integrity Assurance -->
      <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-4">
        <div>
          <div class="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="shield" [size]="16" class="text-blue-600" />
              <h2 class="text-sm font-bold text-slate-900 tracking-tight font-heading">
                P7B Baseline Integrity Contract
              </h2>
            </div>
            
            <!-- Baseline Status Badge -->
            <span [ngClass]="getBaselineStatusBadgeClasses(store.state().remediation.baselineStatus)"
                  class="px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider border">
              {{ store.state().remediation.baselineStatus || 'NOT_AVAILABLE' }}
            </span>
          </div>

          <div class="flex flex-col gap-3 text-xs">
            <p class="text-slate-600 leading-relaxed">
              M8 Validation enforces read-only comparison against a frozen baseline checkpoint.
              Mutations during execution are detected as baseline drift rather than true parity failures.
            </p>

            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-2 font-mono text-[11px]">
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-sans font-medium">Baseline Identity:</span>
                <span class="text-slate-800 font-semibold">{{ store.state().remediation.baselineId || 'None registered' }}</span>
              </div>
              @if (store.state().remediation.baselineHash) {
                <div class="flex items-center justify-between">
                  <span class="text-slate-500 font-sans font-medium">SHA-256 Digest:</span>
                  <span class="text-slate-700 truncate max-w-[220px]" [title]="store.state().remediation.baselineHash">
                    {{ store.state().remediation.baselineHash }}
                  </span>
                </div>
              }
            </div>
          </div>
        </div>

        <div class="text-[11px] text-slate-400 font-medium">
          Evidence Artifact Standard &middot; P7B Compliance Active
        </div>
      </section>

      <!-- Card 2: Governed Remediation & Pipeline Context -->
      <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-4">
        <div>
          <div class="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="wrench" [size]="16" class="text-blue-600" />
              <h2 class="text-sm font-bold text-slate-900 tracking-tight font-heading">
                Governed Remediation &amp; Pipeline Context
              </h2>
            </div>
            <span class="text-[11px] font-semibold text-slate-500">
              Non-Mutating Authority
            </span>
          </div>

          <div class="flex flex-col gap-3 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Linked Pipeline Migration:</span>
              @if (store.state().remediation.linkedMigrationId) {
                <span class="font-mono font-bold text-blue-700">
                  {{ store.state().remediation.linkedMigrationId }}
                </span>
              } @else {
                <span class="text-slate-400">Standalone (Unlinked)</span>
              }
            </div>

            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Remediation Policy:</span>
              <span class="font-semibold text-slate-800">{{ store.state().remediation.autoRepairPolicy || 'Manual Operator Review' }}</span>
            </div>

            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Revalidation Iterations:</span>
              <span class="font-mono font-bold text-slate-800">{{ store.state().remediation.revalidationCount || 0 }} cycles recorded</span>
            </div>

            <p class="text-[11px] text-slate-500 leading-relaxed mt-1">
              Validation Mission is strictly read-only and analytical. Any automated or manual repair action generates a P7B Governed Repair Plan requiring dual-operator signoff before target mutation.
            </p>
          </div>
        </div>

        <div class="flex items-center justify-between pt-2 border-t border-slate-100">
          <span class="text-[11px] text-slate-400">Safe Operator Sandbox</span>
          <button
            type="button"
            (click)="store.setActiveTab('repair')"
            class="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline cursor-pointer flex items-center gap-1">
            <span>Explore Repair &amp; Revalidation</span>
            <app-lucide-icon name="arrow-right" [size]="12" />
          </button>
        </div>
      </section>

    </div>
  `
})
export class WorkstationP7bRemediationComponent {
  readonly store = inject(ValidationWorkstationService);

  getBaselineStatusBadgeClasses(status?: string): string {
    switch (status) {
      case 'VALID': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'STALE': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'NOT_AVAILABLE':
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }
}
