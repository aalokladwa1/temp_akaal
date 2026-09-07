import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationRepairService } from '../validation-repair.service';
import { RevalidationDimension } from '../validation-repair.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-repair-revalidation-card',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200/80 rounded-xl p-6 lg:p-7 shadow-2xs flex flex-col gap-6">
      
      <!-- Section Header -->
      <div class="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-slate-100">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shrink-0">
            <app-lucide-icon name="check-circle-2" [size]="15"></app-lucide-icon>
          </div>
          <div class="flex flex-col gap-0.5">
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
              6. Mandatory Revalidation &mdash; Validation #11 Canonical Authority
            </h2>
            <p class="text-[11.5px] text-slate-500">
              Independent mathematical and structural verification establishing post-repair compliance
            </p>
          </div>
        </div>

        @if (store.revalidation(); as reval) {
          <div class="flex items-center gap-2">
            <span [ngClass]="getRevalidationBadgeClass(reval.state)"
                  class="px-2.5 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider border flex items-center gap-1.5">
              <app-lucide-icon [name]="getRevalidationIcon(reval.state)" [size]="12"></app-lucide-icon>
              <span>{{ formatRevalidationState(reval.state) }}</span>
            </span>
          </div>
        }
      </div>

      <!-- Mandatory Return to Validation #11 Law Callout -->
      <div class="p-4.5 sm:p-5 rounded-xl bg-blue-50/70 border border-blue-200 flex items-start gap-3.5 text-xs text-blue-900 shadow-2xs">
        <div class="shrink-0 mt-0.5 text-blue-600">
          <app-lucide-icon name="shield-check" [size]="18"></app-lucide-icon>
        </div>
        <div class="flex flex-col gap-1">
          <span class="font-bold uppercase tracking-wider text-[11px] text-blue-800 font-heading">
            Permanent Law: Repair Completion &ne; Validation Success
          </span>
          <p class="text-[11.5px] leading-relaxed text-blue-900/90 font-normal">
            A successful target mutation does not automatically certify the migration. Post-repair proof obligations must be independently evaluated through Validation #11 to establish mathematical integrity.
          </p>
        </div>
      </div>

      <!-- Revalidation Content -->
      @if (store.revalidation(); as reval) {
        <div class="flex flex-col gap-6">
          
          <!-- Proof Tiers Verification Matrix (4 Tiers) -->
          <div class="flex flex-col gap-3.5">
            <div class="flex items-center justify-between text-xs">
              <div class="flex items-center gap-2 text-slate-600">
                <app-lucide-icon name="layers" [size]="14"></app-lucide-icon>
                <span class="text-xs font-bold uppercase tracking-wider font-heading">
                  Validation Proof Framework (4 Proof Obligations)
                </span>
              </div>
              <span class="font-mono text-xs text-slate-500 bg-slate-50 px-2.5 py-1 rounded border border-slate-200">Engine: {{ reval.engine }}</span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              @for (tier of reval.proofTiers; track tier.tier) {
                <div class="p-5 rounded-xl border flex flex-col justify-between gap-4 bg-white shadow-2xs"
                     [ngClass]="tier.status === 'PASSED' ? 'border-emerald-200/90 bg-emerald-50/15' : (tier.status === 'FAILED' ? 'border-red-200/90 bg-red-50/15' : (tier.status === 'WITHHELD' ? 'border-amber-200/90 bg-amber-50/15' : 'border-slate-200/90'))">
                  
                  <div class="flex flex-col gap-2.5">
                    <div class="flex items-center justify-between">
                      <div class="flex items-center gap-1.5">
                        <app-lucide-icon [name]="getTierIcon(tier.tier)" [size]="14" class="text-slate-500"></app-lucide-icon>
                        <span class="text-xs font-mono font-bold text-slate-600 uppercase">{{ tier.tier }}</span>
                      </div>
                      <span class="px-2.5 py-0.5 rounded-md text-[10.5px] font-bold uppercase tracking-wider border shadow-2xs"
                            [ngClass]="getTierStatusBadgeClass(tier.status)">
                        {{ tier.status }}
                      </span>
                    </div>
                    <span class="text-xs font-bold text-slate-900 font-heading">{{ tier.name }}</span>
                    <p class="text-xs text-slate-600 leading-relaxed font-normal">
                      {{ tier.detail }}
                    </p>
                  </div>

                  <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-between text-xs">
                    <span class="text-slate-500 font-medium">Differences:</span>
                    <span class="font-mono font-bold" [ngClass]="tier.differencesFound > 0 ? 'text-rose-600' : 'text-slate-700'">
                      {{ tier.differencesFound }}
                    </span>
                  </div>

                </div>
              }
            </div>
          </div>

          <!-- Post-Revalidation Verdict Summary Card -->
          <div class="p-4.5 sm:p-5 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-2xs"
               [ngClass]="reval.state === 'PASSED' ? 'bg-emerald-50/60 border-emerald-200 text-emerald-950' : (reval.state === 'FAILED' ? 'bg-red-50/60 border-red-200 text-red-950' : 'bg-slate-50 border-slate-200 text-slate-800')">
            
            <div class="flex items-start gap-3.5">
              <div class="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 border mt-0.5"
                   [ngClass]="reval.state === 'PASSED' ? 'bg-emerald-100 border-emerald-300 text-emerald-700' : (reval.state === 'FAILED' ? 'bg-red-100 border-red-300 text-red-700' : 'bg-slate-100 border-slate-300 text-slate-600')">
                <app-lucide-icon [name]="reval.state === 'PASSED' ? 'check' : (reval.state === 'FAILED' ? 'x' : 'refresh-cw')" [size]="17"></app-lucide-icon>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-xs font-bold font-heading uppercase tracking-wider">
                  Post-Repair Verdict: {{ formatRevalidationState(reval.state) }}
                </span>
                <p class="text-xs leading-relaxed opacity-90 font-normal">
                  {{ reval.verdictSummary }}
                </p>
                @if (reval.findingsNote) {
                  <span class="text-[11px] italic font-medium opacity-80 mt-0.5">Note: {{ reval.findingsNote }}</span>
                }
              </div>
            </div>

            <!-- Rescan Trigger Action -->
            <div class="shrink-0">
              @if (reval.state === 'REQUIRED' || reval.state === 'RUNNING') {
                <button
                  type="button"
                  (click)="store.triggerRevalidation()"
                  class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
                  <app-lucide-icon name="refresh-cw" [size]="13" [class]="reval.state === 'RUNNING' ? 'animate-spin' : ''"></app-lucide-icon>
                  <span>{{ reval.state === 'RUNNING' ? 'Revalidating...' : 'Trigger Validation #11 Rescan' }}</span>
                </button>
              } @else if (reval.state === 'PASSED') {
                <span class="px-3.5 py-2 rounded-lg bg-emerald-50 text-emerald-800 text-xs font-bold flex items-center gap-1.5 border border-emerald-200">
                  <app-lucide-icon name="check-circle-2" [size]="13"></app-lucide-icon>
                  <span>100% Proof Verified</span>
                </span>
              } @else if (reval.state === 'FAILED') {
                <button
                  type="button"
                  (click)="store.triggerRevalidation()"
                  class="h-9 px-4 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
                  <app-lucide-icon name="rotate-ccw" [size]="13"></app-lucide-icon>
                  <span>Retry Validation #11 Rescan</span>
                </button>
              }
            </div>

          </div>

        </div>
      } @else {
        <!-- Revalidation Not Started State -->
        <div class="p-10 rounded-xl bg-slate-50 border border-slate-200 text-center flex flex-col items-center justify-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500">
            <app-lucide-icon name="refresh-cw" [size]="22"></app-lucide-icon>
          </div>
          <span class="text-xs font-bold text-slate-800 font-heading">Revalidation Not Started</span>
          <p class="text-xs text-slate-500 max-w-md leading-relaxed">
            Validation #11 re-evaluation will automatically activate once controlled repairs are executed.
          </p>
        </div>
      }

    </section>
  `
})
export class RepairRevalidationCardComponent {
  readonly store = inject(ValidationRepairService);

  formatRevalidationState(state: RevalidationDimension): string {
    switch (state) {
      case 'PASSED': return 'Revalidation Passed';
      case 'FAILED': return 'Revalidation Failed';
      case 'WITHHELD': return 'Result Withheld';
      case 'RUNNING': return 'Revalidation Running';
      case 'REQUIRED': return 'Revalidation Required';
      case 'NOT_REQUIRED': return 'Not Required';
      case 'NOT_STARTED': return 'Not Started';
      case 'INTERRUPTED': return 'Interrupted';
      default: return state;
    }
  }

  getRevalidationBadgeClass(state: RevalidationDimension): string {
    switch (state) {
      case 'PASSED': return 'bg-emerald-50 border-emerald-200 text-emerald-800';
      case 'FAILED': return 'bg-red-50 border-red-200 text-red-800';
      case 'WITHHELD':
      case 'INTERRUPTED': return 'bg-amber-50 border-amber-200 text-amber-800';
      case 'RUNNING': return 'bg-blue-50 border-blue-200 text-blue-800';
      default: return 'bg-slate-100 border-slate-200 text-slate-700';
    }
  }

  getRevalidationIcon(state: RevalidationDimension): string {
    switch (state) {
      case 'PASSED': return 'check-circle-2';
      case 'FAILED': return 'alert-octagon';
      case 'WITHHELD': return 'help-circle';
      case 'RUNNING': return 'refresh-cw';
      case 'REQUIRED': return 'clock';
      default: return 'circle';
    }
  }

  getTierStatusBadgeClass(status: string): string {
    switch (status) {
      case 'PASSED': return 'bg-emerald-50 text-emerald-800 border-emerald-200';
      case 'FAILED': return 'bg-red-50 text-red-800 border-red-200';
      case 'WITHHELD': return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'RUNNING': return 'bg-blue-50 text-blue-800 border-blue-200';
      default: return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  }

  getTierIcon(tier: string): string {
    switch (tier) {
      case 'TIER_1': return 'layout-grid';
      case 'TIER_2': return 'hash';
      case 'TIER_3': return 'fingerprint';
      case 'TIER_4': return 'file-diff';
      default: return 'shield';
    }
  }
}
