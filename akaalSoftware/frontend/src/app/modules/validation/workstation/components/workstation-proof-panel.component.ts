import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationWorkstationService } from '../validation-workstation.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProofTierItem, ProofTierStatus } from '../validation-workstation.models';

@Component({
  selector: 'app-workstation-proof-panel',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-5">
      
      <!-- Panel Header -->
      <div class="flex items-center justify-between border-b border-slate-100 pb-3 flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="shield-check" [size]="16" class="text-blue-600" />
          <h2 class="text-sm font-bold text-slate-900 tracking-tight font-heading">
            Multi-Tier Validation Proof Framework
          </h2>
        </div>
        <span class="text-[11px] font-medium text-slate-500">
          Hierarchical 4-Tier Verification Ladder
        </span>
      </div>

      <!-- 4 Proof Tiers Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        @for (tier of store.state().proofTiers; track tier.id) {
          <div class="p-5 rounded-xl border transition-all flex flex-col justify-between gap-4"
               [ngClass]="getTierContainerClasses(tier.status)">
            
            <!-- Tier Header Zone -->
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-start gap-3">
                <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border"
                      [ngClass]="getTierBadgeClasses(tier.status)">
                  Tier {{ tier.tierNumber }}
                </span>
                <div class="flex flex-col">
                  <h3 class="text-xs font-bold text-slate-900">{{ tier.name }}</h3>
                  <p class="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{{ tier.description }}</p>
                </div>
              </div>

              <!-- Status Badge -->
              <span class="px-2.5 py-1 rounded text-[11px] font-bold uppercase tracking-wider border shrink-0 inline-flex items-center gap-1.5"
                    [ngClass]="getStatusBadgeClasses(tier.status)">
                <span class="w-1.5 h-1.5 rounded-sm" [ngClass]="getStatusDotClasses(tier.status)"></span>
                <span>{{ formatStatus(tier.status) }}</span>
              </span>
            </div>

            <!-- Tier Metrics & Detail Line -->
            <div class="pt-3 border-t border-slate-200/60 flex flex-col gap-2">
              <div class="flex items-center justify-between text-xs">
                <span class="text-slate-500 font-medium">Evaluation Scope:</span>
                @if (tier.evaluatedCount !== null && tier.totalCount !== null) {
                  <span class="font-mono font-bold text-slate-800">
                    {{ tier.evaluatedCount | number }} / {{ tier.totalCount | number }}
                  </span>
                } @else {
                  <span class="font-mono text-slate-400 text-xs">Awaiting execution</span>
                }
              </div>

              <div class="flex items-center justify-between text-xs">
                <span class="text-slate-500 font-medium">Findings:</span>
                @if (tier.discrepancyCount !== null) {
                  @if (tier.discrepancyCount === 0) {
                    <span class="font-mono font-semibold text-emerald-700">0 Discrepancies</span>
                  } @else {
                    <span class="font-mono font-bold text-rose-700">
                      {{ tier.discrepancyCount | number }} Discrepancies Detected
                    </span>
                  }
                } @else {
                  <span class="font-mono text-slate-400 text-xs">Unverified</span>
                }
              </div>

              <!-- Technical Details Line -->
              <div class="text-[11px] font-mono text-slate-600 bg-white/70 p-2.5 rounded border border-slate-200/80">
                {{ tier.details }}
              </div>

              <!-- Mandatory Hostile XOR Defect Note (Specifically for Tier 3) -->
              @if (tier.note) {
                <div class="mt-1 px-2.5 py-1.5 rounded bg-amber-50/60 border border-amber-200/70 text-[10px] text-amber-800 flex items-start gap-1.5">
                  <app-lucide-icon name="alert-triangle" [size]="12" class="text-amber-600 shrink-0 mt-0.5" />
                  <span class="font-medium">{{ tier.note }}</span>
                </div>
              }
            </div>

          </div>
        }
      </div>

    </section>
  `
})
export class WorkstationProofPanelComponent {
  readonly store = inject(ValidationWorkstationService);

  formatStatus(status: ProofTierStatus): string {
    switch (status) {
      case 'NOT_EVALUATED': return 'Not Evaluated';
      case 'PASSED': return 'Passed';
      case 'FAILED': return 'Failed';
      case 'EVALUATING': return 'Evaluating';
      case 'SKIPPED': return 'Skipped';
    }
  }

  getTierContainerClasses(status: ProofTierStatus): string {
    switch (status) {
      case 'NOT_EVALUATED': return 'bg-slate-50/50 border-slate-200';
      case 'PASSED': return 'bg-emerald-50/30 border-emerald-200/80';
      case 'FAILED': return 'bg-rose-50/30 border-rose-200/80';
      case 'EVALUATING': return 'bg-blue-50/30 border-blue-200/80';
      case 'SKIPPED': return 'bg-slate-50/30 border-slate-200';
    }
  }

  getTierBadgeClasses(status: ProofTierStatus): string {
    switch (status) {
      case 'NOT_EVALUATED': return 'bg-white text-slate-600 border-slate-200';
      case 'PASSED': return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'FAILED': return 'bg-rose-100 text-rose-800 border-rose-300';
      case 'EVALUATING': return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'SKIPPED': return 'bg-slate-100 text-slate-500 border-slate-200';
    }
  }

  getStatusBadgeClasses(status: ProofTierStatus): string {
    switch (status) {
      case 'NOT_EVALUATED': return 'bg-slate-100 text-slate-600 border-slate-200';
      case 'PASSED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'FAILED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'EVALUATING': return 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse';
      case 'SKIPPED': return 'bg-slate-100 text-slate-500 border-slate-200';
    }
  }

  getStatusDotClasses(status: ProofTierStatus): string {
    switch (status) {
      case 'NOT_EVALUATED': return 'bg-slate-400';
      case 'PASSED': return 'bg-emerald-500';
      case 'FAILED': return 'bg-rose-500';
      case 'EVALUATING': return 'bg-blue-500';
      case 'SKIPPED': return 'bg-slate-400';
    }
  }
}
