/**
 * AKAAL Administration — 5.6 Connector Capabilities View
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-capabilities-view',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Connector Capabilities</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Canonical verification of what each connector driver supports across execution phases.
            </p>
          </div>
        </div>
      </div>

      <!-- Capabilities Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Connector</th>
              <th class="py-3 px-3 text-center">Source</th>
              <th class="py-3 px-3 text-center">Target</th>
              <th class="py-3 px-3 text-center">CDC Stream</th>
              <th class="py-3 px-3 text-center">High Bulk</th>
              <th class="py-3 px-3 text-center">Schema DDl</th>
              <th class="py-3 px-3 text-center">Validation</th>
              <th class="py-3 px-3 text-center">Streaming</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs font-medium text-slate-700">
            @for (item of service.connectors(); track item.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3 px-4 font-bold text-slate-900">
                  <a [routerLink]="['/administration/connectors/detail', item.id]" class="hover:text-blue-600">
                    {{ item.name }}
                  </a>
                </td>
                <td class="py-3 px-3 text-center">
                  <span [class]="item.capabilities.supportsSource ? 'text-emerald-600 font-bold' : 'text-slate-300'">
                    {{ item.capabilities.supportsSource ? 'YES' : '—' }}
                  </span>
                </td>
                <td class="py-3 px-3 text-center">
                  <span [class]="item.capabilities.supportsTarget ? 'text-emerald-600 font-bold' : 'text-slate-300'">
                    {{ item.capabilities.supportsTarget ? 'YES' : '—' }}
                  </span>
                </td>
                <td class="py-3 px-3 text-center">
                  <span [class]="item.capabilities.supportsCdc ? 'text-emerald-600 font-bold' : 'text-slate-300'">
                    {{ item.capabilities.supportsCdc ? 'YES' : '—' }}
                  </span>
                </td>
                <td class="py-3 px-3 text-center">
                  <span [class]="item.capabilities.supportsBulk ? 'text-emerald-600 font-bold' : 'text-slate-300'">
                    {{ item.capabilities.supportsBulk ? 'YES' : '—' }}
                  </span>
                </td>
                <td class="py-3 px-3 text-center">
                  <span [class]="item.capabilities.supportsSchemaIntrospection ? 'text-emerald-600 font-bold' : 'text-slate-300'">
                    {{ item.capabilities.supportsSchemaIntrospection ? 'YES' : '—' }}
                  </span>
                </td>
                <td class="py-3 px-3 text-center">
                  <span [class]="item.capabilities.supportsValidationSampling ? 'text-emerald-600 font-bold' : 'text-slate-300'">
                    {{ item.capabilities.supportsValidationSampling ? 'YES' : '—' }}
                  </span>
                </td>
                <td class="py-3 px-3 text-center">
                  <span [class]="item.capabilities.supportsStreaming ? 'text-emerald-600 font-bold' : 'text-slate-300'">
                    {{ item.capabilities.supportsStreaming ? 'YES' : '—' }}
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
export class CapabilitiesViewComponent {
  public service = inject(ConnectorsPluginsService);
}
