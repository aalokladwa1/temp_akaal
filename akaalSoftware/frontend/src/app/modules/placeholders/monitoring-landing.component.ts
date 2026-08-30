import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-monitoring-landing',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 p-8 font-sans max-w-7xl mx-auto animate-in fade-in duration-150">
      <div class="flex flex-col gap-1 pb-4 border-b border-border-subtle">
        <h1 class="text-xl font-semibold text-text-primary tracking-tight">Real-Time Monitoring</h1>
        <p class="text-xs text-text-secondary">Fleet telemetry, CDC stream lag tracking, and worker buffer diagnostics.</p>
      </div>
      
      <div class="p-12 rounded-2xl bg-surface border border-border-subtle flex flex-col items-center justify-center text-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-surface-elevated border border-border-strong flex items-center justify-center text-accent">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </div>
        <span class="text-sm font-medium text-text-primary">Monitoring Module Ready</span>
        <span class="text-xs text-text-muted max-w-sm">Deep telemetry and ECharts telemetry streaming will be initialized here.</span>
      </div>
    </div>
  `
})
export class MonitoringLandingComponent {}
