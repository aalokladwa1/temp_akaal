/**
 * AKAAL Administration — 5.10 Maintenance Windows List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { PlatformAdminService } from '../../services/platform-admin.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-maintenance-windows-list',
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
              <span class="text-xs font-medium text-slate-500">MAINTENANCE WINDOWS</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Maintenance Windows</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Planned operational maintenance intervals, cluster drain reservations, and kernel patching schedules.
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <a
            routerLink="/administration/platform-admin/lifecycle/maintenance/create"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs">
            Schedule Maintenance
          </a>
        </div>
      </div>

      <!-- Maintenance Windows Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Window Title</th>
              <th class="py-3.5 px-4">Start Time (UTC)</th>
              <th class="py-3.5 px-4">End Time (UTC)</th>
              <th class="py-3.5 px-4">Scope</th>
              <th class="py-3.5 px-4">Job Drain Allowed</th>
              <th class="py-3.5 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (win of platformService.maintenanceWindows(); track win.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900 font-heading">{{ win.title }}</td>
                <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px]">{{ win.scheduledStartTime }}</td>
                <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px]">{{ win.scheduledEndTime }}</td>
                <td class="py-3.5 px-4 text-slate-700 font-mono text-[11px]">{{ win.scope }}</td>
                <td class="py-3.5 px-4 text-slate-600">{{ win.allowJobDrain ? 'Yes (Graceful)' : 'No (Hard Halt)' }}</td>
                <td class="py-3.5 px-4">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                    {{ win.status }}
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
export class MaintenanceWindowsListComponent {
  public platformService = inject(PlatformAdminService);
}
