import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { AccessAssignment } from '../../models/people.models';

@Component({
  selector: 'app-assignment-form',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans py-4 pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/people/assignments" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Assignments
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Grant Access Assignment</h1>
          <p class="text-sm font-medium text-slate-600 max-w-2xl">
            Bind an enterprise principal to an explicit authorization role within a defined scope boundary.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs w-full">
        <form (ngSubmit)="saveAssignment()" class="flex flex-col gap-5 text-xs">
          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Select Principal *</label>
            <app-custom-select
              [options]="principalOptions()"
              [(ngModel)]="formData.principalId"
              name="principalId">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Select Role *</label>
            <app-custom-select
              [options]="roleOptions()"
              [(ngModel)]="formData.roleId"
              name="roleId">
            </app-custom-select>
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
              <label class="font-semibold text-slate-700">Scope Name</label>
              <input type="text" [(ngModel)]="formData.scopeName" name="scopeName" placeholder="e.g. Global Root" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="flex items-center gap-3 pt-4 border-t border-slate-100">
            <button type="submit" class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs cursor-pointer">
              Grant Role
            </button>
            <a routerLink="/administration/people/assignments" class="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-lg">
              Cancel
            </a>
          </div>
        </form>
      </div>

    </div>
  `
})
export class AssignmentFormComponent {
  private router = inject(Router);
  public peopleService = inject(PeopleService);

  public scopeTypeOptions: CustomSelectOption[] = [
    { label: 'GLOBAL', value: 'GLOBAL' },
    { label: 'ORGANIZATION', value: 'ORGANIZATION' },
    { label: 'WORKSPACE', value: 'WORKSPACE' }
  ];

  public principalOptions = computed<CustomSelectOption[]>(() => {
    const users = this.peopleService.users().map(u => ({ label: `${u.name} (${u.email})`, value: u.id, group: 'Users' }));
    const teams = this.peopleService.teams().map(t => ({ label: `${t.name} (Team)`, value: t.id, group: 'Teams' }));
    const srvs = this.peopleService.serviceAccounts().map(s => ({ label: `${s.name} (Service Account)`, value: s.id, group: 'Service Accounts' }));
    return [...users, ...teams, ...srvs];
  });

  public roleOptions = computed<CustomSelectOption[]>(() => {
    return this.peopleService.roles().map(r => ({ label: `${r.name} (${r.domainScope})`, value: r.id }));
  });

  public formData: Partial<AccessAssignment> = {
    principalId: 'usr-aalok-01',
    principalName: 'Aalok Ladwa',
    principalType: 'USER',
    roleId: 'role-migration-architect',
    roleName: 'Migration Initiative Architect',
    scopeType: 'GLOBAL',
    scopeName: 'Global Corporate Root',
    status: 'ACTIVE'
  };

  public saveAssignment(): void {
    const user = this.peopleService.users().find(u => u.id === this.formData.principalId);
    if (user) {
      this.formData.principalName = user.name;
      this.formData.principalType = 'USER';
    }
    const role = this.peopleService.roles().find(r => r.id === this.formData.roleId);
    if (role) {
      this.formData.roleName = role.name;
    }
    this.peopleService.assignAccess(this.formData);
    this.router.navigate(['/administration/people/assignments']);
  }
}