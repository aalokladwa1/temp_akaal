/**
 * AKAAL Administration — 5.6 Driver & Connector Versions View
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-versions-view',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/connectors/intelligence-hub" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Connector Intelligence
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Driver &amp; Connector Versions</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Distinct separation between AKAAL wrapper release, low-level JDBC/client native driver, and engine protocol contract.
            </p>
          </div>
        </div>
      </div>

      <!-- Versions Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Connector</th>
              <th class="py-3 px-4">Provider ID</th>
              <th class="py-3 px-4">Wrapper Version</th>
              <th class="py-3 px-4">Native Driver Release</th>
              <th class="py-3 px-4">IPC Protocol</th>
              <th class="py-3 px-4">Packaging</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs font-medium text-slate-700">
            @for (item of service.connectors(); track item.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900">{{ item.name }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-600">{{ item.providerId }}</td>
                <td class="py-3.5 px-4 font-mono font-bold text-slate-900">{{ item.version }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-700">{{ item.driverVersion }}</td>
                <td class="py-3.5 px-4 font-mono font-semibold text-blue-600">{{ item.engineProtocolVersion }}</td>
                <td class="py-3.5 px-4">
                  <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                    {{ item.isBuiltIn ? 'Built-In' : 'External' }}
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
export class VersionsViewComponent {
  public service = inject(ConnectorsPluginsService);
}
