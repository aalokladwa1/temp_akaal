import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-reports-landing',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 p-8 font-sans max-w-7xl mx-auto animate-in fade-in duration-150">
      <div class="flex flex-col gap-1 pb-4 border-b border-border-subtle">
        <h1 class="text-xl font-semibold text-text-primary tracking-tight">Audit &amp; Compliance Reports</h1>
        <p class="text-xs text-text-secondary">Cryptographic validation seals, reconciliation certificates, and compliance ledgers.</p>
      </div>
      
      <div class="p-12 rounded-2xl bg-surface border border-border-subtle flex flex-col items-center justify-center text-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-surface-elevated border border-border-strong flex items-center justify-center text-accent">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
        </div>
        <span class="text-sm font-medium text-text-primary">Reports Module Ready</span>
        <span class="text-xs text-text-muted max-w-sm">Reconciliation exports and audit PDF/CSV generators will mount in this module.</span>
      </div>
    </div>
  `
})
export class ReportsLandingComponent {}
