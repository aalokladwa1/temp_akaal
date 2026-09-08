import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConnectionWorkspaceService } from '../connection-workspace.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-tab-usage',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (ws.connection(); as conn) {
      <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
        
        <!-- Top Header & Summary -->
        <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-3">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider font-heading">
              Connection Usage &amp; Dependency Governance
            </h2>
            <p class="text-xs text-slate-500 font-normal">
              Association across Projects, referencing Migration workflows, and active Validation missions.
            </p>
          </div>

          <!-- Active Streams & Scheduled Runs Counter Badges -->
          <div class="flex items-center gap-2">
            <span class="px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <strong class="font-mono">{{ conn.usage.activeStreamsCount }}</strong> Active Streams
            </span>
            <span class="px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
              <strong class="font-mono">{{ conn.usage.scheduledExecutionsCount }}</strong> Scheduled
            </span>
          </div>
        </div>

        <!-- Dependency / Reference Protection Alert Banner -->
        @if (conn.usage.referenceProtection.isReferenced) {
          <div class="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-start gap-3.5 text-xs text-slate-800 shadow-2xs">
            <app-lucide-icon name="shield" [size]="16" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
            <div class="flex flex-col gap-1">
              <span class="font-bold text-slate-900">Reference Protection Active</span>
              <p class="text-slate-600 leading-relaxed">{{ conn.usage.referenceProtection.blockReason }}</p>
              <div class="pt-1">
                <button
                  type="button"
                  (click)="ws.setActiveTab('settings')"
                  class="text-xs font-semibold text-blue-600 hover:text-blue-800 cursor-pointer">
                  Go to Settings to Archive &rarr;
                </button>
              </div>
            </div>
          </div>
        }

        <!-- ========================================================================= -->
        <!-- 1. ASSOCIATED PROJECTS (PRIMARY REUSABLE RESOURCE CONTEXT)                -->
        <!-- ========================================================================= -->
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="building-2" [size]="16" class="text-blue-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                1. Associated Projects ({{ conn.usage.projects.length }})
              </span>
            </div>
            <span class="text-[11px] text-slate-400">Primary reusable-resource association context</span>
          </div>

          @if (conn.usage.projects.length > 0) {
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                    <th class="py-2.5 px-3">Project Key</th>
                    <th class="py-2.5 px-3">Project Name</th>
                    <th class="py-2.5 px-3">Environment</th>
                    <th class="py-2.5 px-3">Status</th>
                    <th class="py-2.5 px-3 text-right">Associated Date</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                  @for (proj of conn.usage.projects; track proj.id) {
                    <tr class="hover:bg-slate-50/60 transition-colors">
                      <td class="py-3 px-3 font-mono font-bold text-blue-700">{{ proj.key }}</td>
                      <td class="py-3 px-3 font-semibold text-slate-900">{{ proj.name }}</td>
                      <td class="py-3 px-3 text-slate-600">{{ proj.environment }}</td>
                      <td class="py-3 px-3">
                        <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {{ proj.status }}
                        </span>
                      </td>
                      <td class="py-3 px-3 text-right text-slate-400 font-mono">{{ proj.associatedAt | date:'mediumDate' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          } @else {
            <div class="p-6 text-center text-slate-400 text-xs bg-slate-50 rounded-lg border border-dashed border-slate-200">
              No Projects currently reference this Connection profile.
            </div>
          }
        </div>

        <!-- ========================================================================= -->
        <!-- 2. REFERENCING MIGRATION WORKFLOWS                                        -->
        <!-- ========================================================================= -->
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="arrow-left-right" [size]="16" class="text-blue-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                2. Referencing Migration Workflows ({{ conn.usage.migrations.length }})
              </span>
            </div>
          </div>

          @if (conn.usage.migrations.length > 0) {
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                    <th class="py-2.5 px-3">Migration Name</th>
                    <th class="py-2.5 px-3">Project</th>
                    <th class="py-2.5 px-3">Role</th>
                    <th class="py-2.5 px-3">Execution Mode</th>
                    <th class="py-2.5 px-3">State</th>
                    <th class="py-2.5 px-3 text-right">Last Execution</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                  @for (mig of conn.usage.migrations; track mig.id) {
                    <tr class="hover:bg-slate-50/60 transition-colors">
                      <td class="py-3 px-3 font-semibold text-slate-900">{{ mig.name }}</td>
                      <td class="py-3 px-3 font-mono font-medium text-slate-600">{{ mig.projectKey }}</td>
                      <td class="py-3 px-3">
                        <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                          {{ mig.role }}
                        </span>
                      </td>
                      <td class="py-3 px-3 font-mono text-slate-600">{{ mig.mode }}</td>
                      <td class="py-3 px-3">
                        <span
                          class="px-2 py-0.5 rounded text-[10px] font-semibold"
                          [class.bg-emerald-50]="mig.state === 'EXECUTING'"
                          [class.text-emerald-700]="mig.state === 'EXECUTING'"
                          [class.border-emerald-200]="mig.state === 'EXECUTING'"
                          [class.border]="true"
                          [class.bg-blue-50]="mig.state === 'COMPLETED'"
                          [class.text-blue-700]="mig.state === 'COMPLETED'"
                          [class.border-blue-200]="mig.state === 'COMPLETED'">
                          {{ mig.state }}
                        </span>
                      </td>
                      <td class="py-3 px-3 text-right text-slate-400 font-mono">{{ mig.lastRunAt | date:'medium' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          } @else {
            <div class="p-6 text-center text-slate-400 text-xs bg-slate-50 rounded-lg border border-dashed border-slate-200">
              No active or historical migrations reference this Connection.
            </div>
          }
        </div>

        <!-- ========================================================================= -->
        <!-- 3. REFERENCING VALIDATION MISSIONS                                        -->
        <!-- ========================================================================= -->
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="shield-check" [size]="16" class="text-blue-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                3. Referencing Validation Missions ({{ conn.usage.validations.length }})
              </span>
            </div>
          </div>

          @if (conn.usage.validations.length > 0) {
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                    <th class="py-2.5 px-3">Mission Name</th>
                    <th class="py-2.5 px-3">Project</th>
                    <th class="py-2.5 px-3">Scope Role</th>
                    <th class="py-2.5 px-3">Verdict</th>
                    <th class="py-2.5 px-3 text-right">Last Verified</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                  @for (val of conn.usage.validations; track val.id) {
                    <tr class="hover:bg-slate-50/60 transition-colors">
                      <td class="py-3 px-3 font-semibold text-slate-900">{{ val.name }}</td>
                      <td class="py-3 px-3 font-mono font-medium text-slate-600">{{ val.projectKey }}</td>
                      <td class="py-3 px-3 text-slate-600">{{ val.role }}</td>
                      <td class="py-3 px-3">
                        <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {{ val.verdict }}
                        </span>
                      </td>
                      <td class="py-3 px-3 text-right text-slate-400 font-mono">{{ val.lastRunAt | date:'medium' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          } @else {
            <div class="p-6 text-center text-slate-400 text-xs bg-slate-50 rounded-lg border border-dashed border-slate-200">
              No validation missions currently reference this Connection.
            </div>
          }
        </div>

      </div>
    }
  `
})
export class TabUsageComponent {
  public ws = inject(ConnectionWorkspaceService);
}
