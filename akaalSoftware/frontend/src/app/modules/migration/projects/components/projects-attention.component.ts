import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-projects-attention',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    @if (ps.attentionItems().length > 0 && !ps.isUnavailable() && !ps.isUnauthorized()) {
      <div class="p-5 rounded-xl bg-amber-50/70 border border-amber-200/90 text-amber-950 flex flex-col gap-3.5 shadow-2xs">
        
        <!-- Section Header -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
            <span class="text-xs font-bold uppercase tracking-wider text-amber-900 font-heading">
              Needs Attention &bull; Current Work
            </span>
            <span class="px-2 py-0.5 rounded-md text-[11px] font-bold bg-amber-200/80 text-amber-900 border border-amber-300">
              {{ ps.attentionItems().length }} Actionable
            </span>
          </div>
        </div>

        <!-- Attention Items List -->
        <div class="flex flex-col gap-3">
          @for (item of ps.attentionItems(); track item.id) {
            <div class="p-4 rounded-lg bg-white border border-amber-200/80 shadow-2xs flex flex-col gap-2.5">
              
              <!-- Header Row: Title & Action Button -->
              <div class="flex items-center justify-between gap-3 flex-wrap">
                <div class="flex items-center gap-2.5 min-w-0">
                  <div class="w-2 h-2 rounded-xs bg-amber-500 shrink-0"></div>
                  <span class="text-xs font-bold text-slate-900 truncate">{{ item.title }}</span>
                </div>

                @if (item.actionLabel && item.actionRoute) {
                  <a
                    [routerLink]="item.actionRoute"
                    class="h-8 px-3 rounded-md bg-amber-100 hover:bg-amber-200 text-amber-900 text-xs font-semibold inline-flex items-center justify-center transition-colors cursor-pointer shrink-0 shadow-2xs">
                    {{ item.actionLabel }}
                  </a>
                }
              </div>

              <!-- Description -->
              <p class="text-xs text-slate-600 font-normal leading-relaxed pl-4.5">
                {{ item.description }}
              </p>

              <!-- Associated Metadata Chips -->
              <div class="flex items-center gap-2 pl-4.5 text-[11px] text-slate-600 font-medium flex-wrap pt-0.5">
                @if (item.projectName) {
                  <span class="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 text-slate-700">
                    Project: <strong class="text-slate-900">{{ item.projectName }}</strong>
                  </span>
                }
                @if (item.migrationName) {
                  <span class="px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 text-slate-700">
                    Migration: <strong class="text-slate-900">{{ item.migrationName }}</strong>
                  </span>
                }
              </div>

            </div>
          }
        </div>

      </div>
    }
  `
})
export class ProjectsAttentionComponent {
  public ps = inject(ProjectsService);
}
