import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { InitiativeOverviewComponent } from './initiative-overview.component';
import { InitiativeProjectsComponent } from './initiative-projects.component';
import { InitiativeActivityComponent } from './initiative-activity.component';
import { InitiativeSettingsComponent } from './initiative-settings.component';
import { ProjectsStateFallbackComponent } from '../components/projects-state-fallback.component';
import { InitiativeTabType } from '../projects.models';

@Component({
  selector: 'app-initiative-workspace',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LucideIconComponent,
    InitiativeOverviewComponent,
    InitiativeProjectsComponent,
    InitiativeActivityComponent,
    InitiativeSettingsComponent,
    ProjectsStateFallbackComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-8 w-full max-w-[1680px] mx-auto font-sans pb-12 select-none animate-in fade-in duration-150">
      
      <!-- =============================================================== -->
      <!-- 1. INITIATIVE WORKSPACE HERO HEADER                             -->
      <!-- =============================================================== -->
      @if (ps.activeInitiative(); as init) {
        <div class="flex flex-col gap-4 pb-5 border-b border-slate-200">
          
          <!-- Top Row: Back Button & Inherited Context Chips -->
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <a
              routerLink="/migration/initiatives"
              class="h-8 px-3 rounded-md text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 bg-white hover:bg-slate-50 transition-colors inline-flex items-center justify-center cursor-pointer shadow-2xs">
              Back to Initiatives
            </a>

            <!-- Inherited Context Chips -->
            <div class="flex items-center gap-1.5 text-xs text-slate-500 font-medium bg-slate-100/90 px-3 py-1 rounded-md border border-slate-200">
              <app-lucide-icon name="building-2" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>{{ ps.cs.selectedOrg()?.name || 'Org' }}</span>
              <span class="text-slate-400">&bull;</span>
              <span>{{ ps.cs.selectedWorkspace()?.name || 'Workspace' }}</span>
              <span class="text-slate-400">&bull;</span>
              <span class="font-semibold text-slate-700">{{ ps.cs.selectedEnvironment()?.name || 'Env' }}</span>
            </div>
          </div>

          <!-- Middle Row: Initiative Key, Title & Status -->
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div class="flex items-center gap-3 min-w-0">
              <span class="px-2.5 py-1 rounded-md text-xs font-bold font-mono bg-indigo-50 text-indigo-700 border border-indigo-200/90 shrink-0">
                {{ init.key }}
              </span>
              <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading truncate">
                {{ init.name }}
              </h1>
            </div>

            <!-- Status Badge -->
            <span
              class="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold border select-none shrink-0"
              [class.bg-emerald-50]="init.status === 'ACTIVE'"
              [class.text-emerald-700]="init.status === 'ACTIVE'"
              [class.border-emerald-200]="init.status === 'ACTIVE'"
              [class.bg-blue-50]="init.status === 'PLANNING'"
              [class.text-blue-700]="init.status === 'PLANNING'"
              [class.border-blue-200]="init.status === 'PLANNING'"
              [class.bg-slate-100]="init.status === 'ARCHIVED'"
              [class.text-slate-700]="init.status === 'ARCHIVED'"
              [class.border-slate-200]="init.status === 'ARCHIVED'">
              <span
                class="w-2 h-2 rounded-xs"
                [class.bg-emerald-500]="init.status === 'ACTIVE'"
                [class.bg-blue-500]="init.status === 'PLANNING'"
                [class.bg-slate-400]="init.status === 'ARCHIVED'">
              </span>
              <span>{{ init.status || 'Active' }}</span>
            </span>
          </div>

          <!-- Bottom Row: GDS Segmented Slider Tabs -->
          <div class="flex items-center pt-2">
            <div class="inline-flex items-center p-1 rounded-lg bg-slate-100/90 border border-slate-200">
              
              <button
                type="button"
                (click)="switchTab('overview')"
                class="flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all select-none cursor-pointer"
                [class.bg-white]="ps.activeTab() === 'overview'"
                [class.text-blue-700]="ps.activeTab() === 'overview'"
                [class.shadow-2xs]="ps.activeTab() === 'overview'"
                [class.text-slate-600]="ps.activeTab() !== 'overview'"
                [class.hover:text-slate-900]="ps.activeTab() !== 'overview'">
                <app-lucide-icon name="layout-dashboard" [size]="14"></app-lucide-icon>
                <span>Overview</span>
              </button>

              <button
                type="button"
                (click)="switchTab('projects')"
                class="flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all select-none cursor-pointer"
                [class.bg-white]="ps.activeTab() === 'projects'"
                [class.text-blue-700]="ps.activeTab() === 'projects'"
                [class.shadow-2xs]="ps.activeTab() === 'projects'"
                [class.text-slate-600]="ps.activeTab() !== 'projects'"
                [class.hover:text-slate-900]="ps.activeTab() !== 'projects'">
                <app-lucide-icon name="folder-kanban" [size]="14"></app-lucide-icon>
                <span>Projects</span>
                <span
                  class="px-1.5 py-0.5 rounded-md text-[10.5px] font-mono font-bold"
                  [class.bg-blue-50]="ps.activeTab() === 'projects'"
                  [class.text-blue-700]="ps.activeTab() === 'projects'"
                  [class.bg-slate-200]="ps.activeTab() !== 'projects'"
                  [class.text-slate-600]="ps.activeTab() !== 'projects'">
                  {{ init.associatedProjectIds.length }}
                </span>
              </button>

              <button
                type="button"
                (click)="switchTab('activity')"
                class="flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all select-none cursor-pointer"
                [class.bg-white]="ps.activeTab() === 'activity'"
                [class.text-blue-700]="ps.activeTab() === 'activity'"
                [class.shadow-2xs]="ps.activeTab() === 'activity'"
                [class.text-slate-600]="ps.activeTab() !== 'activity'"
                [class.hover:text-slate-900]="ps.activeTab() !== 'activity'">
                <app-lucide-icon name="activity" [size]="14"></app-lucide-icon>
                <span>Activity</span>
              </button>

              <button
                type="button"
                (click)="switchTab('settings')"
                class="flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all select-none cursor-pointer"
                [class.bg-white]="ps.activeTab() === 'settings'"
                [class.text-blue-700]="ps.activeTab() === 'settings'"
                [class.shadow-2xs]="ps.activeTab() === 'settings'"
                [class.text-slate-600]="ps.activeTab() !== 'settings'"
                [class.hover:text-slate-900]="ps.activeTab() !== 'settings'">
                <app-lucide-icon name="settings" [size]="14"></app-lucide-icon>
                <span>Settings</span>
              </button>

            </div>
          </div>

        </div>

        <!-- =============================================================== -->
        <!-- 2. ACTIVE TAB WORKSPACE CANVAS                                  -->
        <!-- =============================================================== -->
        <main class="w-full">
          @switch (ps.activeTab()) {
            @case ('overview') {
              <app-initiative-overview (navigateTab)="switchTab($event)" />
            }
            @case ('projects') {
              <app-initiative-projects />
            }
            @case ('activity') {
              <app-initiative-activity />
            }
            @case ('settings') {
              <app-initiative-settings />
            }
          }
        </main>
      } @else {
        <!-- Fallback view when Initiative is not found or store is unavailable -->
        <div class="py-16">
          <app-projects-state-fallback
            [state]="'UNAVAILABLE'"
            entityName="initiatives"
            customErrorMessage="Initiative workspace not found or unavailable in current context."
            (retry)="handleBack()">
          </app-projects-state-fallback>
        </div>
      }

    </div>
  `
})
export class InitiativeWorkspaceComponent implements OnInit, OnDestroy {
  public ps = inject(ProjectsService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private sub?: Subscription;

  ngOnInit(): void {
    this.sub = this.route.paramMap.subscribe(params => {
      const id = params.get('initiativeId');
      const tab = params.get('tab') as InitiativeTabType;
      
      if (id) {
        this.ps.setActiveInitiativeId(id);
      }
      if (tab && ['overview', 'projects', 'activity', 'settings'].includes(tab)) {
        this.ps.setActiveTab(tab);
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  public switchTab(tab: InitiativeTabType): void {
    this.ps.setActiveTab(tab);
    const active = this.ps.activeInitiative();
    if (active) {
      this.router.navigate(['/migration/initiatives', active.id, tab]);
    }
  }

  public handleBack(): void {
    this.router.navigate(['/migration/initiatives']);
  }
}
