import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-settings-landing',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 p-8 font-sans max-w-7xl mx-auto animate-in fade-in duration-150">
      <div class="flex flex-col gap-1 pb-4 border-b border-border-subtle">
        <h1 class="text-xl font-semibold text-text-primary tracking-tight">Platform Settings</h1>
        <p class="text-xs text-text-secondary">Organization, Workspace, and Environment configuration preferences.</p>
      </div>
      
      <div class="p-12 rounded-2xl bg-surface border border-border-subtle flex flex-col items-center justify-center text-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-surface-elevated border border-border-strong flex items-center justify-center text-accent">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </div>
        <span class="text-sm font-medium text-text-primary">Settings Module Ready</span>
        <span class="text-xs text-text-muted max-w-sm">Organization context, active workspace, and network topology routes are configured here.</span>
      </div>
    </div>
  `
})
export class SettingsLandingComponent {}
