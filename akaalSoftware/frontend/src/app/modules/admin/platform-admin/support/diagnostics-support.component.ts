/**
 * AKAAL Administration — 5.10 Support & Diagnostics
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PlatformAdminService } from '../../services/platform-admin.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-diagnostics-support',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/platform-admin"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">PLATFORM</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">SUPPORT & DIAGNOSTICS</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Support & Diagnostics</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Generate sanitized diagnostic support packages, compile environment facts, and export system diagnostic bundles.
          </p>
        </div>
      </div>

      <!-- Request Bundle Panel -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
        <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Generate New Diagnostic Bundle</h2>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div class="flex flex-col gap-1.5 md:col-span-2">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Support Ticket or Incident Reference</label>
            <input
              type="text"
              [(ngModel)]="ticketRef"
              placeholder="e.g. SUP-10042"
              class="h-10 px-3.5 rounded-lg border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>

          <div>
            <button
              type="button"
              (click)="onRequest()"
              [disabled]="!ticketRef.trim()"
              class="h-10 px-5 w-full rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold text-xs inline-flex items-center justify-center transition-colors shadow-2xs cursor-pointer">
              Generate Sanitized Bundle
            </button>
          </div>
        </div>

        <span class="text-[11px] text-slate-500">
          Strict Security Law: All passwords, access tokens, customer payloads, and private cryptographic keys are permanently redacted before compilation.
        </span>
      </div>

      <!-- Historical Packages Table -->
      <div class="flex flex-col gap-3">
        <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Diagnostic Bundles</h2>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
                <th class="py-3.5 px-4">Package ID</th>
                <th class="py-3.5 px-4">Ticket Reference</th>
                <th class="py-3.5 px-4">Sanitized Logs Included</th>
                <th class="py-3.5 px-4">Config Snapshot</th>
                <th class="py-3.5 px-4">Package Size</th>
                <th class="py-3.5 px-4">Requested Timestamp</th>
                <th class="py-3.5 px-4">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200 text-xs">
              @for (pkg of platformService.diagnostics(); track pkg.id) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-mono font-bold text-blue-600">{{ pkg.id }}</td>
                  <td class="py-3.5 px-4 font-mono font-medium text-slate-900">{{ pkg.ticketRef }}</td>
                  <td class="py-3.5 px-4 text-emerald-700 font-semibold">{{ pkg.includesSanitizedLogs ? 'Yes (Redacted)' : 'No' }}</td>
                  <td class="py-3.5 px-4 text-emerald-700 font-semibold">{{ pkg.includesConfigSnapshot ? 'Yes' : 'No' }}</td>
                  <td class="py-3.5 px-4 text-slate-600">{{ pkg.packageSize }}</td>
                  <td class="py-3.5 px-4 text-slate-600">{{ pkg.requestedAt }}</td>
                  <td class="py-3.5 px-4">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {{ pkg.status }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class DiagnosticsSupportComponent {
  public platformService = inject(PlatformAdminService);
  public ticketRef = '';

  public onRequest(): void {
    if (!this.ticketRef.trim()) return;
    this.platformService.requestDiagnostics(this.ticketRef.trim().toUpperCase());
    this.ticketRef = '';
  }
}
