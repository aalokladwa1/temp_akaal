/**
 * AKAAL Administration — Transfer Ownership
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EnterpriseService } from '../../../services/enterprise.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-ownership-transfer',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="ownership()">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a [routerLink]="['/administration/enterprise/ownership', ownId]" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Ownership Details
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Transfer Resource Custody</h1>
            <p class="text-sm font-medium text-slate-600">
              Reassign primary custodianship, secondary backup, and escalation responsibilities.
            </p>
          </div>
        </div>
      </div>

      <!-- Form Body -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs p-6 flex flex-col gap-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">New Primary Owner Name</label>
            <input
              type="text"
              [(ngModel)]="newPrimaryName"
              placeholder="e.g. Rachel Adams"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">New Primary Owner Email</label>
            <input
              type="email"
              [(ngModel)]="newPrimaryEmail"
              placeholder="e.g. r.adams@akaaltech.corp"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Assigned Engineering Team</label>
            <input
              type="text"
              [(ngModel)]="assignedTeam"
              placeholder="e.g. Infrastructure Platform Team"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Escalation SLA Contact</label>
            <input
              type="text"
              [(ngModel)]="escalationContact"
              placeholder="e.g. oncall-infra@akaaltech.corp"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5 md:col-span-2">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Handover Notes / Approval Ticket Reference</label>
            <textarea
              [(ngModel)]="transferNotes"
              rows="3"
              placeholder="Provide reason for transfer and change request approval ticket ID..."
              class="p-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"></textarea>
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            [routerLink]="['/administration/enterprise/ownership', ownId]"
            class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded transition-colors shadow-2xs">
            Cancel
          </a>
          <button
            (click)="save()"
            [disabled]="!newPrimaryName || !newPrimaryEmail"
            class="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded transition-colors shadow-2xs cursor-pointer">
            Confirm & Execute Transfer
          </button>
        </div>
      </div>
    </div>
  `
})
export class OwnershipTransferComponent {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  public enterprise = inject(EnterpriseService);

  public ownId = '';
  public newPrimaryName = '';
  public newPrimaryEmail = '';
  public assignedTeam = '';
  public escalationContact = '';
  public transferNotes = '';

  constructor() {
    this.route.paramMap.subscribe(params => {
      this.ownId = params.get('id') || '';
      const o = this.ownership();
      if (o) {
        this.assignedTeam = o.assignedTeam;
        this.escalationContact = o.escalationContact;
      }
    });
  }

  public ownership() {
    return this.enterprise.resourceOwnerships().find(o => o.id === this.ownId);
  }

  public save() {
    if (!this.newPrimaryName || !this.newPrimaryEmail) return;
    this.enterprise.transferOwnership(
      this.ownId,
      this.newPrimaryName,
      this.newPrimaryEmail,
      undefined,
      undefined,
      this.assignedTeam || 'Platform Team'
    );
    this.router.navigate(['/administration/enterprise/ownership', this.ownId]);
  }
}
