import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TemplateUiService } from '../../../core/services/template-ui.service';
import { MigrationUiService } from '../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { MigrationTemplateItem } from '../../../core/models/migration-view.models';

@Component({
  selector: 'app-template-browser',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto pb-16 font-sans select-none animate-in fade-in duration-150">
      
      <!-- Header (55) -->
      <div class="flex items-center justify-between gap-4 pb-4 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <span class="text-xs font-semibold text-slate-500">Standardized Blueprints</span>
          <h1 class="text-2xl font-bold font-heading text-slate-900 tracking-tight">Migration Templates &amp; Profiles</h1>
          <p class="text-xs text-slate-600 font-medium">Enterprise certified migration profiles with policy strength controls and compatibility drift analysis.</p>
        </div>
      </div>

      <!-- Templates Grid (56) -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        @for (t of ts.filteredTemplates(); track t.id) {
          <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col justify-between gap-5">
            <div class="flex flex-col gap-3">
              <div class="flex items-center justify-between">
                <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">{{ t.version }}</span>
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">{{ t.strength }}</span>
              </div>
              <h3 class="text-base font-bold text-slate-900">{{ t.title }}</h3>
              <p class="text-xs text-slate-600 font-medium leading-relaxed">{{ t.description }}</p>
              
              <div class="flex flex-wrap gap-1.5 pt-1">
                @for (tag of t.tags; track tag) {
                  <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px]">{{ tag }}</span>
                }
              </div>
            </div>

            <div class="pt-4 border-t border-slate-100 flex items-center justify-between">
              <span class="text-xs text-slate-500 font-medium">Used {{ t.usageCount }} times</span>
              <button
                type="button"
                (click)="applyTemplate(t)"
                class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs transition-colors cursor-pointer flex items-center gap-1.5">
                <span>Instantiate Migration</span>
                <app-lucide-icon name="arrow-right" [size]="14"></app-lucide-icon>
              </button>
            </div>
          </div>
        }
      </div>

    </div>
  `
})
export class TemplateBrowserComponent {
  public ts = inject(TemplateUiService);
  private ms = inject(MigrationUiService);
  private router = inject(Router);

  public applyTemplate(tmpl: MigrationTemplateItem): void {
    this.ms.loadTemplateIntoDraft(tmpl);
    this.router.navigate(['/migration/create']);
  }
}
