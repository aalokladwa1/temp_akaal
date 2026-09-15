/**
 * AKAAL Administration — 5.6 Platform Compatibility View
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-compatibility-view',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Engine &amp; Platform Compatibility</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Supported database engine versions, cloud managed variants, and dialect support matrix.
            </p>
          </div>
        </div>
      </div>

      <!-- Compatibility Cards List -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        @for (item of service.connectors(); track item.id) {
          <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-4">
            <div>
              <div class="flex items-center justify-between">
                <h2 class="text-base font-bold text-slate-900 font-heading">{{ item.name }}</h2>
                <span class="font-mono text-xs font-semibold text-slate-500">{{ item.version }}</span>
              </div>
              <span class="text-xs text-slate-500">{{ item.category }}</span>

              <div class="mt-4 flex flex-col gap-2">
                <span class="text-xs font-bold text-slate-700 font-heading">Validated Target / Source Dialects:</span>
                <div class="flex flex-wrap gap-1.5">
                  @for (dialect of item.supportedDialects; track dialect) {
                    <span class="px-2.5 py-1 bg-slate-50 text-slate-800 border border-slate-200 rounded-md text-xs font-medium">
                      {{ dialect }}
                    </span>
                  }
                </div>
              </div>
            </div>

            <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Engine Protocol: <strong class="font-mono text-slate-700">{{ item.engineProtocolVersion }}</strong></span>
              <a [routerLink]="['/administration/connectors/detail', item.id]" class="font-semibold text-blue-600 hover:text-blue-700">
                Specification &rarr;
              </a>
            </div>
          </div>
        }
      </div>

    </div>
  `
})
export class CompatibilityViewComponent {
  public service = inject(ConnectorsPluginsService);
}
