import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { TemplateWorkspaceService } from '../template-workspace.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-tab-template-usage',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 text-xs font-sans animate-in fade-in duration-150">
      
      @if (ws.template(); as tmpl) {
        
        <!-- SECTION 1: USAGE & REFERENCE METRICS -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div class="flex flex-col">
              <span class="font-bold text-slate-900 text-sm">Template Usage & Materialization Dependencies</span>
              <span class="text-xs text-slate-500 font-normal">Tracking active projects and migrations instantiated from this template.</span>
            </div>
            
            <!-- Reference Protection Badge -->
            <div
              class="px-2.5 py-1 rounded-md text-xs font-semibold border flex items-center gap-1.5"
              [class]="tmpl.referenceProtection.isProtected ? 'bg-amber-50 text-amber-800 border-amber-300' : 'bg-slate-50 text-slate-700 border-slate-200'">
              <app-lucide-icon [name]="tmpl.referenceProtection.isProtected ? 'shield' : 'check'" [size]="13"></app-lucide-icon>
              <span>{{ tmpl.referenceProtection.isProtected ? 'Reference Protected (Active Migrations)' : 'No Active Lock' }}</span>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Referenced Projects</span>
              <span class="text-base font-bold text-slate-900 font-heading">{{ tmpl.usage.referencedProjectCount }} Projects</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Materialized Migrations</span>
              <span class="text-base font-bold text-slate-900 font-heading">{{ tmpl.usage.migrationCount }} Migrations</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Active / Running Migrations</span>
              <span class="text-base font-bold text-blue-600 font-heading">{{ tmpl.referenceProtection.activeMigrationCount }} Active</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Last Applied Date</span>
              <span class="text-xs font-semibold text-slate-800">{{ (tmpl.usage.lastUsedAt | date:'mediumDate') || 'Never used' }}</span>
            </div>
          </div>
        </div>

        <!-- SECTION 2: MATERIALIZATION LAW BANNER (Permanent Law) -->
        <div class="p-3.5 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-3">
          <app-lucide-icon name="info" [size]="16" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
          <div class="flex flex-col gap-0.5">
            <span class="font-bold text-slate-900">Independent Migration Materialization</span>
            <p class="text-[11px] text-slate-600 font-normal m-0 leading-relaxed">
              When an engineer provisions a migration from this template, values are materialized into the new migration's independent execution plan. Any subsequent updates to this template will <strong>never</strong> modify initialized or running migrations.
            </p>
          </div>
        </div>

        <!-- SECTION 3: MIGRATIONS CREATED TABLE -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3.5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900 text-sm">Migrations Materialized from this Template</span>
            <span class="text-[10px] font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
              {{ tmpl.usage.migrations.length }} Records
            </span>
          </div>

          <div class="overflow-x-auto border border-slate-200 rounded-md">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase">
                  <th class="px-3 py-2.5">Migration Name</th>
                  <th class="px-3 py-2.5">Bound Project</th>
                  <th class="px-3 py-2.5">Template Version Used</th>
                  <th class="px-3 py-2.5">Status</th>
                  <th class="px-3 py-2.5">Applied Date</th>
                  <th class="px-3 py-2.5 text-right">Overrides</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (m of tmpl.usage.migrations; track m.migrationId) {
                  <tr class="hover:bg-slate-50/70 transition-colors">
                    <td class="px-3 py-2.5 font-mono font-bold text-slate-900 text-xs">
                      {{ m.migrationName }}
                    </td>
                    <td class="px-3 py-2.5 text-slate-700 font-medium">{{ m.projectName }}</td>
                    <td class="px-3 py-2.5 font-mono text-blue-600 font-semibold">{{ m.versionUsedAtInstantiation }}</td>
                    <td class="px-3 py-2.5">
                      <span
                        class="px-2 py-0.5 text-[10px] font-bold rounded-md"
                        [class.bg-blue-50]="m.lifecycleState === 'RUNNING'"
                        [class.text-blue-700]="m.lifecycleState === 'RUNNING'"
                        [class.border-blue-200]="m.lifecycleState === 'RUNNING'"
                        [class.bg-emerald-50]="m.lifecycleState === 'COMPLETED'"
                        [class.text-emerald-700]="m.lifecycleState === 'COMPLETED'"
                        [class.border-emerald-200]="m.lifecycleState === 'COMPLETED'"
                        [class.bg-slate-100]="m.lifecycleState === 'ARCHIVED'"
                        [class.text-slate-700]="m.lifecycleState === 'ARCHIVED'"
                        [class.border-slate-200]="m.lifecycleState === 'ARCHIVED'">
                        {{ m.lifecycleState }}
                      </span>
                    </td>
                    <td class="px-3 py-2.5 text-slate-600">{{ m.appliedAt | date:'mediumDate' }}</td>
                    <td class="px-3 py-2.5 text-right font-mono text-slate-600">
                      {{ m.overridesCount > 0 ? m.overridesCount + ' parameters' : 'Default' }}
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

        <!-- SECTION 4: REFERENCING PROJECTS TABLE -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3.5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900 text-sm">Projects Referencing this Template</span>
            <span class="text-[10px] font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
              {{ tmpl.usage.projects.length }} Projects
            </span>
          </div>

          <div class="overflow-x-auto border border-slate-200 rounded-md">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase">
                  <th class="px-3 py-2.5">Project Name</th>
                  <th class="px-3 py-2.5">Environment</th>
                  <th class="px-3 py-2.5">Scope Boundary</th>
                  <th class="px-3 py-2.5">Referencing Migrations</th>
                  <th class="px-3 py-2.5 text-right">Last Used</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (p of tmpl.usage.projects; track p.projectId) {
                  <tr class="hover:bg-slate-50/70 transition-colors">
                    <td class="px-3 py-2.5 font-bold text-slate-900 text-xs">{{ p.projectName }}</td>
                    <td class="px-3 py-2.5 text-slate-600">{{ p.environment }}</td>
                    <td class="px-3 py-2.5 text-slate-600 font-mono text-[11px]">{{ p.scope }}</td>
                    <td class="px-3 py-2.5 font-mono font-bold text-slate-900">{{ p.referencingMigrationCount }}</td>
                    <td class="px-3 py-2.5 text-right text-slate-600">{{ p.lastUsedAt | date:'mediumDate' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

      }

    </div>
  `
})
export class TabTemplateUsageComponent {
  public ws = inject(TemplateWorkspaceService);
}
