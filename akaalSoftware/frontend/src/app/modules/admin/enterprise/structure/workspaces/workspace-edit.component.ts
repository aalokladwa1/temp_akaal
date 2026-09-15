/**
 * AKAAL Administration — Edit Workspace
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';
import { WorkspaceTier } from '../../../models/enterprise.models';

@Component({
  selector: 'app-workspace-edit',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans py-4 pb-16 select-none animate-in fade-in duration-150" *ngIf="workspace()">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a [routerLink]="['/administration/enterprise/workspaces', wsId]" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Workspace Details
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Edit Workspace</h1>
          <p class="text-sm font-medium text-slate-600 max-w-2xl">
            Update workspace attributes, tier, and storage allocations.
          </p>
        </div>
      </div>

      <!-- Form Body -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs p-6 flex flex-col gap-6 w-full">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Workspace Name *</label>
            <input
              type="text"
              [(ngModel)]="name"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Workspace Code *</label>
            <input
              type="text"
              [(ngModel)]="code"
              class="h-9 px-3 text-xs font-mono uppercase rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Workspace Tier</label>
            <app-custom-select
              [options]="tierOptions"
              [(ngModel)]="tier">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Residency Region</label>
            <input
              type="text"
              [(ngModel)]="residencyRegion"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Owner Name</label>
            <input
              type="text"
              [(ngModel)]="ownerName"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Owner Email</label>
            <input
              type="email"
              [(ngModel)]="ownerEmail"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
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
            [routerLink]="['/administration/enterprise/workspaces', wsId]"
            class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors shadow-2xs">
            Cancel
          </a>
          <button
            (click)="save()"
            class="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs cursor-pointer">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  `
})
export class WorkspaceEditComponent {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  public enterprise = inject(EnterpriseService);

  public tierOptions: CustomSelectOption[] = [
    { label: 'Enterprise Production', value: 'ENTERPRISE_PRODUCTION' },
    { label: 'High Throughput Replication', value: 'HIGH_THROUGHPUT_REPLICATION' },
    { label: 'Staging Validation', value: 'STAGING_VALIDATION' },
    { label: 'Development Sandbox', value: 'DEVELOPMENT_SANDBOX' }
  ];

  public wsId = '';
  public name = '';
  public code = '';
  public tier: WorkspaceTier = 'ENTERPRISE_PRODUCTION';
  public residencyRegion = '';
  public ownerName = '';
  public ownerEmail = '';
  public description = '';

  constructor() {
    this.route.paramMap.subscribe(params => {
      this.wsId = params.get('id') || '';
      const ws = this.workspace();
      if (ws) {
        this.name = ws.name;
        this.code = ws.code;
        this.tier = ws.tier;
        this.residencyRegion = ws.residencyRegion;
        this.ownerName = ws.ownerName;
        this.ownerEmail = ws.ownerEmail;
        this.description = ws.description;
      }
    });
  }

  public workspace() {
    return this.enterprise.workspaces().find(w => w.id === this.wsId);
  }

  public save() {
    this.enterprise.updateWorkspace(this.wsId, {
      name: this.name,
      code: this.code,
      tier: this.tier,
      residencyRegion: this.residencyRegion,
      ownerName: this.ownerName,
      ownerEmail: this.ownerEmail,
      description: this.description
    });
    this.router.navigate(['/administration/enterprise/workspaces', this.wsId]);
  }
}
