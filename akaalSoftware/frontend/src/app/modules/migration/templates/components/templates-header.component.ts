import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-templates-header',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
      <!-- Left: Title & Purpose -->
      <div class="flex flex-col gap-1">
        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">MIGRATION</span>
        <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Templates</h1>
        <p class="text-sm font-medium text-slate-600">
          Reusable configurations to accelerate migration creation across supported operational modes.
        </p>
      </div>

      <!-- Right: Primary CTA (Text-Led, No Icons in Action Button) -->
      <div class="flex items-center gap-3 pt-1">
        <a
          routerLink="/migration/templates/new"
          class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold shadow-xs transition-colors flex items-center justify-center cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/40">
          New Template
        </a>
      </div>
    </div>
  `
})
export class TemplatesHeaderComponent {}
