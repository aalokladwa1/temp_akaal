/**
 * AKAAL Administration — 5.6 Plugin Detail
 */

import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-plugin-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/connectors/plugins" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Plugins
          </a>
        </div>

        @if (plugin(); as item) {
          <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
            <div class="flex flex-col gap-1">
              <div class="flex items-center gap-3">
                <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ item.name }}</h1>
                <span
                  [class]="item.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-600 border-slate-200'"
                  class="px-2 py-0.5 rounded text-[11px] font-semibold border">
                  {{ item.status }}
                </span>
              </div>
              <p class="text-sm font-medium text-slate-600 max-w-3xl">
                Vendor: <strong class="text-slate-800">{{ item.vendor }}</strong> &bull; Version: <span class="font-mono text-slate-800">{{ item.version }}</span>
              </p>
            </div>

            <div class="flex items-center gap-2">
              <button
                (click)="onToggleStatus()"
                class="px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors shadow-2xs cursor-pointer"
                [ngClass]="item.status === 'ACTIVE' ? 'text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200' : 'text-white bg-blue-600 hover:bg-blue-700'">
                {{ item.status === 'ACTIVE' ? 'Disable Plugin' : 'Enable Plugin' }}
              </button>
            </div>
          </div>
        }
      </div>

      @if (plugin(); as item) {
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <div class="lg:col-span-2 flex flex-col gap-6">
            <!-- Overview & Description -->
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-3">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Plugin Description &amp; Scope</h2>
              <p class="text-xs text-slate-600 leading-relaxed">{{ item.description }}</p>
            </div>

            <!-- Granted Runtime Permissions -->
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Granted Runtime Permissions</h2>
              <div class="flex flex-col gap-2">
                @for (perm of item.permissions; track perm) {
                  <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs font-mono">
                    <span class="font-bold text-slate-800">{{ perm }}</span>
                    <span class="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      Sandbox Approved
                    </span>
                  </div>
                }
              </div>
            </div>

            <!-- Cryptographic Digest -->
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-2">
              <h2 class="text-sm font-bold text-slate-900 font-heading">SHA-256 Digest Integrity</h2>
              <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg font-mono text-xs text-slate-800 break-all select-all">
                {{ item.sha256Digest }}
              </div>
              <span class="text-[11px] text-slate-500">Verified against vendor release manifest at installation.</span>
            </div>
          </div>

          <div class="flex flex-col gap-6">
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Lifecycle Properties</h2>
              
              <div class="flex flex-col gap-3 text-xs">
                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-500 font-medium">Plugin Code</span>
                  <span class="font-mono font-bold text-slate-900">{{ item.code }}</span>
                </div>

                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-500 font-medium">Plugin Type</span>
                  <span class="font-bold text-slate-800">{{ item.pluginType }}</span>
                </div>

                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-500 font-medium">Signature Status</span>
                  <span class="font-semibold text-emerald-700">{{ item.signatureStatus }}</span>
                </div>

                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-500 font-medium">Installation Date</span>
                  <span class="text-slate-700">{{ item.installedAt }}</span>
                </div>
              </div>
            </div>
          </div>

        </div>
      }

    </div>
  `
})
export class PluginDetailComponent {
  private service = inject(ConnectorsPluginsService);
  private route = inject(ActivatedRoute);

  public plugin = computed(() => {
    const id = this.route.snapshot.paramMap.get('id');
    return id ? this.service.getPluginById(id) : undefined;
  });

  public onToggleStatus(): void {
    const p = this.plugin();
    if (p) {
      this.service.togglePluginStatus(p.id);
    }
  }
}
