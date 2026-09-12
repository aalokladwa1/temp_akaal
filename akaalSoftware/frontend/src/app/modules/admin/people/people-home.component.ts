/**
 * AKAAL Administration — 5.2 People & Access Domain Home
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { PeopleService } from '../services/people.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-people-home',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Top Premium Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Administration
        </a>
      </div>

      <!-- Domain Title & Subtitle -->
      <div class="flex items-start justify-between gap-6 pb-6 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1.5">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">People & Access</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Directory identity governance, enterprise role bindings, just-in-time access elevation, and continuous entitlement review lifecycle.
          </p>
        </div>
      </div>

      <!-- Overview Metric Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">Total Principals</span>
            <app-lucide-icon name="users" [size]="16" class="text-slate-400"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ peopleService.users().length }}</div>
          <span class="text-[11px] text-emerald-600 font-medium font-mono">100% MFA Enforced</span>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">Teams & Groups</span>
            <app-lucide-icon name="shield" [size]="16" class="text-slate-400"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ peopleService.teams().length }}</div>
          <span class="text-[11px] text-slate-500 font-medium">Mapped across 3 Orgs</span>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">Active JIT Requests</span>
            <app-lucide-icon name="clock" [size]="16" class="text-amber-500"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ pendingJitCount() }}</div>
          <span class="text-[11px] text-amber-600 font-medium">Awaiting Dual-Approval</span>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-1 shadow-2xs">
          <div class="flex items-center justify-between text-slate-500">
            <span class="text-xs font-semibold">Active Sessions</span>
            <app-lucide-icon name="key" [size]="16" class="text-blue-500"></app-lucide-icon>
          </div>
          <div class="text-2xl font-bold text-slate-900 font-heading">{{ activeSessionsCount() }}</div>
          <span class="text-[11px] text-slate-500 font-medium">Zero Anomaly Logins</span>
        </div>
      </div>

      <!-- Domain Navigation Sections -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Section 1: Directory -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col justify-between gap-6 shadow-2xs">
          <div class="flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="users" [size]="20"></app-lucide-icon>
              </div>
              <div>
                <h2 class="text-base font-bold text-slate-900 font-heading">Directory</h2>
                <p class="text-xs text-slate-500 font-medium">Humans, teams, and programmatic machine service accounts.</p>
              </div>
            </div>
            
            <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
              <a routerLink="/administration/people/users" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-blue-600 transition-colors">
                <span>Users & Identities</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ peopleService.users().length }} users</span>
              </a>
              <a routerLink="/administration/people/teams" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-blue-600 transition-colors">
                <span>Teams & Engineering Units</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ peopleService.teams().length }} teams</span>
              </a>
              <a routerLink="/administration/people/service-accounts" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-blue-600 transition-colors">
                <span>Service Accounts</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ peopleService.serviceAccounts().length }} accounts</span>
              </a>
            </div>
          </div>
        </div>

        <!-- Section 2: Access Control -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col justify-between gap-6 shadow-2xs">
          <div class="flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                <app-lucide-icon name="shield" [size]="20"></app-lucide-icon>
              </div>
              <div>
                <h2 class="text-base font-bold text-slate-900 font-heading">Access Control</h2>
                <p class="text-xs text-slate-500 font-medium">Granular role-based permissions, explicit bindings, and conditional access policies.</p>
              </div>
            </div>
            
            <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
              <a routerLink="/administration/people/roles" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-indigo-600 transition-colors">
                <span>Roles & Permissions</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ peopleService.roles().length }} roles</span>
              </a>
              <a routerLink="/administration/people/assignments" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-indigo-600 transition-colors">
                <span>Access Assignments</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ peopleService.assignments().length }} grants</span>
              </a>
              <a routerLink="/administration/people/conditional-access" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-indigo-600 transition-colors">
                <span>Conditional Access Policies</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700">{{ peopleService.conditionalRules().length }} active</span>
              </a>
            </div>
          </div>
        </div>

        <!-- Section 3: Privileged Access -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col justify-between gap-6 shadow-2xs">
          <div class="flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600">
                <app-lucide-icon name="key" [size]="20"></app-lucide-icon>
              </div>
              <div>
                <h2 class="text-base font-bold text-slate-900 font-heading">Privileged Access</h2>
                <p class="text-xs text-slate-500 font-medium">Just-in-time time-bounded access requests and toxic separation-of-duties conflict detection.</p>
              </div>
            </div>
            
            <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
              <a routerLink="/administration/people/jit-access" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-amber-600 transition-colors">
                <span>Just-In-Time (JIT) Elevation</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-amber-50 text-amber-700">{{ peopleService.jitRequests().length }} requests</span>
              </a>
              <a routerLink="/administration/people/access-conflicts" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-amber-600 transition-colors">
                <span>Access Conflicts & Toxic Combinations</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-rose-50 text-rose-700">{{ peopleService.accessConflicts().length }} flagged</span>
              </a>
            </div>
          </div>
        </div>

        <!-- Section 4: Access Lifecycle -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col justify-between gap-6 shadow-2xs">
          <div class="flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
                <app-lucide-icon name="clock" [size]="20"></app-lucide-icon>
              </div>
              <div>
                <h2 class="text-base font-bold text-slate-900 font-heading">Access Lifecycle</h2>
                <p class="text-xs text-slate-500 font-medium">Live principal authentication sessions and recurring attestation review campaigns.</p>
              </div>
            </div>
            
            <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
              <a routerLink="/administration/people/sessions" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-emerald-600 transition-colors">
                <span>Active Principal Sessions</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700">{{ activeSessionsCount() }} live</span>
              </a>
              <a routerLink="/administration/people/access-reviews" class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-emerald-600 transition-colors">
                <span>Access Review Campaigns</span>
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600">{{ peopleService.accessReviews().length }} campaigns</span>
              </a>
            </div>
          </div>
        </div>

      </div>

    </div>
  `
})
export class PeopleHomeComponent {
  public peopleService = inject(PeopleService);

  public pendingJitCount = () => this.peopleService.jitRequests().filter(j => j.status === 'PENDING_APPROVAL').length;
  public activeSessionsCount = () => this.peopleService.sessions().filter(s => s.status === 'ACTIVE').length;
}
