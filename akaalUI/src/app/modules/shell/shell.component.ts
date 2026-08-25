import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../core/theme/theme.service';
import { BrandLogoComponent } from '../../shared/components/brand-logo/brand-logo.component';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, BrandLogoComponent],
  template: `
    <div class="w-full h-full flex flex-col bg-app text-text-primary">
      <!-- Window Title Bar -->
      <header class="h-12 border-b border-border-subtle bg-surface flex items-center justify-between px-4 select-none">
        <div class="flex items-center gap-3">
          <app-brand-logo [size]="24" />
          <span class="font-heading font-bold tracking-tight text-base">AKAAL</span>
          <span class="text-xs px-2 py-0.5 rounded bg-accent-subtle text-accent font-mono">v2.0.0</span>
        </div>
        <div class="flex items-center gap-2">
          <!-- Quick Theme Switcher -->
          <button (click)="toggleTheme()" class="text-xs px-3 py-1 rounded border border-border-strong hover:bg-surface-elevated transition-colors">
            Theme: {{ themeService.currentTheme() }}
          </button>
        </div>
      </header>

      <!-- Main Shell Body -->
      <div class="flex-1 flex overflow-hidden">
        <!-- Sidebar Navigation Rail -->
        <aside class="w-60 border-r border-border-subtle bg-surface flex flex-col p-3 gap-1">
          <button class="flex items-center gap-2.5 px-3 py-2 rounded-md bg-accent-subtle text-accent font-medium text-sm">
            <span>Dashboard</span>
          </button>
          <button class="flex items-center gap-2.5 px-3 py-2 rounded-md hover:bg-surface-elevated text-text-secondary font-medium text-sm">
            <span>Migration</span>
          </button>
          <button class="flex items-center gap-2.5 px-3 py-2 rounded-md hover:bg-surface-elevated text-text-secondary font-medium text-sm">
            <span>Monitoring</span>
          </button>
          <button class="flex items-center gap-2.5 px-3 py-2 rounded-md hover:bg-surface-elevated text-text-secondary font-medium text-sm">
            <span>Reports</span>
          </button>
          <button class="flex items-center gap-2.5 px-3 py-2 rounded-md hover:bg-surface-elevated text-text-secondary font-medium text-sm">
            <span>Administration</span>
          </button>
          <button class="flex items-center gap-2.5 px-3 py-2 rounded-md hover:bg-surface-elevated text-text-secondary font-medium text-sm">
            <span>Settings</span>
          </button>
        </aside>

        <!-- Main Content Viewport -->
        <main class="flex-1 overflow-auto p-6 bg-app">
          <div class="glass-panel p-6">
            <h1 class="text-2xl font-heading font-bold">Welcome to AKAAL</h1>
            <p class="text-text-secondary mt-1 text-sm">Enterprise Database Migration Platform — Workspace Ready</p>
          </div>
        </main>
      </div>
    </div>
  `,
})
export class ShellComponent {
  public readonly themeService = inject(ThemeService);

  toggleTheme(): void {
    const current = this.themeService.currentTheme();
    this.themeService.setTheme(current === 'enterprise-blue' ? 'midnight-blue-gray' : 'enterprise-blue');
  }
}
