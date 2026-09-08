import { Component, inject, signal, HostListener, Optional } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ConnectionsService } from '../connections.service';
import {
  ConnectionRecord,
  ConnectionFamily,
  ConnectionVerificationState
} from '../connections.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../shared/components/custom-select.component';

@Component({
  selector: 'app-connections-table',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    CustomSelectComponent
  ],
  template: `
    <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5 select-none" (click)="closeAllMenus()">
      
      <!-- =============================================================== -->
      <!-- 1. INTEGRATED OPERATIONAL TOOLBAR (Sibling Aligned)             -->
      <!-- =============================================================== -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-200 flex-wrap gap-3">
        
        <!-- Left: Inventory Title & Count Badge -->
        <div class="flex items-center gap-2.5">
          <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Connection Inventory</span>
          <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 font-mono">
            {{ cs.filteredConnections().length }}
          </span>
        </div>

        <!-- Right: Search Input + GDS Filter Dropdowns + Clear Filters Action -->
        <div class="flex items-center gap-2.5 flex-wrap">
          
          <!-- Search Input with Absolutely Positioned Search Icon -->
          <div class="relative flex items-center w-64 sm:w-72">
            <app-lucide-icon 
              name="search" 
              [size]="14"
              class="absolute left-2.5 text-slate-400 pointer-events-none z-10">
            </app-lucide-icon>
            
            <input
              type="text"
              [ngModel]="cs.filters().searchQuery"
              (ngModelChange)="cs.setSearchQuery($event)"
              placeholder="Search connections..."
              class="w-full h-8 pl-8 pr-7 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
            />

            @if (cs.filters().searchQuery) {
              <button
                type="button"
                (click)="cs.setSearchQuery('')"
                class="absolute right-2 text-slate-400 hover:text-slate-700 cursor-pointer">
                <app-lucide-icon name="x" [size]="13"></app-lucide-icon>
              </button>
            }
          </div>

          <!-- Provider Family Filter Dropdown (GDS) -->
          <div class="w-44">
            <app-custom-select
              [options]="familyOptions"
              [value]="cs.filters().family"
              (valueChange)="onFamilyChange($event)"
              [size]="'sm'">
            </app-custom-select>
          </div>

          <!-- Verification Status Filter Dropdown (GDS) -->
          <div class="w-44">
            <app-custom-select
              [options]="verificationOptions"
              [value]="cs.filters().verificationState"
              (valueChange)="onVerificationChange($event)"
              [size]="'sm'">
            </app-custom-select>
          </div>

          <!-- Clear Filters Button (Text-Led, No Icon Inside Action Button) -->
          @if (cs.isFiltered()) {
            <button
              type="button"
              (click)="cs.clearFilters()"
              class="h-8 px-3 rounded-md bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-700 text-xs font-semibold transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-400">
              Clear filters
            </button>
          }

        </div>

      </div>

      <!-- =============================================================== -->
      <!-- 2. FOUR CORE COLUMNS INVENTORY TABLE + OVERFLOW ACTIONS (⋯)     -->
      <!-- =============================================================== -->
      <div class="overflow-x-auto overflow-y-visible">
        <table class="w-full text-left border-collapse min-w-[850px]">
          <!-- Table Header -->
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider select-none">
              
              <!-- Column 1: Connection (Sortable) -->
              <th scope="col" class="py-3 px-4 font-bold min-w-[280px]">
                <button
                  type="button"
                  (click)="toggleSort('name')"
                  class="flex items-center gap-1.5 text-slate-600 hover:text-slate-900 focus:outline-hidden font-bold cursor-pointer uppercase">
                  <span>Connection</span>
                  <span class="text-[10px] font-mono text-slate-400" *ngIf="cs.filters().sortBy === 'name'">
                    {{ cs.filters().sortDirection === 'asc' ? '▲' : '▼' }}
                  </span>
                </button>
              </th>

              <!-- Column 2: Provider (Sortable) -->
              <th scope="col" class="py-3 px-4 font-bold min-w-[200px]">
                <button
                  type="button"
                  (click)="toggleSort('provider')"
                  class="flex items-center gap-1.5 text-slate-600 hover:text-slate-900 focus:outline-hidden font-bold cursor-pointer uppercase">
                  <span>Provider</span>
                  <span class="text-[10px] font-mono text-slate-400" *ngIf="cs.filters().sortBy === 'provider'">
                    {{ cs.filters().sortDirection === 'asc' ? '▲' : '▼' }}
                  </span>
                </button>
              </th>

              <!-- Column 3: Verification (Sortable) -->
              <th scope="col" class="py-3 px-4 font-bold min-w-[240px]">
                <button
                  type="button"
                  (click)="toggleSort('lastVerified')"
                  class="flex items-center gap-1.5 text-slate-600 hover:text-slate-900 focus:outline-hidden font-bold cursor-pointer uppercase">
                  <span>Verification</span>
                  <span class="text-[10px] font-mono text-slate-400" *ngIf="cs.filters().sortBy === 'lastVerified'">
                    {{ cs.filters().sortDirection === 'asc' ? '▲' : '▼' }}
                  </span>
                </button>
              </th>

              <!-- Column 4: Usage (Sortable) -->
              <th scope="col" class="py-3 px-4 font-bold min-w-[150px]">
                <button
                  type="button"
                  (click)="toggleSort('usageCount')"
                  class="flex items-center gap-1.5 text-slate-600 hover:text-slate-900 focus:outline-hidden font-bold cursor-pointer uppercase">
                  <span>Usage</span>
                  <span class="text-[10px] font-mono text-slate-400" *ngIf="cs.filters().sortBy === 'usageCount'">
                    {{ cs.filters().sortDirection === 'asc' ? '▲' : '▼' }}
                  </span>
                </button>
              </th>

              <!-- Column 5: Overflow Actions (⋯) -->
              <th scope="col" class="py-3 px-3 text-right font-bold w-14">
                <span class="sr-only">Actions</span>
              </th>

            </tr>
          </thead>

          <!-- Table Body -->
          <tbody class="divide-y divide-slate-100 text-sm text-slate-700">
            <tr
              *ngFor="let conn of cs.filteredConnections(); let i = index; trackBy: trackById"
              class="hover:bg-slate-50/70 transition-colors group cursor-pointer"
              (click)="onRowClick(conn)">
              
              <!-- Column 1: Connection (Only clean name) -->
              <td class="py-3.5 px-4 align-middle">
                <div class="flex items-center gap-2">
                  <span class="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors text-sm truncate">
                    {{ conn.name }}
                  </span>
                </div>
              </td>

              <!-- Column 2: Provider (Only provider name) -->
              <td class="py-3.5 px-4 align-middle whitespace-nowrap">
                <span class="text-xs font-semibold text-slate-800">
                  {{ conn.providerName }}
                </span>
              </td>

              <!-- Column 3: Verification Truth -->
              <td class="py-3.5 px-4 align-middle whitespace-nowrap">
                <div class="flex items-center gap-2.5">
                  <span [class]="getVerificationBadgeClass(conn.verificationState)" class="whitespace-nowrap">
                    <span [class]="getVerificationDotClass(conn.verificationState)"></span>
                    <span>{{ getVerificationLabel(conn.verificationState) }}</span>
                  </span>

                  <span class="text-[11px] text-slate-400 whitespace-nowrap" *ngIf="conn.lastVerifiedAt && conn.verificationState !== 'TESTING'">
                    &bull; {{ formatTimeAgo(conn.lastVerifiedAt) }}
                  </span>
                  <span class="text-[11px] text-blue-600 font-medium animate-pulse whitespace-nowrap" *ngIf="conn.verificationState === 'TESTING'">
                    &bull; Probing...
                  </span>
                </div>
              </td>

              <!-- Column 4: Usage (Only number of connections/projects) -->
              <td class="py-3.5 px-4 align-middle whitespace-nowrap">
                <div *ngIf="!conn.usage.usageAvailable" class="text-xs text-slate-400 italic">
                  Usage unavailable
                </div>

                <div *ngIf="conn.usage.usageAvailable">
                  <span *ngIf="conn.usage.isUnused" class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                    Unused
                  </span>

                  <span *ngIf="!conn.usage.isUnused" class="text-xs font-medium text-slate-800">
                    <strong class="font-mono font-bold text-slate-900">{{ conn.usage.referencedProjectCount }}</strong> {{ conn.usage.referencedProjectCount === 1 ? 'Project' : 'Projects' }}
                  </span>
                </div>
              </td>

              <!-- Column 5: Overflow Actions (⋯) Context Menu -->
              <td class="py-3.5 px-3 text-right whitespace-nowrap align-middle" (click)="$event.stopPropagation()">
                <div class="relative inline-block text-left">
                  <button
                    type="button"
                    (click)="toggleMenu(conn.id, $event)"
                    class="w-8 h-8 flex items-center justify-center rounded-lg border border-transparent text-slate-400 hover:text-slate-700 hover:bg-slate-100 hover:border-slate-200 transition-colors cursor-pointer focus:outline-none"
                    [class.bg-slate-100]="activeMenuId() === conn.id"
                    [class.text-slate-700]="activeMenuId() === conn.id"
                    [class.border-slate-200]="activeMenuId() === conn.id"
                    title="Quick Actions">
                    <app-lucide-icon name="more-horizontal" [size]="16"></app-lucide-icon>
                  </button>

                  <!-- Popover Menu with Upward Flip on Lower Rows -->
                  @if (activeMenuId() === conn.id) {
                    <div
                      (click)="$event.stopPropagation()"
                      class="absolute right-0 w-48 rounded-xl bg-white border border-slate-200 shadow-xl p-1.5 flex flex-col gap-0.5 z-50 text-left animate-in fade-in zoom-in-95 duration-100"
                      [ngClass]="(i >= cs.filteredConnections().length - 2 && cs.filteredConnections().length > 2)
                        ? 'bottom-full mb-1 origin-bottom-right'
                        : 'top-full mt-1 origin-top-right'">
                      
                      <!-- 1. View Connection -->
                      <button
                        type="button"
                        (click)="onViewConnection(conn)"
                        class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2 cursor-pointer">
                        <app-lucide-icon name="panel-right-open" [size]="14" class="text-slate-500"></app-lucide-icon>
                        <span>View Connection</span>
                      </button>

                      <!-- 2. Test Connection (Truthful point-in-time probe simulation) -->
                      <button
                        type="button"
                        (click)="onTestConnection(conn)"
                        class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-blue-700 hover:bg-blue-50 transition-colors flex items-center gap-2 cursor-pointer">
                        <app-lucide-icon name="activity" [size]="14" class="text-blue-600"></app-lucide-icon>
                        <span>Test Connection</span>
                      </button>

                      <div class="border-t border-slate-100 my-0.5"></div>

                      <!-- 3. Edit Configuration -->
                      <button
                        type="button"
                        (click)="onEditConfiguration(conn)"
                        class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-2 cursor-pointer">
                        <app-lucide-icon name="sliders" [size]="14" class="text-slate-500"></app-lucide-icon>
                        <span>Edit Configuration</span>
                      </button>

                    </div>
                  }
                </div>
              </td>

            </tr>
          </tbody>
        </table>
      </div>

      <!-- Table Footer / Inventory Record Count & Truth Note -->
      <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 flex-wrap gap-2">
        <div>
          Showing <span class="font-semibold text-slate-800 font-mono">{{ cs.filteredConnections().length }}</span> of
          <span class="font-semibold text-slate-800 font-mono">{{ cs.connections().length }}</span> connection profiles
        </div>
        <div class="text-[11px] text-slate-400">
          Point-in-time verification truth &bull; Never synthetic health
        </div>
      </div>

    </div>
  `
})
export class ConnectionsTableComponent {
  public cs = inject(ConnectionsService);
  public activeMenuId = signal<string | null>(null);
  public router?: Router;

  constructor(@Optional() router?: Router) {
    if (router) this.router = router;
    else {
      try {
        this.router = inject(Router);
      } catch {}
    }
  }

  public familyOptions: CustomSelectOption[] = [
    { label: 'All Providers', value: 'ALL' },
    { label: 'Relational', value: 'RELATIONAL' },
    { label: 'Warehouse / Lake', value: 'WAREHOUSE_LAKE' },
    { label: 'NoSQL / Graph', value: 'NOSQL_GRAPH' },
    { label: 'Streaming', value: 'STREAMING' },
    { label: 'Object Storage', value: 'OBJECT_STORAGE' },
    { label: 'Time Series', value: 'TIME_SERIES' },
    { label: 'Application / SaaS', value: 'APPLICATION' },
    { label: 'Cloud Resolvers', value: 'MANAGED_CLOUD' }
  ];

  public verificationOptions: CustomSelectOption[] = [
    { label: 'All Verification States', value: 'ALL' },
    { label: 'Verified (Point-in-Time)', value: 'VERIFIED_GROUP' },
    { label: 'Needs Attention', value: 'ATTENTION_GROUP' },
    { label: 'Never Tested', value: 'NEVER_TESTED' }
  ];

  @HostListener('document:click', ['$event'])
  public onDocumentClick(): void {
    this.closeAllMenus();
  }

  public closeAllMenus(): void {
    this.activeMenuId.set(null);
  }

  public toggleMenu(connId: string, event: MouseEvent): void {
    event.stopPropagation();
    if (this.activeMenuId() === connId) {
      this.activeMenuId.set(null);
    } else {
      this.activeMenuId.set(connId);
    }
  }

  public onViewConnection(conn: ConnectionRecord): void {
    this.closeAllMenus();
    if (this.router) {
      this.router.navigate(['/connections', conn.id]);
    } else {
      this.cs.openInspectDrawer(conn);
    }
  }

  public onTestConnection(conn: ConnectionRecord): void {
    this.closeAllMenus();
    this.cs.verifyConnection(conn.id);
  }

  public onEditConfiguration(conn: ConnectionRecord): void {
    this.closeAllMenus();
    if (this.router) {
      this.router.navigate(['/connections', conn.id, 'configuration']);
    } else {
      this.cs.openInspectDrawer(conn);
    }
  }

  trackById(_index: number, item: ConnectionRecord): string {
    return item.id;
  }

  onRowClick(conn: ConnectionRecord): void {
    this.closeAllMenus();
    if (this.router) {
      this.router.navigate(['/connections', conn.id]);
    } else {
      this.cs.openInspectDrawer(conn);
    }
  }

  onFamilyChange(val: string): void {
    this.cs.setFamilyFilter(val as ConnectionFamily | 'ALL');
  }

  onVerificationChange(val: string): void {
    this.cs.setVerificationFilter(val as ConnectionVerificationState | 'ALL' | 'VERIFIED_GROUP' | 'ATTENTION_GROUP');
  }

  toggleSort(field: 'name' | 'provider' | 'lastVerified' | 'usageCount'): void {
    this.cs.toggleSort(field);
  }

  getVerificationLabel(state: ConnectionVerificationState): string {
    switch (state) {
      case 'VERIFIED_RECENT': return 'Verified (Fresh)';
      case 'VERIFIED_POINT_IN_TIME': return 'Verified (Point-in-Time)';
      case 'VERIFIED_STALE': return 'Verified (Stale)';
      case 'CONFIG_CHANGED_SINCE_TEST': return 'Needs Verification';
      case 'PARTIAL_VERIFIED': return 'Partial (L1/L2 Only)';
      case 'TESTING': return 'Testing Probe...';
      case 'NEVER_TESTED': return 'Never Tested';
      case 'VERIFICATION_FAILED': return 'Failed Probe';
      case 'UNAVAILABLE': return 'Bridge Unavailable';
      case 'UNAUTHORIZED': return 'Unauthorized';
      case 'UNKNOWN': return 'Unknown State';
      default: return state;
    }
  }

  getVerificationBadgeClass(state: ConnectionVerificationState): string {
    switch (state) {
      case 'VERIFIED_RECENT':
      case 'VERIFIED_POINT_IN_TIME':
        return 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200';
      case 'VERIFIED_STALE':
      case 'CONFIG_CHANGED_SINCE_TEST':
        return 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200';
      case 'PARTIAL_VERIFIED':
        return 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-sky-50 text-sky-700 border border-sky-200';
      case 'TESTING':
        return 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200';
      case 'VERIFICATION_FAILED':
        return 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-rose-50 text-rose-700 border border-rose-200';
      case 'UNAVAILABLE':
      case 'UNAUTHORIZED':
      case 'UNKNOWN':
      case 'NEVER_TESTED':
      default:
        return 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200';
    }
  }

  getVerificationDotClass(state: ConnectionVerificationState): string {
    switch (state) {
      case 'VERIFIED_RECENT':
      case 'VERIFIED_POINT_IN_TIME':
        return 'w-1.5 h-1.5 rounded-full bg-emerald-500';
      case 'VERIFIED_STALE':
      case 'CONFIG_CHANGED_SINCE_TEST':
        return 'w-1.5 h-1.5 rounded-full bg-amber-500';
      case 'PARTIAL_VERIFIED':
        return 'w-1.5 h-1.5 rounded-full bg-sky-500';
      case 'TESTING':
        return 'w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping';
      case 'VERIFICATION_FAILED':
        return 'w-1.5 h-1.5 rounded-full bg-rose-500';
      case 'NEVER_TESTED':
      default:
        return 'w-1.5 h-1.5 rounded-full bg-slate-400';
    }
  }

  formatTimeAgo(isoDateString: string): string {
    try {
      const date = new Date(isoDateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffHours / 24);

      if (diffHours < 1) return 'moments ago';
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays === 1) return 'yesterday';
      return `${diffDays}d ago`;
    } catch {
      return 'recently';
    }
  }
}
