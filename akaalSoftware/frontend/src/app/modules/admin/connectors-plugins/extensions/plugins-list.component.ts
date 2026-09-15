/**
 * AKAAL Administration — 5.6 Plugins List
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-plugins-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/connectors/extensions-hub" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Extensions
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Plugins</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Installed transformation, validation, and reporter extension plugins executing within the migration pipeline.
            </p>
          </div>
        </div>
      </div>

      <!-- Plugins Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Plugin Name</th>
              <th class="py-3 px-4">Type</th>
              <th class="py-3 px-4">Vendor</th>
              <th class="py-3 px-4">Version</th>
              <th class="py-3 px-4">Signature Digest</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs font-medium text-slate-700">
            @for (item of service.plugins(); track item.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900">
                  <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full" [class]="item.status === 'ACTIVE' ? 'bg-emerald-500' : 'bg-slate-300'"></span>
                    <span>{{ item.name }}</span>
                  </div>
                </td>
                <td class="py-3.5 px-4 font-mono text-[11px] font-semibold text-slate-800">{{ item.pluginType }}</td>
                <td class="py-3.5 px-4 text-slate-600">{{ item.vendor }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-800">{{ item.version }}</td>
                <td class="py-3.5 px-4">
                  <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
                    {{ item.signatureStatus }}
                  </span>
                </td>
                <td class="py-3.5 px-4">
                  <span
                    [class]="item.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-600 border-slate-200'"
                    class="px-2 py-0.5 rounded text-[11px] font-semibold border">
                    {{ item.status }}
                  </span>
                </td>
                <td class="py-3.5 px-4 text-right">
                  <a
                    [routerLink]="['/administration/connectors/plugins/detail', item.id]"
                    class="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors cursor-pointer">
                    View Details
                  </a>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class PluginsListComponent {
  public service = inject(ConnectorsPluginsService);
}
