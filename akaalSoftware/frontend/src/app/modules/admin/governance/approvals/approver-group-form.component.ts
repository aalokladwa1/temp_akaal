import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { GovernanceService } from '../../services/governance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ApproverGroup } from '../../models/governance.models';

@Component({
  selector: 'app-approver-group-form',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans py-4 pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/governance-centre/approver-groups" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Approver Groups
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">
            {{ isEditMode ? 'Edit Approver Group' : 'Create Approver Group' }}
          </h1>
          <p class="text-sm font-medium text-slate-600 max-w-2xl">
            Configure signers and quorum thresholds for dual authorization.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs w-full">
        <form (ngSubmit)="saveGroup()" class="flex flex-col gap-5 text-xs">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Group Name *</label>
              <input type="text" [(ngModel)]="formData.name" name="name" required placeholder="e.g. Lead Database Architects" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Group Code *</label>
              <input type="text" [(ngModel)]="formData.code" name="code" required placeholder="e.g. GRP-LEAD-DBA" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Description</label>
            <textarea [(ngModel)]="formData.description" name="description" rows="3" placeholder="Describe the group responsibilities..." class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white"></textarea>
          </div>

          <div class="flex items-center gap-3 pt-4 border-t border-slate-100">
            <button type="submit" class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs cursor-pointer">
              {{ isEditMode ? 'Update Group' : 'Create Group' }}
            </button>
            <a routerLink="/administration/governance-centre/approver-groups" class="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-lg">
              Cancel
            </a>
          </div>
        </form>
      </div>

    </div>
  `
})
export class ApproverGroupFormComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private govService = inject(GovernanceService);

  public isEditMode = false;
  public gId = '';

  public formData: Partial<ApproverGroup> = {
    name: '',
    code: '',
    description: '',
    quorumThreshold: 1,
    eligibleApprovers: [{ name: 'Aalok Ladwa', email: 'aalok.ladwa@akaaltech.internal', title: 'Principal Lead Architect' }]
  };

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode = true;
      this.gId = id;
      const found = this.govService.approverGroups().find(g => g.id === id);
      if (found) this.formData = { ...found };
    }
  }

  public saveGroup(): void {
    if (this.isEditMode) {
      this.govService.updateApproverGroup(this.gId, this.formData);
      this.router.navigate(['/administration/governance-centre/approver-groups', this.gId]);
    } else {
      const created = this.govService.createApproverGroup(this.formData);
      this.router.navigate(['/administration/governance-centre/approver-groups', created.id]);
    }
  }
}