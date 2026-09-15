import { Component, inject, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-team-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="team(); else notFound">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/people/teams" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Teams
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ team()?.name }}</h1>
            <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700">
              {{ team()?.status }}
            </span>
          </div>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            {{ team()?.description }}
          </p>
        </div>

        <div class="flex items-center gap-2 pt-1">
          <a
            [routerLink]="['/administration/people/teams', team()?.id, 'edit']"
            class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded transition-colors shadow-2xs">
            Edit Team
          </a>
        </div>
      </div>

      <!-- Details -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col gap-4 shadow-2xs md:col-span-2">
          <h2 class="text-base font-bold text-slate-900 font-heading border-b border-slate-100 pb-3">Team Specification</h2>
          
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Team Code</span>
              <span class="font-mono font-semibold text-slate-900">{{ team()?.code }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Lead Owner</span>
              <span class="font-semibold text-slate-900">{{ team()?.leadOwnerName }} ({{ team()?.leadOwnerEmail }})</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Organization</span>
              <span class="font-semibold text-slate-900">{{ team()?.orgName }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Created Date</span>
              <span class="font-semibold text-slate-900">{{ team()?.createdAt | date:'mediumDate' }}</span>
            </div>
          </div>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col gap-4 shadow-2xs">
          <h2 class="text-base font-bold text-slate-900 font-heading border-b border-slate-100 pb-3">Metrics</h2>
          <div class="flex flex-col gap-3 text-xs">
            <div class="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-100">
              <span class="font-medium text-slate-600">Active Members</span>
              <span class="font-bold text-slate-900">{{ team()?.membersCount }}</span>
            </div>
            <div class="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-100">
              <span class="font-medium text-slate-600">Assigned Roles</span>
              <span class="font-bold text-slate-900">{{ team()?.assignedRolesCount }}</span>
            </div>
          </div>
        </div>
      </div>

    </div>
    <ng-template #notFound>
      <div class="p-8 text-center text-slate-500 text-sm">
        Team not found. <a routerLink="/administration/people/teams" class="text-blue-600 underline">Back to teams</a>
      </div>
    </ng-template>
  `
})
export class TeamDetailComponent {
  private route = inject(ActivatedRoute);
  private peopleService = inject(PeopleService);

  public teamId = signal<string>(this.route.snapshot.paramMap.get('id') || '');
  public team = computed(() => this.peopleService.teams().find(t => t.id === this.teamId()));
}