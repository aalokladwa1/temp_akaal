/**
 * AKAAL Administration — 5.6 Built-In Connectors
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-builtin-connectors',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Built-In Connectors</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Native connector implementations packaged and maintained within the core AKAAL platform binary distribution.
            </p>
          </div>
        </div>
      </div>

      <!-- Built-In List Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        @for (item of service.connectors(); track item.id) {
          <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
            <div class="flex flex-col gap-3">
              <div class="flex items-center justify-between">
                <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                  <app-lucide-icon name="box" [size]="20"></app-lucide-icon>
                </div>
                <span class="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {{ item.certificationLevel }}
                </span>
              </div>

              <div>
                <h2 class="text-base font-bold text-slate-900 font-heading">{{ item.name }}</h2>
                <span class="text-xs font-semibold text-slate-500">{{ item.category }}</span>
                <p class="text-xs text-slate-600 mt-2">{{ item.qualificationNotes }}</p>
              </div>

              <div class="grid grid-cols-2 gap-2 pt-3 border-t border-slate-100 text-xs">
                <div>
                  <span class="text-slate-500 block text-[11px]">Version</span>
                  <span class="font-mono font-bold text-slate-800">{{ item.version }}</span>
                </div>
                <div>
                  <span class="text-slate-500 block text-[11px]">Driver</span>
                  <span class="font-mono text-slate-800 text-[11px] truncate block">{{ item.driverVersion }}</span>
                </div>
              </div>
            </div>

            <a
              [routerLink]="['/administration/connectors/detail', item.id]"
              class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
              <span>View Specifications</span>
              <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
            </a>
          </div>
        }
      </div>

    </div>
  `
})
export class BuiltinConnectorsComponent {
  public service = inject(ConnectorsPluginsService);
}
