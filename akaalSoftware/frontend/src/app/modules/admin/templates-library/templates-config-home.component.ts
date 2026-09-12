/**
 * AKAAL Administration — 5.5 Template & Configuration Library Home
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TemplatesConfigService } from '../services/templates-config.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-templates-config-home',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Administration
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Template & Configuration Library</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Enterprise repository of reusable migration blueprints, data mapping schemas, transformation recipes, compliance privacy policies, and runtime profiles.
            </p>
          </div>

          <div class="flex items-center gap-2">
            <a
              routerLink="/administration/templates-library/import"
              class="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors shadow-2xs flex items-center gap-1.5">
              <app-lucide-icon name="upload" [size]="13"></app-lucide-icon>
              <span>Import Asset</span>
            </a>
            <a
              routerLink="/administration/templates-library/create"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs flex items-center gap-1.5">
              <app-lucide-icon name="plus" [size]="13"></app-lucide-icon>
              <span>Create New Asset</span>
            </a>
          </div>
        </div>
      </div>

      <!-- Asset Families Grid (6 Families) -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          *ngFor="let summary of library.familySummaries()"
          class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col justify-between gap-5 hover:border-slate-300 transition-all">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon [name]="summary.icon" [size]="20"></app-lucide-icon>
              </div>
              <span class="text-xs font-bold text-slate-700 font-mono">{{ summary.totalAssetsCount }} ASSETS</span>
            </div>

            <div>
              <h2 class="text-base font-bold text-slate-900 font-heading">{{ summary.title }}</h2>
              <p class="text-xs text-slate-600 mt-1">{{ summary.description }}</p>
            </div>

            <div class="grid grid-cols-3 gap-2 pt-3 border-t border-slate-100">
              <div class="flex flex-col">
                <span class="text-[10px] text-slate-500 uppercase tracking-wider font-heading">Published</span>
                <span class="text-xs font-bold text-emerald-600">{{ summary.publishedCount }}</span>
              </div>
              <div class="flex flex-col">
                <span class="text-[10px] text-slate-500 uppercase tracking-wider font-heading">Deprecated</span>
                <span class="text-xs font-bold text-amber-600">{{ summary.deprecatedCount }}</span>
              </div>
              <div class="flex flex-col">
                <span class="text-[10px] text-slate-500 uppercase tracking-wider font-heading">Active Usages</span>
                <span class="text-xs font-bold text-slate-800">{{ summary.activeUsagesCount }}</span>
              </div>
            </div>
          </div>

          <a
            [routerLink]="summary.routePath"
            class="inline-flex items-center justify-between px-3.5 py-2 text-xs font-semibold text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 rounded-lg transition-colors cursor-pointer">
            <span>Browse {{ summary.title }}</span>
            <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
          </a>
        </div>
      </div>

    </div>
  `
})
export class TemplatesConfigHomeComponent {
  public library = inject(TemplatesConfigService);
}
