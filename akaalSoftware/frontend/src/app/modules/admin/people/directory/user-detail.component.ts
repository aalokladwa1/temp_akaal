import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-user-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="user(); else notFound">
      
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
          <div class="flex items-center gap-3">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ user()?.name }}</h1>
            <span
              class="rounded px-2 py-0.5 text-[11px] font-semibold"
              [ngClass]="{
                'bg-emerald-50 text-emerald-700': user()?.status === 'ACTIVE',
                'bg-rose-50 text-rose-700': user()?.status === 'SUSPENDED',
                'bg-amber-50 text-amber-700': user()?.status === 'PROVISIONING'
              }">
              {{ user()?.status }}
            </span>
          </div>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            {{ user()?.title }} &bull; {{ user()?.department }}
          </p>
        </div>

        <div class="flex items-center gap-2 pt-1">
          <a
            [routerLink]="['/administration/people/users', user()?.id, 'edit']"
            class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded transition-colors shadow-2xs">
            Edit User
          </a>
          <button
            (click)="toggleStatus()"
            class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs cursor-pointer">
            {{ user()?.status === 'ACTIVE' ? 'Suspend Principal' : 'Activate Principal' }}
          </button>
        </div>
      </div>

      <!-- Detail Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <!-- Left: Identity Core Info -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col gap-4 shadow-2xs md:col-span-2">
          <h2 class="text-base font-bold text-slate-900 font-heading border-b border-slate-100 pb-3">Identity & Authentication Details</h2>
          
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Email Address</span>
              <span class="font-mono font-semibold text-slate-900">{{ user()?.email }}</span>
            </div>

            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Principal ID</span>
              <span class="font-mono font-semibold text-slate-900">{{ user()?.id }}</span>
            </div>

            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Principal Classification</span>
              <span class="font-semibold text-slate-800">{{ user()?.type }}</span>
            </div>

            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Primary Organization</span>
              <span class="font-semibold text-slate-800">{{ user()?.primaryOrgName }} ({{ user()?.primaryOrgId }})</span>
            </div>

            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Multi-Factor Authentication</span>
              <span class="font-semibold text-emerald-600">{{ user()?.mfaEnforced ? 'Hardware Token Enforced' : 'Not Enforced' }}</span>
            </div>

            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Last Authentication</span>
              <span class="font-semibold text-slate-800">{{ user()?.lastActive }}</span>
            </div>
          </div>
        </div>

        <!-- Right: Entitlements Summary -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col gap-4 shadow-2xs">
          <h2 class="text-base font-bold text-slate-900 font-heading border-b border-slate-100 pb-3">Entitlements</h2>
          
          <div class="flex flex-col gap-3 text-xs">
            <div class="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-100">
              <span class="font-medium text-slate-600">Assigned Roles</span>
              <span class="font-bold text-slate-900">{{ user()?.assignedRolesCount }}</span>
            </div>

            <div class="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-100">
              <span class="font-medium text-slate-600">Team Memberships</span>
              <span class="font-bold text-slate-900">{{ user()?.teamsCount }}</span>
            </div>

            <div class="pt-2">
              <a routerLink="/administration/people/assignments" class="text-xs font-semibold text-blue-600 hover:text-blue-800">
                View detailed role assignments &rarr;
              </a>
            </div>
          </div>
        </div>

      </div>

    </div>

    <ng-template #notFound>
      <div class="p-8 text-center text-slate-500 text-sm">
        User not found. <a routerLink="/administration/people/users" class="text-blue-600 underline">Back to users</a>
      </div>
    </ng-template>
  `
})
export class UserDetailComponent {
  private route = inject(ActivatedRoute);
  private peopleService = inject(PeopleService);

  public userId = signal<string>(this.route.snapshot.paramMap.get('id') || '');

  public user = computed(() => {
    return this.peopleService.users().find(u => u.id === this.userId());
  });

  public toggleStatus(): void {
    const current = this.user();
    if (!current) return;
    const nextStatus = current.status === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
    this.peopleService.updateUser(current.id, { status: nextStatus });
  }
}