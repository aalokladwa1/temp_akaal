import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-migration-landing',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 p-8 font-sans max-w-7xl mx-auto animate-in fade-in duration-150">
      <div class="flex flex-col gap-1 pb-4 border-b border-border-subtle">
        <h1 class="text-xl font-semibold text-text-primary tracking-tight">Migration Portfolio</h1>
        <p class="text-xs text-text-secondary">Enterprise migration portfolio, execution planner, and mission control directory.</p>
      </div>
      
      <div class="p-12 rounded-2xl bg-surface border border-border-subtle flex flex-col items-center justify-center text-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-surface-elevated border border-border-strong flex items-center justify-center text-accent">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <ellipse cx="12" cy="5" rx="9" ry="3"/>
            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
          </svg>
        </div>
        <span class="text-sm font-medium text-text-primary">Migration Module Ready</span>
        <span class="text-xs text-text-muted max-w-sm">Detailed migration portfolio and 9-step creation wizard will be mounted in subsequent module phases.</span>
      </div>
    </div>
  `
})
export class MigrationLandingComponent {}
