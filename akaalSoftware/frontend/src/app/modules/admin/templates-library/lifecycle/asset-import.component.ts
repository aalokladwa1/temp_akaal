/**
 * AKAAL Administration — Import Template Asset
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TemplatesConfigService } from '../../services/templates-config.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-asset-import',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/templates-library" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Template Library
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Import Asset Bundle</h1>
            <p class="text-sm font-medium text-slate-600">
              Import pre-packaged templates, schema mapping bundles, or privacy policies from external JSON / YAML exports.
            </p>
          </div>
        </div>
      </div>

      <!-- Form Body -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs p-6 flex flex-col gap-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Target Asset Family</label>
            <app-custom-select
              [options]="familyOptions"
              [(ngModel)]="family">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Imported Asset Name Override (Optional)</label>
            <input
              type="text"
              [(ngModel)]="nameOverride"
              placeholder="Leave blank to infer from bundle..."
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5 md:col-span-2">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">JSON / YAML Specification Content</label>
            <textarea
              [(ngModel)]="importPayload"
              rows="10"
              placeholder="Paste exported asset JSON or YAML content here..."
              class="p-3 font-mono text-xs rounded border border-slate-200 bg-slate-900 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-blue-500 transition-colors leading-relaxed"></textarea>
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/templates-library"
            class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors shadow-2xs">
            Cancel
          </a>
          <button
            (click)="import()"
            [disabled]="!importPayload"
            class="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors shadow-2xs cursor-pointer">
            Validate & Import Asset
          </button>
        </div>
      </div>
    </div>
  `
})
export class AssetImportComponent {
  private router = inject(Router);
  public library = inject(TemplatesConfigService);

  public family: any = 'MIGRATION_TEMPLATE';
  public nameOverride = '';
  public importPayload = '{\n  "name": "Imported Financial Mapping Template",\n  "version": "1.0.0",\n  "spec": {}\n}';

  public familyOptions: CustomSelectOption[] = [
    { label: 'Migration Template', value: 'MIGRATION_TEMPLATE' },
    { label: 'Mapping Template', value: 'MAPPING_TEMPLATE' },
    { label: 'Transformation Template', value: 'TRANSFORMATION_TEMPLATE' },
    { label: 'Privacy Policy', value: 'PRIVACY_POLICY' },
    { label: 'Data Quality Policy', value: 'DATA_QUALITY_POLICY' },
    { label: 'Configuration Profile', value: 'CONFIGURATION_PROFILE' }
  ];

  public import(): void {
    if (!this.importPayload) return;
    let inferredName = this.nameOverride || 'Imported Template Asset';
    try {
      const parsed = JSON.parse(this.importPayload);
      if (parsed.name && !this.nameOverride) inferredName = parsed.name;
    } catch (e) {
      // Allow raw string payload if not pure JSON
    }

    const created = this.library.createAsset({
      name: inferredName,
      family: this.family,
      specPayload: this.importPayload,
      description: 'Imported externally from template bundle.'
    });

    this.router.navigate(['/administration/templates-library/asset', created.id]);
  }
}
