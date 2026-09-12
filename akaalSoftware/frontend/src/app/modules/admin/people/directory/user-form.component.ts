import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { AdminUser, PrincipalType, PrincipalStatus } from '../../models/people.models';

@Component({
  selector: 'app-user-form',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans py-4 pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Top Premium Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/people/users" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Users
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">
            {{ isEditMode ? 'Edit User Principal' : 'Add New User Principal' }}
          </h1>
          <p class="text-sm font-medium text-slate-600 max-w-2xl">
            Configure identity parameters, role attributes, and organizational bindings.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs w-full">
        <form (ngSubmit)="saveUser()" class="flex flex-col gap-5 text-xs">
          
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Full Name *</label>
              <input
                type="text"
                [(ngModel)]="formData.name"
                name="name"
                required
                placeholder="e.g. Rachel Adams"
                class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Email Address *</label>
              <input
                type="email"
                [(ngModel)]="formData.email"
                name="email"
                required
                placeholder="e.g. r.adams@akaaltech.corp"
                class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Job Title *</label>
              <input
                type="text"
                [(ngModel)]="formData.title"
                name="title"
                required
                placeholder="e.g. Senior Infrastructure Engineer"
                class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Department *</label>
              <input
                type="text"
                [(ngModel)]="formData.department"
                name="department"
                required
                placeholder="e.g. Cloud Operations"
                class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Principal Type</label>
              <app-custom-select
                [options]="principalTypeOptions"
                [(ngModel)]="formData.type"
                name="type">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Primary Organization</label>
              <input
                type="text"
                [(ngModel)]="formData.primaryOrgName"
                name="primaryOrgName"
                placeholder="e.g. Akaal Corporate Global"
                class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="mfa"
              [(ngModel)]="formData.mfaEnforced"
              name="mfaEnforced"
              class="rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
            <label for="mfa" class="font-medium text-slate-700 cursor-pointer">Enforce Hardware Multi-Factor Authentication (MFA)</label>
          </div>

          <div class="flex items-center gap-3 pt-4 border-t border-slate-100">
            <button
              type="submit"
              class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs cursor-pointer">
              {{ isEditMode ? 'Update User' : 'Create User Principal' }}
            </button>
            <a
              routerLink="/administration/people/users"
              class="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-lg">
              Cancel
            </a>
          </div>

        </form>
      </div>

    </div>
  `
})
export class UserFormComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private peopleService = inject(PeopleService);

  public isEditMode = false;
  public userId = '';

  public principalTypeOptions: CustomSelectOption[] = [
    { label: 'Employee', value: 'EMPLOYEE' },
    { label: 'Contractor', value: 'CONTRACTOR' },
    { label: 'System Operator', value: 'SYSTEM_OPERATOR' },
    { label: 'External Auditor', value: 'EXTERNAL_AUDITOR' }
  ];

  public formData: Partial<AdminUser> = {
    name: '',
    email: '',
    title: '',
    department: '',
    type: 'EMPLOYEE' as PrincipalType,
    status: 'ACTIVE' as PrincipalStatus,
    primaryOrgId: 'org-global-corp',
    primaryOrgName: 'Akaal Corporate Global',
    mfaEnforced: true,
    assignedRolesCount: 1,
    teamsCount: 1
  };

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode = true;
      this.userId = id;
      const found = this.peopleService.users().find(u => u.id === id);
      if (found) {
        this.formData = { ...found };
      }
    }
  }

  public saveUser(): void {
    if (this.isEditMode) {
      this.peopleService.updateUser(this.userId, this.formData);
      this.router.navigate(['/administration/people/users', this.userId]);
    } else {
      const created = this.peopleService.createUser(this.formData);
      this.router.navigate(['/administration/people/users', created.id]);
    }
  }
}