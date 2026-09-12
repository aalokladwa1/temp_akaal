import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ConditionalAccessRule } from '../../models/people.models';

@Component({
  selector: 'app-conditional-access-form',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans py-4 pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/people/conditional-access" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Conditional Access
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">
            {{ isEditMode ? 'Edit Conditional Policy' : 'Create Conditional Policy' }}
          </h1>
          <p class="text-sm font-medium text-slate-600 max-w-2xl">
            Configure step-up authentication thresholds and IP network boundaries.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs w-full">
        <form (ngSubmit)="savePolicy()" class="flex flex-col gap-5 text-xs">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Policy Name *</label>
              <input type="text" [(ngModel)]="formData.name" name="name" required placeholder="e.g. Production Console Zero-Trust Guard" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Target Role *</label>
              <input type="text" [(ngModel)]="formData.targetRole" name="targetRole" required placeholder="e.g. ROLE-PLATFORM-ADMIN" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Description</label>
            <textarea [(ngModel)]="formData.description" name="description" rows="3" placeholder="Describe the policy condition..." class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white"></textarea>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex items-center gap-2 pt-2">
              <input type="checkbox" id="ip" [(ngModel)]="formData.ipAllowlistRequired" name="ipAllowlistRequired" class="rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
              <label for="ip" class="font-medium text-slate-700 cursor-pointer">Require Corporate IP Allowlist</label>
            </div>
            <div class="flex items-center gap-2 pt-2">
              <input type="checkbox" id="mfaStep" [(ngModel)]="formData.mfaStepUpRequired" name="mfaStepUpRequired" class="rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
              <label for="mfaStep" class="font-medium text-slate-700 cursor-pointer">Require FIDO2 Hardware Step-Up</label>
            </div>
          </div>

          <div class="flex items-center gap-3 pt-4 border-t border-slate-100">
            <button type="submit" class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs cursor-pointer">
              {{ isEditMode ? 'Update Policy' : 'Create Policy' }}
            </button>
            <a routerLink="/administration/people/conditional-access" class="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-lg">
              Cancel
            </a>
          </div>
        </form>
      </div>

    </div>
  `
})
export class ConditionalAccessFormComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private peopleService = inject(PeopleService);

  public isEditMode = false;
  public ruleId = '';

  public formData: Partial<ConditionalAccessRule> = {
    name: '',
    description: '',
    targetRole: 'ROLE-PLATFORM-ADMIN',
    enforcementMode: 'STRICT_ENFORCED',
    ipAllowlistRequired: true,
    mfaStepUpRequired: true
  };

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode = true;
      this.ruleId = id;
      const found = this.peopleService.conditionalRules().find(r => r.id === id);
      if (found) this.formData = { ...found };
    }
  }

  public savePolicy(): void {
    if (this.isEditMode) {
      this.peopleService.updateConditionalRule(this.ruleId, this.formData);
      this.router.navigate(['/administration/people/conditional-access', this.ruleId]);
    } else {
      const created = this.peopleService.createConditionalRule(this.formData);
      this.router.navigate(['/administration/people/conditional-access', created.id]);
    }
  }
}