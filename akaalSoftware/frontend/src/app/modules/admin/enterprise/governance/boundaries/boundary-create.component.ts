/**
 * AKAAL Administration — Create Boundary
 */

import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-boundary-create',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans py-4 pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/enterprise/boundaries" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Resource Boundaries
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Create Resource Boundary</h1>
          <p class="text-sm font-medium text-slate-600 max-w-2xl">
            Define a logical isolation policy and data classification boundary.
          </p>
        </div>
      </div>

      <!-- Form Body -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs p-6 flex flex-col gap-6 w-full">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Parent Workspace</label>
            <app-custom-select
              [options]="workspaceOptions()"
              [(ngModel)]="workspaceId">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Boundary Name *</label>
            <input
              type="text"
              [(ngModel)]="name"
              placeholder="e.g. PCI Data Vault Isolation"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Boundary Code *</label>
            <input
              type="text"
              [(ngModel)]="code"
              placeholder="e.g. BND-PCI-VAULT"
              class="h-9 px-3 text-xs font-mono uppercase rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Lead Owner Name</label>
            <input
              type="text"
              [(ngModel)]="leadOwnerName"
              placeholder="e.g. Aalok Ladwa"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Isolation Policy</label>
            <app-custom-select
              [options]="isolationOptions"
              [(ngModel)]="isolationPolicy">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Data Classification</label>
            <app-custom-select
              [options]="classificationOptions"
              [(ngModel)]="dataClassification">
            </app-custom-select>
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/enterprise/boundaries"
            class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors shadow-2xs">
            Cancel
          </a>
          <button
            (click)="save()"
            [disabled]="!name || !code || !workspaceId"
            class="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 rounded-lg transition-colors shadow-2xs cursor-pointer">
            Create Boundary
          </button>
        </div>
      </div>
    </div>
  `
})
export class BoundaryCreateComponent {
  private router = inject(Router);
  public enterprise = inject(EnterpriseService);

  public workspaceId = '';
  public name = '';
  public code = '';
  public leadOwnerName = '';
  public isolationPolicy: 'STRICT_ISOLATED' | 'CROSS_TENANT_READ' | 'FEDERATED_PEER' = 'STRICT_ISOLATED';
  public dataClassification: 'RESTRICTED_CONFIDENTIAL' | 'CONFIDENTIAL' | 'INTERNAL' | 'PUBLIC' = 'CONFIDENTIAL';

  public isolationOptions: CustomSelectOption[] = [
    { label: 'Strict Isolated', value: 'STRICT_ISOLATED' },
    { label: 'Cross Tenant Read', value: 'CROSS_TENANT_READ' },
    { label: 'Federated Peer', value: 'FEDERATED_PEER' }
  ];

  public classificationOptions: CustomSelectOption[] = [
    { label: 'Restricted Confidential', value: 'RESTRICTED_CONFIDENTIAL' },
    { label: 'Confidential', value: 'CONFIDENTIAL' },
    { label: 'Internal', value: 'INTERNAL' },
    { label: 'Public', value: 'PUBLIC' }
  ];

  public workspaceOptions = computed<CustomSelectOption[]>(() => {
    return this.enterprise.workspaces().map(ws => ({
      label: ws.name,
      value: ws.id
    }));
  });

  constructor() {
    const ws = this.enterprise.workspaces();
    if (ws.length > 0) {
      this.workspaceId = ws[0].id;
    }
  }

  public save() {
    if (!this.name || !this.code || !this.workspaceId) return;
    const newB = this.enterprise.createBoundary({
      workspaceId: this.workspaceId,
      name: this.name,
      code: this.code,
      leadOwnerName: this.leadOwnerName || 'Admin Lead',
      isolationPolicy: this.isolationPolicy,
      dataClassification: this.dataClassification,
      crossBoundaryAllowed: this.isolationPolicy !== 'STRICT_ISOLATED',
      tags: ['GOVERNANCE']
    });
    this.router.navigate(['/administration/enterprise/boundaries', newB.id]);
  }
}
