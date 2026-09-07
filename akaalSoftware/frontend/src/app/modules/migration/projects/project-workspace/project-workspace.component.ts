import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectOverviewComponent } from './project-overview.component';
import { ProjectMigrationsComponent } from './project-migrations.component';
import { ProjectValidationsComponent } from './project-validations.component';
import { ProjectResourcesComponent } from './project-resources.component';
import { ProjectActivityComponent } from './project-activity.component';
import { ProjectAccessComponent } from './project-access.component';
import { ProjectGovernanceComponent } from './project-governance.component';
import { ProjectSettingsComponent } from './project-settings.component';
import { ProjectTabPlaceholderComponent } from './project-tab-placeholder.component';
import { ProjectsStateFallbackComponent } from '../components/projects-state-fallback.component';
import { ProjectWorkspaceTabType } from '../projects.models';

export interface ProjectWorkspaceTabDef {
  key: ProjectWorkspaceTabType;
  label: string;
  icon: string;
}

@Component({
  selector: 'app-project-workspace',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LucideIconComponent,
    ProjectOverviewComponent,
    ProjectMigrationsComponent,
    ProjectValidationsComponent,
    ProjectResourcesComponent,
    ProjectActivityComponent,
    ProjectAccessComponent,
    ProjectGovernanceComponent,
    ProjectSettingsComponent,
    ProjectTabPlaceholderComponent,
    ProjectsStateFallbackComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-8 w-full max-w-[1680px] mx-auto font-sans pb-12 select-none animate-in fade-in duration-150">
      
      <!-- =============================================================== -->
      <!-- 1. PROJECT WORKSPACE HERO HEADER                                -->
      <!-- =============================================================== -->
      @if (ps.activeProject(); as proj) {
        <div class="flex flex-col gap-4 pb-5 border-b border-slate-200">
          
          <!-- Top Row: Back Button & Inherited Context Chips -->
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <a
              routerLink="/migration/projects"
              class="h-8 px-3 rounded-md text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 bg-white hover:bg-slate-50 transition-colors inline-flex items-center justify-center cursor-pointer shadow-2xs">
              Back to Projects
            </a>

            <!-- Inherited Context Chips -->
            <div class="flex items-center gap-1.5 text-xs text-slate-500 font-medium bg-slate-100/90 px-3 py-1 rounded-md border border-slate-200">
              <app-lucide-icon name="building-2" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>{{ ps.cs.selectedOrg()?.name || 'Org' }}</span>
              <span class="text-slate-400">&bull;</span>
              <span>{{ ps.cs.selectedWorkspace()?.name || 'Workspace' }}</span>
              <span class="text-slate-400">&bull;</span>
              <span class="font-semibold text-slate-700">{{ proj.environmentName || ps.cs.selectedEnvironment()?.name || 'Env' }}</span>
              @if (proj.isProduction) {
                <span class="px-1 py-0.2 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">PROD</span>
              }
            </div>
          </div>

          <!-- Middle Row: Project Key, Title, Initiative Badge & Status -->
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div class="flex items-center gap-3 min-w-0">
              <span class="px-2.5 py-1 rounded-md text-xs font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200/90 shrink-0">
                {{ proj.key }}
              </span>
              <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading truncate">
                {{ proj.name }}
              </h1>

              <!-- Initiative Alignment Link (if assigned) -->
              @if (proj.initiativeId) {
                <a
                  [routerLink]="['/migration/initiatives', proj.initiativeId, 'overview']"
                  class="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 transition-colors shadow-2xs">
                  <app-lucide-icon name="target" [size]="12" class="text-indigo-600"></app-lucide-icon>
                  <span>{{ proj.initiativeKey || 'Initiative' }}</span>
                </a>
              }
            </div>

            <!-- Status Badge -->
            <span
              class="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold border select-none shrink-0"
              [class.bg-emerald-50]="proj.status === 'ACTIVE'"
              [class.text-emerald-700]="proj.status === 'ACTIVE'"
              [class.border-emerald-200]="proj.status === 'ACTIVE'"
              [class.bg-blue-50]="proj.status === 'PLANNING'"
              [class.text-blue-700]="proj.status === 'PLANNING'"
              [class.border-blue-200]="proj.status === 'PLANNING'"
              [class.bg-slate-100]="proj.status === 'ARCHIVED' || proj.status === 'COMPLETED'"
              [class.text-slate-700]="proj.status === 'ARCHIVED' || proj.status === 'COMPLETED'"
              [class.border-slate-200]="proj.status === 'ARCHIVED' || proj.status === 'COMPLETED'">
              <span
                class="w-2 h-2 rounded-xs"
                [class.bg-emerald-500]="proj.status === 'ACTIVE'"
                [class.bg-blue-500]="proj.status === 'PLANNING'"
                [class.bg-slate-400]="proj.status === 'ARCHIVED' || proj.status === 'COMPLETED'">
              </span>
              <span>{{ proj.status || 'Active' }}</span>
            </span>
          </div>

          <!-- Bottom Row: 8-Tab GDS Segmented Slider Tabs -->
          <div class="flex items-center pt-2 overflow-x-auto">
            <div class="inline-flex items-center p-1 rounded-lg bg-slate-100/90 border border-slate-200 shrink-0">
              @for (t of tabs; track t.key) {
                <button
                  type="button"
                  (click)="switchTab(t.key)"
                  class="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-all select-none cursor-pointer shrink-0"
                  [class.bg-white]="ps.activeProjectTab() === t.key"
                  [class.text-blue-700]="ps.activeProjectTab() === t.key"
                  [class.shadow-2xs]="ps.activeProjectTab() === t.key"
                  [class.text-slate-600]="ps.activeProjectTab() !== t.key"
                  [class.hover:text-slate-900]="ps.activeProjectTab() !== t.key">
                  <app-lucide-icon [name]="t.icon" [size]="13"></app-lucide-icon>
                  <span>{{ t.label }}</span>
                </button>
              }
            </div>
          </div>

        </div>

        <!-- =============================================================== -->
        <!-- 2. ACTIVE TAB WORKSPACE CANVAS                                  -->
        <!-- =============================================================== -->
        <main class="w-full">
          @switch (ps.activeProjectTab()) {
            @case ('overview') {
              <app-project-overview (navigateTab)="switchTab($event)" />
            }
            @case ('migrations') {
              <app-project-migrations />
            }
            @case ('validations') {
              <app-project-validations />
            }
            @case ('resources') {
              <app-project-resources />
            }
            @case ('activity') {
              <app-project-activity />
            }
            @case ('access') {
              <app-project-access />
            }
            @case ('governance') {
              <app-project-governance />
            }
            @case ('settings') {
              <app-project-settings />
            }
            @default {
              <app-project-tab-placeholder
                [tab]="ps.activeProjectTab()"
                [project]="proj"
                (navigateOverview)="switchTab('overview')">
              </app-project-tab-placeholder>
            }
          }
        </main>
      } @else {
        <!-- Fallback view when Project is not found or store is unavailable -->
        <div class="py-16">
          <app-projects-state-fallback
            [state]="'UNAVAILABLE'"
            entityName="projects"
            customErrorMessage="Project workspace not found or unavailable in current context."
            (retry)="handleBack()">
          </app-projects-state-fallback>
        </div>
      }

    </div>
  `
})
export class ProjectWorkspaceComponent implements OnInit, OnDestroy {
  public ps = inject(ProjectsService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private sub?: Subscription;

  public tabs: ProjectWorkspaceTabDef[] = [
    { key: 'overview', label: 'Overview', icon: 'layout-dashboard' },
    { key: 'migrations', label: 'Migrations', icon: 'arrow-left-right' },
    { key: 'validations', label: 'Validations', icon: 'check-circle-2' },
    { key: 'resources', label: 'Resources', icon: 'database' },
    { key: 'activity', label: 'Activity', icon: 'activity' },
    { key: 'access', label: 'Access', icon: 'shield' },
    { key: 'governance', label: 'Governance', icon: 'scale' },
    { key: 'settings', label: 'Settings', icon: 'settings' }
  ];

  ngOnInit(): void {
    this.sub = this.route.paramMap.subscribe(params => {
      const id = params.get('projectId');
      const tab = params.get('tab') as ProjectWorkspaceTabType;
      
      if (id) {
        this.ps.setActiveProjectId(id);
      }
      if (tab && ['overview', 'migrations', 'validations', 'resources', 'activity', 'access', 'governance', 'settings'].includes(tab)) {
        this.ps.setActiveProjectTab(tab);
      } else {
        this.ps.setActiveProjectTab('overview');
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  public switchTab(tab: ProjectWorkspaceTabType): void {
    this.ps.setActiveProjectTab(tab);
    const active = this.ps.activeProject();
    if (active) {
      this.router.navigate(['/migration/projects', active.id, tab]);
    }
  }

  public handleBack(): void {
    this.router.navigate(['/migration/projects']);
  }
}
