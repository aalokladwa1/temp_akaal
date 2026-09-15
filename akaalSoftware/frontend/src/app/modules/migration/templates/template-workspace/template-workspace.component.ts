import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { TemplateWorkspaceService } from './template-workspace.service';
import { TemplateWorkspaceTab } from './template-workspace.models';
import { TemplateWorkspaceHeaderComponent } from './components/template-workspace-header.component';
import { TemplateWorkspaceNavComponent } from './components/template-workspace-nav.component';
import { TabTemplateOverviewComponent } from './tabs/tab-template-overview.component';
import { TabTemplateConfigurationComponent } from './tabs/tab-template-configuration.component';
import { TabTemplateApplicabilityComponent } from './tabs/tab-template-applicability.component';
import { TabTemplateVersionsComponent } from './tabs/tab-template-versions.component';
import { TabTemplateUsageComponent } from './tabs/tab-template-usage.component';
import { TabTemplateActivityComponent } from './tabs/tab-template-activity.component';
import { TabTemplateSettingsComponent } from './tabs/tab-template-settings.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-template-workspace',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TemplateWorkspaceHeaderComponent,
    TemplateWorkspaceNavComponent,
    TabTemplateOverviewComponent,
    TabTemplateConfigurationComponent,
    TabTemplateApplicabilityComponent,
    TabTemplateVersionsComponent,
    TabTemplateUsageComponent,
    TabTemplateActivityComponent,
    TabTemplateSettingsComponent,
    LucideIconComponent
  ],
  template: `
    <div class="min-h-screen bg-slate-50/60 font-sans select-none flex flex-col text-slate-800">
      
      <!-- Top Persistent Identity & Actions Header -->
      <app-template-workspace-header />

      <!-- Horizontal 7-Tab Navigation Bar -->
      <app-template-workspace-nav />

      <!-- Main Workspace Viewport -->
      <main class="max-w-[1680px] w-full mx-auto p-6 lg:p-8 flex flex-col gap-6 flex-1">
        
        @if (ws.isLoading()) {
          <div class="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
            <app-lucide-icon name="loader" [size]="24" class="animate-spin text-blue-600"></app-lucide-icon>
            <span class="text-xs font-medium">Loading Template Workspace...</span>
          </div>
        } @else if (ws.errorMessage()) {
          <div class="p-8 text-center bg-white border border-rose-200 rounded-xl flex flex-col items-center gap-3">
            <app-lucide-icon name="alert-triangle" [size]="24" class="text-rose-600"></app-lucide-icon>
            <span class="text-sm font-bold text-slate-900">Unable to load template workspace</span>
            <p class="text-xs text-slate-500 max-w-md">{{ ws.errorMessage() }}</p>
            <button
              type="button"
              (click)="ws.loadTemplate(ws.templateId() || 'tmpl-ora-pg-m2')"
              class="h-8 px-4 bg-slate-800 hover:bg-slate-900 text-white rounded-md text-xs font-semibold cursor-pointer">
              Retry Loading
            </button>
          </div>
        } @else {
          
          @switch (ws.activeTab()) {
            
            <!-- Tab 1: OVERVIEW -->
            @case ('overview') {
              <app-tab-template-overview />
            }

            <!-- Tab 2: CONFIGURATION -->
            @case ('configuration') {
              <app-tab-template-configuration />
            }

            <!-- Tab 3: APPLICABILITY -->
            @case ('applicability') {
              <app-tab-template-applicability />
            }

            <!-- Tab 4: VERSIONS -->
            @case ('versions') {
              <app-tab-template-versions />
            }

            <!-- Tab 5: USAGE -->
            @case ('usage') {
              <app-tab-template-usage />
            }

            <!-- Tab 6: ACTIVITY -->
            @case ('activity') {
              <app-tab-template-activity />
            }

            <!-- Tab 7: SETTINGS -->
            @case ('settings') {
              <app-tab-template-settings />
            }

          }

        }

      </main>

      <!-- ========================================================================= -->
      <!-- MODAL 1: DELETE CONFIRMATION DIALOG                                       -->
      <!-- ========================================================================= -->
      @if (ws.isDeleteDialogOpen()) {
        <div class="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-100">
          <div class="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full p-6 flex flex-col gap-4">
            <div class="flex items-center gap-3 text-rose-600">
              <div class="w-10 h-10 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-center">
                <app-lucide-icon name="alert-triangle" [size]="20"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900 font-heading">Delete Template Specification</h3>
                <span class="text-xs text-slate-500">Consequential Operation</span>
              </div>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed m-0">
              Are you sure you want to permanently delete template <strong class="text-slate-900 font-mono">{{ ws.template()?.id }}</strong>? This action cannot be undone. Historical migrations will remain independent.
            </p>

            <div class="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                (click)="ws.closeDeleteDialog()"
                class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold cursor-pointer">
                Cancel
              </button>
              <button
                type="button"
                (click)="confirmDelete()"
                class="h-8 px-4 rounded-md bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold cursor-pointer">
                Delete Template
              </button>
            </div>
          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- MODAL 2: DEPRECATE CONFIRMATION DIALOG                                    -->
      <!-- ========================================================================= -->
      @if (ws.isDeprecateDialogOpen()) {
        <div class="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-100">
          <div class="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full p-6 flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
                <app-lucide-icon name="alert-circle" [size]="20"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900 font-heading">Deprecate Template</h3>
                <span class="text-xs text-slate-500">Lifecycle State Transition</span>
              </div>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed m-0">
              Deprecating <strong class="text-slate-900">{{ ws.template()?.name }}</strong> will warn operators against provisioning new migrations with it. Existing migrations and audit history remain unaffected.
            </p>

            <div class="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                (click)="ws.closeDeprecateDialog()"
                class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold cursor-pointer">
                Cancel
              </button>
              <button
                type="button"
                (click)="ws.applyDeprecate()"
                class="h-8 px-4 rounded-md bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold cursor-pointer">
                Confirm Deprecation
              </button>
            </div>
          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- MODAL 3: ARCHIVE CONFIRMATION DIALOG                                      -->
      <!-- ========================================================================= -->
      @if (ws.isArchiveDialogOpen()) {
        <div class="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-100">
          <div class="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full p-6 flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700">
                <app-lucide-icon name="archive" [size]="20"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900 font-heading">Archive Template</h3>
                <span class="text-xs text-slate-500">Read-Only Cold Storage</span>
              </div>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed m-0">
              Archiving <strong class="text-slate-900">{{ ws.template()?.name }}</strong> will lock all configuration and prevent new migration instantiation. Historical records remain viewable.
            </p>

            <div class="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                (click)="ws.closeArchiveDialog()"
                class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold cursor-pointer">
                Cancel
              </button>
              <button
                type="button"
                (click)="ws.applyArchive()"
                class="h-8 px-4 rounded-md bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold cursor-pointer">
                Confirm Archive
              </button>
            </div>
          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- MODAL 4: CREATE NEW VERSION DIALOG                                        -->
      <!-- ========================================================================= -->
      @if (ws.isNewVersionDialogOpen()) {
        <div class="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-100">
          <div class="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full p-6 flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="git-branch" [size]="20"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900 font-heading">Create New Revision</h3>
                <span class="text-xs text-slate-500">Version Incrementation</span>
              </div>
            </div>

            <div class="flex flex-col gap-1.5">
              <label for="rev-summary" class="font-semibold text-slate-800 text-xs">Summary of Changes</label>
              <textarea
                id="rev-summary"
                rows="3"
                [ngModel]="ws.newVersionSummary()"
                (ngModelChange)="ws.newVersionSummary.set($event)"
                placeholder="Describe parameter changes, concurrency updates, or masking additions in this revision..."
                class="p-2.5 bg-white border border-slate-200 rounded-md text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs resize-none"></textarea>
            </div>

            <div class="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                (click)="ws.closeNewVersionDialog()"
                class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold cursor-pointer">
                Cancel
              </button>
              <button
                type="button"
                (click)="confirmCreateVersion()"
                class="h-8 px-4 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold cursor-pointer shadow-2xs">
                Publish Revision
              </button>
            </div>
          </div>
        </div>
      }

    </div>
  `
})
export class TemplateWorkspaceComponent implements OnInit, OnDestroy {
  public ws = inject(TemplateWorkspaceService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private paramSub?: Subscription;

  public ngOnInit(): void {
    this.paramSub = this.route.paramMap.subscribe(params => {
      const id = params.get('templateId') || 'tmpl-ora-pg-m2';
      const tabParam = params.get('tab') as TemplateWorkspaceTab;
      
      this.ws.loadTemplate(id);

      if (tabParam && ['overview', 'configuration', 'applicability', 'versions', 'usage', 'activity', 'settings'].includes(tabParam)) {
        this.ws.setActiveTab(tabParam);
      }
    });
  }

  public ngOnDestroy(): void {
    this.paramSub?.unsubscribe();
  }

  public confirmDelete(): void {
    this.ws.closeDeleteDialog();
    this.router.navigate(['/migration/templates']);
  }

  public confirmCreateVersion(): void {
    const tmpl = this.ws.template();
    if (tmpl) {
      const nextRev = tmpl.revisionNumber + 1;
      const nextLabel = `v${nextRev}.0.0`;
      const newVer = {
        versionLabel: nextLabel,
        revisionNumber: nextRev,
        createdAt: new Date().toISOString(),
        createdBy: 'Current Operator',
        lifecycle: 'PUBLISHED' as const,
        changeSummary: this.ws.newVersionSummary() || 'Configuration revision update.',
        usageCount: 0,
        supersedesVersion: tmpl.versionLabel,
        isCurrent: true,
        configurationSnapshot: JSON.parse(JSON.stringify(tmpl.configuration))
      };
      const updatedVersions = [newVer, ...tmpl.versions.map(v => ({ ...v, isCurrent: false }))];
      this.ws.template.set({
        ...tmpl,
        versionLabel: nextLabel,
        revisionNumber: nextRev,
        versions: updatedVersions,
        updatedAt: new Date().toISOString()
      });
    }
    this.ws.closeNewVersionDialog();
  }
}
