import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-history-header',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-1 pb-4 border-b border-slate-200">
      <div class="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
        <span>Migration Operations</span>
        <span class="text-slate-300">/</span>
        <span class="text-blue-600 font-bold">History &amp; Evidence Ledger</span>
      </div>
      <div class="flex items-center justify-between gap-4 flex-wrap mt-0.5">
        <div class="flex flex-col gap-0.5">
          <h1 class="text-2xl font-bold font-heading text-slate-900 tracking-tight">
            Migration History &amp; Evidence Home
          </h1>
          <p class="text-xs text-slate-600 font-normal">
            Canonical immutable audit ledger of historical migration executions, cryptographic SHA-256 evidence seals, validation verdicts, and continuity records across all M1–M8 modes.
          </p>
        </div>
      </div>
    </div>
  `
})
export class HistoryHeaderComponent {}
