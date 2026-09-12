import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { GovernanceService } from '../../services/governance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-break-glass-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
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
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Break-Glass Emergency Access</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Air-gapped emergency override procedures for disaster recovery and total lockout remediation.
          </p>
        </div>
      </div>

      <!-- Status Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
          <div class="flex items-center gap-3">
            <span class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></span>
            <h2 class="text-base font-bold text-slate-900 font-heading">Escrow Vault Status: {{ govService.breakGlass().status }}</h2>
          </div>
          <span class="rounded px-2.5 py-1 text-[11px] font-semibold bg-emerald-50 text-emerald-700 font-mono">
            HSM Key ID: {{ govService.breakGlass().emergencyEscrowKeyId }}
          </span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Primary Incident Commander</span>
            <span class="font-semibold text-slate-900">{{ govService.breakGlass().primaryIncidentCommander }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Secondary Incident Commander</span>
            <span class="font-semibold text-slate-900">{{ govService.breakGlass().secondaryIncidentCommander }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Auto-Revocation Window</span>
            <span class="font-semibold text-slate-900">{{ govService.breakGlass().autoRevokeHours }} hours</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Last Drilled Date</span>
            <span class="font-semibold text-slate-900">{{ govService.breakGlass().lastDrillDate | date:'mediumDate' }}</span>
          </div>
        </div>
      </div>

    </div>
  `
})
export class BreakGlassListComponent {
  public govService = inject(GovernanceService);
}