/**
 * AKAAL Administration — 5.11 Notification Policies List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IntegrationsService } from '../../services/integrations.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-policies-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/integrations"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">INTEGRATIONS</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">NOTIFICATION POLICIES</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Notification Policies</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Rules binding alert severity levels to destination channels, escalation delay timers, and quiet hour suppression windows.
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <a
            routerLink="/administration/integrations/notifications/policies/create"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs">
            Create Policy
          </a>
        </div>
      </div>

      <!-- Policies Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3.5 px-4">Policy Name</th>
              <th class="py-3.5 px-4">Severity Levels</th>
              <th class="py-3.5 px-4">Target Channels</th>
              <th class="py-3.5 px-4">Quiet Hours</th>
              <th class="py-3.5 px-4">Escalation Timer</th>
              <th class="py-3.5 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-xs">
            @for (pol of integrationsService.policies(); track pol.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900 font-heading">{{ pol.name }}</td>
                <td class="py-3.5 px-4">
                  <div class="flex flex-wrap gap-1">
                    @for (lvl of pol.severityLevels; track lvl) {
                      <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                        {{ lvl }}
                      </span>
                    }
                  </div>
                </td>
                <td class="py-3.5 px-4 text-slate-700">{{ pol.channelIds.length }} channels</td>
                <td class="py-3.5 px-4 text-slate-600">
                  {{ pol.quietHoursStart ? pol.quietHoursStart + ' - ' + pol.quietHoursEnd : 'None (24/7 Delivery)' }}
                </td>
                <td class="py-3.5 px-4 text-slate-600">
                  {{ pol.escalationDelayMinutes ? pol.escalationDelayMinutes + ' min delay' : 'Immediate' }}
                </td>
                <td class="py-3.5 px-4">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {{ pol.status }}
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
export class PoliciesListComponent {
  public integrationsService = inject(IntegrationsService);
}
