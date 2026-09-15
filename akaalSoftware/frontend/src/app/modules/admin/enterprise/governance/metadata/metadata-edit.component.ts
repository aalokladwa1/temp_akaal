/**
 * AKAAL Administration — Edit Metadata Attribute
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-metadata-edit',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="tag()">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a [routerLink]="['/administration/enterprise/metadata', mId]" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Attribute Details
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-mono font-bold text-slate-900 tracking-tight font-heading">Edit {{ tag()?.key }}</h1>
            <p class="text-sm font-medium text-slate-600">
              Update description, schema validation, and enforcement policy.
            </p>
          </div>
        </div>
      </div>

      <!-- Form Body -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs p-6 flex flex-col gap-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Category</label>
            <app-custom-select
              [options]="categoryOptions"
              [(ngModel)]="category">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Value Schema</label>
            <input
              type="text"
              [(ngModel)]="valueSchema"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex items-center gap-3 pt-4 md:col-span-2">
            <input
              type="checkbox"
              id="editIsMandatory"
              [(ngModel)]="isMandatory"
              class="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <label for="editIsMandatory" class="text-xs font-bold text-slate-700">Enforce as Mandatory on Tagged Resources</label>
          </div>

          <div class="flex flex-col gap-1.5 md:col-span-2">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Description</label>
            <textarea
              [(ngModel)]="description"
              rows="3"
              class="p-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"></textarea>
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            [routerLink]="['/administration/enterprise/metadata', mId]"
            class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded transition-colors shadow-2xs">
            Cancel
          </a>
          <button
            (click)="save()"
            class="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs cursor-pointer">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  `
})
export class MetadataEditComponent {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  public enterprise = inject(EnterpriseService);

  public mId = '';
  public category: 'COST_CENTER' | 'DATA_GOVERNANCE' | 'SECURITY_CLASSIFICATION' | 'OPERATIONAL_TIER' = 'DATA_GOVERNANCE';
  public valueSchema = '';
  public isMandatory = false;
  public description = '';

  public categoryOptions: CustomSelectOption[] = [
    { label: 'Cost Center', value: 'COST_CENTER' },
    { label: 'Data Governance', value: 'DATA_GOVERNANCE' },
    { label: 'Security Classification', value: 'SECURITY_CLASSIFICATION' },
    { label: 'Operational Tier', value: 'OPERATIONAL_TIER' }
  ];

  constructor() {
    this.route.paramMap.subscribe(params => {
      this.mId = params.get('id') || '';
      const t = this.tag();
      if (t) {
        this.category = t.category;
        this.valueSchema = t.valueSchema;
        this.isMandatory = t.isMandatory;
        this.description = t.description;
      }
    });
  }

  public tag() {
    return this.enterprise.metadataTags().find(t => t.id === this.mId);
  }

  public save() {
    this.enterprise.updateMetadataTag(this.mId, {
      category: this.category,
      valueSchema: this.valueSchema,
      isMandatory: this.isMandatory,
      description: this.description
    });
    this.router.navigate(['/administration/enterprise/metadata', this.mId]);
  }
}
