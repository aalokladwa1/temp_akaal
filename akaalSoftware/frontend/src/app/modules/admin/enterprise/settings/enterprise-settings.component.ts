/**
 * AKAAL Administration — Enterprise Settings
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { EnterpriseService } from '../../services/enterprise.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-enterprise-settings',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Breadcrumbs -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/enterprise" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Enterprise
        
          </a>
        </div>

        

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Enterprise Settings</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Global tenant identity, baseline governance configurations, and security defaults.
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              routerLink="/administration/enterprise/settings/edit"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
              Edit Settings
            </a>
          </div>
        </div>
      </div>

      <!-- Settings Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Organization Identity -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 class="text-sm font-bold text-slate-900 font-heading">Enterprise Identity</h2>
            <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">VERIFIED</span>
          </div>

          <div class="flex flex-col gap-3 text-xs">
            <div class="flex justify-between py-1 border-b border-slate-50">
              <span class="text-slate-500 font-medium">Legal Entity Name</span>
              <span class="font-bold text-slate-900">{{ enterprise.settings().legalEntityName }}</span>
            </div>
            <div class="flex justify-between py-1 border-b border-slate-50">
              <span class="text-slate-500 font-medium">Enterprise Identifier</span>
              <span class="font-mono font-bold text-slate-900">{{ enterprise.settings().enterpriseIdentifier }}</span>
            </div>
            <div class="flex justify-between py-1 border-b border-slate-50">
              <span class="text-slate-500 font-medium">Primary Domain</span>
              <span class="font-mono text-slate-900">{{ enterprise.settings().primaryDomain }}</span>
            </div>
            <div class="flex justify-between py-1">
              <span class="text-slate-500 font-medium">Compliance Tier</span>
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                {{ enterprise.settings().globalComplianceTier }}
              </span>
            </div>
          </div>
        </div>

        <!-- Security Baseline -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 class="text-sm font-bold text-slate-900 font-heading">Security Baseline</h2>
            <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">ENFORCED</span>
          </div>

          <div class="flex flex-col gap-3 text-xs">
            <div class="flex justify-between py-1 border-b border-slate-50">
              <span class="text-slate-500 font-medium">Mandatory MFA</span>
              <span class="font-bold text-emerald-700">ENFORCED</span>
            </div>
            <div class="flex justify-between py-1 border-b border-slate-50">
              <span class="text-slate-500 font-medium">Session Timeout</span>
              <span class="font-mono text-slate-900">{{ enterprise.settings().securityBaseline.sessionTimeoutMinutes }} Minutes</span>
            </div>
            <div class="flex justify-between py-1 border-b border-slate-50">
              <span class="text-slate-500 font-medium">Four-Eyes Quorum Threshold</span>
              <span class="font-mono text-slate-900">{{ enterprise.settings().securityBaseline.fourEyesQuorumThreshold }} Approvers</span>
            </div>
            <div class="flex justify-between py-1">
              <span class="text-slate-500 font-medium">Audit Log Retention</span>
              <span class="font-mono text-slate-900">{{ enterprise.settings().securityBaseline.auditLogRetentionDays }} Days</span>
            </div>
          </div>
        </div>

        <!-- Maintenance Window -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 class="text-sm font-bold text-slate-900 font-heading">Maintenance Schedule</h2>
            <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">SCHEDULED</span>
          </div>

          <div class="flex flex-col gap-3 text-xs">
            <div class="flex justify-between py-1 border-b border-slate-50">
              <span class="text-slate-500 font-medium">Preferred Window Day</span>
              <span class="font-bold text-slate-900">{{ enterprise.settings().maintenanceWindow.preferredDay }}</span>
            </div>
            <div class="flex justify-between py-1 border-b border-slate-50">
              <span class="text-slate-500 font-medium">Start Time</span>
              <span class="font-mono text-slate-900">{{ enterprise.settings().maintenanceWindow.startUtc }} UTC</span>
            </div>
            <div class="flex justify-between py-1">
              <span class="text-slate-500 font-medium">Window Duration</span>
              <span class="font-mono text-slate-900">{{ enterprise.settings().maintenanceWindow.durationHours }} Hours</span>
            </div>
          </div>
        </div>

        <!-- Emergency Break Glass -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 class="text-sm font-bold text-slate-900 font-heading">Emergency Break Glass</h2>
            <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">ESCROW READY</span>
          </div>

          <div class="flex flex-col gap-3 text-xs">
            <div class="flex justify-between py-1 border-b border-slate-50">
              <span class="text-slate-500 font-medium">Incident Commander</span>
              <span class="font-bold text-slate-900">{{ enterprise.settings().emergencyBreakGlass.primaryContact }}</span>
            </div>
            <div class="flex justify-between py-1 border-b border-slate-50">
              <span class="text-slate-500 font-medium">Emergency Email</span>
              <span class="font-mono text-slate-900">{{ enterprise.settings().emergencyBreakGlass.emergencyEmail }}</span>
            </div>
            <div class="flex justify-between py-1">
              <span class="text-slate-500 font-medium">Escrow Reference</span>
              <span class="font-mono text-slate-900">{{ enterprise.settings().emergencyBreakGlass.vaultEscrowReference }}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  `
})
export class EnterpriseSettingsComponent {
  public enterprise = inject(EnterpriseService);
}
