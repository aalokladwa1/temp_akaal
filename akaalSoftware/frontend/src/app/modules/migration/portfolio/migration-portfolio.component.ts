import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ProgressBarModule } from 'primeng/progressbar';
import { MigrationHomeService } from '../../../core/services/migration-home.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { StatusBadgeComponent } from '../components/status-badge.component';

interface CoreFunctionCard {
  title: string;
  description: string;
  actionText: string;
  iconName: string;
  route: string;
  iconBg: string;
  iconColor: string;
}

@Component({
  selector: 'app-migration-portfolio',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    TableModule,
    TagModule,
    ProgressBarModule,
    LucideIconComponent,
    StatusBadgeComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- =============================================================== -->
      <!-- 1. MIGRATION HEADER & DYNAMIC OPERATIONAL SUBTEXT (SECTION 11-13) -->
      <!-- =============================================================== -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">OPERATIONS</span>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight">MIGRATION HOME</h1>
          <p class="text-sm font-medium text-slate-700">
            {{ mhs.dynamicHeadline() }}
          </p>
        </div>

        <div class="flex items-center gap-3 pt-1">
          <a
            routerLink="/migration/create"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/40">
            <app-lucide-icon name="plus" [size]="15"></app-lucide-icon>
            <span>Create Migration</span>
          </a>
        </div>
      </div>

      <!-- Database Unavailable Warning (Section 34) -->
      @if (mhs.isUnavailable()) {
        <div class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2.5">
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
            <span class="font-semibold">{{ mhs.errorMessage() }}</span>
          </div>
          <button
            type="button"
            (click)="mhs.loadState()"
            class="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs cursor-pointer">
            Retry Connection
          </button>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 2. STATUS OVERVIEW — 4 EQUAL KPI CARDS (SECTION 14-15)          -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <!-- ACTIVE KPI CARD -->
        <div class="p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between h-28">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-600 uppercase tracking-wider">ACTIVE</span>
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          </div>
          <div class="flex items-baseline justify-between gap-2">
            <span class="text-3xl font-bold text-slate-900 tracking-tight">
              {{ mhs.computedCounters().active }}
            </span>
            <span class="text-xs font-medium text-slate-600">
              {{ mhs.computedCounters().active }} progressing
            </span>
          </div>
        </div>

        <!-- ATTENTION KPI CARD -->
        <div class="p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between h-28">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-amber-700 uppercase tracking-wider">ATTENTION</span>
            <span class="w-2 h-2 rounded-full" [class.bg-amber-500]="mhs.computedCounters().attention > 0" [class.bg-slate-300]="mhs.computedCounters().attention === 0"></span>
          </div>
          <div class="flex items-baseline justify-between gap-2">
            <span class="text-3xl font-bold text-slate-900 tracking-tight" [class.text-amber-700]="mhs.computedCounters().attention > 0">
              {{ mhs.computedCounters().attention }}
            </span>
            <span class="text-xs font-medium text-slate-600">
              {{ mhs.computedCounters().attention > 0 ? 'Actionable items' : 'All clear' }}
            </span>
          </div>
        </div>

        <!-- SCHEDULED KPI CARD -->
        <div class="p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between h-28">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-600 uppercase tracking-wider">SCHEDULED</span>
            <span class="w-2 h-2 rounded-full bg-slate-400"></span>
          </div>
          <div class="flex items-baseline justify-between gap-2">
            <span class="text-3xl font-bold text-slate-900 tracking-tight">
              {{ mhs.computedCounters().scheduled }}
            </span>
            <span class="text-xs font-medium text-slate-600">Maintenance window</span>
          </div>
        </div>

        <!-- COMPLETED KPI CARD -->
        <div class="p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between h-28">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-600 uppercase tracking-wider">COMPLETED</span>
            <span class="w-2 h-2 rounded-full bg-blue-500"></span>
          </div>
          <div class="flex items-baseline justify-between gap-2">
            <span class="text-3xl font-bold text-slate-900 tracking-tight">
              {{ mhs.computedCounters().completed }}
            </span>
            <span class="text-xs font-medium text-slate-600">100% verified</span>
          </div>
        </div>

      </div>

      <!-- =============================================================== -->
      <!-- 3. CORE MIGRATION FUNCTIONS — 6 LARGE FUNCTIONAL CARDS (16-18)  -->
      <!-- =============================================================== -->
      <div class="flex flex-col gap-3.5">
        <span class="text-xs font-bold text-slate-600 uppercase tracking-wider">CORE MIGRATION FUNCTIONS</span>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          @for (card of functionCards; track card.title) {
            <div
              (click)="navigateTo(card.route)"
              (keydown.enter)="navigateTo(card.route)"
              (keydown.space)="navigateTo(card.route)"
              tabindex="0"
              role="button"
              [attr.aria-label]="card.title + ': ' + card.description"
              class="p-5 rounded-xl bg-white border border-slate-200/90 hover:border-blue-500 hover:shadow-xs transition-all duration-150 flex flex-col justify-between h-36 cursor-pointer group select-none focus:outline-none focus:ring-2 focus:ring-blue-500/40">
              
              <div class="flex items-start gap-3.5">
                <div class="w-9 h-9 rounded-lg {{ card.iconBg }} {{ card.iconColor }} flex items-center justify-center shrink-0">
                  <app-lucide-icon [name]="card.iconName" [size]="18"></app-lucide-icon>
                </div>
                <div class="flex flex-col">
                  <h3 class="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                    {{ card.title }}
                  </h3>
                  <p class="text-xs text-slate-600 font-normal pt-0.5">
                    {{ card.description }}
                  </p>
                </div>
              </div>

              <!-- Action Button (Pill Button, Single Arrow, Blue Hover) -->
              <div class="pt-2 flex items-center justify-end">
                <div class="h-7 px-3 rounded-lg bg-slate-50 group-hover:bg-blue-50 border border-slate-200/80 group-hover:border-blue-200 text-slate-700 group-hover:text-blue-700 text-xs font-semibold transition-all duration-150 inline-flex items-center gap-1.5 shadow-2xs">
                  <span>{{ card.actionText }}</span>
                  <app-lucide-icon name="arrow-right" [size]="13" class="text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all"></app-lucide-icon>
                </div>
              </div>

            </div>
          }
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- 4. INDEPENDENT MIGRATIONS TABLE (SECTION 19-21)                 -->
      <!-- =============================================================== -->
      <div class="p-6 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-4">
        
        <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider">INDEPENDENT MIGRATIONS</span>
            <span class="text-xs text-slate-500 font-medium">({{ independentMigrations().length }})</span>
          </div>
          <a routerLink="/migration/projects" class="h-7 px-2.5 rounded-lg bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200/80 hover:border-blue-200 text-xs font-semibold transition-all shadow-2xs inline-flex items-center gap-1.5 group/btn cursor-pointer">
            <span>View all</span>
            <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover/btn:text-blue-600 group-hover/btn:translate-x-0.5 transition-all"></app-lucide-icon>
          </a>
        </div>

        @if (independentMigrations().length === 0) {
          <div class="py-12 flex flex-col items-center justify-center text-center gap-2">
            <app-lucide-icon name="database" [size]="28" class="text-slate-300"></app-lucide-icon>
            <span class="text-xs font-semibold text-slate-700">No independent migrations active</span>
            <p class="text-xs text-slate-600 font-normal">Create an independent migration to run outside project groups.</p>
          </div>
        } @else {
          <div class="overflow-x-auto">
            <div class="min-w-[840px] flex flex-col divide-y divide-slate-100 font-normal">
              
              <!-- 4 Mathematically Equal Data Columns (25% each) + Extreme-Right Action Slot -->
              <div class="flex items-center justify-between gap-6 px-4 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider bg-slate-50/60 rounded-lg">
                <div class="grid grid-cols-4 items-center gap-6 flex-1 min-w-0">
                  <div>Migration</div>
                  <div>Route</div>
                  <div>Mode</div>
                  <div>State</div>
                </div>
                <div class="w-28 text-right shrink-0"></div>
              </div>

              <!-- Data Rows: 4 Mathematically Equal Columns (25% each) + Extreme-Right Action Button -->
              @for (m of independentMigrations(); track m.id) {
                <div class="flex items-center justify-between gap-6 px-4 py-3.5 hover:bg-slate-50/80 transition-colors h-16 text-xs">
                  
                  <div class="grid grid-cols-4 items-center gap-6 flex-1 min-w-0">
                    <!-- Migration Name & Stage -->
                    <div class="flex flex-col gap-0.5 min-w-0">
                      <a [routerLink]="['/migration', m.id]" class="font-bold text-slate-900 hover:text-blue-600 transition-colors truncate">
                        {{ m.name }}
                      </a>
                      <span class="text-xs text-slate-600 truncate">{{ m.current_stage }}</span>
                    </div>

                    <!-- Route -->
                    <div class="whitespace-nowrap text-slate-800 font-semibold truncate flex items-center gap-2">
                      <span class="truncate">{{ m.source_provider }}</span>
                      <span class="text-slate-400 font-normal">&rarr;</span>
                      <span class="text-slate-900 truncate">{{ m.target_provider }}</span>
                    </div>

                    <!-- Mode -->
                    <div class="whitespace-nowrap">
                      <app-status-badge [mode]="m.mode"></app-status-badge>
                    </div>

                    <!-- State -->
                    <div class="whitespace-nowrap">
                      <app-status-badge [lifecycle]="m.lifecycle_state"></app-status-badge>
                    </div>
                  </div>

                  <!-- Extreme Right Action Button -->
                  <div class="w-28 flex justify-end shrink-0 whitespace-nowrap">
                    <a
                      [routerLink]="['/migration', m.id]"
                      class="h-7 px-3 rounded-lg bg-slate-50 hover:bg-blue-50 border border-slate-200/80 hover:border-blue-200 text-slate-700 hover:text-blue-700 text-xs font-semibold transition-all inline-flex items-center gap-1.5 shadow-2xs group/btn cursor-pointer">
                      <span>Open Cockpit</span>
                      <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover/btn:text-blue-600 group-hover/btn:translate-x-0.5 transition-all"></app-lucide-icon>
                    </a>
                  </div>

                </div>
              }
            </div>
          </div>
        }

      </div>

      <!-- =============================================================== -->
      <!-- 5. PROJECTS & INITIATIVES CARDS (SECTION 22-24)                 -->
      <!-- =============================================================== -->
      <div class="flex flex-col gap-3.5">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <span class="text-xs font-bold text-slate-600 uppercase tracking-wider">PROJECTS &amp; INITIATIVES</span>
          <a routerLink="/migration/projects" class="h-7 px-2.5 rounded-lg bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200/80 hover:border-blue-200 text-xs font-semibold transition-all shadow-2xs inline-flex items-center gap-1.5 group/btn cursor-pointer">
            <span>View all</span>
            <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover/btn:text-blue-600 group-hover/btn:translate-x-0.5 transition-all"></app-lucide-icon>
          </a>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-stretch">
          @for (proj of mhs.projects(); track proj.id) {
            <div class="p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between h-full min-h-[280px]">
              
              <div class="flex flex-col gap-3">
                <div class="flex items-center justify-between">
                  <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">{{ proj.environment }}</span>
                  <span class="px-2 py-0.5 rounded text-[11px] font-bold border"
                        [class.bg-emerald-50]="proj.health === 'HEALTHY'"
                        [class.text-emerald-700]="proj.health === 'HEALTHY'"
                        [class.border-emerald-200]="proj.health === 'HEALTHY'"
                        [class.bg-amber-50]="proj.health !== 'HEALTHY'"
                        [class.text-amber-800]="proj.health !== 'HEALTHY'"
                        [class.border-amber-200]="proj.health !== 'HEALTHY'">
                    {{ proj.health }}
                  </span>
                </div>

                <h3 class="text-sm font-bold text-slate-900 leading-snug">
                  {{ proj.name }}
                </h3>

                <div class="flex items-center gap-2 text-xs text-slate-600 font-medium">
                  <span>{{ proj.migration_count }} migrations</span>
                  <span>&bull;</span>
                  <span>
                    {{ proj.active_count }} active
                    {{ proj.attention_count > 0 ? ('· ' + proj.attention_count + ' attention') : '· All clear' }}
                  </span>
                </div>

                <!-- Progress Bar -->
                <div class="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden mt-0.5">
                  <div
                    class="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                    [style.width.%]="proj.delivery_percent">
                  </div>
                </div>

                <!-- Dynamic Remaining Time -->
                <div class="flex items-center justify-between text-xs pt-0.5">
                  <span class="font-bold text-slate-900">
                    {{ mhs.formatProjectRemainingTime(proj.target_date).primary }}
                  </span>
                  <span class="text-slate-500 font-medium">
                    {{ mhs.formatProjectRemainingTime(proj.target_date).secondary }}
                  </span>
                </div>

                <!-- Contextual Attention Warning (With consistent height budget) -->
                <div class="min-h-[28px] flex items-center">
                  @if (proj.attention_count > 0) {
                    <div class="w-full p-2 rounded-lg bg-amber-50 text-amber-800 text-xs font-semibold flex items-center gap-1.5 border border-amber-200">
                      <app-lucide-icon name="alert-circle" [size]="13" class="text-amber-600 shrink-0"></app-lucide-icon>
                      <span>{{ proj.attention_count }} item{{ proj.attention_count === 1 ? '' : 's' }} need attention</span>
                    </div>
                  }
                </div>
              </div>

              <!-- Premium Card Footer Action (Firmly bottom aligned) -->
              <div class="pt-4 mt-auto border-t border-slate-100 flex items-center">
                <a [routerLink]="['/migration/projects', proj.id]" class="w-full h-8 px-3 rounded-lg bg-slate-50 hover:bg-blue-50 border border-slate-200/80 hover:border-blue-200 text-slate-700 hover:text-blue-700 text-xs font-semibold transition-all flex items-center justify-center gap-1.5 shadow-2xs group/btn cursor-pointer">
                  <span>Open Project</span>
                  <app-lucide-icon name="arrow-right" [size]="13" class="text-slate-400 group-hover/btn:text-blue-600 group-hover/btn:translate-x-0.5 transition-all"></app-lucide-icon>
                </a>
              </div>

            </div>
          }
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- 6. RECENT ACTIVITY — DEDICATED FULL-WIDTH CARD (SECTION 25-28)  -->
      <!-- =============================================================== -->
      <div class="p-6 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-4">
        
        <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="activity" [size]="16" class="text-blue-600"></app-lucide-icon>
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider">RECENT ACTIVITY</span>
          </div>
          <a routerLink="/migration/history" class="h-7 px-2.5 rounded-lg bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200/80 hover:border-blue-200 text-xs font-semibold transition-all shadow-2xs inline-flex items-center gap-1.5 group/btn cursor-pointer">
            <span>View all history</span>
            <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover/btn:text-blue-600 group-hover/btn:translate-x-0.5 transition-all"></app-lucide-icon>
          </a>
        </div>

        @if (mhs.activities().length === 0) {
          <div class="py-8 flex flex-col items-center justify-center text-center gap-1 text-slate-500">
            <span class="text-xs font-medium">No migration activity yet.</span>
          </div>
        } @else {
          <div class="flex flex-col divide-y divide-slate-100 font-normal">
            @for (act of mhs.activities(); track act.id) {
              <div class="py-3.5 first:pt-0 last:pb-0 flex items-center justify-between gap-4 text-xs">
                
                <div class="flex items-center gap-3.5 min-w-0">
                  <!-- Severity Dot -->
                  <div
                    class="w-2 h-2 rounded-full shrink-0"
                    [class.bg-emerald-500]="act.severity === 'SUCCESS'"
                    [class.bg-amber-500]="act.severity === 'WARNING'"
                    [class.bg-blue-500]="act.severity === 'INFO'"
                    [class.bg-rose-500]="act.severity === 'ERROR'">
                  </div>

                  <!-- Relative and Exact Time in clean Roboto -->
                  <div class="flex flex-col shrink-0 w-24">
                    <span class="font-bold text-slate-900 text-xs">
                      {{ mhs.formatRelativeTime(act.occurred_at).relative }}
                    </span>
                    <span class="text-[11px] text-slate-500 font-medium">
                      {{ mhs.formatRelativeTime(act.occurred_at).exactTime }}
                    </span>
                  </div>

                  <!-- Activity Title & Subject Name -->
                  <div class="flex flex-col min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                      <span class="font-bold text-slate-900">{{ act.title }}</span>
                      <span class="text-slate-300">&bull;</span>
                      <span class="font-semibold text-blue-700 truncate">{{ act.subject_name }}</span>
                    </div>
                    <span class="text-xs text-slate-600 truncate font-normal">{{ act.status_text }}</span>
                  </div>
                </div>

                <!-- Action Button (Enterprise Blue / Amber Hover) -->
                <div class="shrink-0">
                  <a
                    [routerLink]="getActivityRoute(act)"
                    class="h-7 px-3 rounded-lg border text-xs font-semibold transition-all inline-flex items-center gap-1.5 shadow-2xs group/btn cursor-pointer"
                    [ngClass]="act.action_type === 'REVIEW' 
                      ? 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100 hover:border-amber-300' 
                      : 'bg-slate-50 text-slate-700 border-slate-200/80 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200'">
                    <span>{{ act.action_type === 'REVIEW' ? 'Review' : 'View' }}</span>
                    <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover/btn:text-blue-600 group-hover/btn:translate-x-0.5 transition-all"></app-lucide-icon>
                  </a>
                </div>

              </div>
            }
          </div>
        }

      </div>

    </div>
  `
})
export class MigrationPortfolioComponent {
  public mhs = inject(MigrationHomeService);
  private router = inject(Router);

  public functionCards: CoreFunctionCard[] = [
    {
      title: 'Create Migration',
      description: 'Start a new migration.',
      actionText: 'Create',
      iconName: 'plus-circle',
      route: '/migration/create',
      iconBg: 'bg-blue-50',
      iconColor: 'text-blue-600'
    },
    {
      title: 'Projects',
      description: 'Coordinate migration initiatives.',
      actionText: 'Open',
      iconName: 'folder-git-2',
      route: '/migration/projects',
      iconBg: 'bg-indigo-50',
      iconColor: 'text-indigo-600'
    },
    {
      title: 'Connections',
      description: 'Manage reusable endpoints.',
      actionText: 'Open',
      iconName: 'database',
      route: '/migration/connections',
      iconBg: 'bg-emerald-50',
      iconColor: 'text-emerald-600'
    },
    {
      title: 'Validation',
      description: 'Prove synchronization.',
      actionText: 'Open',
      iconName: 'shield-check',
      route: '/migration/validation',
      iconBg: 'bg-purple-50',
      iconColor: 'text-purple-600'
    },
    {
      title: 'Templates',
      description: 'Reuse migration blueprints.',
      actionText: 'Browse',
      iconName: 'file-code-2',
      route: '/migration/templates',
      iconBg: 'bg-amber-50',
      iconColor: 'text-amber-600'
    },
    {
      title: 'History & Evidence',
      description: 'Investigate what happened.',
      actionText: 'Open',
      iconName: 'history',
      route: '/migration/history',
      iconBg: 'bg-sky-50',
      iconColor: 'text-sky-600'
    }
  ];

  public independentMigrations() {
    return this.mhs.migrations().filter(m => !m.project_id);
  }

  public navigateTo(route: string): void {
    this.router.navigate([route]);
  }

  public getActivityRoute(act: any): string[] {
    if (act.subject_type === 'migration') {
      return ['/migration', act.subject_id];
    }
    if (act.subject_type === 'validation') {
      return ['/migration/validation', act.subject_id];
    }
    if (act.subject_type === 'project') {
      return ['/migration/projects', act.subject_id];
    }
    return ['/migration/history'];
  }
}
