import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-users-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Top Premium Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/people" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to People & Access
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Users & Identities</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Enterprise human principals, authentication posture, primary organization bindings, and role entitlements.
          </p>
        </div>

        <div class="flex items-center gap-2 pt-1">
          <a
            routerLink="/administration/people/users/new"
            class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
            Add User
          </a>
        </div>
      </div>

      <!-- Search & Filters Toolbar -->
      <div class="flex items-center justify-between gap-4 flex-wrap bg-white p-3.5 border border-slate-200 rounded-xl shadow-2xs">
        <div class="relative flex-1 min-w-[240px] max-w-md">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <app-lucide-icon name="search" [size]="14"></app-lucide-icon>
          </div>
          <input
            type="text"
            [(ngModel)]="searchQuery"
            placeholder="Search by name, email, or department..."
            class="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors" />
        </div>

        <div class="flex items-center gap-2 flex-wrap min-w-[280px]">
          <div class="w-36">
            <app-custom-select
              size="sm"
              [options]="statusOptions"
              [(ngModel)]="statusFilter">
            </app-custom-select>
          </div>

          <div class="w-40">
            <app-custom-select
              size="sm"
              [options]="typeOptions"
              [(ngModel)]="typeFilter">
            </app-custom-select>
          </div>
        </div>
      </div>

      <!-- Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">User Principal</th>
                <th class="py-3 px-4">Title & Department</th>
                <th class="py-3 px-4">Type</th>
                <th class="py-3 px-4">Primary Org</th>
                <th class="py-3 px-4">Status</th>
                <th class="py-3 px-4">MFA</th>
                <th class="py-3 px-4">Roles</th>
                <th class="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              <tr *ngFor="let u of filteredUsers()" class="hover:bg-slate-50/50 transition-colors">
                <td class="py-3 px-4">
                  <div class="flex flex-col">
                    <a [routerLink]="['/administration/people/users', u.id]" class="font-bold text-slate-900 hover:text-blue-600 transition-colors">
                      {{ u.name }}
                    </a>
                    <span class="text-[11px] text-slate-500 font-mono">{{ u.email }}</span>
                  </div>
                </td>
                <td class="py-3 px-4">
                  <div class="flex flex-col">
                    <span class="font-medium text-slate-800">{{ u.title }}</span>
                    <span class="text-[11px] text-slate-500">{{ u.department }}</span>
                  </div>
                </td>
                <td class="py-3 px-4">
                  <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700">
                    {{ u.type }}
                  </span>
                </td>
                <td class="py-3 px-4 font-medium text-slate-700">
                  {{ u.primaryOrgName }}
                </td>
                <td class="py-3 px-4">
                  <span
                    class="rounded px-2 py-0.5 text-[11px] font-semibold"
                    [ngClass]="{
                      'bg-emerald-50 text-emerald-700': u.status === 'ACTIVE',
                      'bg-rose-50 text-rose-700': u.status === 'SUSPENDED',
                      'bg-amber-50 text-amber-700': u.status === 'PROVISIONING'
                    }">
                    {{ u.status }}
                  </span>
                </td>
                <td class="py-3 px-4">
                  <span *ngIf="u.mfaEnforced" class="rounded px-2 py-0.5 text-[11px] font-semibold bg-blue-50 text-blue-700">
                    Enforced
                  </span>
                  <span *ngIf="!u.mfaEnforced" class="rounded px-2 py-0.5 text-[11px] font-semibold bg-rose-50 text-rose-700">
                    Disabled
                  </span>
                </td>
                <td class="py-3 px-4 font-semibold text-slate-800">
                  {{ u.assignedRolesCount }}
                </td>
                <td class="py-3 px-4 text-right">
                  <div class="flex items-center justify-end gap-2">
                    <a [routerLink]="['/administration/people/users', u.id]" class="text-xs font-semibold text-blue-600 hover:text-blue-800">
                      View
                    </a>
                    <span class="text-slate-300">|</span>
                    <a [routerLink]="['/administration/people/users', u.id, 'edit']" class="text-xs font-semibold text-slate-600 hover:text-slate-900">
                      Edit
                    </a>
                  </div>
                </td>
              </tr>
              <tr *ngIf="filteredUsers().length === 0">
                <td colspan="8" class="py-8 text-center text-xs text-slate-500">
                  No users found matching your search and filter criteria.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class UsersListComponent {
  private peopleService = inject(PeopleService);

  public searchQuery = '';
  public statusFilter = 'ALL';
  public typeFilter = 'ALL';

  public statusOptions: CustomSelectOption[] = [
    { label: 'All Statuses', value: 'ALL' },
    { label: 'Active', value: 'ACTIVE' },
    { label: 'Suspended', value: 'SUSPENDED' },
    { label: 'Provisioning', value: 'PROVISIONING' }
  ];

  public typeOptions: CustomSelectOption[] = [
    { label: 'All Types', value: 'ALL' },
    { label: 'Employee', value: 'EMPLOYEE' },
    { label: 'Contractor', value: 'CONTRACTOR' },
    { label: 'System Operator', value: 'SYSTEM_OPERATOR' },
    { label: 'External Auditor', value: 'EXTERNAL_AUDITOR' }
  ];

  public filteredUsers = computed(() => {
    const list = this.peopleService.users();
    return list.filter(u => {
      const matchSearch =
        !this.searchQuery ||
        u.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        u.email.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        u.department.toLowerCase().includes(this.searchQuery.toLowerCase());
      
      const matchStatus = this.statusFilter === 'ALL' || u.status === this.statusFilter;
      const matchType = this.typeFilter === 'ALL' || u.type === this.typeFilter;

      return matchSearch && matchStatus && matchType;
    });
  });
}