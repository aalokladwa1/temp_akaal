import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  template: `
    <main class="h-screen w-screen flex flex-col items-center justify-center bg-background text-text-primary font-sans p-8">
      <div class="p-8 rounded-3xl bg-surface border border-border-strong shadow-2xl flex flex-col items-center text-center max-w-md gap-4">
        <div class="w-12 h-12 rounded-2xl bg-accent text-white flex items-center justify-center font-extrabold text-xl font-heading shadow-md">
          A
        </div>
        <h1 class="text-2xl font-extrabold font-heading tracking-tight">AKAAL Enterprise</h1>
        <p class="text-xs text-text-secondary leading-relaxed">
          Wails + Angular + PrimeNG + Tailwind stack ready for clean-slate engineering.
        </p>
        <span class="px-3 py-1 rounded-full bg-status-success/15 text-status-success text-xs font-mono font-bold">
          INGREDIENTS READY
        </span>
      </div>
    </main>
  `
})
export class AppComponent {
  public title = signal('AKAAL Enterprise');
}
