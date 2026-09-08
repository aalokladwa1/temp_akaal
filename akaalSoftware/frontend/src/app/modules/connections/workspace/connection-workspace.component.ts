import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';
import { ConnectionWorkspaceService } from './connection-workspace.service';
import { ConnectionWorkspaceTab } from './connection-workspace.models';
import { WorkspaceHeaderComponent } from './components/workspace-header.component';
import { WorkspaceNavComponent } from './components/workspace-nav.component';
import { TabOverviewComponent } from './tabs/tab-overview.component';
import { TabConfigurationComponent } from './tabs/tab-configuration.component';
import { TabCapabilitiesComponent } from './tabs/tab-capabilities.component';
import { TabUsageComponent } from './tabs/tab-usage.component';
import { TabActivityComponent } from './tabs/tab-activity.component';
import { TabSettingsComponent } from './tabs/tab-settings.component';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-connection-workspace',
  standalone: true,
  imports: [
    CommonModule,
    WorkspaceHeaderComponent,
    WorkspaceNavComponent,
    TabOverviewComponent,
    TabConfigurationComponent,
    TabCapabilitiesComponent,
    TabUsageComponent,
    TabActivityComponent,
    TabSettingsComponent,
    LucideIconComponent
  ],
  template: `
    <div class="min-h-screen bg-slate-50/60 font-sans select-none flex flex-col text-slate-800">
      
      <!-- Top Persistent Identity & Actions Header -->
      <app-workspace-header />

      <!-- Horizontal 6-Tab Navigation Bar -->
      <app-workspace-nav />

      <!-- Main Workspace Viewport -->
      <main class="max-w-[1680px] w-full mx-auto p-6 lg:p-8 flex flex-col gap-6 flex-1">
        
        @if (ws.isLoading()) {
          <div class="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
            <app-lucide-icon name="loader" [size]="24" class="animate-spin text-blue-600"></app-lucide-icon>
            <span class="text-xs font-medium">Loading Connection Workspace...</span>
          </div>
        } @else if (ws.errorMessage()) {
          <div class="p-8 text-center bg-white border border-rose-200 rounded-xl flex flex-col items-center gap-3">
            <app-lucide-icon name="alert-triangle" [size]="24" class="text-rose-600"></app-lucide-icon>
            <span class="text-sm font-bold text-slate-900">Unable to load connection workspace</span>
            <p class="text-xs text-slate-500">{{ ws.errorMessage() }}</p>
          </div>
        } @else {
          
          @switch (ws.activeTab()) {
            
            <!-- Tab 1: OVERVIEW -->
            @case ('overview') {
              <app-tab-overview />
            }

            <!-- Tab 2: CONFIGURATION -->
            @case ('configuration') {
              <app-tab-configuration />
            }

            <!-- Tab 3: CAPABILITIES -->
            @case ('capabilities') {
              <app-tab-capabilities />
            }

            <!-- Tab 4: USAGE -->
            @case ('usage') {
              <app-tab-usage />
            }

            <!-- Tab 5: ACTIVITY -->
            @case ('activity') {
              <app-tab-activity />
            }

            <!-- Tab 6: SETTINGS -->
            @case ('settings') {
              <app-tab-settings />
            }

          }

        }

      </main>

    </div>
  `
})
export class ConnectionWorkspaceComponent implements OnInit, OnDestroy {
  public ws = inject(ConnectionWorkspaceService);
  private route = inject(ActivatedRoute);
  private sub?: Subscription;

  ngOnInit(): void {
    this.sub = this.route.paramMap.subscribe(params => {
      const id = params.get('connectionId');
      const tab = params.get('tab') as ConnectionWorkspaceTab | null;
      if (id) {
        this.ws.loadConnection(id, tab || 'overview');
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
