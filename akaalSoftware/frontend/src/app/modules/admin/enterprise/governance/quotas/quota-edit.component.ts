/**
 * AKAAL Administration — Edit Quota
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-quota-edit',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="quota()">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a [routerLink]="['/administration/enterprise/quotas', qId]" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Quota Details
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Adjust Resource Quotas</h1>
            <p class="text-sm font-medium text-slate-600">
              Update capacity limits, IOPS caps, and network throughput thresholds.
            </p>
          </div>
        </div>
      </div>

      <!-- Form Body -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs p-6 flex flex-col gap-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Max Concurrent Migrations</label>
            <input
              type="number"
              [(ngModel)]="concurrentMigrationsLimit"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Bandwidth Cap (Mbps)</label>
            <input
              type="number"
              [(ngModel)]="bandwidthMbpsLimit"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Max Active Connections</label>
            <input
              type="number"
              [(ngModel)]="maxActiveConnectionsLimit"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Storage Quota (GB)</label>
            <input
              type="number"
              [(ngModel)]="storageQuotaGb"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            [routerLink]="['/administration/enterprise/quotas', qId]"
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
export class QuotaEditComponent {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  public enterprise = inject(EnterpriseService);

  public qId = '';
  public concurrentMigrationsLimit = 5;
  public bandwidthMbpsLimit = 1000;
  public maxActiveConnectionsLimit = 25;
  public storageQuotaGb = 1024;

  constructor() {
    this.route.paramMap.subscribe(params => {
      this.qId = params.get('id') || '';
      const q = this.quota();
      if (q) {
        this.concurrentMigrationsLimit = q.concurrentMigrationsLimit;
        this.bandwidthMbpsLimit = q.bandwidthMbpsLimit;
        this.maxActiveConnectionsLimit = q.maxActiveConnectionsLimit;
        this.storageQuotaGb = q.storageQuotaGb;
      }
    });
  }

  public quota() {
    return this.enterprise.quotaAllocations().find(q => q.id === this.qId);
  }

  public save() {
    this.enterprise.updateQuotas(this.qId, {
      concurrentMigrationsLimit: this.concurrentMigrationsLimit,
      bandwidthMbpsLimit: this.bandwidthMbpsLimit,
      maxActiveConnectionsLimit: this.maxActiveConnectionsLimit,
      storageQuotaGb: this.storageQuotaGb
    });
    this.router.navigate(['/administration/enterprise/quotas', this.qId]);
  }
}
