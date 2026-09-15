/**
 * AKAAL Administration — 5.7 Infrastructure as Code (IaC) Configuration
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { InfrastructureService } from '../../services/infrastructure.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-iac-config',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/infrastructure/automation-hub" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Automation
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Infrastructure as Code</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Declared cloud landing zones, OpenTofu and Terraform source repositories, and remote state storage locking.
            </p>
          </div>
        </div>
      </div>

      <!-- IaC Configurations List -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        @for (item of service.iacConfigs(); track item.id) {
          <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5">
            <div class="flex flex-col gap-3">
              <div class="flex items-center justify-between">
                <h2 class="text-base font-bold text-slate-900 font-heading">{{ item.name }}</h2>
                <span class="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-100 text-slate-800 border border-slate-200">
                  {{ item.toolType }}
                </span>
              </div>

              <div class="flex flex-col gap-2.5 text-xs mt-2">
                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-500 font-medium">Git Source Repository</span>
                  <span class="font-mono text-slate-800 font-semibold truncate">{{ item.repositoryRef }}</span>
                </div>

                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-500 font-medium">Remote State Backend</span>
                  <span class="font-medium text-slate-800">{{ item.stateStorageBackend }}</span>
                </div>

                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-500 font-medium">State Storage Object URI</span>
                  <span class="font-mono text-slate-700 truncate text-[11px]">{{ item.stateStorageRef }}</span>
                </div>
              </div>
            </div>

            <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Last Plan: <strong class="text-slate-700">{{ item.lastPlanDate }}</strong></span>
              <span class="font-mono text-[11px] text-slate-400">{{ item.lastPlanChecksum }}</span>
            </div>
          </div>
        }
      </div>

    </div>
  `
})
export class IacConfigComponent {
  public service = inject(InfrastructureService);
}
