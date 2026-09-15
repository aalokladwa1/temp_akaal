/**
 * AKAAL Administration — 5.6 Plugin Security & Lifecycle
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-plugin-security',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Plugin Security &amp; Lifecycle Audit</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Cryptographic digest verification, permission boundary introspection, and administrative execution enablement.
            </p>
          </div>
        </div>
      </div>

      <!-- Security Policies Banner -->
      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shrink-0">
            <app-lucide-icon name="shield-check" [size]="20"></app-lucide-icon>
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-900 font-heading">Strict Sandboxing Enforced</h2>
            <p class="text-xs text-slate-600">All plugins execute within isolated WebAssembly/gRPC processes with unprivileged kernel namespaces.</p>
          </div>
        </div>
        <span class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200">
          Zero Violations Reported
        </span>
      </div>

      <!-- Security Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Plugin</th>
              <th class="py-3 px-4">Type</th>
              <th class="py-3 px-4">Permissions Requested</th>
              <th class="py-3 px-4">Digest Integrity</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs font-medium text-slate-700">
            @for (item of service.plugins(); track item.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900">{{ item.name }}</td>
                <td class="py-3.5 px-4 font-mono text-[11px] text-slate-700">{{ item.pluginType }}</td>
                <td class="py-3.5 px-4">
                  <div class="flex flex-wrap gap-1">
                    @for (perm of item.permissions; track perm) {
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-700 border border-slate-200">
                        {{ perm }}
                      </span>
                    }
                  </div>
                </td>
                <td class="py-3.5 px-4">
                  <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
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
                  <button
                    (click)="service.togglePluginStatus(item.id)"
                    class="text-xs font-semibold cursor-pointer transition-colors"
                    [class]="item.status === 'ACTIVE' ? 'text-amber-600 hover:text-amber-800' : 'text-blue-600 hover:text-blue-800'">
                    {{ item.status === 'ACTIVE' ? 'Disable' : 'Enable' }}
                  </button>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class PluginSecurityComponent {
  public service = inject(ConnectorsPluginsService);
}
