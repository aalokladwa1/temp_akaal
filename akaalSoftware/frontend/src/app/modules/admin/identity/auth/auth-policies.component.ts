/**
 * AKAAL Administration — Authentication Policies
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { AuthPolicy } from '../../models/identity.models';

@Component({
  selector: 'app-auth-policies',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/identity/auth" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Authentication
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Authentication Policies</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Password complexity thresholds, lockout durations, session idle timeouts, and IP fencing rules.
            </p>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <button
              (click)="showCreateModal = true"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs cursor-pointer">
              Create Policy
            </button>
          </div>
        </div>
      </div>

      <!-- Policy Table View -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Policy Name</th>
              <th class="py-3 px-4">Tier</th>
              <th class="py-3 px-4">Min Length</th>
              <th class="py-3 px-4">Lockout</th>
              <th class="py-3 px-4">Idle TTL</th>
              <th class="py-3 px-4">MFA Enforcement</th>
              <th class="py-3 px-4">Assigned Users</th>
              <th class="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-sans">
            <tr *ngFor="let p of identity.authPolicies()" class="hover:bg-slate-50/60 transition-colors">
              <td class="py-3 px-4">
                <div class="flex flex-col">
                  <span class="font-bold text-slate-900">{{ p.name }}</span>
                  <span class="text-[11px] text-slate-500">{{ p.description }}</span>
                </div>
              </td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ p.tier }}
                </span>
              </td>
              <td class="py-3 px-4 font-mono font-semibold text-slate-800">{{ p.minPasswordLength }} chars</td>
              <td class="py-3 px-4 font-medium text-slate-700">{{ p.lockoutThresholdAttempts }} attempts ({{ p.lockoutDurationMinutes }}m)</td>
              <td class="py-3 px-4 font-medium text-slate-700">{{ p.sessionIdleTimeoutMinutes }} mins</td>
              <td class="py-3 px-4">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                  {{ p.mfaEnforcement }}
                </span>
              </td>
              <td class="py-3 px-4 font-bold text-slate-800">{{ p.assignedPrincipalsCount }}</td>
              <td class="py-3 px-4">
                <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {{ p.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Create Policy Modal -->
      <div *ngIf="showCreateModal" class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl border border-slate-200 shadow-xl w-full max-w-2xl p-6 flex flex-col gap-6 animate-in zoom-in-95 duration-150 max-h-[90vh] overflow-y-auto">
          <div class="flex items-center justify-between pb-4 border-b border-slate-200">
            <h2 class="text-lg font-bold text-slate-900 font-heading">Create Authentication Policy</h2>
            <button (click)="showCreateModal = false" class="text-slate-400 hover:text-slate-600 p-1">
              <app-lucide-icon name="x" [size]="18"></app-lucide-icon>
            </button>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5 md:col-span-2">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Policy Name</label>
              <input
                type="text"
                [(ngModel)]="newName"
                placeholder="e.g. Finance Division Strict Auth"
                class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
              />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Policy Tier</label>
              <app-custom-select
                [options]="tierOptions"
                [(ngModel)]="newTier">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">MFA Enforcement</label>
              <app-custom-select
                [options]="mfaOptions"
                [(ngModel)]="newMfa">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Min Password Length</label>
              <input
                type="number"
                [(ngModel)]="newMinLength"
                class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
              />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Lockout Attempts</label>
              <input
                type="number"
                [(ngModel)]="newLockoutAttempts"
                class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
              />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Idle Timeout (Mins)</label>
              <input
                type="number"
                [(ngModel)]="newIdleMins"
                class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
              />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Max Password Age (Days)</label>
              <input
                type="number"
                [(ngModel)]="newMaxAgeDays"
                class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
              />
            </div>

            <div class="flex flex-col gap-1.5 md:col-span-2">
              <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Description</label>
              <textarea
                [(ngModel)]="newDescription"
                rows="2"
                placeholder="Scope and purpose of this authentication policy..."
                class="p-2.5 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"></textarea>
            </div>
          </div>

          <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <button
              (click)="showCreateModal = false"
              class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors shadow-2xs cursor-pointer">
              Cancel
            </button>
            <button
              (click)="savePolicy()"
              [disabled]="!newName"
              class="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors shadow-2xs cursor-pointer">
              Create Policy
            </button>
          </div>
        </div>
      </div>

    </div>
  `
})
export class AuthPoliciesComponent {
  public identity = inject(IdentityService);

  public showCreateModal = false;
  public newName = '';
  public newTier: any = 'ENTERPRISE_HIGH';
  public newMfa: any = 'ENFORCED_ALL';
  public newMinLength = 14;
  public newLockoutAttempts = 5;
  public newIdleMins = 30;
  public newMaxAgeDays = 90;
  public newDescription = '';

  public tierOptions: CustomSelectOption[] = [
    { label: 'Critical Gov', value: 'CRITICAL_GOV' },
    { label: 'Enterprise High', value: 'ENTERPRISE_HIGH' },
    { label: 'Standard', value: 'STANDARD' }
  ];

  public mfaOptions: CustomSelectOption[] = [
    { label: 'Enforced for All Users', value: 'ENFORCED_ALL' },
    { label: 'Enforced for Privileged Only', value: 'ENFORCED_PRIVILEGED_ONLY' },
    { label: 'Optional', value: 'OPTIONAL' }
  ];

  public savePolicy(): void {
    if (!this.newName) return;
    this.identity.createAuthPolicy({
      name: this.newName,
      tier: this.newTier,
      mfaEnforcement: this.newMfa,
      minPasswordLength: this.newMinLength,
      lockoutThresholdAttempts: this.newLockoutAttempts,
      sessionIdleTimeoutMinutes: this.newIdleMins,
      passwordMaxAgeDays: this.newMaxAgeDays,
      description: this.newDescription
    });
    this.showCreateModal = false;
    this.newName = '';
    this.newDescription = '';
  }
}
