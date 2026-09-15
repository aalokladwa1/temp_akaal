/**
 * AKAAL Administration — 5.10 Deployment Configuration
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { PlatformAdminService } from '../../services/platform-admin.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-deployment-config',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/platform-admin"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">PLATFORM</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">DEPLOYMENT TARGET</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Deployment Configuration</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Target infrastructure orchestrator, deployment profile, and container rollout strategy.
          </p>
        </div>
      </div>

      <!-- Properties Grid -->
      @if (platformService.deploymentConfig(); as dep) {
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Target Environment</span>
            <span class="text-xs font-bold text-slate-900">{{ dep.targetEnvironment }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Orchestrator Platform</span>
            <span class="text-xs font-mono font-bold text-blue-600">{{ dep.orchestrator }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Rollout Strategy</span>
            <span class="text-xs font-mono text-slate-700">{{ dep.rolloutStrategy }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Configuration Version</span>
            <span class="text-xs font-mono text-slate-700">{{ dep.configVersion }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Active Blueprint Profile</span>
            <span class="text-xs font-mono text-slate-700">{{ dep.activeProfile }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Last Deployed Timestamp</span>
            <span class="text-xs font-medium text-slate-600">{{ dep.lastDeployedAt }}</span>
          </div>
        </div>
      }
    </div>
  `
})
export class DeploymentConfigComponent {
  public platformService = inject(PlatformAdminService);
}
