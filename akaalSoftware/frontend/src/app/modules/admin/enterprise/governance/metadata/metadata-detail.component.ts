/**
 * AKAAL Administration — Metadata Detail
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-metadata-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="tag()">
      
      <!-- Back Link & Breadcrumbs -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/enterprise/metadata" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Enterprise Metadata
        
          </a>
        </div>

        

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">{{ tag()?.category }}</span>
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold" [ngClass]="tag()?.isMandatory ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-slate-100 text-slate-700 border border-slate-200'">
                {{ tag()?.isMandatory ? 'MANDATORY ATTRIBUTE' : 'OPTIONAL ATTRIBUTE' }}
              </span>
            </div>
            <h1 class="text-2xl font-mono font-bold text-slate-900 tracking-tight font-heading">{{ tag()?.key }}</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              {{ tag()?.description }}
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              [routerLink]="['/administration/enterprise/metadata', tag()?.id, 'edit']"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
              Edit Attribute
            </a>
          </div>
        </div>
      </div>

      <!-- Overview Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">VALUE SCHEMA</span>
          <span class="text-base font-mono font-bold text-slate-900">{{ tag()?.valueSchema }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">APPLIED RESOURCES</span>
          <span class="text-base font-bold text-slate-900">{{ tag()?.appliedResourceCount }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">ALLOWED VALUES</span>
          <span class="text-xs font-mono text-slate-700">{{ tag()?.allowedValues?.join(', ') || 'Any value matching schema' }}</span>
        </div>

        <div class="bg-white p-4 border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-1">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">CREATED AT</span>
          <span class="text-sm font-mono text-slate-700">{{ tag()?.createdAt }}</span>
        </div>
      </div>
    </div>
  `
})
export class MetadataDetailComponent {
  private route = inject(ActivatedRoute);
  public enterprise = inject(EnterpriseService);

  public mId = '';

  constructor() {
    this.route.paramMap.subscribe(params => {
      this.mId = params.get('id') || '';
    });
  }

  public tag() {
    return this.enterprise.metadataTags().find(t => t.id === this.mId);
  }
}
