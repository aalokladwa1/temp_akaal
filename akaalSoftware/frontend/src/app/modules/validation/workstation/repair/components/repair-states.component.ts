import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RepairViewStatus } from '../validation-repair.models';
import { ValidationRepairService } from '../validation-repair.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-repair-states',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="w-full">
      @switch (status) {
        
        <!-- State 1: UNAVAILABLE (Truthful Production Default) -->
        @case ('UNAVAILABLE') {
          <section class="bg-white border border-slate-200/80 rounded-xl p-10 sm:p-12 shadow-2xs flex flex-col items-center justify-center text-center max-w-2xl mx-auto my-6 gap-6">
            <div class="w-16 h-16 rounded-2xl bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600 shadow-2xs">
              <app-lucide-icon name="wrench" [size]="32"></app-lucide-icon>
            </div>
            
            <div class="flex flex-col gap-2 max-w-lg">
              <h2 class="text-base font-bold text-slate-900 font-heading">
                Controlled Repair Execution Unavailable
              </h2>
              <p class="text-xs text-slate-600 leading-relaxed">
                The current Validation Mission is operating in strictly read-only mode (M8 authority).
                Controlled target mutation requires an authorized physical repair executor connected via governed P7B change packages.
              </p>
            </div>

            <div class="p-4.5 sm:p-5 rounded-xl bg-slate-50/80 border border-slate-200 text-left w-full text-xs flex flex-col gap-3 text-slate-700 shadow-2xs">
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-medium">Validation Authority:</span>
                <span class="font-mono font-bold text-slate-900">M8 Validation #11 (Non-mutating)</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-medium">Remediation Status:</span>
                <span class="font-mono text-slate-800 font-semibold">Pre-P7D Standby</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-medium">Governance Policy:</span>
                <span class="font-mono text-slate-800">Dual-Signoff Required</span>
              </div>
            </div>

            <div class="flex items-center gap-3 pt-2">
              <button
                type="button"
                (click)="store.setFixture('SINGLE_UPDATE_PROPOSAL')"
                class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold cursor-pointer transition-colors shadow-2xs flex items-center gap-2">
                <app-lucide-icon name="sparkles" [size]="13"></app-lucide-icon>
                <span>Explore Governed Repair Workflow</span>
              </button>
            </div>
          </section>
        }

        <!-- State 2: NO_REMEDIATION_REQUIRED (Zero Discrepancies / Passed) -->
        @case ('NO_REMEDIATION_REQUIRED') {
          <section class="bg-white border border-slate-200/80 rounded-xl p-10 sm:p-12 shadow-2xs flex flex-col items-center justify-center text-center max-w-2xl mx-auto my-6 gap-6">
            <div class="w-16 h-16 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shadow-2xs">
              <app-lucide-icon name="check-circle-2" [size]="32"></app-lucide-icon>
            </div>
            
            <div class="flex flex-col gap-2 max-w-lg">
              <h2 class="text-base font-bold text-slate-900 font-heading">
                No Findings Require Controlled Remediation
              </h2>
              <p class="text-xs text-slate-600 leading-relaxed">
                All validated datasets in scope satisfy required proof obligations across Structural, Cardinality, Partition Hash, and Attribute levels.
              </p>
            </div>

            <div class="p-4.5 sm:p-5 rounded-xl bg-emerald-50/40 border border-emerald-200 text-left w-full text-xs flex flex-col gap-2.5 text-emerald-950 shadow-2xs">
              <div class="flex items-center justify-between">
                <span class="font-medium text-emerald-800">Validation Verification:</span>
                <span class="font-bold text-emerald-950">100% Proof Verification Complete</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="font-medium text-emerald-800">Target Divergence:</span>
                <span class="font-mono font-bold text-emerald-950">0 Differences Detected</span>
              </div>
            </div>
          </section>
        }

        <!-- State 3: AUDIT_ONLY (Policy Prohibits Mutation) -->
        @case ('AUDIT_ONLY') {
          <section class="bg-white border border-slate-200/80 rounded-xl p-10 sm:p-12 shadow-2xs flex flex-col items-center justify-center text-center max-w-2xl mx-auto my-6 gap-6">
            <div class="w-16 h-16 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 shadow-2xs">
              <app-lucide-icon name="lock" [size]="32"></app-lucide-icon>
            </div>
            
            <div class="flex flex-col gap-2 max-w-lg">
              <h2 class="text-base font-bold text-slate-900 font-heading">
                Audit-Only Mission &mdash; Mutation Prohibited
              </h2>
              <p class="text-xs text-slate-600 leading-relaxed">
                This validation mission is configured with an immutable audit-only governance policy. Target modifications cannot be executed through this workspace.
              </p>
            </div>

            <div class="p-4.5 sm:p-5 rounded-xl bg-slate-50/80 border border-slate-200 text-left w-full text-xs flex flex-col gap-2.5 text-slate-700 shadow-2xs">
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-medium">Policy Classification:</span>
                <span class="font-mono font-bold text-slate-900">READ_ONLY_AUDIT_STRICT</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-medium">Reconciliation Path:</span>
                <span class="font-semibold text-slate-800">External Governed Remediation</span>
              </div>
            </div>
          </section>
        }

        <!-- State 4: LOADING (Pulse Skeleton) -->
        @case ('LOADING') {
          <section class="bg-white border border-slate-200/80 rounded-xl p-8 lg:p-10 shadow-2xs flex flex-col gap-6 animate-pulse">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-xl bg-slate-200"></div>
              <div class="flex flex-col gap-2 flex-1">
                <div class="h-4 bg-slate-200 rounded w-1/4"></div>
                <div class="h-3 bg-slate-200 rounded w-1/2"></div>
              </div>
            </div>
            <div class="h-32 bg-slate-100 rounded-xl"></div>
            <div class="grid grid-cols-4 gap-4">
              <div class="h-20 bg-slate-100 rounded-xl"></div>
              <div class="h-20 bg-slate-100 rounded-xl"></div>
              <div class="h-20 bg-slate-100 rounded-xl"></div>
              <div class="h-20 bg-slate-100 rounded-xl"></div>
            </div>
          </section>
        }

        <!-- State 5: ERROR -->
        @case ('ERROR') {
          <section class="bg-white border border-red-200 rounded-xl p-10 sm:p-12 shadow-2xs flex flex-col items-center justify-center text-center max-w-2xl mx-auto my-6 gap-6">
            <div class="w-16 h-16 rounded-2xl bg-red-50 border border-red-200 flex items-center justify-center text-red-600 shadow-2xs">
              <app-lucide-icon name="alert-triangle" [size]="32"></app-lucide-icon>
            </div>
            
            <div class="flex flex-col gap-2 max-w-lg">
              <h2 class="text-base font-bold text-slate-900 font-heading">
                Remediation Context Retrieval Error
              </h2>
              <p class="text-xs text-slate-600 leading-relaxed">
                {{ errorMessage || 'Failed to retrieve proposal data from canonical authorities.' }}
              </p>
            </div>

            <button
              type="button"
              (click)="store.setFixture('SINGLE_UPDATE_PROPOSAL')"
              class="h-9 px-4 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold cursor-pointer transition-colors shadow-2xs flex items-center gap-2">
              <app-lucide-icon name="rotate-ccw" [size]="13"></app-lucide-icon>
              <span>Retry Retrieval</span>
            </button>
          </section>
        }

      }
    </div>
  `
})
export class RepairStatesComponent {
  @Input() status: RepairViewStatus = 'UNAVAILABLE';
  @Input() errorMessage?: string;
  readonly store = inject(ValidationRepairService);
}
