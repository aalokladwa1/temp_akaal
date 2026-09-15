import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { GovernanceService } from '../../services/governance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { PolicySimulationResult } from '../../models/governance.models';

@Component({
  selector: 'app-policy-simulation',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/governance-centre" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Governance Centre
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Policy Evaluation Simulator</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Simulate policy engine evaluation against hypothetical resource operations prior to production rollout.
          </p>
        </div>
      </div>

      <!-- Simulator Inputs -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs md:col-span-1 flex flex-col gap-4 text-xs">
          <h2 class="text-sm font-bold text-slate-900 font-heading border-b border-slate-100 pb-2">Simulation Parameters</h2>
          
          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Target Policy Code</label>
            <input type="text" [(ngModel)]="policyCode" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Target Resource ARN / ID</label>
            <input type="text" [(ngModel)]="targetResource" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Action Name</label>
            <input type="text" [(ngModel)]="action" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500" />
          </div>

          <button (click)="runSim()" class="mt-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
            Run Evaluation Simulator
          </button>
        </div>

        <!-- Simulation Output -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs md:col-span-2 flex flex-col gap-4 text-xs" *ngIf="simResult()">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 class="text-sm font-bold text-slate-900 font-heading">Evaluation Result</h2>
            <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 font-mono">
              {{ simResult()?.evaluationDecision }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <span class="text-slate-500 font-medium">Policy Evaluated:</span>
              <div class="font-bold text-slate-900">{{ simResult()?.policyCode }}</div>
            </div>
            <div>
              <span class="text-slate-500 font-medium">Action:</span>
              <div class="font-bold text-slate-900">{{ simResult()?.action }}</div>
            </div>
          </div>

          <div class="flex flex-col gap-2 pt-2">
            <span class="text-slate-500 font-medium">Evaluation Audit Reasons:</span>
            <ul class="list-disc pl-5 text-slate-700 space-y-1">
              <li *ngFor="let r of simResult()?.reasons">{{ r }}</li>
            </ul>
          </div>
        </div>
      </div>

    </div>
  `
})
export class PolicySimulationComponent {
  private govService = inject(GovernanceService);

  public policyCode = 'POL-MASK-001';
  public targetResource = 'arn:akaal:pg:database/prod_analytics_raw';
  public action = 'akaal:db:execute_migration';

  public simResult = signal<PolicySimulationResult | null>(null);

  public runSim(): void {
    const res = this.govService.simulatePolicy(this.policyCode, this.targetResource, this.action);
    this.simResult.set(res);
  }
}