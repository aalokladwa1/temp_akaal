import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { TemplateWorkspaceService } from '../template-workspace.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { TEMPLATE_MODE_DESCRIPTORS, TemplateMigrationMode, TemplateLifecycle, TemplateScope } from '../../templates.models';

@Component({
  selector: 'app-template-workspace-header',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <header class="bg-white border-b border-slate-200 px-6 lg:px-8 py-4 sticky top-0 z-30 shadow-2xs select-none">
      <div class="max-w-[1680px] mx-auto flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        
        <!-- Identity Zone -->
        @if (ws.template(); as tmpl) {
          <div class="flex flex-col gap-2 min-w-0 flex-1">
            
            <!-- Breadcrumbs & Context Badges -->
            <div class="flex items-center flex-wrap gap-2 text-xs">
              <span class="text-slate-500 font-medium">AKAAL Enterprise</span>
              <span class="text-slate-300">/</span>
              <a routerLink="/migration/templates" class="text-slate-500 hover:text-blue-600 font-medium transition-colors">
                Templates
              </a>
              <span class="text-slate-300">/</span>
              
              <!-- Canonical Template ID copy trigger -->
              <button
                type="button"
                (click)="ws.copyTemplateId()"
                class="inline-flex items-center gap-1.5 font-mono text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 hover:border-blue-300 transition-colors border border-slate-200 cursor-pointer"
                [title]="'Click to copy template ID: ' + tmpl.id">
                <span>{{ tmpl.id }}</span>
                <app-lucide-icon
                  [name]="ws.copiedId() ? 'check' : 'copy'"
                  [size]="12"
                  [class]="ws.copiedId() ? 'text-emerald-600' : 'text-slate-400'"></app-lucide-icon>
              </button>

              <!-- Scope Tag -->
              <span class="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-50 text-slate-700 border border-slate-200">
                {{ formatScope(tmpl.scope) }}
              </span>

              <!-- Version Tag -->
              <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200">
                {{ tmpl.versionLabel }}
              </span>
            </div>

            <!-- Main Heading Row: Icon + Name + Mode Badge + Applicability + Lifecycle Badge -->
            <div class="flex items-center flex-wrap gap-3 pt-0.5">
              
              <div class="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700 shrink-0">
                <app-lucide-icon name="file-text" [size]="17"></app-lucide-icon>
              </div>

              <h1 class="text-xl font-bold text-slate-900 tracking-tight font-heading truncate max-w-2xl">
                {{ tmpl.name }}
              </h1>

              <!-- Clean Mode Badge (Human-Readable Label, Zero MN Prefix) -->
              <span class="px-2.5 py-0.5 rounded-md text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200 shrink-0">
                {{ getModeLabel(tmpl.mode) }}
              </span>

              <!-- Applicability Pair: Source -> Target -->
              <span class="px-2.5 py-0.5 rounded-md text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 shrink-0 font-mono">
                {{ tmpl.applicability.sourceProviderName }} &rarr; {{ tmpl.applicability.targetProviderName }}
              </span>

              <!-- Lifecycle State Badge -->
              <span
                class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-bold border select-none shrink-0"
                [class.bg-emerald-50]="tmpl.lifecycle === 'PUBLISHED'"
                [class.text-emerald-700]="tmpl.lifecycle === 'PUBLISHED'"
                [class.border-emerald-200]="tmpl.lifecycle === 'PUBLISHED'"
                [class.bg-amber-50]="tmpl.lifecycle === 'DRAFT'"
                [class.text-amber-700]="tmpl.lifecycle === 'DRAFT'"
                [class.border-amber-200]="tmpl.lifecycle === 'DRAFT'"
                [class.bg-rose-50]="tmpl.lifecycle === 'DEPRECATED'"
                [class.text-rose-700]="tmpl.lifecycle === 'DEPRECATED'"
                [class.border-rose-200]="tmpl.lifecycle === 'DEPRECATED'"
                [class.bg-slate-100]="tmpl.lifecycle === 'ARCHIVED'"
                [class.text-slate-700]="tmpl.lifecycle === 'ARCHIVED'"
                [class.border-slate-200]="tmpl.lifecycle === 'ARCHIVED'">
                <span
                  class="w-1.5 h-1.5 rounded-full"
                  [class.bg-emerald-500]="tmpl.lifecycle === 'PUBLISHED'"
                  [class.bg-amber-500]="tmpl.lifecycle === 'DRAFT'"
                  [class.bg-rose-500]="tmpl.lifecycle === 'DEPRECATED'"
                  [class.bg-slate-400]="tmpl.lifecycle === 'ARCHIVED'"></span>
                <span>{{ tmpl.lifecycle }}</span>
              </span>

            </div>

          </div>

          <!-- Actions Zone: Text-Only Action Buttons (Permanent Law) -->
          <div class="flex items-center gap-2.5 shrink-0 pt-2 lg:pt-0">
            
            <button
              type="button"
              (click)="navigateToCreateMigration(tmpl.id)"
              class="h-9 px-4 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/40">
              Apply to Migration
            </button>

            <button
              type="button"
              (click)="ws.setActiveTab('configuration'); ws.startEditingConfig()"
              class="h-9 px-3.5 rounded-md bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold border border-slate-200 shadow-2xs transition-colors cursor-pointer">
              Edit Configuration
            </button>

            <button
              type="button"
              (click)="ws.openNewVersionDialog()"
              class="h-9 px-3.5 rounded-md bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold border border-slate-200 shadow-2xs transition-colors cursor-pointer">
              New Version
            </button>

          </div>
        }

      </div>
    </header>
  `
})
export class TemplateWorkspaceHeaderComponent {
  public ws = inject(TemplateWorkspaceService);
  private router = inject(Router);

  public getModeLabel(mode: TemplateMigrationMode): string {
    return TEMPLATE_MODE_DESCRIPTORS[mode]?.label || mode;
  }

  public formatScope(scope: TemplateScope): string {
    switch (scope) {
      case 'ORGANIZATION':
        return 'Organization Scope';
      case 'WORKSPACE':
        return 'Workspace Scope';
      case 'PROJECT':
        return 'Project Scope';
      default:
        return scope;
    }
  }

  public navigateToCreateMigration(templateId: string): void {
    this.router.navigate(['/migration/create'], { queryParams: { templateId } });
  }
}
