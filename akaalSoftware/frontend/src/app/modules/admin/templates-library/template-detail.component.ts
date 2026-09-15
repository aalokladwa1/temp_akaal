/**
 * AKAAL Administration — Template Asset Detail
 */

import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TemplatesConfigService } from '../services/templates-config.service';
import { TemplateAsset } from '../models/templates-config.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-template-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="asset()">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a [routerLink]="parentFamilyRoute()" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to {{ familyDisplayName() }}
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold font-mono"
                [ngClass]="{
                  'bg-emerald-50 text-emerald-700 border border-emerald-200': asset()?.environmentTier === 'PRODUCTION',
                  'bg-amber-50 text-amber-700 border border-amber-200': asset()?.environmentTier === 'STAGING',
                  'bg-slate-100 text-slate-700 border border-slate-200': asset()?.environmentTier === 'DEVELOPMENT'
                }">
                {{ asset()?.environmentTier }}
              </span>
              <span class="rounded px-2 py-0.5 text-[11px] font-semibold"
                [ngClass]="{
                  'bg-emerald-50 text-emerald-700 border border-emerald-200': asset()?.status === 'PUBLISHED',
                  'bg-amber-50 text-amber-700 border border-amber-200': asset()?.status === 'DEPRECATED',
                  'bg-slate-100 text-slate-700 border border-slate-200': asset()?.status === 'DRAFT'
                }">
                {{ asset()?.status }}
              </span>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ asset()?.name }}</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              {{ asset()?.description }}
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <a
              [routerLink]="['/administration/templates-library/asset', assetId, 'promote']"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs flex items-center gap-1.5">
              <app-lucide-icon name="arrow-up-circle" [size]="13"></app-lucide-icon>
              <span>Promote Asset</span>
            </a>
            <button
              *ngIf="asset()?.status !== 'DEPRECATED'"
              (click)="showDeprecateModal = true"
              class="px-3.5 py-1.5 text-xs font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-lg transition-colors shadow-2xs cursor-pointer">
              Mark Deprecated
            </button>
          </div>
        </div>
      </div>

      <!-- Deprecation Alert if applicable -->
      <div *ngIf="asset()?.status === 'DEPRECATED'" class="p-4 rounded-xl border border-amber-200 bg-amber-50/70 flex flex-col gap-1">
        <div class="flex items-center gap-2 font-bold text-amber-900 text-xs">
          <app-lucide-icon name="alert-triangle" [size]="15" class="text-amber-600"></app-lucide-icon>
          <span>This asset has been marked as DEPRECATED</span>
        </div>
        <p class="text-xs text-amber-800">
          Reason: {{ asset()?.deprecationNotice?.reason || 'Superseded by newer architecture version.' }}
        </p>
      </div>

      <!-- Detail Tabs Navigation -->
      <div class="flex border-b border-slate-200 gap-6">
        <button
          (click)="activeTab = 'spec'"
          class="pb-3 text-xs font-bold transition-colors border-b-2 cursor-pointer font-heading"
          [ngClass]="activeTab === 'spec' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-800'">
          Configuration Specification
        </button>
        <button
          (click)="activeTab = 'versions'"
          class="pb-3 text-xs font-bold transition-colors border-b-2 cursor-pointer font-heading"
          [ngClass]="activeTab === 'versions' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-800'">
          Version History ({{ asset()?.versions?.length || 0 }})
        </button>
        <button
          (click)="activeTab = 'usages'"
          class="pb-3 text-xs font-bold transition-colors border-b-2 cursor-pointer font-heading"
          [ngClass]="activeTab === 'usages' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-800'">
          Active Dependencies & Usages ({{ asset()?.usages?.length || 0 }})
        </button>
      </div>

      <!-- Tab 1: Spec -->
      <div *ngIf="activeTab === 'spec'" class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Specification Payload (JSON / YAML)</span>
          <span class="text-xs font-mono text-slate-500">v{{ asset()?.currentVersion }}</span>
        </div>
        <pre class="bg-slate-900 text-slate-100 p-4 rounded-lg font-mono text-xs overflow-x-auto select-all leading-relaxed">{{ asset()?.specPayload }}</pre>
      </div>

      <!-- Tab 2: Version History -->
      <div *ngIf="activeTab === 'versions'" class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Version</th>
              <th class="py-3 px-4">Release Date</th>
              <th class="py-3 px-4">Author</th>
              <th class="py-3 px-4">Changelog</th>
              <th class="py-3 px-4">Breaking</th>
              <th class="py-3 px-4">Checksum</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-sans">
            <tr *ngFor="let v of asset()?.versions" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4 font-mono font-bold text-slate-900">v{{ v.version }}</td>
              <td class="py-3 px-4 text-slate-600 font-mono">{{ v.releaseDate }}</td>
              <td class="py-3 px-4 text-slate-800 font-medium">{{ v.authorEmail }}</td>
              <td class="py-3 px-4 text-slate-700">{{ v.changelog }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[10px] font-semibold"
                  [ngClass]="v.breakingChanges ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-slate-100 text-slate-600 border border-slate-200'">
                  {{ v.breakingChanges ? 'BREAKING' : 'NONE' }}
                </span>
              </td>
              <td class="py-3 px-4 font-mono text-[11px] text-slate-500">{{ v.checksum }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Tab 3: Usages -->
      <div *ngIf="activeTab === 'usages'" class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Consumer Entity</th>
              <th class="py-3 px-4">Type</th>
              <th class="py-3 px-4">Scope</th>
              <th class="py-3 px-4">Bound Version</th>
              <th class="py-3 px-4">Last Executed</th>
              <th class="py-3 px-4">Health</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-sans">
            <tr *ngFor="let u of asset()?.usages" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4 font-bold text-slate-900">{{ u.consumerName }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ u.consumerType }}
                </span>
              </td>
              <td class="py-3 px-4 text-slate-600">{{ u.consumerScope }}</td>
              <td class="py-3 px-4 font-mono font-semibold text-slate-800">v{{ u.boundVersion }}</td>
              <td class="py-3 px-4 text-slate-600 font-mono text-[11px]">{{ u.lastExecutionTimestamp }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {{ u.healthStatus }}
                </span>
              </td>
            </tr>
            <tr *ngIf="asset()?.usages?.length === 0">
              <td colspan="6" class="py-6 text-center text-slate-400">No active consumers or dependencies currently bound to this asset.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Deprecation Modal -->
      <div *ngIf="showDeprecateModal" class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl border border-slate-200 shadow-xl w-full max-w-lg p-6 flex flex-col gap-5 animate-in zoom-in-95 duration-150">
          <div class="flex items-center justify-between pb-3 border-b border-slate-200">
            <h2 class="text-base font-bold text-slate-900 font-heading">Deprecate Template Asset</h2>
            <button (click)="showDeprecateModal = false" class="text-slate-400 hover:text-slate-600 p-1">
              <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
            </button>
          </div>

          <div class="flex flex-col gap-3">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Deprecation Reason</label>
              <textarea
                [(ngModel)]="deprecateReason"
                rows="3"
                placeholder="Explain why this template is being deprecated and guide consumers to the replacement..."
                class="p-2.5 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"></textarea>
            </div>
          </div>

          <div class="flex items-center justify-end gap-3 pt-3 border-t border-slate-200">
            <button
              (click)="showDeprecateModal = false"
              class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors shadow-2xs cursor-pointer">
              Cancel
            </button>
            <button
              (click)="confirmDeprecation()"
              class="px-4 py-1.5 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-700 rounded-lg transition-colors shadow-2xs cursor-pointer">
              Confirm Deprecation
            </button>
          </div>
        </div>
      </div>

    </div>
  `
})
export class TemplateDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  public library = inject(TemplatesConfigService);

  public assetId = '';
  public activeTab: 'spec' | 'versions' | 'usages' = 'spec';
  public showDeprecateModal = false;
  public deprecateReason = '';

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      this.assetId = params.get('id') || '';
    });
  }

  public asset(): TemplateAsset | undefined {
    return this.library.getAssetById(this.assetId);
  }

  public parentFamilyRoute(): string {
    const a = this.asset();
    if (!a) return '/administration/templates-library';
    switch (a.family) {
      case 'MIGRATION_TEMPLATE': return '/administration/templates-library/migration';
      case 'MAPPING_TEMPLATE': return '/administration/templates-library/mapping';
      case 'TRANSFORMATION_TEMPLATE': return '/administration/templates-library/transformation';
      case 'PRIVACY_POLICY': return '/administration/templates-library/privacy';
      case 'DATA_QUALITY_POLICY': return '/administration/templates-library/quality';
      case 'CONFIGURATION_PROFILE': return '/administration/templates-library/configuration';
      default: return '/administration/templates-library';
    }
  }

  public familyDisplayName(): string {
    const a = this.asset();
    if (!a) return 'Library';
    switch (a.family) {
      case 'MIGRATION_TEMPLATE': return 'Migration Templates';
      case 'MAPPING_TEMPLATE': return 'Mapping Templates';
      case 'TRANSFORMATION_TEMPLATE': return 'Transformation Templates';
      case 'PRIVACY_POLICY': return 'Privacy Policies';
      case 'DATA_QUALITY_POLICY': return 'Data Quality Policies';
      case 'CONFIGURATION_PROFILE': return 'Configuration Profiles';
      default: return 'Library';
    }
  }

  public confirmDeprecation(): void {
    if (!this.assetId) return;
    this.library.deprecateAsset(this.assetId, this.deprecateReason);
    this.showDeprecateModal = false;
  }
}
