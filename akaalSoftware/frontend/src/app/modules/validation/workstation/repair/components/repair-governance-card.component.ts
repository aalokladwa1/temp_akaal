import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationRepairService } from '../validation-repair.service';
import { GovernanceDimension } from '../validation-repair.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-repair-governance-card',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200/80 rounded-xl p-6 lg:p-7 shadow-2xs flex flex-col gap-6">
      
      <!-- Section Header -->
      <div class="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-slate-100">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shrink-0">
            <app-lucide-icon name="shield" [size]="15"></app-lucide-icon>
          </div>
          <div class="flex flex-col gap-0.5">
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
              4. Governance, Policy &amp; Cryptographic Authorization
            </h2>
            <p class="text-[11.5px] text-slate-500">
              Target mutation authorization governed by institutional sign-off policies and HMAC plan bindings
            </p>
          </div>
        </div>

        @if (store.governance(); as gov) {
          <div class="flex items-center gap-2">
            <span [ngClass]="getGovernanceBadgeClass(gov.state)"
                  class="px-2.5 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider border flex items-center gap-1.5">
              <app-lucide-icon [name]="getGovernanceIcon(gov.state)" [size]="12"></app-lucide-icon>
              <span>{{ formatGovernanceState(gov.state) }}</span>
            </span>
          </div>
        }
      </div>

      <!-- Governance Content -->
      @if (store.governance(); as gov) {
        <div class="flex flex-col gap-6">
          
          <!-- Policy Summary Banner -->
          <div class="p-4.5 sm:p-5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="shield-check" [size]="14" class="text-indigo-600 shrink-0"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-900 font-heading">{{ gov.policyName }}</span>
                <span class="text-[10.5px] font-mono text-slate-400">({{ gov.policyId }})</span>
              </div>
              <p class="text-xs text-slate-600 leading-relaxed max-w-2xl">
                {{ gov.policySummary }}
              </p>
            </div>

            <div class="flex items-center gap-3 shrink-0">
              <div class="px-3.5 py-2 rounded-lg bg-white border border-slate-200 text-xs flex flex-col items-center shadow-2xs">
                <span class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Quorum Satisfied</span>
                <span class="font-mono font-bold text-slate-900">{{ gov.quorumSatisfied }} of {{ gov.quorumRequired }}</span>
              </div>
            </div>
          </div>

          <!-- Approver Roles & Signature Cards -->
          <div class="flex flex-col gap-3.5">
            <div class="flex items-center gap-2 text-slate-600">
              <app-lucide-icon name="users" [size]="14"></app-lucide-icon>
              <span class="text-xs font-bold uppercase tracking-wider font-heading">
                Custodians &amp; Sign-off Roles ({{ gov.approvers.length }} Required)
              </span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              @for (app of gov.approvers; track app.role) {
                <div class="p-5 rounded-xl border flex items-center justify-between gap-4 bg-white transition-all shadow-2xs"
                     [ngClass]="app.status === 'APPROVED' ? 'border-emerald-200/90 bg-emerald-50/15' : (app.status === 'REJECTED' ? 'border-red-200/90 bg-red-50/15' : 'border-slate-200/90')">
                  
                  <div class="flex items-center gap-3.5 min-w-0">
                    <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border shadow-2xs"
                         [ngClass]="app.status === 'APPROVED' ? 'bg-emerald-50 border-emerald-200 text-emerald-600' : (app.status === 'REJECTED' ? 'bg-red-50 border-red-200 text-red-600' : 'bg-slate-50 border-slate-200 text-slate-500')">
                      <app-lucide-icon [name]="app.status === 'APPROVED' ? 'user-check' : (app.status === 'REJECTED' ? 'user-x' : 'user-round')" [size]="18"></app-lucide-icon>
                    </div>

                    <div class="flex flex-col gap-1 min-w-0">
                      <span class="text-xs font-bold text-slate-900 truncate font-heading">{{ app.role }}</span>
                      @if (app.userName) {
                        <span class="text-[11.5px] font-mono text-slate-600 truncate">{{ app.userName }}</span>
                      }
                      @if (app.timestamp) {
                        <span class="text-[11px] text-slate-400">Signed {{ app.timestamp }}</span>
                      }
                      @if (app.signatureDigest) {
                        <span class="text-[10.5px] font-mono text-emerald-700 bg-emerald-50/60 px-2 py-0.5 rounded border border-emerald-200/60 truncate max-w-[200px]" [title]="app.signatureDigest">{{ app.signatureDigest }}</span>
                      }
                    </div>
                  </div>

                  <div class="shrink-0">
                    @if (app.status === 'APPROVED') {
                      <span class="px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1.5 shadow-2xs">
                        <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                        <span>Signed</span>
                      </span>
                    } @else if (app.status === 'REJECTED') {
                      <span class="px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider bg-red-50 text-red-800 border border-red-200 flex items-center gap-1.5 shadow-2xs">
                        <app-lucide-icon name="x" [size]="12"></app-lucide-icon>
                        <span>Rejected</span>
                      </span>
                    } @else {
                      <button
                        type="button"
                        (click)="store.approveProposal(app.role)"
                        class="h-9 px-3.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold cursor-pointer transition-colors shadow-2xs flex items-center gap-2">
                        <app-lucide-icon name="badge-check" [size]="14"></app-lucide-icon>
                        <span>Sign Off</span>
                      </button>
                    }
                  </div>

                </div>
              }
            </div>
          </div>

          <!-- Execution Conditions & Authorization Status -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            <!-- Prerequisites Checklist -->
            <div class="p-4.5 sm:p-5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col gap-2.5">
              <div class="flex items-center gap-2 text-slate-700">
                <app-lucide-icon name="file-check" [size]="13"></app-lucide-icon>
                <span class="text-[10.5px] font-bold uppercase tracking-wider">Policy Authorization Conditions</span>
              </div>
              <ul class="flex flex-col gap-2 text-xs text-slate-700">
                @for (cond of gov.conditions; track cond) {
                  <li class="flex items-start gap-2.5">
                    <app-lucide-icon name="check-circle-2" [size]="14" class="text-emerald-600 shrink-0 mt-0.5"></app-lucide-icon>
                    <span class="leading-relaxed">{{ cond }}</span>
                  </li>
                } @empty {
                  <li class="text-slate-400 italic">No additional conditions specified</li>
                }
              </ul>
            </div>

            <!-- Authorization Verdict Card -->
            <div class="p-4.5 sm:p-5 rounded-xl border flex flex-col justify-between gap-3.5"
                 [ngClass]="gov.isAuthorized ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900' : (gov.state === 'REJECTED' ? 'bg-red-50/60 border-red-200 text-red-900' : 'bg-slate-50 border-slate-200 text-slate-800')">
              
              <div class="flex flex-col gap-1.5">
                <div class="flex items-center gap-2">
                  <app-lucide-icon [name]="gov.isAuthorized ? 'shield-check' : (gov.state === 'REJECTED' ? 'shield-x' : 'clock')" [size]="16"></app-lucide-icon>
                  <span class="text-xs font-bold uppercase tracking-wider font-heading">
                    {{ gov.isAuthorized ? 'Target Mutation Authorized' : (gov.state === 'REJECTED' ? 'Proposal Rejected' : 'Authorization Pending') }}
                  </span>
                </div>
                <p class="text-xs leading-relaxed opacity-90 font-normal">
                  {{ gov.authorizationNote || (gov.isAuthorized ? 'Plan satisfies all governance conditions and quorum.' : 'Awaiting required sign-offs.') }}
                </p>
                @if (gov.rejectionReason) {
                  <div class="mt-2 p-3 rounded-lg bg-white/90 border border-red-200 text-xs font-medium text-red-900">
                    <span class="font-bold">Rejection Rationale:</span> {{ gov.rejectionReason }}
                  </div>
                }
              </div>

              <!-- Rejection Trigger Button (If Pending) -->
              @if (gov.state === 'APPROVAL_REQUIRED' || gov.state === 'PENDING') {
                <div class="flex items-center gap-2 pt-2.5 border-t border-slate-200/60 justify-end">
                  <button
                    type="button"
                    (click)="store.rejectProposal('Operator rejected plan during governed review.')"
                    class="h-8 px-3 rounded-lg bg-white hover:bg-red-50 border border-red-200 text-red-700 text-xs font-semibold cursor-pointer transition-colors flex items-center gap-1.5 shadow-2xs">
                    <app-lucide-icon name="shield-x" [size]="12"></app-lucide-icon>
                    <span>Reject Proposal</span>
                  </button>
                </div>
              }

            </div>

          </div>

          <!-- Governance Permanent Law Footnote -->
          <div class="p-4 rounded-xl bg-slate-50/80 border border-slate-200 text-[11.5px] text-slate-500 flex items-center gap-2.5">
            <app-lucide-icon name="info" [size]="14" class="text-slate-400 shrink-0"></app-lucide-icon>
            <span class="leading-relaxed">
              <strong class="text-slate-700 font-semibold">Governance Permanent Law:</strong> Human approval is policy-dependent, not universally mandatory. Approval alone does not guarantee execution if operational or boundary fencing locks expire.
            </span>
          </div>

        </div>
      } @else {
        <!-- Governance Not Evaluated State -->
        <div class="p-10 rounded-xl bg-slate-50 border border-slate-200 text-center flex flex-col items-center justify-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500">
            <app-lucide-icon name="shield" [size]="22"></app-lucide-icon>
          </div>
          <span class="text-xs font-bold text-slate-800 font-heading">Governance State Not Evaluated</span>
          <p class="text-xs text-slate-500 max-w-md leading-relaxed">
            No institutional approval policy is active for the current workspace context.
          </p>
        </div>
      }

    </section>
  `
})
export class RepairGovernanceCardComponent {
  readonly store = inject(ValidationRepairService);

  formatGovernanceState(state: GovernanceDimension): string {
    switch (state) {
      case 'APPROVED': return 'Fully Authorized';
      case 'NO_APPROVAL_REQUIRED': return 'Auto-Authorized (Policy)';
      case 'APPROVAL_REQUIRED': return 'Approval Required';
      case 'PENDING': return 'Quorum Pending';
      case 'REJECTED': return 'Rejected';
      case 'EXPIRED': return 'Lease Expired';
      default: return state;
    }
  }

  getGovernanceBadgeClass(state: GovernanceDimension): string {
    switch (state) {
      case 'APPROVED':
      case 'NO_APPROVAL_REQUIRED': return 'bg-emerald-50 border-emerald-200 text-emerald-800';
      case 'REJECTED': return 'bg-red-50 border-red-200 text-red-800';
      case 'APPROVAL_REQUIRED':
      case 'PENDING': return 'bg-amber-50 border-amber-200 text-amber-800';
      case 'EXPIRED': return 'bg-slate-100 border-slate-200 text-slate-700';
      default: return 'bg-slate-100 border-slate-200 text-slate-700';
    }
  }

  getGovernanceIcon(state: GovernanceDimension): string {
    switch (state) {
      case 'APPROVED':
      case 'NO_APPROVAL_REQUIRED': return 'shield-check';
      case 'REJECTED': return 'shield-x';
      case 'APPROVAL_REQUIRED':
      case 'PENDING': return 'clock';
      default: return 'shield';
    }
  }
}
