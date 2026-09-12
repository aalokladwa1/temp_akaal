/**
 * AKAAL Administration — Promote Template Asset
 */

import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TemplatesConfigService } from '../../services/templates-config.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { PromotionTargetEnv } from '../../models/templates-config.models';

@Component({
  selector: 'app-asset-promote',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="asset()">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a [routerLink]="['/administration/templates-library/asset', assetId]" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Asset Details
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Promote Asset Environment Tier</h1>
            <p class="text-sm font-medium text-slate-600">
              Advance <strong class="text-slate-900">{{ asset()?.name }}</strong> to an elevated deployment lifecycle tier with automated validation.
            </p>
          </div>
        </div>
      </div>

      <!-- Current State Card -->
      <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-center justify-between">
        <div class="flex flex-col gap-0.5">
          <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Current Tier</span>
          <span class="text-sm font-bold text-slate-900">{{ asset()?.environmentTier }}</span>
        </div>
        <div class="flex items-center gap-2">
          <app-lucide-icon name="arrow-right" [size]="16" class="text-slate-400"></app-lucide-icon>
        </div>
        <div class="flex flex-col gap-0.5 text-right">
          <span class="text-[11px] font-bold text-blue-600 uppercase tracking-wider font-heading">Target Tier</span>
          <span class="text-sm font-bold text-blue-700">{{ targetTier }}</span>
        </div>
      </div>

      <!-- Form Body -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs p-6 flex flex-col gap-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Target Environment Tier</label>
            <app-custom-select
              [options]="tierOptions"
              [(ngModel)]="targetTier">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Approval Change Ticket ID</label>
            <input
              type="text"
              [(ngModel)]="ticketId"
              placeholder="e.g. CHG-2026-8812"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5 md:col-span-2">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Promotion Release Notes</label>
            <textarea
              [(ngModel)]="notes"
              rows="3"
              placeholder="Describe what validation checks and integration testing were conducted..."
              class="p-2.5 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"></textarea>
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            [routerLink]="['/administration/templates-library/asset', assetId]"
            class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors shadow-2xs">
            Cancel
          </a>
          <button
            (click)="promote()"
            class="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs cursor-pointer">
            Execute Promotion
          </button>
        </div>
      </div>
    </div>
  `
})
export class AssetPromoteComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  public library = inject(TemplatesConfigService);

  public assetId = '';
  public targetTier: PromotionTargetEnv = 'PRODUCTION';
  public ticketId = '';
  public notes = '';

  public tierOptions: CustomSelectOption[] = [
    { label: 'Production Tier', value: 'PRODUCTION' },
    { label: 'Staging Tier', value: 'STAGING' },
    { label: 'Development Tier', value: 'DEVELOPMENT' }
  ];

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      this.assetId = params.get('id') || '';
    });
  }

  public asset() {
    return this.library.getAssetById(this.assetId);
  }

  public promote(): void {
    if (!this.assetId) return;
    this.library.promoteAsset(this.assetId, this.targetTier);
    this.router.navigate(['/administration/templates-library/asset', this.assetId]);
  }
}
