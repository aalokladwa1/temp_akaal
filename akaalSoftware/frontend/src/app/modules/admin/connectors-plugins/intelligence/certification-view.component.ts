/**
 * AKAAL Administration — 5.6 Connector Certification & Proof Standards View
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-certification-view',
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
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Connector Certification &amp; Proof Evidence</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Internal qualification verification ledger based on proven test evidence, live validation runs, and capability assertions.
            </p>
          </div>
        </div>
      </div>

      <!-- Proof Levels Legend Banner -->
      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs">
        <span class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading block mb-3">Internal Proof Standards</span>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div class="p-3 bg-emerald-50/50 border border-emerald-100 rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <span class="font-mono font-bold text-emerald-800 text-[11px]">LIVE_PROVEN</span>
            </div>
            <p class="text-slate-600 text-[11px]">Exercised and proven against real cloud or on-premises engine endpoints under transactional migration loads.</p>
          </div>

          <div class="p-3 bg-blue-50/50 border border-blue-100 rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <span class="font-mono font-bold text-blue-800 text-[11px]">INTEGRATION_PROVEN</span>
            </div>
            <p class="text-slate-600 text-[11px]">Verified in integration test suites against local containerized emulator instances with full protocol validation.</p>
          </div>

          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <span class="font-mono font-bold text-slate-800 text-[11px]">UNIT_PROVEN</span>
            </div>
            <p class="text-slate-600 text-[11px]">Verified via static schema and unit assertion suites. Live external engine connectivity deferred to production runtime.</p>
          </div>
        </div>
      </div>

      <!-- Evidence Ledger Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Connector</th>
              <th class="py-3 px-4">Proof Classification</th>
              <th class="py-3 px-4">Qualification Summary</th>
              <th class="py-3 px-4">Verification Freshness</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs font-medium text-slate-700">
            @for (item of service.connectors(); track item.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900">
                  <a [routerLink]="['/administration/connectors/detail', item.id]" class="hover:text-blue-600">
                    {{ item.name }}
                  </a>
                </td>
                <td class="py-3.5 px-4">
                  <span
                    [ngClass]="{
                      'bg-emerald-50 text-emerald-700 border-emerald-200': item.certificationLevel === 'LIVE_PROVEN',
                      'bg-blue-50 text-blue-700 border-blue-200': item.certificationLevel === 'INTEGRATION_PROVEN',
                      'bg-slate-50 text-slate-700 border-slate-200': item.certificationLevel === 'UNIT_PROVEN'
                    }"
                    class="px-2 py-0.5 rounded text-[10px] font-bold border font-mono uppercase tracking-wide">
                    {{ item.certificationLevel }}
                  </span>
                </td>
                <td class="py-3.5 px-4 text-slate-600 max-w-lg leading-relaxed">{{ item.qualificationNotes }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">{{ item.lastTestedDate }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class CertificationViewComponent {
  public service = inject(ConnectorsPluginsService);
}
