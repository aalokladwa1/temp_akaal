import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { GovernanceService } from '../services/governance.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-governance-home',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Top Premium Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Administration
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-6 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1.5">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Governance Centre</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Multi-stage quorum approvals, maker-checker dual authorization, Separation of Duties (SoD) policies, and immutable audit logs.
          </p>
        </div>
      </div>

      <!-- KPI Metrics -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">Active Policies</span>
            <app-lucide-icon name="file-text" [size]="16" class="text-slate-400"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ govService.policies().length }}</div>
          <span class="text-[11px] text-emerald-600 font-medium">100% Strictly Enforced</span>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">Approval Chains</span>
            <app-lucide-icon name="git-pull-request" [size]="16" class="text-slate-400"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ govService.approvalChains().length }}</div>
          <span class="text-[11px] text-slate-500 font-medium">Quorum 2-3 Signers</span>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">SoD Conflict Rules</span>
            <app-lucide-icon name="shield-alert" [size]="16" class="text-amber-500"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ govService.sodRules().length }}</div>
          <span class="text-[11px] text-emerald-600 font-medium">Zero Critical Collisions</span>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">Break-Glass State</span>
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-rose-500"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ govService.breakGlass().status }}</div>
          <span class="text-[11px] text-emerald-600 font-medium">Escrow Key Armed</span>
        </div>
      </div>

      <!-- Domain Navigation Sections -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Section 1: Policy Framework -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col justify-between gap-6 shadow-2xs">
          <div class="flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="file-text" [size]="20"></app-lucide-icon>
              </div>
              <div>
                <h2 class="text-base font-bold text-slate-900 font-heading">Policy Framework</h2>
                <p class="text-xs text-slate-500 font-medium">Governance policies and real-time policy evaluation simulator.</p>
              </div>
            </div>
            
            <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
              <a routerLink="/administration/governance-centre/policies" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-blue-600 transition-colors">
                <span>Enterprise Policies</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ govService.policies().length }} policies</span>
              </a>
              <a routerLink="/administration/governance-centre/policy-simulation" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-blue-600 transition-colors">
                <span>Policy Evaluation Simulator</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-blue-50 text-blue-700">Interactive Tester</span>
              </a>
            </div>
          </div>
        </div>

        <!-- Section 2: Approvals & Dual Control -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col justify-between gap-6 shadow-2xs">
          <div class="flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                <app-lucide-icon name="git-pull-request" [size]="20"></app-lucide-icon>
              </div>
              <div>
                <h2 class="text-base font-bold text-slate-900 font-heading">Approvals & Dual Control</h2>
                <p class="text-xs text-slate-500 font-medium">Multi-stage approval workflows, signer groups, and maker/checker queues.</p>
              </div>
            </div>
            
            <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
              <a routerLink="/administration/governance-centre/approval-chains" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-indigo-600 transition-colors">
                <span>Approval Chains</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ govService.approvalChains().length }} chains</span>
              </a>
              <a routerLink="/administration/governance-centre/approver-groups" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-indigo-600 transition-colors">
                <span>Approver Signer Groups</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ govService.approverGroups().length }} groups</span>
              </a>
              <a routerLink="/administration/governance-centre/maker-checker" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-indigo-600 transition-colors">
                <span>Maker / Checker Enforcement</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-indigo-50 text-indigo-700">{{ govService.makerCheckerPolicies().length }} guarded ops</span>
              </a>
            </div>
          </div>
        </div>

        <!-- Section 3: Privileged Governance -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col justify-between gap-6 shadow-2xs">
          <div class="flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600">
                <app-lucide-icon name="shield-alert" [size]="20"></app-lucide-icon>
              </div>
              <div>
                <h2 class="text-base font-bold text-slate-900 font-heading">Privileged Governance</h2>
                <p class="text-xs text-slate-500 font-medium">Separation of duties, high-risk privileged actions, waivers, and break-glass escrow.</p>
              </div>
            </div>
            
            <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
              <a routerLink="/administration/governance-centre/sod" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-amber-600 transition-colors">
                <span>Separation of Duties (SoD)</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ govService.sodRules().length }} rules</span>
              </a>
              <a routerLink="/administration/governance-centre/privileged-ops" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-amber-600 transition-colors">
                <span>Privileged Operations</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ govService.privilegedOps().length }} protected</span>
              </a>
              <a routerLink="/administration/governance-centre/waivers" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-amber-600 transition-colors">
                <span>Exceptions & Waivers</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700">{{ govService.waivers().length }} active</span>
              </a>
              <a routerLink="/administration/governance-centre/break-glass" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-rose-600 transition-colors">
                <span>Break-Glass Emergency Access</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-rose-50 text-rose-700">Armed</span>
              </a>
            </div>
          </div>
        </div>

        <!-- Section 4: Audit & History -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col justify-between gap-6 shadow-2xs">
          <div class="flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
                <app-lucide-icon name="history" [size]="20"></app-lucide-icon>
              </div>
              <div>
                <h2 class="text-base font-bold text-slate-900 font-heading">Audit & History</h2>
                <p class="text-xs text-slate-500 font-medium">Immutable governance decision log and execution audit trail.</p>
              </div>
            </div>
            
            <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
              <a routerLink="/administration/governance-centre/history" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-emerald-600 transition-colors">
                <span>Governance History</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ govService.auditHistory().length }} events</span>
              </a>
            </div>
          </div>
        </div>

      </div>

    </div>
  `
})
export class GovernanceHomeComponent {
  public govService = inject(GovernanceService);
}