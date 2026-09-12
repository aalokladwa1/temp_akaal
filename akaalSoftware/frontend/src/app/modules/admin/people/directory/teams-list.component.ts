import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-teams-list',
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
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Teams & Engineering Units</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Cross-functional engineering groups, operational ownership units, and team-level access groupings.
          </p>
        </div>

        <div class="flex items-center gap-2 pt-1">
          <a
            routerLink="/administration/people/teams/new"
            class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-2xs">
            Create Team
          </a>
        </div>
      </div>

      <!-- Search Toolbar -->
      <div class="flex items-center justify-between gap-4 flex-wrap bg-white p-3.5 border border-slate-200 rounded-xl shadow-2xs">
        <div class="relative flex-1 min-w-[240px] max-w-md">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <app-lucide-icon name="search" [size]="14"></app-lucide-icon>
          </div>
          <input
            type="text"
            [(ngModel)]="searchQuery"
            placeholder="Search teams by name, code, or lead..."
            class="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors" />
        </div>
      </div>

      <!-- Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4">Team Name & Code</th>
                <th class="py-3 px-4">Description</th>
                <th class="py-3 px-4">Lead Owner</th>
                <th class="py-3 px-4">Organization</th>
                <th class="py-3 px-4">Members</th>
                <th class="py-3 px-4">Roles</th>
                <th class="py-3 px-4">Status</th>
                <th class="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              <tr *ngFor="let t of filteredTeams()" class="hover:bg-slate-50/50 transition-colors">
                <td class="py-3 px-4">
                  <div class="flex flex-col">
                    <a [routerLink]="['/administration/people/teams', t.id]" class="font-bold text-slate-900 hover:text-blue-600 transition-colors">
                      {{ t.name }}
                    </a>
                    <span class="text-[11px] text-slate-500 font-mono">{{ t.code }}</span>
                  </div>
                </td>
                <td class="py-3 px-4 max-w-xs truncate text-slate-600">
                  {{ t.description }}
                </td>
                <td class="py-3 px-4">
                  <div class="flex flex-col">
                    <span class="font-medium text-slate-900">{{ t.leadOwnerName }}</span>
                    <span class="text-[11px] text-slate-500 font-mono">{{ t.leadOwnerEmail }}</span>
                  </div>
                </td>
                <td class="py-3 px-4 font-medium text-slate-700">
                  {{ t.orgName }}
                </td>
                <td class="py-3 px-4 font-bold text-slate-800">
                  {{ t.membersCount }}
                </td>
                <td class="py-3 px-4 font-semibold text-slate-800">
                  {{ t.assignedRolesCount }}
                </td>
                <td class="py-3 px-4">
                  <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700">
                    {{ t.status }}
                  </span>
                </td>
                <td class="py-3 px-4 text-right">
                  <div class="flex items-center justify-end gap-2">
                    <a [routerLink]="['/administration/people/teams', t.id]" class="text-xs font-semibold text-blue-600 hover:text-blue-800">
                      View
                    </a>
                    <span class="text-slate-300">|</span>
                    <a [routerLink]="['/administration/people/teams', t.id, 'edit']" class="text-xs font-semibold text-slate-600 hover:text-slate-900">
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
export class TeamsListComponent {
  private peopleService = inject(PeopleService);
  public searchQuery = '';

  public filteredTeams = computed(() => {
    const list = this.peopleService.teams();
    return list.filter(t =>
      !this.searchQuery ||
      t.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
      t.code.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
      t.leadOwnerName.toLowerCase().includes(this.searchQuery.toLowerCase())
    );
  });
}