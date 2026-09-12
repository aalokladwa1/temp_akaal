import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MigrationAlertsDTO } from '../../models/migration-monitoring.models';

@Component({
  selector: 'app-migration-alerts-tab',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Active Contextual Alerts -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Contextual Active Alerts</h3>
          <span class="text-xs text-slate-500 font-medium">{{ alerts.active_alerts.length }} alerts firing</span>
        </div>

        @if (alerts.active_alerts.length === 0) {
          <div class="p-6 rounded-xl bg-slate-50 border border-slate-100 text-center text-xs text-slate-500">
            No active alerts firing for this migration.
          </div>
        } @else {
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-600">
              <thead>
                <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                  <th class="py-2.5 px-3">Rule Name</th>
                  <th class="py-2.5 px-3">Component</th>
                  <th class="py-2.5 px-3">Triggered</th>
                  <th class="py-2.5 px-3">Summary</th>
                  <th class="py-2.5 px-3">Severity</th>
                  <th class="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (al of alerts.active_alerts; track al.id) {
                  <tr class="hover:bg-slate-50/50 transition-colors">
                    <td class="py-2.5 px-3 whitespace-nowrap font-bold text-slate-900">
                      {{ al.alert_rule_name }}
                    </td>
                    <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-700">
                      {{ al.affected_component }}
                    </td>
                    <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-500">
                      {{ al.triggered_at | date:'HH:mm:ss' }}
                    </td>
                    <td class="py-2.5 px-3 text-slate-800">
                      {{ al.summary }}
                    </td>
                    <td class="py-2.5 px-3 whitespace-nowrap">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-semibold"
                        [ngClass]="{
                          'bg-amber-50 text-amber-700': al.severity === 'WARNING',
                          'bg-rose-50 text-rose-700': al.severity === 'CRITICAL'
                        }">
                        {{ al.severity }}
                      </span>
                    </td>
                    <td class="py-2.5 px-3 whitespace-nowrap text-right">
                      <a [routerLink]="al.deep_link_route" class="text-xs font-semibold text-blue-600 hover:text-blue-700">
                        View Alert →
                      </a>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>

      <!-- 2. Linked Incidents -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Linked Incidents</h3>
          <span class="text-xs text-slate-500 font-medium">{{ alerts.linked_incidents.length }} linked incidents</span>
        </div>

        @if (alerts.linked_incidents.length === 0) {
          <div class="p-6 rounded-xl bg-slate-50 border border-slate-100 text-center text-xs text-slate-500">
            No active incidents linked to this migration workload.
          </div>
        } @else {
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-600">
              <thead>
                <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                  <th class="py-2.5 px-3">Incident Title</th>
                  <th class="py-2.5 px-3">Status</th>
                  <th class="py-2.5 px-3">Opened</th>
                  <th class="py-2.5 px-3">Summary</th>
                  <th class="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (inc of alerts.linked_incidents; track inc.id) {
                  <tr class="hover:bg-slate-50/50 transition-colors">
                    <td class="py-2.5 px-3 whitespace-nowrap font-bold text-slate-900">
                      {{ inc.incident_title }}
                    </td>
                    <td class="py-2.5 px-3 whitespace-nowrap font-semibold text-slate-700">
                      {{ inc.status }}
                    </td>
                    <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-500">
                      {{ inc.opened_at | date:'HH:mm:ss' }}
                    </td>
                    <td class="py-2.5 px-3 text-slate-800">
                      {{ inc.summary }}
                    </td>
                    <td class="py-2.5 px-3 whitespace-nowrap text-right">
                      <a [routerLink]="inc.deep_link_route" class="text-xs font-semibold text-blue-600 hover:text-blue-700">
                        View Incident →
                      </a>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>

    </div>
  `
})
export class MigrationAlertsTabComponent {
  @Input({ required: true }) alerts!: MigrationAlertsDTO;
}
