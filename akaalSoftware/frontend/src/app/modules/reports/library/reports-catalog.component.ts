import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReportsService } from '../services/reports.service';
import { ReportCategoryDefinition, ReportCategoryKey } from '../models/reports.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-reports-catalog',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full select-none">
      
      <!-- Catalog Introduction -->
      <div class="flex flex-col gap-1">
        <h2 class="text-lg font-bold text-slate-900 font-heading">Canonical Report Catalog</h2>
        <p class="text-xs text-slate-500">
          Fourteen specialized reporting domains across the migration lifecycle. Select any category to browse historical reports.
        </p>
      </div>

      <!-- 14 Categories Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        @for (category of categories; track category.key) {
          <div 
            (click)="onSelectCategory(category.key)"
            class="p-5 bg-white border border-slate-200 hover:border-blue-400 rounded-xl shadow-2xs flex flex-col justify-between gap-4 cursor-pointer transition-all hover:shadow-xs group">
            
            <div class="flex flex-col gap-2.5">
              <div class="flex items-start justify-between gap-3">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                    <app-lucide-icon [name]="category.icon" [size]="18"></app-lucide-icon>
                  </div>
                  <h3 class="text-sm font-bold text-slate-900 group-hover:text-blue-600 font-heading transition-colors">
                    {{ category.label }}
                  </h3>
                </div>
              </div>

              <p class="text-xs text-slate-600 leading-relaxed">
                {{ category.description }}
              </p>
            </div>

            <div class="pt-3.5 border-t border-slate-100 flex items-center justify-between">
              <span class="text-[11px] font-medium text-slate-500">{{ category.technicalScope }}</span>
              <span class="h-7 px-3 rounded-lg bg-slate-50 group-hover:bg-blue-600 border border-slate-200 group-hover:border-blue-600 text-slate-700 group-hover:text-white font-semibold text-xs inline-flex items-center gap-1.5 transition-all shadow-2xs">
                <span>Browse Domain</span>
                <app-lucide-icon name="arrow-right" [size]="12" class="transition-transform group-hover:translate-x-0.5"></app-lucide-icon>
              </span>
            </div>

          </div>
        }
      </div>

    </div>
  `
})
export class ReportsCatalogComponent {
  public categories: ReportCategoryDefinition[];

  constructor(private reportsService: ReportsService) {
    this.categories = this.reportsService.categories;
  }

  public onSelectCategory(key: ReportCategoryKey): void {
    this.reportsService.selectCategory(key);
  }
}
