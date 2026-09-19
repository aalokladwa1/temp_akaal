import { Component, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { DashboardService } from '../../core/services/dashboard.service';
import { ContextService } from '../../core/services/context.service';
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
  imports: [CommonModule, RouterLink, LucideIconComponent],
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
            Personal identity, active workspace context, security posture, and runtime sessions.
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
          <!-- AVATAR WITH DYNAMIC INITIALS AND CAPABILITY-AWARE EDIT AFFORDANCE -->
          <div class="relative group shrink-0">
            <div class="w-16 h-16 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center text-xl font-bold tracking-wider shadow-md">
              {{ userInitials() }}
            </div>
            <button
              type="button"
              (click)="isAvatarDialogOpen.set(true)"
              title="Change profile photo"
              class="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors shadow-2xs cursor-pointer">
              <app-lucide-icon name="camera" [size]="12"></app-lucide-icon>
            </button>
          </div>
          
          <div class="space-y-1">
            <div class="flex items-center gap-3 flex-wrap">
              <h2 class="text-lg font-bold text-slate-900 dark:text-white leading-none">{{ userName() }}</h2>
            </div>
            <p class="text-xs text-slate-500 dark:text-slate-400 font-medium">
              Active Desktop Principal
            </p>
          </div>
        </div>

        <div class="flex items-center gap-3 w-full md:w-auto border-t md:border-t-0 pt-4 md:pt-0 border-slate-100 dark:border-white/5">
          <a
            routerLink="/settings"
            class="h-9 px-3.5 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 hover:bg-slate-50 dark:hover:bg-white/10 text-slate-700 dark:text-slate-200 text-xs font-semibold shadow-2xs transition-colors flex items-center gap-2 cursor-pointer">
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
          <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300 font-bold">
            1
          </span>
        </button>
      </div>

      <!-- TAB 1: OVERVIEW & ACCESS TRANSPARENCY -->
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
                
                <!-- DISPLAY NAME -->
                <div class="p-3 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 space-y-1">
                  <span class="text-slate-500 dark:text-slate-400 font-medium block">Display Name</span>
                  <span class="font-bold text-slate-900 dark:text-white block">{{ userName() }}</span>
                </div>

                <!-- IDENTITY CONTEXT -->
                <div class="p-3 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 space-y-1">
                  <span class="text-slate-500 dark:text-slate-400 font-medium block">Identity Context</span>
                  <span class="font-semibold text-slate-900 dark:text-white block">Desktop Standalone Runtime</span>
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
                      <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">PROD</span>
                    }
                  </div>
                </div>
              </div>

              <p class="text-[11px] text-slate-400 font-medium">
                Context switching is managed via the global header dropdown.
              </p>
            </div>

          </div>

          <!-- RIGHT 1 COL: ACCESS INFORMATION -->
          <div class="space-y-6">
            <div class="rounded-xl bg-white dark:bg-[#0c0d0e] border border-slate-200 dark:border-white/10 p-5 space-y-4 shadow-2xs">
              <div class="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/5">
                <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-heading">
                  My Access
                </h3>
              </div>

              <div class="p-3 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/60 dark:border-white/5 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Assigned roles and entitlement policies are managed by your organization administrators under Administration &gt; People &amp; Access.
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
                Security Posture
              </h3>
            </div>

            <div class="p-3.5 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Account authentication and credential policies are governed by your enterprise identity configuration.
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              <!-- PASSWORD SUMMARY -->
              <div class="p-4 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 space-y-1">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="key" [size]="15" class="text-slate-600 dark:text-slate-400"></app-lucide-icon>
                  <span class="text-xs font-bold text-slate-900 dark:text-white">Account Password</span>
                </div>
                <p class="text-[11px] text-slate-500 dark:text-slate-400">
                  Authentication is federated via your Enterprise Identity Provider.
                </p>
              </div>

              <!-- MFA SUMMARY -->
              <div class="p-4 rounded-lg bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 space-y-1">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="shield-check" [size]="15" class="text-emerald-600 dark:text-emerald-400"></app-lucide-icon>
                  <span class="text-xs font-bold text-slate-900 dark:text-white">Multi-Factor Authentication</span>
                </div>
                <p class="text-[11px] text-slate-500 dark:text-slate-400">
                  Enforced by corporate security policy.
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
                  Active Authenticated Session
                </h3>
                <p class="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                  Current desktop runtime session bound to your local workstation.
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
                    <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-blue-100 dark:bg-blue-900/60 text-blue-800 dark:text-blue-300">THIS DEVICE</span>
                  </div>
                  <p class="text-[11px] text-slate-500 dark:text-slate-400">
                    Desktop Application (Wails Runtime) &bull; Local IPC Bridge &bull; Status: Active
                  </p>
                </div>
              </div>

              <button
                type="button"
                (click)="signOut($event)"
                class="h-8 px-3 rounded-md bg-white dark:bg-white/10 border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/20 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 shrink-0">
                <app-lucide-icon name="log-out" [size]="13" class="text-slate-400"></app-lucide-icon>
                <span>Sign Out</span>
              </button>
            </div>

            <!-- INFORMATIONAL CAPABILITY NOTICE -->
            <div class="p-3 rounded-lg bg-slate-100 dark:bg-white/5 border border-slate-200/60 dark:border-white/5 text-xs text-slate-500 dark:text-slate-400 flex items-center gap-2">
              <app-lucide-icon name="info" [size]="14" class="text-slate-400 shrink-0"></app-lucide-icon>
              <span>Remote session tracking and revocation are not active in desktop standalone runtime.</span>
            </div>
          </div>
        </div>
      }

      <!-- CAPABILITY-AWARE AVATAR DIALOG -->
      @if (isAvatarDialogOpen()) {
        <div class="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150">
          <div class="w-full max-w-sm rounded-xl bg-white dark:bg-[#121315] border border-slate-200 dark:border-white/10 shadow-2xl p-6 space-y-5">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-bold text-slate-900 dark:text-white font-heading">Profile Photo</h3>
              <button
                type="button"
                (click)="isAvatarDialogOpen.set(false)"
                class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1">
                <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
              </button>
            </div>

            <div class="flex flex-col items-center gap-3 text-center">
              <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center text-2xl font-bold tracking-wider shadow-lg">
                {{ userInitials() }}
              </div>
              <p class="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Custom profile photo upload is not active in this desktop identity context. Display initials are dynamically generated from your active account name.
              </p>
            </div>

            <div class="pt-2 flex justify-end">
              <button
                type="button"
                (click)="isAvatarDialogOpen.set(false)"
                class="h-8 px-4 rounded-lg bg-slate-100 dark:bg-white/10 hover:bg-slate-200 dark:hover:bg-white/20 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-colors cursor-pointer">
                Close
              </button>
            </div>
          </div>
        </div>
      }

    </div>
  `
})
export class ProfileHomeComponent {
  public ds: DashboardService;
  public cs: ContextService;

  constructor(
    ds?: DashboardService,
    cs?: ContextService,
    private router?: Router
  ) {
    this.ds = ds || (tryInject(DashboardService) as DashboardService);
    this.cs = cs || (tryInject(ContextService) as ContextService);
    this.router = router || (tryInject(Router) as Router);
  }

  public activeTab = signal<ProfileTab>('overview');
  public isAvatarDialogOpen = signal<boolean>(false);

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

  public setTab(tab: ProfileTab): void {
    this.activeTab.set(tab);
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
