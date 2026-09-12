import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { AdminRole } from '../../models/people.models';

@Component({
  selector: 'app-role-form',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans py-4 pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/people/roles" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Roles
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">
            {{ isEditMode ? 'Edit Custom Role' : 'Create Custom Role' }}
          </h1>
          <p class="text-sm font-medium text-slate-600 max-w-2xl">
            Define fine-grained permission bundles and target domain boundaries.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs w-full">
        <form (ngSubmit)="saveRole()" class="flex flex-col gap-5 text-xs">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Role Name *</label>
              <input type="text" [(ngModel)]="formData.name" name="name" required placeholder="e.g. Audit Compliance Inspector" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Role Code *</label>
              <input type="text" [(ngModel)]="formData.code" name="code" required placeholder="e.g. ROLE-AUDIT-INSPECTOR" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Description</label>
            <textarea [(ngModel)]="formData.description" name="description" rows="3" placeholder="Describe the authority granted by this role..." class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white"></textarea>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Domain Scope</label>
            <app-custom-select
              [options]="domainScopeOptions"
              [(ngModel)]="formData.domainScope"
              name="domainScope">
            </app-custom-select>
          </div>

          <div class="flex items-center gap-3 pt-4 border-t border-slate-100">
            <button type="submit" class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs cursor-pointer">
              {{ isEditMode ? 'Update Role' : 'Create Role' }}
            </button>
            <a routerLink="/administration/people/roles" class="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-lg">
              Cancel
            </a>
          </div>
        </form>
      </div>

    </div>
  `
})
export class RoleFormComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private peopleService = inject(PeopleService);

  public isEditMode = false;
  public roleId = '';

  public domainScopeOptions: CustomSelectOption[] = [
    { label: 'GLOBAL', value: 'GLOBAL' },
    { label: 'ORGANIZATION', value: 'ORGANIZATION' },
    { label: 'WORKSPACE', value: 'WORKSPACE' },
    { label: 'PIPELINE', value: 'PIPELINE' }
  ];

  public formData: Partial<AdminRole> = {
    name: '',
    code: '',
    description: '',
    domainScope: 'GLOBAL',
    isSystemRole: false,
    permissions: ['akaal:audit:read', 'akaal:reports:export']
  };

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode = true;
      this.roleId = id;
      const found = this.peopleService.roles().find(r => r.id === id);
      if (found) this.formData = { ...found };
    }
  }

  public saveRole(): void {
    if (this.isEditMode) {
      this.peopleService.updateRole(this.roleId, this.formData);
      this.router.navigate(['/administration/people/roles', this.roleId]);
    } else {
      const created = this.peopleService.createRole(this.formData);
      this.router.navigate(['/administration/people/roles', created.id]);
    }
  }
}