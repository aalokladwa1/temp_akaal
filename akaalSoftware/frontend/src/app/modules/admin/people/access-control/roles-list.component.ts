import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-roles-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/people" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to People & Access
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Roles & Permissions</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Coarse and fine-grained authorization roles, permission bundles, and domain scopes.
          </p>
        </div>

        <div class="flex items-center gap-2 pt-1">
          <a
            routerLink="/administration/people/roles/new"
            class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
            Create Custom Role
          </a>
        </div>
      </div>

      <!-- Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Role Name & Code</th>
                <th class="py-3 px-4">Domain Scope</th>
                <th class="py-3 px-4">Type</th>
                <th class="py-3 px-4">Assigned Principals</th>
                <th class="py-3 px-4">Permissions</th>
                <th class="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              <tr *ngFor="let r of peopleService.roles()" class="hover:bg-slate-50/50 transition-colors">
                <td class="py-3 px-4">
                  <div class="flex flex-col">
                    <a [routerLink]="['/administration/people/roles', r.id]" class="font-bold text-slate-900 hover:text-blue-600 transition-colors">
                      {{ r.name }}
                    </a>
                    <span class="text-[11px] text-slate-500 font-mono">{{ r.code }}</span>
                  </div>
                </td>
                <td class="py-3 px-4 font-semibold text-slate-800">
                  {{ r.domainScope }}
                </td>
                <td class="py-3 px-4">
                  <span class="rounded px-2 py-0.5 text-[11px] font-semibold" [ngClass]="r.isSystemRole ? 'bg-indigo-50 text-indigo-700' : 'bg-slate-100 text-slate-700'">
                    {{ r.isSystemRole ? 'System Built-In' : 'Custom' }}
                  </span>
                </td>
                <td class="py-3 px-4 font-bold text-slate-800">
                  {{ r.assignedPrincipalsCount }}
                </td>
                <td class="py-3 px-4 font-semibold text-slate-700">
                  {{ r.permissionsCount }} grants
                </td>
                <td class="py-3 px-4 text-right">
                  <div class="flex items-center justify-end gap-2">
                    <a [routerLink]="['/administration/people/roles', r.id]" class="text-xs font-semibold text-blue-600 hover:text-blue-800">
                      View
                    </a>
                    <span *ngIf="!r.isSystemRole" class="text-slate-300">|</span>
                    <a *ngIf="!r.isSystemRole" [routerLink]="['/administration/people/roles', r.id, 'edit']" class="text-xs font-semibold text-slate-600 hover:text-slate-900">
                      Edit
                    </a>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class RolesListComponent {
  public peopleService = inject(PeopleService);
}