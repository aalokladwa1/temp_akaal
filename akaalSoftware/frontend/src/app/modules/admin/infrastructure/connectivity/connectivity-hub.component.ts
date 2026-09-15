/**
 * AKAAL Administration — 5.7 Connectivity Routing Hub
 */

import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-connectivity-hub',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/infrastructure" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Cloud &amp; Infrastructure
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Connectivity</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Private transit links, enterprise forward/reverse proxies, SSH bastion routes, and hybrid interconnection topologies.
            </p>
          </div>
        </div>
      </div>

      <!-- Feature Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <!-- Private Connectivity -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="lock" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">PrivateLink &bull; PSC</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Private Connectivity</h2>
              <p class="text-xs text-slate-600 mt-1">
                Zero-egress private transit endpoints, AWS PrivateLink, Azure Private Endpoints, and Google PSC.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/infrastructure/connectivity/private"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Manage Private Links</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- Network Routing / Proxy / Bastion -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="network" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">Proxies &bull; Bastions</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Network Routing &amp; Bastions</h2>
              <p class="text-xs text-slate-600 mt-1">
                Egress forward proxies, reverse ingress gateways, SSH jump host bastions, and bypass lists.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/infrastructure/connectivity/routing"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Configure Routing</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

        <!-- Hybrid Environments -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="layers" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">DirectConnect &bull; VPN</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">Hybrid Environments</h2>
              <p class="text-xs text-slate-600 mt-1">
                Administrative cross-cloud and on-premises physical trunk relationships and bandwidth allocations.
              </p>
            </div>
          </div>
          <a
            routerLink="/administration/infrastructure/connectivity/hybrid"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Inspect Hybrid Trunks</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>

      </div>
    </div>
  `
})
export class ConnectivityHubComponent {}
