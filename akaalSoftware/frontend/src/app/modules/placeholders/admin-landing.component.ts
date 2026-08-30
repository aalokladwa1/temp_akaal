import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-admin-landing',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 p-8 font-sans max-w-7xl mx-auto animate-in fade-in duration-150">
      <div class="flex flex-col gap-1 pb-4 border-b border-border-subtle">
        <h1 class="text-xl font-semibold text-text-primary tracking-tight">Platform Administration</h1>
        <p class="text-xs text-text-secondary">Operator roles, four-eyes policy quorum rules, and enterprise cluster nodes.</p>
      </div>
      
      <div class="p-12 rounded-2xl bg-surface border border-border-subtle flex flex-col items-center justify-center text-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-surface-elevated border border-border-strong flex items-center justify-center text-accent">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>
        <span class="text-sm font-medium text-text-primary">Administration Module Ready</span>
        <span class="text-xs text-text-muted max-w-sm">RBAC policies, cluster health, and vault credentials configuration mount here.</span>
      </div>
    </div>
  `
})
export class AdminLandingComponent {}
