/**
 * AKAAL Administration — Enterprise Structure Routing Hub
 */

import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-enterprise-structure',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <div class="flex flex-col gap-2">
        

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Structure</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Organizations, workspaces, and environment deployment boundaries.
            </p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <a
          routerLink="/administration/enterprise/structure/organizations"
          class="rounded-xl bg-white border border-slate-200 p-6 shadow-2xs hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer select-none group flex flex-col justify-between gap-6">
          <div class="flex flex-col gap-3">
            <div class="w-10 h-10 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 flex items-center justify-center group-hover:bg-blue-50 group-hover:border-blue-200 group-hover:text-blue-600 transition-colors">
              <app-lucide-icon name="building-2" [size]="20"></app-lucide-icon>
            </div>
            <h3 class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors font-heading">
              Organizations
            </h3>
            <p class="text-xs text-slate-500 font-medium leading-relaxed">
              Top-level holding legal entities, regional subsidiaries, and business units.
            </p>
          </div>
          <div class="flex items-center justify-between pt-3 border-t border-slate-100">
            <span class="text-xs font-semibold text-blue-600 group-hover:text-blue-700">Manage Organizations</span>
            <app-lucide-icon name="arrow-right" [size]="14" class="text-blue-600 group-hover:translate-x-0.5 transition-transform"></app-lucide-icon>
          </div>
        </a>

        <a
          routerLink="/administration/enterprise/structure/workspaces"
          class="rounded-xl bg-white border border-slate-200 p-6 shadow-2xs hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer select-none group flex flex-col justify-between gap-6">
          <div class="flex flex-col gap-3">
            <div class="w-10 h-10 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 flex items-center justify-center group-hover:bg-blue-50 group-hover:border-blue-200 group-hover:text-blue-600 transition-colors">
              <app-lucide-icon name="folder-kanban" [size]="20"></app-lucide-icon>
            </div>
            <h3 class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors font-heading">
              Workspaces
            </h3>
            <p class="text-xs text-slate-500 font-medium leading-relaxed">
              Program workspaces, data domain boundaries, and project operational containers.
            </p>
          </div>
          <div class="flex items-center justify-between pt-3 border-t border-slate-100">
            <span class="text-xs font-semibold text-blue-600 group-hover:text-blue-700">Manage Workspaces</span>
            <app-lucide-icon name="arrow-right" [size]="14" class="text-blue-600 group-hover:translate-x-0.5 transition-transform"></app-lucide-icon>
          </div>
        </a>

        <a
          routerLink="/administration/enterprise/structure/environments"
          class="rounded-xl bg-white border border-slate-200 p-6 shadow-2xs hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer select-none group flex flex-col justify-between gap-6">
          <div class="flex flex-col gap-3">
            <div class="w-10 h-10 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 flex items-center justify-center group-hover:bg-blue-50 group-hover:border-blue-200 group-hover:text-blue-600 transition-colors">
              <app-lucide-icon name="server" [size]="20"></app-lucide-icon>
            </div>
            <h3 class="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors font-heading">
              Environments
            </h3>
            <p class="text-xs text-slate-500 font-medium leading-relaxed">
              Deployment tiers, production isolation barriers, and maintenance locks.
            </p>
          </div>
          <div class="flex items-center justify-between pt-3 border-t border-slate-100">
            <span class="text-xs font-semibold text-blue-600 group-hover:text-blue-700">Manage Environments</span>
            <app-lucide-icon name="arrow-right" [size]="14" class="text-blue-600 group-hover:translate-x-0.5 transition-transform"></app-lucide-icon>
          </div>
        </a>

      </div>

    </div>
  `
})
export class EnterpriseStructureComponent {}
