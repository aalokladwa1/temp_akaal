import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DashboardService } from '../../core/services/dashboard.service';
import { ContextService } from '../../core/services/context.service';
import { AdministrationIpc } from '../../core/services/ipc/administration.ipc';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';

export type ProfileTab = 'overview' | 'security' | 'sessions';

function tryInject<T>(token: any): T | null {
  try {
    return inject(token);
  } catch {
    return null as any;
  }
}

@Component({
  selector: 'app-profile-home',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="max-w-6xl mx-auto space-y-6 pb-12 font-sans">
      
      <!-- PAGE HEADER -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-white/10">
        <div class="space-y-1">
          <div class="flex items-center gap-2.5">
            <app-lucide-icon name="user" [size]="22" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
            <h1 class="text-xl font-bold tracking-tight text-slate-900 dark:text-white font-heading">Profile &amp; Account</h1>
          </div>
          <p class="text-xs text-slate-500 dark:text-slate-400 font-medium">
            Personal identity, workspace scope, security posture, and active session management.
          </p>
        </div>

        <!-- CONTEXT BADGE -->
        <div class="flex items-center gap-2 self-start sm:self-auto">
          <span class="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-100 dark:bg-white/5 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-white/10 flex items-center gap-1.5">
            <app-lucide-icon name="building-2" [size]="13" class="text-slate-400"></app-lucide-icon>
            {{ cs.selectedOrg()?.name || 'Enterprise Scope' }}
          </span>
        </div>
      </div>

      <!-- PROFILE TOP CARD (IDENTITY HEADER) -->
      <div class="rounded-xl bg-white dark:bg-[#0c0d0e] border border-slate-200 dark:border-white/10 p-6 shadow-2xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div class="flex items-center gap-4">
          <!-- AVATAR WITH DYNAMIC INITIALS / PHOTO AND EDIT AFFORDANCE -->
          <div class="relative group shrink-0">
            @if (userAvatar()) {
              <img
                [src]="userAvatar()"
                alt="Profile Avatar"
                class="w-16 h-16 rounded-lg object-cover border border-slate-200 dark:border-white/10 shadow-md"
              />
            } @else {
              <div class="w-16 h-16 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center text-xl font-bold tracking-wider shadow-md">
                {{ userInitials() }}
              </div>
            }
            <button
              type="button"
              (click)="isAvatarDialogOpen.set(true)"
              title="Change profile photo"
              class="absolute -bottom-1 -right-1 w-7 h-7 rounded-md bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 transition-all shadow-xs cursor-pointer active:scale-95">
              <app-lucide-icon name="camera" [size]="13"></app-lucide-icon>
            </button>
          </div>
          
          <div class="space-y-1">
            <div class="flex items-center gap-3 flex-wrap">
              <h2 class="text-lg font-bold text-slate-900 dark:text-white leading-none">{{ userName() }}</h2>
            </div>
            <p class="text-xs text-slate-500 dark:text-slate-400 font-medium">
              {{ userEmail() }}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-3 w-full md:w-auto border-t md:border-t-0 pt-4 md:pt-0 border-slate-100 dark:border-white/5">
          <a
            routerLink="/settings"
            class="h-9 px-3.5 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 hover:bg-slate-50 dark:hover:bg-white/10 text-slate-700 dark:text-slate-200 text-xs font-semibold shadow-2xs transition-all flex items-center gap-2 cursor-pointer active:scale-95">
            <app-lucide-icon name="settings" [size]="14" class="text-slate-400"></app-lucide-icon>
            <span>Platform Settings</span>
          </a>
        </div>
      </div>

      <!-- WORKSPACE TABS -->
      <div class="border-b border-slate-200 dark:border-white/10 flex items-center gap-2">
        <button
          type="button"
          (click)="setTab('overview')"
          class="px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer flex items-center gap-2"
          [class.border-blue-600]="activeTab() === 'overview'"
          [class.text-blue-600]="activeTab() === 'overview'"
          [class.dark:text-blue-400]="activeTab() === 'overview'"
          [class.border-transparent]="activeTab() !== 'overview'"
          [class.text-slate-600]="activeTab() !== 'overview'"
          [class.dark:text-slate-400]="activeTab() !== 'overview'"
          [class.hover:text-slate-900]="activeTab() !== 'overview'">
          <app-lucide-icon name="user" [size]="14"></app-lucide-icon>
          <span>Overview &amp; Access</span>
        </button>

        <button
          type="button"
          (click)="setTab('security')"
          class="px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer flex items-center gap-2"
          [class.border-blue-600]="activeTab() === 'security'"
          [class.text-blue-600]="activeTab() === 'security'"
          [class.dark:text-blue-400]="activeTab() === 'security'"
          [class.border-transparent]="activeTab() !== 'security'"
          [class.text-slate-600]="activeTab() !== 'security'"
          [class.dark:text-slate-400]="activeTab() !== 'security'"
          [class.hover:text-slate-900]="activeTab() !== 'security'">
          <app-lucide-icon name="shield-check" [size]="14"></app-lucide-icon>
          <span>Security &amp; Credentials</span>
        </button>

        <button
          type="button"
          (click)="setTab('sessions')"
          class="px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer flex items-center gap-2"
          [class.border-blue-600]="activeTab() === 'sessions'"
          [class.text-blue-600]="activeTab() === 'sessions'"
          [class.dark:text-blue-400]="activeTab() === 'sessions'"
          [class.border-transparent]="activeTab() !== 'sessions'"
          [class.text-slate-600]="activeTab() !== 'sessions'"
          [class.dark:text-slate-400]="activeTab() !== 'sessions'"
          [class.hover:text-slate-900]="activeTab() !== 'sessions'">
          <app-lucide-icon name="monitor" [size]="14"></app-lucide-icon>
          <span>Active Sessions</span>
          <span class="px-1.5 py-0.5 rounded-md text-[10px] bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300 font-bold">
            1
          </span>
        </button>
      </div>

      <!-- TAB 1: OVERVIEW & ACCESS -->
      @if (activeTab() === 'overview') {
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <!-- LEFT 2 COLS: IDENTITY & SCOPE -->
          <div class="lg:col-span-2 space-y-6">
            
            <!-- PERSONAL IDENTITY PANEL -->
            <div class="rounded-xl bg-white dark:bg-[#0c0d0e] border border-slate-200 dark:border-white/10 p-5 space-y-4 shadow-2xs">
              <div class="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/5">
                <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-heading">
                  Personal Identity
                </h3>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                
                <!-- DISPLAY NAME (RECTANGULAR SLIGHTLY ROUNDED GDS BUTTON) -->
                <div class="p-3.5 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="text-slate-500 dark:text-slate-400 font-medium">Display Name</span>
                    @if (!isEditingName()) {
                      <button
                        type="button"
                        (click)="startEditName()"
                        class="h-7 px-3 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 hover:bg-slate-100 dark:hover:bg-white/10 text-slate-700 dark:text-slate-200 text-[11px] font-semibold shadow-2xs hover:shadow-xs hover:border-slate-300 dark:hover:border-white/20 transition-all flex items-center gap-1.5 cursor-pointer active:scale-95">
                        <app-lucide-icon name="user" [size]="12" class="text-slate-400"></app-lucide-icon>
                        <span>Edit</span>
                      </button>
                    }
                  </div>

                  @if (isEditingName()) {
                    <div class="space-y-2 pt-1">
                      <input
                        type="text"
                        [(ngModel)]="editNameInput"
                        placeholder="Enter display name"
                        class="w-full h-8 px-2.5 rounded-md border border-slate-300 dark:border-white/20 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-xs focus:outline-none focus:border-blue-500 shadow-2xs"
                      />
                      @if (nameError()) {
                        <p class="text-[11px] text-red-500">{{ nameError() }}</p>
                      }
                      <div class="flex items-center gap-2 pt-1">
                        <button
                          type="button"
                          (click)="saveName()"
                          [disabled]="isSavingName()"
                          class="h-7.5 px-3.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-semibold transition-all shadow-2xs cursor-pointer active:scale-95">
                          {{ isSavingName() ? 'Saving...' : 'Save' }}
                        </button>
                        <button
                          type="button"
                          (click)="cancelEditName()"
                          [disabled]="isSavingName()"
                          class="h-7.5 px-3.5 rounded-md border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 text-[11px] font-semibold hover:bg-slate-100 dark:hover:bg-white/5 transition-all cursor-pointer active:scale-95">
                          Cancel
                        </button>
                      </div>
                    </div>
                  } @else {
                    <span class="font-bold text-slate-900 dark:text-white block leading-snug">{{ userName() }}</span>
                  }
                </div>

                <!-- EMAIL ADDRESS (RECTANGULAR SLIGHTLY ROUNDED GDS BUTTON) -->
                <div class="p-3.5 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="text-slate-500 dark:text-slate-400 font-medium">Email Address</span>
                    @if (!isEditingEmail()) {
                      <button
                        type="button"
                        (click)="startEditEmail()"
                        class="h-7 px-3 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 hover:bg-slate-100 dark:hover:bg-white/10 text-slate-700 dark:text-slate-200 text-[11px] font-semibold shadow-2xs hover:shadow-xs hover:border-slate-300 dark:hover:border-white/20 transition-all flex items-center gap-1.5 cursor-pointer active:scale-95">
                        <app-lucide-icon name="user" [size]="12" class="text-slate-400"></app-lucide-icon>
                        <span>Edit</span>
                      </button>
                    }
                  </div>

                  @if (isEditingEmail()) {
                    <div class="space-y-2 pt-1">
                      <input
                        type="email"
                        [(ngModel)]="editEmailInput"
                        placeholder="Enter email address"
                        class="w-full h-8 px-2.5 rounded-md border border-slate-300 dark:border-white/20 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-xs focus:outline-none focus:border-blue-500 shadow-2xs"
                      />
                      @if (emailError()) {
                        <p class="text-[11px] text-red-500">{{ emailError() }}</p>
                      }
                      <div class="flex items-center gap-2 pt-1">
                        <button
                          type="button"
                          (click)="saveEmail()"
                          [disabled]="isSavingEmail()"
                          class="h-7.5 px-3.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-semibold transition-all shadow-2xs cursor-pointer active:scale-95">
                          {{ isSavingEmail() ? 'Saving...' : 'Save' }}
                        </button>
                        <button
                          type="button"
                          (click)="cancelEditEmail()"
                          [disabled]="isSavingEmail()"
                          class="h-7.5 px-3.5 rounded-md border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 text-[11px] font-semibold hover:bg-slate-100 dark:hover:bg-white/5 transition-all cursor-pointer active:scale-95">
                          Cancel
                        </button>
                      </div>
                    </div>
                  } @else {
                    <span class="font-semibold text-slate-900 dark:text-white block leading-snug">{{ userEmail() }}</span>
                  }
                </div>

              </div>
            </div>

            <!-- CURRENT OPERATIONAL CONTEXT -->
            <div class="rounded-xl bg-white dark:bg-[#0c0d0e] border border-slate-200 dark:border-white/10 p-5 space-y-4 shadow-2xs">
              <div class="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/5">
                <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-heading">
                  Active Context Scope
                </h3>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div class="p-3 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 space-y-1">
                  <span class="text-[10px] font-bold uppercase text-slate-400 tracking-wider block">Organization</span>
                  <span class="font-semibold text-slate-800 dark:text-slate-200 block truncate">
                    {{ cs.selectedOrg()?.name || 'Default Organization' }}
                  </span>
                </div>

                <div class="p-3 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 space-y-1">
                  <span class="text-[10px] font-bold uppercase text-slate-400 tracking-wider block">Workspace</span>
                  <span class="font-semibold text-slate-800 dark:text-slate-200 block truncate">
                    {{ cs.selectedWorkspace()?.name || 'Default Workspace' }}
                  </span>
                </div>

                <div class="p-3 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 space-y-1">
                  <span class="text-[10px] font-bold uppercase text-slate-400 tracking-wider block">Environment</span>
                  <div class="flex items-center gap-1.5">
                    <span class="font-semibold text-slate-800 dark:text-slate-200 truncate">
                      {{ cs.selectedEnvironment()?.name || 'Development' }}
                    </span>
                    @if (cs.isProduction()) {
                      <span class="px-1.5 py-0.2 rounded-md text-[9px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">PROD</span>
                    }
                  </div>
                </div>
              </div>

              <p class="text-[11px] text-slate-400 font-medium">
                Context switching is managed via the header organization selector.
              </p>
            </div>

          </div>

          <!-- RIGHT 1 COL: ACCESS TRANSPARENCY -->
          <div class="space-y-6">
            <div class="rounded-xl bg-white dark:bg-[#0c0d0e] border border-slate-200 dark:border-white/10 p-5 space-y-4 shadow-2xs">
              <div class="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/5">
                <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-heading">
                  My Access
                </h3>
              </div>

              <div class="p-3.5 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/60 dark:border-white/5 text-xs text-slate-600 dark:text-slate-400 leading-relaxed space-y-2">
                <p>
                  Assigned roles and entitlement policies are managed by organization administrators under 
                  <strong class="text-slate-800 dark:text-slate-200">Administration &gt; People &amp; Access</strong>.
                </p>
                <div class="pt-1">
                  <a
                    routerLink="/admin"
                    class="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline">
                    View Administration &rarr;
                  </a>
                </div>
              </div>
            </div>
          </div>

        </div>
      }

      <!-- TAB 2: SECURITY & CREDENTIALS -->
      @if (activeTab() === 'security') {
        <div class="space-y-6">
          
          <div class="rounded-xl bg-white dark:bg-[#0c0d0e] border border-slate-200 dark:border-white/10 p-5 space-y-4 shadow-2xs">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/5">
              <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-heading">
                Security &amp; Credentials
              </h3>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              <!-- PASSWORD MANAGEMENT WITH RECTANGULAR GDS BUTTON -->
              <div class="p-4 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 space-y-3">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <app-lucide-icon name="key" [size]="15" class="text-slate-600 dark:text-slate-400"></app-lucide-icon>
                    <span class="text-xs font-bold text-slate-900 dark:text-white">Account Password</span>
                  </div>
                  <button
                    type="button"
                    (click)="isPasswordModalOpen.set(true)"
                    class="h-7 px-3 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 hover:bg-slate-100 dark:hover:bg-white/10 text-slate-700 dark:text-slate-200 text-[11px] font-semibold shadow-2xs hover:shadow-xs hover:border-slate-300 dark:hover:border-white/20 transition-all flex items-center gap-1.5 cursor-pointer active:scale-95">
                    <app-lucide-icon name="key" [size]="12" class="text-slate-400"></app-lucide-icon>
                    <span>Change</span>
                  </button>
                </div>
                <p class="text-[11px] text-slate-500 dark:text-slate-400">
                  Update your account password to maintain credential security.
                </p>
              </div>

              <!-- MFA STATUS -->
              <div class="p-4 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 space-y-3">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="shield-check" [size]="15" class="text-emerald-600 dark:text-emerald-400"></app-lucide-icon>
                  <span class="text-xs font-bold text-slate-900 dark:text-white">Multi-Factor Authentication</span>
                </div>
                <p class="text-[11px] text-slate-500 dark:text-slate-400">
                  Multi-factor authentication settings and enrollment.
                </p>
              </div>

            </div>
          </div>

        </div>
      }

      <!-- TAB 3: ACTIVE SESSIONS -->
      @if (activeTab() === 'sessions') {
        <div class="space-y-6">
          <div class="rounded-xl bg-white dark:bg-[#0c0d0e] border border-slate-200 dark:border-white/10 p-5 space-y-4 shadow-2xs">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/5">
              <div>
                <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-heading">
                  Active Workstation Session
                </h3>
                <p class="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                  Current desktop runtime session bound to your workstation.
                </p>
              </div>
            </div>

            <!-- CURRENT DESKTOP SESSION -->
            <div class="p-4 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 flex items-center justify-between gap-4 text-xs">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 flex items-center justify-center shrink-0">
                  <app-lucide-icon name="monitor" [size]="18"></app-lucide-icon>
                </div>

                <div class="space-y-0.5">
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-slate-900 dark:text-white">DevKros Desktop Workstation</span>
                    <span class="px-1.5 py-0.2 rounded-md text-[9px] font-bold bg-blue-100 dark:bg-blue-900/60 text-blue-800 dark:text-blue-300">THIS DEVICE</span>
                  </div>
                  <p class="text-[11px] text-slate-500 dark:text-slate-400">
                    Status: Active Application Session
                  </p>
                </div>
              </div>

              <!-- TRUTHFUL EXIT DEVKROS ACTION -->
              <button
                type="button"
                (click)="signOut($event)"
                title="Exit application runtime"
                class="h-8.5 px-3.5 rounded-md bg-white dark:bg-white/10 border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/20 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-all shadow-2xs cursor-pointer flex items-center gap-1.5 shrink-0 active:scale-95">
                <app-lucide-icon name="log-out" [size]="13" class="text-slate-400"></app-lucide-icon>
                <span>Exit DevKros</span>
              </button>
            </div>
          </div>
        </div>
      }

      <!-- REAL PHOTO MANAGEMENT AVATAR DIALOG WITH RECTANGULAR GDS MODAL CLOSE BUTTON -->
      @if (isAvatarDialogOpen()) {
        <div class="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150">
          <div class="w-full max-w-sm rounded-xl bg-white dark:bg-[#121315] border border-slate-200 dark:border-white/10 shadow-2xl p-6 space-y-5">
            <div class="flex items-center justify-between border-b border-slate-100 dark:border-white/5 pb-3">
              <h3 class="text-sm font-bold text-slate-900 dark:text-white font-heading">Profile Photo</h3>
              <button
                type="button"
                (click)="isAvatarDialogOpen.set(false)"
                title="Close dialog"
                class="w-8 h-8 rounded-md bg-slate-100 dark:bg-white/10 hover:bg-slate-200 dark:hover:bg-white/20 text-slate-500 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-all flex items-center justify-center cursor-pointer active:scale-95">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
                </svg>
              </button>
            </div>

            <div class="flex flex-col items-center gap-4 text-center">
              @if (userAvatar()) {
                <img
                  [src]="userAvatar()"
                  alt="Avatar Preview"
                  class="w-24 h-24 rounded-lg object-cover border border-slate-200 dark:border-white/10 shadow-lg"
                />
              } @else {
                <div class="w-24 h-24 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center text-3xl font-bold tracking-wider shadow-lg">
                  {{ userInitials() }}
                </div>
              }

              @if (avatarError()) {
                <p class="text-xs text-red-500 font-medium">{{ avatarError() }}</p>
              }

              <div class="flex items-center gap-3 w-full pt-1">
                <input
                  #fileInput
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  (change)="onAvatarFileSelected($event)"
                  class="hidden"
                />
                <button
                  type="button"
                  (click)="fileInput.click()"
                  class="flex-1 h-9 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer flex items-center justify-center gap-1.5 active:scale-95">
                  <app-lucide-icon name="camera" [size]="14"></app-lucide-icon>
                  <span>Upload Photo</span>
                </button>

                @if (userAvatar()) {
                  <button
                    type="button"
                    (click)="removeAvatar()"
                    class="h-9 px-3.5 rounded-md border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/60 text-xs font-semibold transition-all cursor-pointer active:scale-95">
                    Remove
                  </button>
                }
              </div>
            </div>

            <div class="pt-2 flex justify-end border-t border-slate-100 dark:border-white/5">
              <button
                type="button"
                (click)="isAvatarDialogOpen.set(false)"
                class="h-8.5 px-4 rounded-md bg-slate-100 dark:bg-white/10 hover:bg-slate-200 dark:hover:bg-white/20 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-all cursor-pointer active:scale-95">
                Done
              </button>
            </div>
          </div>
        </div>
      }

      <!-- CHANGE PASSWORD MODAL WITH RECTANGULAR GDS MODAL CLOSE BUTTON -->
      @if (isPasswordModalOpen()) {
        <div class="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150">
          <div class="w-full max-w-sm rounded-xl bg-white dark:bg-[#121315] border border-slate-200 dark:border-white/10 shadow-2xl p-6 space-y-4">
            <div class="flex items-center justify-between border-b border-slate-100 dark:border-white/5 pb-3">
              <h3 class="text-sm font-bold text-slate-900 dark:text-white font-heading">Change Password</h3>
              <button
                type="button"
                (click)="isPasswordModalOpen.set(false)"
                title="Close dialog"
                class="w-8 h-8 rounded-md bg-slate-100 dark:bg-white/10 hover:bg-slate-200 dark:hover:bg-white/20 text-slate-500 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-all flex items-center justify-center cursor-pointer active:scale-95">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
                </svg>
              </button>
            </div>

            <div class="space-y-3 text-xs">
              <div class="space-y-1">
                <label class="text-slate-600 dark:text-slate-400 font-medium block">Current Password</label>
                <input
                  type="password"
                  [(ngModel)]="currentPasswordInput"
                  placeholder="Enter current password"
                  class="w-full h-8 px-2.5 rounded-md border border-slate-300 dark:border-white/20 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-xs focus:outline-none focus:border-blue-500 shadow-2xs"
                />
              </div>

              <div class="space-y-1">
                <label class="text-slate-600 dark:text-slate-400 font-medium block">New Password</label>
                <input
                  type="password"
                  [(ngModel)]="newPasswordInput"
                  placeholder="At least 8 characters"
                  class="w-full h-8 px-2.5 rounded-md border border-slate-300 dark:border-white/20 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-xs focus:outline-none focus:border-blue-500 shadow-2xs"
                />
              </div>

              <div class="space-y-1">
                <label class="text-slate-600 dark:text-slate-400 font-medium block">Confirm New Password</label>
                <input
                  type="password"
                  [(ngModel)]="confirmPasswordInput"
                  placeholder="Confirm new password"
                  class="w-full h-8 px-2.5 rounded-md border border-slate-300 dark:border-white/20 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-xs focus:outline-none focus:border-blue-500 shadow-2xs"
                />
              </div>

              @if (passwordError()) {
                <p class="text-xs text-red-500 font-medium">{{ passwordError() }}</p>
              }

              @if (passwordSuccess()) {
                <p class="text-xs text-emerald-600 font-semibold">{{ passwordSuccess() }}</p>
              }
            </div>

            <div class="pt-2 flex justify-end gap-2 border-t border-slate-100 dark:border-white/5">
              <button
                type="button"
                (click)="isPasswordModalOpen.set(false)"
                class="h-8.5 px-3.5 rounded-md border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 text-xs font-semibold hover:bg-slate-100 dark:hover:bg-white/5 transition-all cursor-pointer active:scale-95">
                Cancel
              </button>
              <button
                type="button"
                (click)="savePassword()"
                [disabled]="isSavingPassword()"
                class="h-8.5 px-4 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer active:scale-95">
                {{ isSavingPassword() ? 'Updating...' : 'Update Password' }}
              </button>
            </div>
          </div>
        </div>
      }

    </div>
  `
})
export class ProfileHomeComponent implements OnInit {
  public ds: DashboardService;
  public cs: ContextService;
  private adminIpc: AdministrationIpc;

  constructor(
    ds?: DashboardService,
    cs?: ContextService,
    adminIpc?: AdministrationIpc,
    private router?: Router
  ) {
    this.ds = ds || (tryInject(DashboardService) as DashboardService);
    this.cs = cs || (tryInject(ContextService) as ContextService);
    this.adminIpc = adminIpc || (tryInject(AdministrationIpc) as AdministrationIpc);
    this.router = router || (tryInject(Router) as Router);
  }

  public activeTab = signal<ProfileTab>('overview');
  public isAvatarDialogOpen = signal<boolean>(false);
  public isPasswordModalOpen = signal<boolean>(false);

  // Identity signals
  public userEmail = signal<string>('aalok.ladwa@akaal.io');
  public userAvatar = signal<string | null>(null);
  public avatarError = signal<string | null>(null);

  // Edit Name State
  public isEditingName = signal<boolean>(false);
  public editNameInput = signal<string>('');
  public isSavingName = signal<boolean>(false);
  public nameError = signal<string | null>(null);

  // Edit Email State
  public isEditingEmail = signal<boolean>(false);
  public editEmailInput = signal<string>('');
  public isSavingEmail = signal<boolean>(false);
  public emailError = signal<string | null>(null);

  // Change Password State
  public currentPasswordInput = signal<string>('');
  public newPasswordInput = signal<string>('');
  public confirmPasswordInput = signal<string>('');
  public isSavingPassword = signal<boolean>(false);
  public passwordError = signal<string | null>(null);
  public passwordSuccess = signal<string | null>(null);

  // Dynamic user name from DashboardService
  public userName = computed(() => this.ds.userName());

  public userInitials = computed(() => {
    const name = this.userName().trim();
    if (!name) return 'U';
    const parts = name.split(/\s+/);
    return parts.length > 1
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : parts[0].substring(0, 2).toUpperCase();
  });

  public ngOnInit(): void {
    this.loadUserIdentity();
  }

  private async loadUserIdentity(): Promise<void> {
    try {
      if (this.adminIpc && typeof this.adminIpc.getCurrentAccount === 'function') {
        const res = await this.adminIpc.getCurrentAccount();
        if (res?.status === 'SUCCESS' && res.data) {
          const acc = res.data;
          if (acc.display_name || acc.name) {
            this.ds.userName.set(acc.display_name || acc.name);
          }
          if (acc.email) {
            this.userEmail.set(acc.email);
          }
          if (acc.avatar !== undefined) {
            this.userAvatar.set(acc.avatar || null);
          }
          return;
        }
      }
      if (this.adminIpc && typeof this.adminIpc.listUsers === 'function') {
        const res = await this.adminIpc.listUsers();
        if (res?.status === 'SUCCESS' && Array.isArray(res.data) && res.data.length > 0) {
          const user = res.data[0];
          if (user.display_name) {
            this.ds.userName.set(user.display_name);
          }
          if (user.email) {
            this.userEmail.set(user.email);
          }
        }
      }
    } catch {
      // Safe fallback to active defaults
    }
  }

  public setTab(tab: ProfileTab): void {
    this.activeTab.set(tab);
  }

  // Display Name Editing Actions
  public startEditName(): void {
    this.editNameInput.set(this.userName());
    this.nameError.set(null);
    this.isEditingName.set(true);
  }

  public cancelEditName(): void {
    this.isEditingName.set(false);
    this.nameError.set(null);
  }

  public async saveName(): Promise<void> {
    const val = this.editNameInput().trim();
    if (!val) {
      this.nameError.set('Display name cannot be empty');
      return;
    }
    this.isSavingName.set(true);
    this.nameError.set(null);

    try {
      if (this.adminIpc && typeof this.adminIpc.updateSelfProfile === 'function') {
        const res = await this.adminIpc.updateSelfProfile({ display_name: val });
        if (res?.status === 'ERROR') {
          this.nameError.set(res.error || 'Failed to update display name');
          return;
        }
      }
      this.ds.userName.set(val);
      this.isEditingName.set(false);
    } catch (err: any) {
      this.nameError.set(err?.message || 'Failed to update display name');
    } finally {
      this.isSavingName.set(false);
    }
  }

  // Email Editing Actions
  public startEditEmail(): void {
    this.editEmailInput.set(this.userEmail());
    this.emailError.set(null);
    this.isEditingEmail.set(true);
  }

  public cancelEditEmail(): void {
    this.isEditingEmail.set(false);
    this.emailError.set(null);
  }

  public async saveEmail(): Promise<void> {
    const val = this.editEmailInput().trim();
    if (!val || !val.includes('@')) {
      this.emailError.set('Please enter a valid email address');
      return;
    }
    this.isSavingEmail.set(true);
    this.emailError.set(null);

    try {
      if (this.adminIpc && typeof this.adminIpc.updateSelfProfile === 'function') {
        const res = await this.adminIpc.updateSelfProfile({ email: val });
        if (res?.status === 'ERROR') {
          this.emailError.set(res.error || 'Failed to update email address');
          return;
        }
      }
      this.userEmail.set(val);
      this.isEditingEmail.set(false);
    } catch (err: any) {
      this.emailError.set(err?.message || 'Failed to update email address');
    } finally {
      this.isSavingEmail.set(false);
    }
  }

  // Avatar Management Actions
  public onAvatarFileSelected(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (!target?.files || target.files.length === 0) return;

    const file = target.files[0];
    this.avatarError.set(null);

    if (file.size > 2 * 1024 * 1024) {
      this.avatarError.set('Image size must be under 2MB');
      return;
    }

    if (!file.type.startsWith('image/')) {
      this.avatarError.set('Only valid image files (PNG, JPEG, WEBP, GIF) are supported');
      return;
    }

    const reader = new FileReader();
    reader.onload = async () => {
      if (typeof reader.result === 'string') {
        const dataUrl = reader.result;
        try {
          if (this.adminIpc && typeof this.adminIpc.updateSelfAvatar === 'function') {
            const res = await this.adminIpc.updateSelfAvatar(dataUrl);
            if (res?.status === 'ERROR') {
              this.avatarError.set(res.error || 'Failed to save avatar image');
              return;
            }
          }
          this.userAvatar.set(dataUrl);
        } catch (err: any) {
          this.avatarError.set(err?.message || 'Failed to save avatar image');
        }
      }
    };
    reader.readAsDataURL(file);
  }

  public async removeAvatar(): Promise<void> {
    this.avatarError.set(null);
    try {
      if (this.adminIpc && typeof this.adminIpc.removeSelfAvatar === 'function') {
        const res = await this.adminIpc.removeSelfAvatar();
        if (res?.status === 'ERROR') {
          this.avatarError.set(res.error || 'Failed to remove avatar photo');
          return;
        }
      }
      this.userAvatar.set(null);
    } catch (err: any) {
      this.avatarError.set(err?.message || 'Failed to remove avatar photo');
    }
  }

  // Password Management Actions
  public async savePassword(): Promise<void> {
    const current = this.currentPasswordInput().trim();
    const newPass = this.newPasswordInput().trim();
    const confirm = this.confirmPasswordInput().trim();

    this.passwordError.set(null);
    this.passwordSuccess.set(null);

    if (!current) {
      this.passwordError.set('Current password is required');
      return;
    }
    if (newPass.length < 8) {
      this.passwordError.set('New password must be at least 8 characters long');
      return;
    }
    if (newPass !== confirm) {
      this.passwordError.set('New passwords do not match');
      return;
    }

    this.isSavingPassword.set(true);
    try {
      if (this.adminIpc && typeof this.adminIpc.changeSelfPassword === 'function') {
        const res = await this.adminIpc.changeSelfPassword(current, newPass);
        if (res?.status === 'ERROR') {
          this.passwordError.set(res.error || 'Failed to update password');
          return;
        }
      }
      this.passwordSuccess.set('Password updated successfully');
      this.currentPasswordInput.set('');
      this.newPasswordInput.set('');
      this.confirmPasswordInput.set('');
      setTimeout(() => {
        this.isPasswordModalOpen.set(false);
        this.passwordSuccess.set(null);
      }, 1500);
    } catch (err: any) {
      this.passwordError.set(err?.message || 'Failed to update password');
    } finally {
      this.isSavingPassword.set(false);
    }
  }

  public signOut(event?: Event): void {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (typeof window !== 'undefined') {
      if (typeof (window as any).runtime?.Quit === 'function') {
        (window as any).runtime.Quit();
      } else if (window.location) {
        window.location.reload();
      }
    }
  }
}
