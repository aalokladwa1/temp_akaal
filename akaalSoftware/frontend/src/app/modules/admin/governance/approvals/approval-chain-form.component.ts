import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { GovernanceService } from '../../services/governance.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ApprovalChain } from '../../models/governance.models';

@Component({
  selector: 'app-approval-chain-form',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans py-4 pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/governance-centre/approval-chains" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Approval Chains
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">
            {{ isEditMode ? 'Edit Approval Chain' : 'Create Approval Chain' }}
          </h1>
          <p class="text-sm font-medium text-slate-600 max-w-2xl">
            Configure quorum thresholds, signers, and expiry hours.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs w-full">
        <form (ngSubmit)="saveChain()" class="flex flex-col gap-5 text-xs">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Chain Name *</label>
              <input type="text" [(ngModel)]="formData.name" name="name" required placeholder="e.g. Multi-Cloud Replica Promotion Chain" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Chain Code *</label>
              <input type="text" [(ngModel)]="formData.code" name="code" required placeholder="e.g. CHAIN-REPLICA-PROMOTION" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Description</label>
            <textarea [(ngModel)]="formData.description" name="description" rows="3" placeholder="Describe the workflow requirement..." class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white"></textarea>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Target Operation</label>
              <input type="text" [(ngModel)]="formData.targetOperation" name="targetOperation" placeholder="e.g. Replica Promotion" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Quorum Required</label>
              <input type="number" [(ngModel)]="formData.quorumApproversRequired" name="quorumApproversRequired" min="1" max="5" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Timeout (Hours)</label>
              <input type="number" [(ngModel)]="formData.timeoutHours" name="timeoutHours" min="1" max="48" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="flex items-center gap-3 pt-4 border-t border-slate-100">
            <button type="submit" class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs cursor-pointer">
              {{ isEditMode ? 'Update Chain' : 'Create Chain' }}
            </button>
            <a routerLink="/administration/governance-centre/approval-chains" class="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-lg">
              Cancel
            </a>
          </div>
        </form>
      </div>

    </div>
  `
})
export class ApprovalChainFormComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private govService = inject(GovernanceService);

  public isEditMode = false;
  public cId = '';

  public formData: Partial<ApprovalChain> = {
    name: '',
    code: '',
    description: '',
    targetOperation: 'Production Cutover',
    stagesCount: 2,
    quorumApproversRequired: 2,
    timeoutHours: 12
  };

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode = true;
      this.cId = id;
      const found = this.govService.approvalChains().find(c => c.id === id);
      if (found) this.formData = { ...found };
    }
  }

  public saveChain(): void {
    if (this.isEditMode) {
      this.govService.updateApprovalChain(this.cId, this.formData);
      this.router.navigate(['/administration/governance-centre/approval-chains', this.cId]);
    } else {
      const created = this.govService.createApprovalChain(this.formData);
      this.router.navigate(['/administration/governance-centre/approval-chains', created.id]);
    }
  }
}