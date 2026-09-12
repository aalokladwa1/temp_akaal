/**
 * AKAAL Administration — Edit Boundary
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-boundary-edit',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="boundary()">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a [routerLink]="['/administration/enterprise/boundaries', bId]" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Boundary Details
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Edit Resource Boundary</h1>
            <p class="text-sm font-medium text-slate-600">
              Update isolation level and security classification tags.
            </p>
          </div>
        </div>
      </div>

      <!-- Form Body -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs p-6 flex flex-col gap-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Boundary Name</label>
            <input
              type="text"
              [(ngModel)]="name"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Lead Owner Name</label>
            <input
              type="text"
              [(ngModel)]="leadOwnerName"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Isolation Policy</label>
            <app-custom-select
              [options]="isolationPolicyOptions"
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
            [routerLink]="['/administration/enterprise/boundaries', bId]"
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
export class BoundaryEditComponent {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  public enterprise = inject(EnterpriseService);

  public bId = '';
  public name = '';
  public leadOwnerName = '';
  public isolationPolicy: 'STRICT_ISOLATED' | 'CROSS_TENANT_READ' | 'FEDERATED_PEER' = 'STRICT_ISOLATED';
  public dataClassification: 'RESTRICTED_CONFIDENTIAL' | 'CONFIDENTIAL' | 'INTERNAL' | 'PUBLIC' = 'CONFIDENTIAL';

  public isolationPolicyOptions: CustomSelectOption[] = [
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

  constructor() {
    this.route.paramMap.subscribe(params => {
      this.bId = params.get('id') || '';
      const b = this.boundary();
      if (b) {
        this.name = b.name;
        this.leadOwnerName = b.leadOwnerName;
        this.isolationPolicy = b.isolationPolicy;
        this.dataClassification = b.dataClassification;
      }
    });
  }

  public boundary() {
    return this.enterprise.boundaries().find(b => b.id === this.bId);
  }

  public save() {
    this.enterprise.updateBoundary(this.bId, {
      name: this.name,
      leadOwnerName: this.leadOwnerName,
      isolationPolicy: this.isolationPolicy,
      dataClassification: this.dataClassification
    });
    this.router.navigate(['/administration/enterprise/boundaries', this.bId]);
  }
}
