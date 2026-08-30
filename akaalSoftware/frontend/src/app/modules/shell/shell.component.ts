import { Component, signal, inject, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DashboardService } from '../../core/services/dashboard.service';
import { ContextService, Organization, Workspace, Environment } from '../../core/services/context.service';
import { IpcService } from '../../core/services/ipc.service';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

interface CommandItem {
  id: string;
  label: string;
  category: string;
  icon: string;
  action: () => void;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col h-screen w-screen bg-slate-50 text-slate-900 font-sans overflow-hidden select-none">
      
      <!-- =============================================================== -->
      <!-- 1. FULL-WIDTH GLOBAL HEADER (TOP CHROME)                        -->
      <!-- =============================================================== -->
      <header class="h-16 w-full px-6 lg:px-8 bg-white border-b border-slate-200 flex items-center justify-between z-40 shrink-0 shadow-2xs">
        
        <!-- Left: Product Identity & Operational Context Switchers -->
        <div class="flex items-center gap-5 lg:gap-6">
          
          <!-- DevKros Brand Identity -->
          <div class="flex items-center gap-3 cursor-pointer" routerLink="/dashboard" (click)="closeAllDropdowns()">
            <div class="w-9 h-9 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-sm shadow-xs">
              DK
            </div>
            <div class="flex flex-col">
              <span class="text-base font-bold tracking-tight text-slate-900 leading-none">DEVKROS</span>
              <span class="text-[10px] text-slate-600 font-semibold tracking-wide">ENTERPRISE</span>
            </div>
          </div>

          <!-- Divider -->
          <div class="h-6 w-px bg-slate-200 hidden sm:block"></div>

          <!-- Operational Context Switchers (Desktop: 3 Independent Clean Selectors) -->
          <div class="hidden lg:flex items-center gap-2">
            
            <!-- 1. Organization Selector -->
            <div class="relative" (click)="$event.stopPropagation()">
              <button
                type="button"
                (click)="toggleOrgDropdown($event)"
                class="h-9 px-3 rounded-xl bg-slate-50 hover:bg-slate-100/90 border border-slate-200/80 hover:border-slate-300 flex items-center gap-2 text-slate-700 hover:text-slate-900 transition-all cursor-pointer shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                [class.bg-blue-50]="isOrgOpen()"
                [class.border-blue-300]="isOrgOpen()"
                [title]="cs.selectedOrg()?.name || 'Organization'">
                <app-lucide-icon name="building-2" [size]="15" class="text-slate-500"></app-lucide-icon>
                <span class="text-xs font-semibold max-w-[130px] truncate">
                  {{ cs.selectedOrg()?.name || 'Organization' }}
                </span>
                <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
              </button>

              @if (isOrgOpen()) {
                <div 
                  class="absolute left-0 mt-2 w-72 rounded-2xl bg-white border border-slate-200 shadow-xl p-3 flex flex-col gap-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                  <div class="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span class="text-xs font-bold text-slate-900 uppercase tracking-wider">Select Organization</span>
                    <button type="button" (click)="isOrgOpen.set(false)" class="p-1 text-slate-400 hover:text-slate-700 rounded-md">
                      <app-lucide-icon name="x" [size]="13"></app-lucide-icon>
                    </button>
                  </div>

                  @if (cs.organizations().length === 0) {
                    <div class="py-6 flex flex-col items-center justify-center text-center gap-2">
                      <app-lucide-icon name="building-2" [size]="24" class="text-slate-300"></app-lucide-icon>
                      <span class="text-xs font-semibold text-slate-700">Organization data unavailable</span>
                      <p class="text-[11px] text-slate-500 font-medium max-w-[200px]">No organization boundaries exposed by current engine contract.</p>
                    </div>
                  } @else {
                    <div class="flex flex-col gap-1 max-h-56 overflow-y-auto">
                      @for (org of cs.organizations(); track org.id) {
                        <button
                          type="button"
                          (click)="selectOrg(org)"
                          class="w-full text-left px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:text-blue-700 hover:bg-blue-50 transition-colors flex items-center justify-between cursor-pointer">
                          <span>{{ org.name }}</span>
                          @if (cs.selectedOrg()?.id === org.id) {
                            <app-lucide-icon name="check" [size]="14" class="text-blue-600"></app-lucide-icon>
                          }
                        </button>
                      }
                    </div>
                  }
                </div>
              }
            </div>

            <!-- 2. Workspace Selector -->
            <div class="relative" (click)="$event.stopPropagation()">
              <button
                type="button"
                (click)="toggleWorkspaceDropdown($event)"
                class="h-9 px-3 rounded-xl bg-slate-50 hover:bg-slate-100/90 border border-slate-200/80 hover:border-slate-300 flex items-center gap-2 text-slate-700 hover:text-slate-900 transition-all cursor-pointer shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                [class.bg-blue-50]="isWorkspaceOpen()"
                [class.border-blue-300]="isWorkspaceOpen()"
                [title]="cs.selectedWorkspace()?.name || 'Workspace'">
                <app-lucide-icon name="panels-top-left" [size]="15" class="text-slate-500"></app-lucide-icon>
                <span class="text-xs font-semibold max-w-[130px] truncate">
                  {{ cs.selectedWorkspace()?.name || 'Workspace' }}
                </span>
                <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
              </button>

              @if (isWorkspaceOpen()) {
                <div 
                  class="absolute left-0 mt-2 w-72 rounded-2xl bg-white border border-slate-200 shadow-xl p-3 flex flex-col gap-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                  <div class="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span class="text-xs font-bold text-slate-900 uppercase tracking-wider">Select Workspace</span>
                    <button type="button" (click)="isWorkspaceOpen.set(false)" class="p-1 text-slate-400 hover:text-slate-700 rounded-md">
                      <app-lucide-icon name="x" [size]="13"></app-lucide-icon>
                    </button>
                  </div>

                  @if (cs.availableWorkspacesForOrg().length === 0) {
                    <div class="py-6 flex flex-col items-center justify-center text-center gap-2">
                      <app-lucide-icon name="panels-top-left" [size]="24" class="text-slate-300"></app-lucide-icon>
                      <span class="text-xs font-semibold text-slate-700">Workspace data unavailable</span>
                      <p class="text-[11px] text-slate-500 font-medium max-w-[200px]">No workspace scopes configured.</p>
                    </div>
                  } @else {
                    <div class="flex flex-col gap-1 max-h-56 overflow-y-auto">
                      @for (ws of cs.availableWorkspacesForOrg(); track ws.id) {
                        <button
                          type="button"
                          (click)="selectWorkspace(ws)"
                          class="w-full text-left px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:text-blue-700 hover:bg-blue-50 transition-colors flex items-center justify-between cursor-pointer">
                          <span>{{ ws.name }}</span>
                          @if (cs.selectedWorkspace()?.id === ws.id) {
                            <app-lucide-icon name="check" [size]="14" class="text-blue-600"></app-lucide-icon>
                          }
                        </button>
                      }
                    </div>
                  }
                </div>
              }
            </div>

            <!-- 3. Environment Selector -->
            <div class="relative" (click)="$event.stopPropagation()">
              <button
                type="button"
                (click)="toggleEnvDropdown($event)"
                class="h-9 px-3 rounded-xl bg-slate-50 hover:bg-slate-100/90 border border-slate-200/80 hover:border-slate-300 flex items-center gap-2 text-slate-700 hover:text-slate-900 transition-all cursor-pointer shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                [class.bg-blue-50]="isEnvOpen()"
                [class.border-blue-300]="isEnvOpen()"
                [title]="cs.selectedEnvironment()?.name || 'Environment'">
                <app-lucide-icon name="server" [size]="15" class="text-slate-500"></app-lucide-icon>
                <span class="text-xs font-semibold max-w-[130px] truncate">
                  {{ cs.selectedEnvironment()?.name || 'Environment' }}
                </span>
                @if (cs.isProduction()) {
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                }
                <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
              </button>

              @if (isEnvOpen()) {
                <div 
                  class="absolute left-0 mt-2 w-72 rounded-2xl bg-white border border-slate-200 shadow-xl p-3 flex flex-col gap-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                  <div class="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span class="text-xs font-bold text-slate-900 uppercase tracking-wider">Select Environment</span>
                    <button type="button" (click)="isEnvOpen.set(false)" class="p-1 text-slate-400 hover:text-slate-700 rounded-md">
                      <app-lucide-icon name="x" [size]="13"></app-lucide-icon>
                    </button>
                  </div>

                  @if (cs.availableEnvironmentsForWorkspace().length === 0) {
                    <div class="py-6 flex flex-col items-center justify-center text-center gap-2">
                      <app-lucide-icon name="server" [size]="24" class="text-slate-300"></app-lucide-icon>
                      <span class="text-xs font-semibold text-slate-700">Environment data unavailable</span>
                      <p class="text-[11px] text-slate-500 font-medium max-w-[200px]">No environment tiers configured.</p>
                    </div>
                  } @else {
                    <div class="flex flex-col gap-1 max-h-56 overflow-y-auto">
                      @for (env of cs.availableEnvironmentsForWorkspace(); track env.id) {
                        <button
                          type="button"
                          (click)="selectEnvironment(env)"
                          class="w-full text-left px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:text-blue-700 hover:bg-blue-50 transition-colors flex items-center justify-between cursor-pointer">
                          <div class="flex items-center gap-2">
                            <span>{{ env.name }}</span>
                            @if (env.isProduction) {
                              <span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">PROD</span>
                            }
                          </div>
                          @if (cs.selectedEnvironment()?.id === env.id) {
                            <app-lucide-icon name="check" [size]="14" class="text-blue-600"></app-lucide-icon>
                          }
                        </button>
                      }
                    </div>
                  }
                </div>
              }
            </div>

          </div>

          <!-- Responsive Combined Context Selector (Mobile/Tablet) -->
          <div class="flex lg:hidden relative" (click)="$event.stopPropagation()">
            <button
              type="button"
              (click)="toggleCombinedContextDropdown($event)"
              class="h-9 px-3 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200/80 flex items-center gap-2 text-slate-700 text-xs font-semibold cursor-pointer shadow-2xs">
              <app-lucide-icon name="building-2" [size]="15" class="text-slate-500"></app-lucide-icon>
              <span>Context</span>
              <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
            </button>

            @if (isCombinedContextOpen()) {
              <div 
                class="absolute left-0 mt-2 w-80 rounded-2xl bg-white border border-slate-200 shadow-xl p-4 flex flex-col gap-3 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div class="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span class="text-xs font-bold text-slate-900 uppercase tracking-wider">Active Operational Context</span>
                  <button type="button" (click)="isCombinedContextOpen.set(false)" class="p-1 text-slate-400 hover:text-slate-700 rounded-md">
                    <app-lucide-icon name="x" [size]="13"></app-lucide-icon>
                  </button>
                </div>

                <div class="flex flex-col gap-2.5 text-xs font-medium">
                  <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-200/70 flex justify-between items-center">
                    <span class="text-slate-500">Organization:</span>
                    <span class="font-semibold text-slate-800">{{ cs.selectedOrg()?.name || 'Unavailable' }}</span>
                  </div>
                  <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-200/70 flex justify-between items-center">
                    <span class="text-slate-500">Workspace:</span>
                    <span class="font-semibold text-slate-800">{{ cs.selectedWorkspace()?.name || 'Unavailable' }}</span>
                  </div>
                  <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-200/70 flex justify-between items-center">
                    <span class="text-slate-500">Environment:</span>
                    <span class="font-semibold text-slate-800">{{ cs.selectedEnvironment()?.name || 'Unavailable' }}</span>
                  </div>
                </div>
              </div>
            }
          </div>

        </div>

        <!-- Right: Global Header Actions (Search / Bell / User) -->
        <div class="flex items-center gap-3.5">
          
          <!-- Search / Command Trigger -->
          <button
            type="button"
            (click)="openCommandPalette($event)"
            class="h-9 px-3.5 rounded-xl bg-slate-100/90 hover:bg-slate-100 border border-slate-200/80 flex items-center gap-3 text-slate-600 hover:text-slate-900 transition-all cursor-pointer group shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20">
            <app-lucide-icon name="search" [size]="15" class="text-slate-500 group-hover:text-slate-700"></app-lucide-icon>
            <span class="text-xs font-medium hidden sm:inline">Search or command...</span>
            <kbd class="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-[10px] font-semibold text-slate-600 shadow-2xs">Ctrl K</kbd>
          </button>

          <!-- Notification Bell -->
          <div class="relative" (click)="$event.stopPropagation()">
            <button
              type="button"
              (click)="toggleNotifications($event)"
              class="w-9 h-9 rounded-xl bg-white hover:bg-slate-100 border border-slate-200/80 flex items-center justify-center text-slate-700 hover:text-slate-900 transition-colors cursor-pointer relative shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              [class.bg-blue-50]="isNotificationsOpen()"
              [class.border-blue-300]="isNotificationsOpen()"
              title="Notification Center">
              <app-lucide-icon name="bell" [size]="17"></app-lucide-icon>
            </button>

            <!-- Interactive Notification Popover -->
            @if (isNotificationsOpen()) {
              <div 
                class="absolute right-0 mt-2 w-80 rounded-2xl bg-white border border-slate-200 shadow-xl p-4 flex flex-col gap-3 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div class="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div class="flex items-center gap-2">
                    <app-lucide-icon name="bell" [size]="16" class="text-blue-600"></app-lucide-icon>
                    <span class="text-sm font-bold text-slate-900">Notifications</span>
                  </div>
                  <button 
                    type="button" 
                    (click)="isNotificationsOpen.set(false)"
                    class="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer">
                    <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
                  </button>
                </div>

                <div class="py-6 flex flex-col items-center justify-center text-center gap-2">
                  <app-lucide-icon name="circle-check" [size]="28" class="text-slate-300"></app-lucide-icon>
                  <span class="text-xs font-semibold text-slate-800">No unread notifications</span>
                  <span class="text-[11px] text-slate-500 font-medium">All alerts and operational events are up to date.</span>
                </div>

                <div class="pt-2 border-t border-slate-100 flex justify-end">
                  <button
                    type="button"
                    (click)="isNotificationsOpen.set(false)"
                    class="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-blue-600 hover:bg-blue-50 transition-colors cursor-pointer">
                    Dismiss
                  </button>
                </div>
              </div>
            }
          </div>

          <!-- User Menu Trigger -->
          <div class="relative" (click)="$event.stopPropagation()">
            <button
              type="button"
              (click)="toggleUserMenu($event)"
              class="h-9 px-3 rounded-xl bg-white hover:bg-slate-100 border border-slate-200/80 flex items-center gap-2.5 text-slate-800 transition-colors cursor-pointer shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              [class.bg-blue-50]="isUserMenuOpen()"
              [class.border-blue-300]="isUserMenuOpen()">
              <div class="w-6 h-6 rounded-full bg-blue-600/10 border border-blue-600/30 text-blue-700 flex items-center justify-center text-xs font-bold">
                AL
              </div>
              <span class="text-xs font-semibold text-slate-900 hidden sm:inline">{{ ds.userName() }}</span>
              <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
            </button>

            <!-- Interactive User Menu Popover -->
            @if (isUserMenuOpen()) {
              <div 
                class="absolute right-0 mt-2 w-64 rounded-2xl bg-white border border-slate-200 shadow-xl p-2 flex flex-col gap-1 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div class="px-3 py-2.5 border-b border-slate-100">
                  <p class="text-xs font-bold text-slate-900 leading-none">{{ ds.userName() }} Ladwa</p>
                  <p class="text-[11px] text-slate-500 font-medium mt-1">Lead Migration Operator</p>
                </div>

                <div class="py-1 flex flex-col gap-0.5">
                  <a 
                    routerLink="/settings" 
                    (click)="isUserMenuOpen.set(false)" 
                    class="px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors flex items-center gap-2.5 cursor-pointer">
                    <app-lucide-icon name="user-round" [size]="14" class="text-slate-500"></app-lucide-icon>
                    <span>Profile &amp; Account</span>
                  </a>

                  <button 
                    type="button"
                    (click)="openHelpDialog($event)"
                    class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors flex items-center gap-2.5 cursor-pointer">
                    <app-lucide-icon name="file-text" [size]="14" class="text-slate-500"></app-lucide-icon>
                    <span>Help &amp; Documentation</span>
                  </button>

                  <button 
                    type="button"
                    (click)="openShortcutsDialog($event)"
                    class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors flex items-center justify-between cursor-pointer">
                    <div class="flex items-center gap-2.5">
                      <app-lucide-icon name="sliders" [size]="14" class="text-slate-500"></app-lucide-icon>
                      <span>Keyboard Shortcuts</span>
                    </div>
                    <kbd class="text-[10px] text-slate-500 font-semibold">Ctrl+/</kbd>
                  </button>

                  <button 
                    type="button"
                    (click)="openAboutDialog($event)"
                    class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors flex items-center gap-2.5 cursor-pointer">
                    <app-lucide-icon name="shield-check" [size]="14" class="text-slate-500"></app-lucide-icon>
                    <span>About DevKros</span>
                  </button>
                </div>

                <div class="border-t border-slate-100 my-0.5"></div>

                <a 
                  routerLink="/settings" 
                  (click)="isUserMenuOpen.set(false)" 
                  class="px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors flex items-center gap-2.5 cursor-pointer">
                  <app-lucide-icon name="settings" [size]="14" class="text-slate-500"></app-lucide-icon>
                  <span>Settings</span>
                </a>

                <div class="border-t border-slate-100 my-0.5"></div>

                <button 
                  type="button" 
                  (click)="isUserMenuOpen.set(false)" 
                  class="w-full text-left px-3 py-2 rounded-lg text-xs font-semibold text-rose-600 hover:bg-rose-50 transition-colors flex items-center gap-2.5 cursor-pointer">
                  <app-lucide-icon name="circle-x" [size]="14" class="text-rose-500"></app-lucide-icon>
                  <span>Lock Session</span>
                </button>
              </div>
            }
          </div>

        </div>
      </header>

      <!-- =============================================================== -->
      <!-- 2. MAIN LAYOUT: SIDEBAR + SCROLLABLE DASHBOARD VIEWPORT         -->
      <!-- =============================================================== -->
      <div class="flex flex-1 h-[calc(100vh-4rem)] w-full overflow-hidden" (click)="closeAllDropdowns()">
        
        <!-- Permanent Left Sidebar (Below Top Header) -->
        <aside 
          (click)="$event.stopPropagation()"
          class="h-full flex flex-col justify-between bg-white border-r border-slate-200 transition-all duration-300 ease-in-out shrink-0 z-30 shadow-xs"
          [class.w-64]="isExpanded()"
          [class.w-20]="!isExpanded()">
          
          <!-- Navigation Items (ONLY 5 PRIMARY MODULES) -->
          <div class="p-3 flex flex-col gap-2">
            <nav class="flex flex-col gap-1.5 pt-2">
              @for (item of primaryNavItems; track item.path) {
                <a
                  [routerLink]="item.path"
                  (click)="closeAllDropdowns()"
                  routerLinkActive="bg-blue-50 text-blue-700 font-semibold shadow-2xs border border-blue-200/60"
                  [routerLinkActiveOptions]="{ exact: item.path === '/dashboard' }"
                  class="flex items-center gap-3.5 px-3.5 py-3 rounded-xl text-sm text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-all group cursor-pointer relative"
                  [title]="!isExpanded() ? item.label : ''">
                  
                  <app-lucide-icon 
                    [name]="item.icon" 
                    [size]="20" 
                    class="text-slate-600 group-hover:text-slate-900">
                  </app-lucide-icon>

                  @if (isExpanded()) {
                    <span class="truncate font-medium">{{ item.label }}</span>
                  }
                </a>
              }
            </nav>
          </div>

          <!-- Bottom Section: Settings & Collapse Button -->
          <div class="p-3 flex flex-col gap-1.5 border-t border-slate-200">
            <a
              routerLink="/settings"
              (click)="closeAllDropdowns()"
              routerLinkActive="bg-blue-50 text-blue-700 font-semibold border border-blue-200/60"
              class="flex items-center gap-3.5 px-3.5 py-3 rounded-xl text-sm text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-all cursor-pointer"
              [title]="!isExpanded() ? 'Settings' : ''">
              <app-lucide-icon name="settings" [size]="20" class="text-slate-600"></app-lucide-icon>
              @if (isExpanded()) {
                <span class="truncate font-medium">Settings</span>
              }
            </a>

            <!-- Collapse / Expand Button Inside Sidebar -->
            <button
              type="button"
              (click)="toggleSidebar()"
              class="flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all cursor-pointer"
              [title]="isExpanded() ? 'Collapse Sidebar' : 'Expand Sidebar'">
              <app-lucide-icon [name]="isExpanded() ? 'panel-left-close' : 'panel-left-open'" [size]="20" class="text-slate-600"></app-lucide-icon>
              @if (isExpanded()) {
                <span class="truncate font-medium text-xs">Collapse</span>
              }
            </button>
          </div>

        </aside>

        <!-- Main Scrollable Content Canvas (Dynamic Fluid Width with Smooth Motion) -->
        <main class="flex-1 overflow-y-auto bg-slate-50 px-6 py-8 sm:px-8 lg:px-10 lg:py-9 transition-all duration-300 ease-in-out">
          <router-outlet></router-outlet>
        </main>

      </div>

      <!-- =============================================================== -->
      <!-- 3. COMMAND / SEARCH PALETTE DIALOG (CTRL + K)                   -->
      <!-- =============================================================== -->
      @if (isCommandPaletteOpen()) {
        <div 
          (click)="closeAllDropdowns()"
          class="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-slate-900/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div 
            class="w-full max-w-xl rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150"
            (click)="$event.stopPropagation()">
            
            <div class="p-4 border-b border-slate-200 flex items-center gap-3">
              <app-lucide-icon name="search" [size]="20" class="text-slate-400"></app-lucide-icon>
              <input
                type="text"
                [(ngModel)]="searchQuery"
                (keydown)="handleSearchKeydown($event)"
                placeholder="Type a command or jump to module..."
                class="w-full bg-transparent text-sm text-slate-900 placeholder-slate-400 focus:outline-none"
                autofocus />
              <kbd class="px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-[10px] text-slate-600 font-semibold">ESC</kbd>
            </div>

            <div class="max-h-80 overflow-y-auto p-2 flex flex-col gap-1">
              <span class="px-3 py-1 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Navigation</span>
              @for (cmd of filteredCommands(); track cmd.id) {
                <button
                  type="button"
                  (click)="executeCommand(cmd)"
                  class="w-full px-3 py-2.5 rounded-xl text-left text-xs font-semibold text-slate-700 hover:text-blue-700 hover:bg-blue-50 transition-colors flex items-center justify-between cursor-pointer group">
                  <div class="flex items-center gap-3">
                    <app-lucide-icon [name]="cmd.icon" [size]="16" class="text-slate-500 group-hover:text-blue-600"></app-lucide-icon>
                    <span>{{ cmd.label }}</span>
                  </div>
                  <span class="text-[10px] text-slate-500 group-hover:text-blue-500 font-semibold">{{ cmd.category }}</span>
                </button>
              }
            </div>

            <div class="p-3 bg-slate-50 border-t border-slate-200 text-right">
              <span class="text-[11px] text-slate-600 font-medium">Use &uarr;&darr; to navigate &bull; Enter to select</span>
            </div>
          </div>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 4. HELP & DOCUMENTATION DIALOG                                  -->
      <!-- =============================================================== -->
      @if (isHelpOpen()) {
        <div 
          (click)="closeAllDropdowns()"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div 
            class="w-full max-w-lg rounded-2xl bg-white border border-slate-200 shadow-2xl p-6 flex flex-col gap-4"
            (click)="$event.stopPropagation()">
            <div class="flex items-center justify-between pb-2 border-b border-slate-100">
              <div class="flex items-center gap-2.5">
                <app-lucide-icon name="file-text" [size]="20" class="text-blue-600"></app-lucide-icon>
                <h3 class="text-base font-bold text-slate-900">DevKros Help &amp; Documentation</h3>
              </div>
              <button type="button" (click)="isHelpOpen.set(false)" class="p-1 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100">
                <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
              </button>
            </div>
            <p class="text-xs text-slate-700 font-medium leading-relaxed">
              DevKros is an enterprise database migration and continuous replication infrastructure platform.
              Access comprehensive runbooks, execution modes (M1–M8), and four-eyes policy manuals under platform settings.
            </p>
            <div class="pt-2 border-t border-slate-100 flex justify-end">
              <button type="button" (click)="isHelpOpen.set(false)" class="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-xl hover:bg-blue-700 cursor-pointer">
                Close
              </button>
            </div>
          </div>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 5. ABOUT DIALOG                                                 -->
      <!-- =============================================================== -->
      @if (isAboutOpen()) {
        <div 
          (click)="closeAllDropdowns()"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div 
            class="w-full max-w-md rounded-2xl bg-white border border-slate-200 shadow-2xl p-6 flex flex-col items-center text-center gap-3"
            (click)="$event.stopPropagation()">
            <div class="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-bold text-base shadow-md">
              DK
            </div>
            <h3 class="text-base font-bold text-slate-900">DevKros Enterprise Platform</h3>
            <span class="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold">
              v1.0.0-PROD • Wails Native Shell
            </span>
            <p class="text-xs text-slate-600 font-medium">
              Direct Named Pipe IPC Bridge • Non-destructive Client Lifecycle
            </p>
            <div class="pt-3 w-full border-t border-slate-100 flex justify-center">
              <button type="button" (click)="isAboutOpen.set(false)" class="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-xl cursor-pointer">
                Done
              </button>
            </div>
          </div>
        </div>
      }

    </div>
  `
})
export class ShellComponent {
  public ds = inject(DashboardService);
  public cs = inject(ContextService);
  public ipc = inject(IpcService);
  private router = inject(Router);

  public isExpanded = signal<boolean>(true);
  
  // Context dropdowns
  public isOrgOpen = signal<boolean>(false);
  public isWorkspaceOpen = signal<boolean>(false);
  public isEnvOpen = signal<boolean>(false);
  public isCombinedContextOpen = signal<boolean>(false);

  // Global action dialogs
  public isNotificationsOpen = signal<boolean>(false);
  public isUserMenuOpen = signal<boolean>(false);
  public isCommandPaletteOpen = signal<boolean>(false);
  public isHelpOpen = signal<boolean>(false);
  public isAboutOpen = signal<boolean>(false);
  public searchQuery = '';

  public primaryNavItems: NavItem[] = [
    { path: '/dashboard', label: 'Dashboard', icon: 'layout-dashboard' },
    { path: '/migration', label: 'Migration', icon: 'arrow-left-right' },
    { path: '/monitoring', label: 'Monitoring', icon: 'activity' },
    { path: '/reports', label: 'Reports', icon: 'file-text' },
    { path: '/administration', label: 'Administration', icon: 'shield' },
  ];

  public commands: CommandItem[] = [
    { id: '1', label: 'Go to Dashboard', category: 'Module', icon: 'layout-dashboard', action: () => this.navigate('/dashboard') },
    { id: '2', label: 'Go to Migration Portfolio', category: 'Module', icon: 'arrow-left-right', action: () => this.navigate('/migration') },
    { id: '3', label: 'Go to Monitoring Telemetry', category: 'Module', icon: 'activity', action: () => this.navigate('/monitoring') },
    { id: '4', label: 'Go to Reports & Audits', category: 'Module', icon: 'file-text', action: () => this.navigate('/reports') },
    { id: '5', label: 'Go to Administration', category: 'Module', icon: 'shield', action: () => this.navigate('/administration') },
    { id: '6', label: 'Go to Platform Settings', category: 'Module', icon: 'settings', action: () => this.navigate('/settings') },
    { id: '7', label: 'Refresh Telemetry', category: 'Action', icon: 'refresh-cw', action: () => { this.ds.refreshDashboard(); this.isCommandPaletteOpen.set(false); } },
  ];

  public filteredCommands(): CommandItem[] {
    if (!this.searchQuery.trim()) return this.commands;
    const q = this.searchQuery.toLowerCase();
    return this.commands.filter(c => c.label.toLowerCase().includes(q) || c.category.toLowerCase().includes(q));
  }

  @HostListener('window:keydown', ['$event'])
  public handleGlobalKeydown(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      this.openCommandPalette();
    } else if (event.key === 'Escape') {
      this.closeAllDropdowns();
    }
  }

  @HostListener('document:click', ['$event'])
  public handleDocumentClick(): void {
    this.closeAllDropdowns();
  }

  public closeAllDropdowns(): void {
    this.isOrgOpen.set(false);
    this.isWorkspaceOpen.set(false);
    this.isEnvOpen.set(false);
    this.isCombinedContextOpen.set(false);
    this.isCommandPaletteOpen.set(false);
    this.isNotificationsOpen.set(false);
    this.isUserMenuOpen.set(false);
    this.isHelpOpen.set(false);
    this.isAboutOpen.set(false);
  }

  public toggleOrgDropdown(event?: MouseEvent): void {
    event?.stopPropagation();
    const next = !this.isOrgOpen();
    this.closeAllDropdowns();
    this.isOrgOpen.set(next);
  }

  public toggleWorkspaceDropdown(event?: MouseEvent): void {
    event?.stopPropagation();
    const next = !this.isWorkspaceOpen();
    this.closeAllDropdowns();
    this.isWorkspaceOpen.set(next);
  }

  public toggleEnvDropdown(event?: MouseEvent): void {
    event?.stopPropagation();
    const next = !this.isEnvOpen();
    this.closeAllDropdowns();
    this.isEnvOpen.set(next);
  }

  public toggleCombinedContextDropdown(event?: MouseEvent): void {
    event?.stopPropagation();
    const next = !this.isCombinedContextOpen();
    this.closeAllDropdowns();
    this.isCombinedContextOpen.set(next);
  }

  public toggleNotifications(event?: MouseEvent): void {
    event?.stopPropagation();
    const next = !this.isNotificationsOpen();
    this.closeAllDropdowns();
    this.isNotificationsOpen.set(next);
  }

  public toggleUserMenu(event?: MouseEvent): void {
    event?.stopPropagation();
    const next = !this.isUserMenuOpen();
    this.closeAllDropdowns();
    this.isUserMenuOpen.set(next);
  }

  public openCommandPalette(event?: MouseEvent): void {
    event?.stopPropagation();
    this.closeAllDropdowns();
    this.searchQuery = '';
    this.isCommandPaletteOpen.set(true);
  }

  public openHelpDialog(event?: MouseEvent): void {
    event?.stopPropagation();
    this.closeAllDropdowns();
    this.isHelpOpen.set(true);
  }

  public openShortcutsDialog(event?: MouseEvent): void {
    event?.stopPropagation();
    this.closeAllDropdowns();
    this.openCommandPalette();
  }

  public openAboutDialog(event?: MouseEvent): void {
    event?.stopPropagation();
    this.closeAllDropdowns();
    this.isAboutOpen.set(true);
  }

  public selectOrg(org: Organization): void {
    this.cs.selectOrganization(org);
    this.isOrgOpen.set(false);
  }

  public selectWorkspace(ws: Workspace): void {
    this.cs.selectWorkspace(ws);
    this.isWorkspaceOpen.set(false);
  }

  public selectEnvironment(env: Environment): void {
    this.cs.selectEnvironment(env);
    this.isEnvOpen.set(false);
  }

  public toggleSidebar(): void {
    this.isExpanded.update(v => !v);
  }

  public executeCommand(cmd: CommandItem): void {
    cmd.action();
    this.isCommandPaletteOpen.set(false);
  }

  public handleSearchKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      const items = this.filteredCommands();
      if (items.length > 0) {
        this.executeCommand(items[0]);
      }
    }
  }

  private navigate(path: string): void {
    this.router.navigate([path]);
    this.isCommandPaletteOpen.set(false);
  }
}
