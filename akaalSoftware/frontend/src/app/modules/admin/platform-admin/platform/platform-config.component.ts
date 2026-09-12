/**
 * AKAAL Administration — 5.10 Platform Configuration
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PlatformAdminService } from '../../services/platform-admin.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-platform-config',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent],
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
              <span class="text-xs font-medium text-slate-500">CONFIGURATION PARAMETERS</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Platform Configuration</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Core execution engine limits, concurrency worker budgets, cryptographic protocol boundaries, and IPC socket paths.
          </p>
        </div>
      </div>

      <!-- Config Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Group</th>
              <th class="py-3.5 px-4">Configuration Key</th>
              <th class="py-3.5 px-4">Description</th>
              <th class="py-3.5 px-4">Configured Value</th>
              <th class="py-3.5 px-4 text-right">Mutability</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (cfg of platformService.platformConfigs(); track cfg.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
                    {{ cfg.group }}
                  </span>
                </td>
                <td class="py-3.5 px-4 font-mono font-bold text-slate-900">{{ cfg.key }}</td>
                <td class="py-3.5 px-4 text-slate-600 max-w-md">{{ cfg.description }}</td>
                <td class="py-3.5 px-4 font-mono font-bold text-blue-600">{{ cfg.value }}</td>
                <td class="py-3.5 px-4 text-right">
                  <span 
                    class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border"
                    [ngClass]="cfg.isEditable ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-50 text-slate-500 border-slate-200'">
                    {{ cfg.isEditable ? 'Editable' : 'Read-Only' }}
                  </span>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class PlatformConfigComponent {
  public platformService = inject(PlatformAdminService);
}
