/**
 * AKAAL Administration — 5.6 Installed / External Connectors
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-external-connectors',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/connectors/connectors-hub" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Connectors
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Installed / External Connectors</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Manage custom, legacy, or proprietary enterprise external connector drivers registered outside the core package.
            </p>
          </div>

          <div class="flex items-center gap-2">
            <a
              routerLink="/administration/connectors/external/register"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs inline-flex items-center gap-1.5 cursor-pointer">
              Register External Connector
            </a>
          </div>
        </div>
      </div>

      <!-- External Connectors Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Name</th>
              <th class="py-3 px-4">Provider Identifier</th>
              <th class="py-3 px-4">Binary Location</th>
              <th class="py-3 px-4">Protocol</th>
              <th class="py-3 px-4">Registered Date</th>
              <th class="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs font-medium text-slate-700">
            @for (item of service.externalConnectors(); track item.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900">{{ item.name }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-600">{{ item.providerIdentifier }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px] truncate max-w-xs">{{ item.binaryPath }}</td>
                <td class="py-3.5 px-4 font-mono font-semibold text-slate-800">{{ item.protocolVersion }}</td>
                <td class="py-3.5 px-4 text-slate-500">{{ item.registeredAt }}</td>
                <td class="py-3.5 px-4">
                  <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {{ item.status }}
                  </span>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="6" class="py-12 text-center text-slate-500 text-xs">
                  <div class="flex flex-col items-center gap-2">
                    <span class="font-medium text-slate-600">No external connectors registered.</span>
                    <a
                      routerLink="/administration/connectors/external/register"
                      class="text-xs font-semibold text-blue-600 hover:text-blue-700 underline">
                      Register an external connector binary
                    </a>
                  </div>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class ExternalConnectorsComponent {
  public service = inject(ConnectorsPluginsService);
}
