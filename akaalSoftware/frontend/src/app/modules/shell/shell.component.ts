import { Component, signal, inject, HostListener, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DashboardService } from '../../core/services/dashboard.service';
import { ContextService, Organization, Workspace, Environment } from '../../core/services/context.service';
import { IpcService } from '../../core/services/ipc.service';
import { MigrationUiService } from '../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

interface CommandItem {
  id: string;
  label: string;
  category: 'Module' | 'Action';
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

          <!-- Operational Context Switchers (Desktop: 3 Compact Popovers) -->
          <div class="hidden lg:flex items-center gap-2">
            
            <!-- 1. Organization Selector -->
            <div class="relative" (click)="$event.stopPropagation()">
              <button
                type="button"
                (click)="toggleOrgDropdown($event)"
                class="h-9 px-3 rounded-lg bg-slate-50 hover:bg-slate-100/90 border border-slate-200 hover:border-slate-300 flex items-center gap-2 text-slate-700 hover:text-slate-900 transition-all cursor-pointer shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                [class.bg-blue-50]="isOrgOpen()"
                [class.border-blue-300]="isOrgOpen()"
                [title]="cs.selectedOrg()?.name || 'Organization'">
                <app-lucide-icon name="building-2" [size]="15" class="text-slate-500"></app-lucide-icon>
                <span class="text-xs font-medium max-w-[130px] truncate">
                  {{ cs.selectedOrg()?.name || 'Organization' }}
                </span>
                <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
              </button>

              @if (isOrgOpen()) {
                <div 
                  class="absolute left-0 mt-1.5 origin-top-left w-64 rounded-xl bg-white border border-slate-200 shadow-xl p-1.5 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-150">
                  @if (cs.organizations().length === 0) {
                    <div class="p-3 text-left flex flex-col gap-0.5">
                      <span class="text-xs font-semibold text-slate-800">No organizations configured</span>
                      <span class="text-[11px] text-slate-500 font-medium">Contact administrator to grant access</span>
                    </div>
                  } @else {
                    <div class="flex flex-col gap-0.5 max-h-56 overflow-y-auto">
                      @for (org of cs.organizations(); track org.id) {
                        <button
                          type="button"
                          (click)="selectOrg(org)"
                          class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                          [class.bg-blue-50]="cs.selectedOrg()?.id === org.id"
                          [class.text-blue-700]="cs.selectedOrg()?.id === org.id">
                          <span class="truncate">{{ org.name }}</span>
                          @if (cs.selectedOrg()?.id === org.id) {
                            <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
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
                class="h-9 px-3 rounded-lg bg-slate-50 hover:bg-slate-100/90 border border-slate-200 hover:border-slate-300 flex items-center gap-2 text-slate-700 hover:text-slate-900 transition-all cursor-pointer shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                [class.bg-blue-50]="isWorkspaceOpen()"
                [class.border-blue-300]="isWorkspaceOpen()"
                [title]="cs.selectedWorkspace()?.name || 'Workspace'">
                <app-lucide-icon name="panels-top-left" [size]="15" class="text-slate-500"></app-lucide-icon>
                <span class="text-xs font-medium max-w-[130px] truncate">
                  {{ cs.selectedWorkspace()?.name || 'Workspace' }}
                </span>
                <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
              </button>

              @if (isWorkspaceOpen()) {
                <div 
                  class="absolute left-0 mt-1.5 origin-top-left w-64 rounded-xl bg-white border border-slate-200 shadow-xl p-1.5 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-150">
                  @if (cs.availableWorkspacesForOrg().length === 0) {
                    <div class="p-3 text-left flex flex-col gap-0.5">
                      <span class="text-xs font-semibold text-slate-800">No workspaces configured</span>
                      <span class="text-[11px] text-slate-500 font-medium">No workspaces in current scope</span>
                    </div>
                  } @else {
                    <div class="flex flex-col gap-0.5 max-h-56 overflow-y-auto">
                      @for (ws of cs.availableWorkspacesForOrg(); track ws.id) {
                        <button
                          type="button"
                          (click)="selectWorkspace(ws)"
                          class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                          [class.bg-blue-50]="cs.selectedWorkspace()?.id === ws.id"
                          [class.text-blue-700]="cs.selectedWorkspace()?.id === ws.id">
                          <span class="truncate">{{ ws.name }}</span>
                          @if (cs.selectedWorkspace()?.id === ws.id) {
                            <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
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
                class="h-9 px-3 rounded-lg bg-slate-50 hover:bg-slate-100/90 border border-slate-200 hover:border-slate-300 flex items-center gap-2 text-slate-700 hover:text-slate-900 transition-all cursor-pointer shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                [class.bg-blue-50]="isEnvOpen()"
                [class.border-blue-300]="isEnvOpen()"
                [title]="cs.selectedEnvironment()?.name || 'Environment'">
                <app-lucide-icon name="server" [size]="15" class="text-slate-500"></app-lucide-icon>
                <span class="text-xs font-medium max-w-[130px] truncate">
                  {{ cs.selectedEnvironment()?.name || 'Environment' }}
                </span>
                @if (cs.isProduction()) {
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                }
                <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
              </button>

              @if (isEnvOpen()) {
                <div 
                  class="absolute left-0 mt-1.5 origin-top-left w-64 rounded-xl bg-white border border-slate-200 shadow-xl p-1.5 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-150">
                  @if (cs.availableEnvironmentsForWorkspace().length === 0) {
                    <div class="p-3 text-left flex flex-col gap-0.5">
                      <span class="text-xs font-semibold text-slate-800">No environments configured</span>
                      <span class="text-[11px] text-slate-500 font-medium">No environment tiers available</span>
                    </div>
                  } @else {
                    <div class="flex flex-col gap-0.5 max-h-56 overflow-y-auto">
                      @for (env of cs.availableEnvironmentsForWorkspace(); track env.id) {
                        <button
                          type="button"
                          (click)="selectEnvironment(env)"
                          class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                          [class.bg-blue-50]="cs.selectedEnvironment()?.id === env.id"
                          [class.text-blue-700]="cs.selectedEnvironment()?.id === env.id">
                          <div class="flex items-center gap-2">
                            <span>{{ env.name }}</span>
                            @if (env.isProduction) {
                              <span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">PROD</span>
                            }
                          </div>
                          @if (cs.selectedEnvironment()?.id === env.id) {
                            <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
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
              class="h-9 px-3 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 flex items-center gap-2 text-slate-700 text-xs font-medium cursor-pointer shadow-2xs">
              <app-lucide-icon name="building-2" [size]="15" class="text-slate-500"></app-lucide-icon>
              <span>Context</span>
              <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
            </button>

            @if (isCombinedContextOpen()) {
              <div 
                class="absolute left-0 mt-1.5 w-72 rounded-xl bg-white border border-slate-200 shadow-xl p-3 flex flex-col gap-2.5 z-50 animate-in fade-in zoom-in-95 duration-150">
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider">Active Context</span>
                <div class="flex flex-col gap-1.5 text-xs font-medium">
                  <div class="p-2 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center">
                    <span class="text-slate-500">Org:</span>
                    <span class="font-semibold text-slate-800">{{ cs.selectedOrg()?.name || 'Unavailable' }}</span>
                  </div>
                  <div class="p-2 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center">
                    <span class="text-slate-500">Workspace:</span>
                    <span class="font-semibold text-slate-800">{{ cs.selectedWorkspace()?.name || 'Unavailable' }}</span>
                  </div>
                  <div class="p-2 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center">
                    <span class="text-slate-500">Environment:</span>
                    <span class="font-semibold text-slate-800">{{ cs.selectedEnvironment()?.name || 'Unavailable' }}</span>
                  </div>
                </div>
              </div>
            }
          </div>

        </div>

        <!-- Right: Global Header Actions (Search / Bell / User) -->
        <div class="flex items-center gap-3">
          
          <!-- Search / Command Trigger -->
          <button
            type="button"
            (click)="openCommandPalette($event)"
            class="h-9 px-3 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 flex items-center gap-3 text-slate-600 hover:text-slate-900 transition-colors cursor-pointer group shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20">
            <app-lucide-icon name="search" [size]="15" class="text-slate-400 group-hover:text-slate-600"></app-lucide-icon>
            <span class="text-xs font-medium hidden sm:inline">Search or command...</span>
            <kbd class="px-1.5 py-0.5 rounded bg-white border border-slate-200 text-[10px] font-mono font-medium text-slate-500">Ctrl K</kbd>
          </button>

          <!-- Notification Bell -->
          <div class="relative" (click)="$event.stopPropagation()">
            <button
              type="button"
              (click)="toggleNotifications($event)"
              class="w-9 h-9 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-700 hover:text-slate-900 transition-colors cursor-pointer relative shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              [class.bg-blue-50]="isNotificationsOpen()"
              [class.border-blue-300]="isNotificationsOpen()"
              title="Notification Center">
              <app-lucide-icon name="bell" [size]="16"></app-lucide-icon>
            </button>

            <!-- Compact Notification Popover -->
            @if (isNotificationsOpen()) {
              <div 
                class="absolute right-0 mt-1.5 w-80 rounded-xl bg-white border border-slate-200 shadow-xl p-0 flex flex-col z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
                <div class="px-4 py-2.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
                  <span class="text-xs font-bold text-slate-900 font-heading">Notifications</span>
                  <button 
                    type="button" 
                    (click)="isNotificationsOpen.set(false)"
                    class="text-[11px] text-blue-600 hover:text-blue-700 font-semibold cursor-pointer select-none">
                    Mark all as read
                  </button>
                </div>

                <div class="py-6 px-4 flex flex-col items-center justify-center text-center gap-1.5">
                  <div class="w-8 h-8 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400">
                    <app-lucide-icon name="bell" [size]="15"></app-lucide-icon>
                  </div>
                  <span class="text-xs font-semibold text-slate-800">No unread notifications</span>
                  <p class="text-[11px] text-slate-500 font-medium">All operational events and barriers are up to date.</p>
                </div>
              </div>
            }
          </div>

          <!-- User Menu Trigger -->
          <div class="relative" (click)="$event.stopPropagation()">
            <button
              type="button"
              (click)="toggleUserMenu($event)"
              class="h-9 px-3 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 flex items-center gap-2.5 text-slate-800 transition-colors cursor-pointer shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              [class.bg-blue-50]="isUserMenuOpen()"
              [class.border-blue-300]="isUserMenuOpen()">
              <div class="w-6 h-6 rounded-md bg-blue-600/10 border border-blue-600/30 text-blue-700 flex items-center justify-center text-xs font-bold">
                AL
              </div>
              <span class="text-xs font-semibold text-slate-900 hidden sm:inline">{{ ds.userName() }}</span>
              <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400"></app-lucide-icon>
            </button>

            <!-- Compact User Menu Popover -->
            @if (isUserMenuOpen()) {
              <div 
                class="absolute right-0 mt-1.5 w-60 rounded-xl bg-white border border-slate-200 shadow-xl p-1.5 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div class="px-3 py-2 border-b border-slate-200 mb-1">
                  <p class="text-xs font-bold text-slate-900 leading-none">{{ ds.userName() }} Ladwa</p>
                  <p class="text-[11px] text-slate-500 font-medium mt-1">Lead Migration Operator</p>
                </div>

                <div class="flex flex-col gap-0.5">
                  <a 
                    routerLink="/settings" 
                    (click)="isUserMenuOpen.set(false)" 
                    class="px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2.5 cursor-pointer">
                    <app-lucide-icon name="user-round" [size]="14" class="text-slate-500"></app-lucide-icon>
                    <span>Profile &amp; Account</span>
                  </a>

                  <button 
                    type="button" 
                    (click)="openHelpDialog($event)"
                    class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2.5 cursor-pointer">
                    <app-lucide-icon name="file-text" [size]="14" class="text-slate-500"></app-lucide-icon>
                    <span>Help &amp; Documentation</span>
                  </button>

                  <button 
                    type="button" 
                    (click)="openShortcutsDialog($event)"
                    class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer">
                    <div class="flex items-center gap-2.5">
                      <app-lucide-icon name="sliders" [size]="14" class="text-slate-500"></app-lucide-icon>
                      <span>Keyboard Shortcuts</span>
                    </div>
                    <kbd class="px-1.5 py-0.5 text-[10px] bg-slate-100 border border-slate-200 rounded font-mono text-slate-500">Ctrl+/</kbd>
                  </button>

                  <button 
                    type="button" 
                    (click)="openAboutDialog($event)"
                    class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2.5 cursor-pointer">
                    <app-lucide-icon name="shield-check" [size]="14" class="text-slate-500"></app-lucide-icon>
                    <span>About DevKros</span>
                  </button>
                </div>

                <div class="border-t border-slate-200 my-1 mx-1"></div>

                <a 
                  routerLink="/settings" 
                  (click)="isUserMenuOpen.set(false)" 
                  class="px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2.5 cursor-pointer">
                  <app-lucide-icon name="settings" [size]="14" class="text-slate-500"></app-lucide-icon>
                  <span>Settings</span>
                </a>

                <div class="border-t border-slate-200 my-1 mx-1"></div>

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
            <nav class="flex flex-col gap-1 pt-1">
              @for (item of primaryNavItems; track item.path) {
                <a
                  [routerLink]="item.path"
                  (click)="closeAllDropdowns()"
                  routerLinkActive="bg-blue-50 text-blue-700 font-semibold border-blue-200/80 shadow-2xs"
                  [routerLinkActiveOptions]="{ exact: item.path === '/dashboard' }"
                  class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100/80 border border-transparent transition-colors group cursor-pointer relative select-none w-full"
                  [title]="!isExpanded() ? item.label : ''">
                  
                  <app-lucide-icon 
                    [name]="item.icon" 
                    [size]="18" 
                    class="text-slate-600 group-hover:text-slate-900 shrink-0">
                  </app-lucide-icon>

                  @if (isExpanded()) {
                    <span class="truncate font-medium">{{ item.label }}</span>
                  }
                </a>
              }
            </nav>
          </div>

          <!-- Bottom Section: Settings & Collapse Button -->
          <div class="p-3 flex flex-col gap-1 border-t border-slate-200">
            <a
              routerLink="/settings"
              (click)="closeAllDropdowns()"
              routerLinkActive="bg-blue-50 text-blue-700 font-semibold border-blue-200/80 shadow-2xs"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100/80 border border-transparent transition-colors cursor-pointer w-full select-none"
              [title]="!isExpanded() ? 'Settings' : ''">
              <app-lucide-icon name="settings" [size]="18" class="text-slate-600 shrink-0"></app-lucide-icon>
              @if (isExpanded()) {
                <span class="truncate font-medium">Settings</span>
              }
            </a>

            <!-- Collapse / Expand Button Inside Sidebar -->
            <button
              type="button"
              (click)="toggleSidebar()"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 border border-transparent transition-colors cursor-pointer w-full select-none"
              [title]="isExpanded() ? 'Collapse Sidebar' : 'Expand Sidebar'">
              <app-lucide-icon 
                [name]="isExpanded() ? 'panel-left-close' : 'panel-left-open'" 
                [size]="18" 
                class="text-slate-500 shrink-0">
              </app-lucide-icon>
              @if (isExpanded()) {
                <span class="truncate font-medium">Collapse</span>
              }
            </button>
          </div>

        </aside>

        <!-- Main Body Canvas (Single Viewport) -->
        <main class="flex-1 h-full overflow-y-auto bg-slate-50/50 p-6 lg:p-9 relative">
          <router-outlet></router-outlet>
        </main>

      </div>

      <!-- =============================================================== -->
      <!-- 3. COMMAND PALETTE (CTRL+K COMPACT MODAL)                       -->
      <!-- =============================================================== -->
      @if (isCommandPaletteOpen()) {
        <div 
          (click)="closeAllDropdowns()"
          class="fixed inset-0 z-50 flex items-start justify-center pt-24 sm:pt-32 bg-slate-900/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          
          <div 
            class="w-full max-w-xl rounded-xl bg-white border border-slate-200 shadow-2xl overflow-hidden flex flex-col"
            (click)="$event.stopPropagation()">
            
            <!-- Search Header -->
            <div class="p-3 border-b border-slate-200 flex items-center gap-3 bg-white">
              <app-lucide-icon name="search" [size]="18" class="text-slate-400 shrink-0"></app-lucide-icon>
              <input 
                type="text" 
                [(ngModel)]="searchQuery"
                (keydown)="handleSearchKeydown($event)"
                placeholder="Search navigation or actions..." 
                class="w-full bg-transparent text-sm font-medium text-slate-900 focus:outline-none placeholder:text-slate-400"
                autofocus />
              <kbd class="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-[10px] text-slate-500 font-mono">ESC</kbd>
            </div>

            <!-- Command List with Clean Category Grouping -->
            <div class="max-h-[380px] overflow-y-auto p-2 flex flex-col gap-2">
              @if (navigationCommands().length > 0) {
                <div class="flex flex-col gap-0.5">
                  <span class="px-3 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Navigation</span>
                  @for (cmd of navigationCommands(); track cmd.id) {
                    <button
                      type="button"
                      (click)="executeCommand(cmd)"
                      class="w-full px-3 py-2 rounded-lg text-left text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer group">
                      <div class="flex items-center gap-2.5">
                        <app-lucide-icon [name]="cmd.icon" [size]="16" class="text-slate-400 group-hover:text-blue-600"></app-lucide-icon>
                        <span class="font-medium text-slate-800 group-hover:text-blue-700">{{ cmd.label }}</span>
                      </div>
                      <span class="text-[10px] text-slate-400 font-medium">Navigate</span>
                    </button>
                  }
                </div>
              }

              @if (actionCommands().length > 0) {
                <div class="flex flex-col gap-0.5">
                  <span class="px-3 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Actions</span>
                  @for (cmd of actionCommands(); track cmd.id) {
                    <button
                      type="button"
                      (click)="executeCommand(cmd)"
                      class="w-full px-3 py-2 rounded-lg text-left text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer group">
                      <div class="flex items-center gap-2.5">
                        <app-lucide-icon [name]="cmd.icon" [size]="16" class="text-slate-400 group-hover:text-blue-600"></app-lucide-icon>
                        <span class="font-medium text-slate-800 group-hover:text-blue-700">{{ cmd.label }}</span>
                      </div>
                      <span class="text-[10px] text-slate-400 font-medium">Action</span>
                    </button>
                  }
                </div>
              }

              @if (filteredCommands().length === 0) {
                <div class="py-8 text-center text-xs text-slate-500 font-medium">
                  No commands found matching "{{ searchQuery }}"
                </div>
              }
            </div>

            <!-- Footer Hints -->
            <div class="px-4 py-2 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500 font-medium">
              <span>Use &uarr;&darr; to navigate &bull; Enter to select</span>
              <span class="font-mono text-[10px] text-slate-400">ESC to exit</span>
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
            <div class="flex items-center justify-between pb-3 border-b border-slate-200">
              <div class="flex items-center gap-2.5">
                <app-lucide-icon name="file-text" [size]="20" class="text-blue-600"></app-lucide-icon>
                <h3 class="text-base font-bold text-slate-900 font-heading">DevKros Help &amp; Documentation</h3>
              </div>
              <button type="button" (click)="isHelpOpen.set(false)" class="p-1 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 cursor-pointer">
                <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
              </button>
            </div>
            <p class="text-xs text-slate-700 font-medium leading-relaxed">
              DevKros is an enterprise database migration and continuous replication infrastructure platform.
              Access comprehensive runbooks, execution modes (M1–M8), and four-eyes policy manuals under platform settings.
            </p>
            <div class="pt-3 border-t border-slate-200 flex justify-end">
              <button type="button" (click)="isHelpOpen.set(false)" class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer">
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
            <div class="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold text-base shadow-md">
              DK
            </div>
            <h3 class="text-base font-bold text-slate-900 font-heading">DevKros Enterprise Platform</h3>
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold select-none">
              <span class="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
              <span>v1.0.0-PROD • Wails Native Shell</span>
            </span>
            <p class="text-xs text-slate-600 font-medium">
              Direct Named Pipe IPC Bridge • Non-destructive Client Lifecycle
            </p>
            <div class="pt-3 w-full border-t border-slate-200 flex justify-center">
              <button type="button" (click)="isAboutOpen.set(false)" class="h-9 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors cursor-pointer">
                Done
              </button>
            </div>
          </div>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 6. GLOBAL DESTRUCTIVE ACTION CONFIRMATION MODAL                 -->
      <!-- =============================================================== -->
      @if (ms.isDestructiveConfirmModalOpen()) {
        <div 
          class="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
          (click)="ms.cancelDestructiveAction()">
          
          <div 
            class="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-2xl p-6 space-y-5 animate-in zoom-in-95 duration-100"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-center gap-3 text-rose-600">
              <div class="w-10 h-10 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center shrink-0">
                <app-lucide-icon name="alert-triangle" [size]="20"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <span class="text-sm font-bold text-slate-900">Destructive Action Confirmation</span>
                <span class="text-[11px] text-rose-600 font-semibold uppercase tracking-wider">Production Environment Guard</span>
              </div>
            </div>

            <div class="p-3.5 bg-rose-50/70 border border-rose-200 rounded-xl text-xs text-rose-900 space-y-2">
              <p class="font-medium">
                You have selected <strong>Drop and recreate</strong> in a <strong>Production</strong> environment.
              </p>
              <p class="text-[11px] text-rose-800 leading-relaxed">
                This strategy will permanently destroy existing target tables, views, and schemas prior to loading. This action cannot be undone.
              </p>
            </div>

            <div class="flex flex-col gap-2">
              <label class="text-xs font-semibold text-slate-700">
                Type <span class="font-mono font-bold text-rose-700 select-all">DROP TARGET TABLES</span> to confirm:
              </label>
              <input
                type="text"
                [ngModel]="ms.dropConfirmationInput()"
                (ngModelChange)="ms.dropConfirmationInput.set($event)"
                placeholder="DROP TARGET TABLES"
                class="w-full h-9 px-3 text-xs bg-white border border-slate-300 focus:border-rose-600 rounded-lg text-slate-900 font-mono focus:outline-none"
                autofocus />
            </div>

            <div class="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                (click)="ms.cancelDestructiveAction()"
                class="px-3.5 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-800 bg-white border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
                Cancel
              </button>
              <button
                type="button"
                (click)="ms.confirmDestructiveAction()"
                [disabled]="ms.dropConfirmationInput().trim() !== 'DROP TARGET TABLES'"
                class="px-4 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg shadow-2xs transition-colors cursor-pointer">
                Acknowledge &amp; Drop
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
  public ms = inject(MigrationUiService);
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

  public navigationCommands = computed(() => this.filteredCommands().filter(c => c.category === 'Module'));
  public actionCommands = computed(() => this.filteredCommands().filter(c => c.category === 'Action'));

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
