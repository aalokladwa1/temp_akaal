import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-assignments-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
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
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Access Assignments</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Direct and inherited role bindings across users, teams, and machine service accounts.
          </p>
        </div>

        <div class="flex items-center gap-2 pt-1">
          <a
            routerLink="/administration/people/assignments/new"
            class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
            Grant Access Assignment
          </a>
        </div>
      </div>

      <!-- Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Principal Target</th>
                <th class="py-3 px-4">Role Binding</th>
                <th class="py-3 px-4">Scope</th>
                <th class="py-3 px-4">Assigned By</th>
                <th class="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              <tr *ngFor="let a of peopleService.assignments()" class="hover:bg-slate-50/50 transition-colors">
                <td class="py-3 px-4">
                  <div class="flex flex-col">
                    <span class="font-bold text-slate-900">{{ a.principalName }}</span>
                    <span class="text-[11px] text-slate-500 font-mono">{{ a.principalType }}</span>
                  </div>
                </td>
                <td class="py-3 px-4 font-semibold text-indigo-700">
                  {{ a.roleName }}
                </td>
                <td class="py-3 px-4">
                  <div class="flex flex-col">
                    <span class="font-medium text-slate-800">{{ a.scopeName }}</span>
                    <span class="text-[11px] text-slate-500">{{ a.scopeType }}</span>
                  </div>
                </td>
                <td class="py-3 px-4 text-slate-600">
                  {{ a.assignedBy }}
                </td>
                <td class="py-3 px-4">
                  <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700">
                    {{ a.status }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class AssignmentsListComponent {
  public peopleService = inject(PeopleService);
}