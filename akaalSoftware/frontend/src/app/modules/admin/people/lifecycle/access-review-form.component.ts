import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { AccessReviewCampaign } from '../../models/people.models';

@Component({
  selector: 'app-access-review-form',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans py-4 pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/people/access-reviews" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Access Reviews
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Start Access Review Campaign</h1>
          <p class="text-sm font-medium text-slate-600 max-w-2xl">
            Launch a targeted attestation workflow requiring owners to recertify member entitlements.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs w-full">
        <form (ngSubmit)="saveReview()" class="flex flex-col gap-5 text-xs">
          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Campaign Name *</label>
            <input type="text" [(ngModel)]="formData.name" name="name" required placeholder="e.g. Q2 2026 Privileged Role Recertification" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Scope Type</label>
              <app-custom-select
                [options]="scopeTypeOptions"
                [(ngModel)]="formData.scopeType"
                name="scopeType">
              </app-custom-select>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Scope Target Name</label>
              <input type="text" [(ngModel)]="formData.scopeName" name="scopeName" placeholder="e.g. All Privileged Roles" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Reviewer Name</label>
              <input type="text" [(ngModel)]="formData.reviewerName" name="reviewerName" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Reviewer Email</label>
              <input type="email" [(ngModel)]="formData.reviewerEmail" name="reviewerEmail" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="flex items-center gap-3 pt-4 border-t border-slate-100">
            <button type="submit" class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs cursor-pointer">
              Initiate Campaign
            </button>
            <a routerLink="/administration/people/access-reviews" class="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-lg">
              Cancel
            </a>
          </div>
        </form>
      </div>

    </div>
  `
})
export class AccessReviewFormComponent {
  private router = inject(Router);
  private peopleService = inject(PeopleService);

  public scopeTypeOptions: CustomSelectOption[] = [
    { label: 'ROLE_TIER', value: 'ROLE_TIER' },
    { label: 'ORGANIZATION', value: 'ORGANIZATION' },
    { label: 'WORKSPACE', value: 'WORKSPACE' }
  ];

  public formData: Partial<AccessReviewCampaign> = {
    name: '',
    scopeType: 'ROLE_TIER',
    scopeName: 'All Privileged Tier Roles',
    reviewerName: 'Aalok Ladwa',
    reviewerEmail: 'aalok.ladwa@akaaltech.internal',
    totalEntitlements: 12
  };

  public saveReview(): void {
    const created = this.peopleService.createAccessReview(this.formData);
    this.router.navigate(['/administration/people/access-reviews', created.id]);
  }
}