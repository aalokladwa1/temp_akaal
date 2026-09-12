/**
 * AKAAL Administration — 5.6 Connector Registry
 */

import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-connector-registry',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/connectors/connectors-hub" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Connectors
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Connector Registry</h1>
            <p class="text-sm font-medium text-slate-600 max-w-3xl">
              Inventory of canonical connector and provider software implementations registered across the platform.
            </p>
          </div>

          <div class="flex items-center gap-2">
            <a
              routerLink="/administration/connectors/external/register"
              class="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs inline-flex items-center gap-1.5 cursor-pointer">
              Register External Connector
            </a>
          </div>
        </div>
      </div>

      <!-- Filters & Search Toolbar -->
      <div class="flex items-center justify-between gap-4 flex-wrap bg-white p-3.5 border border-slate-200 rounded-xl shadow-2xs">
        <div class="flex items-center gap-3 flex-1 min-w-[280px]">
          <div class="relative flex-1 max-w-md">
            <input
              type="text"
              [(ngModel)]="searchQuery"
              placeholder="Search connectors by name or provider..."
              class="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all" />
            <app-lucide-icon name="search" [size]="14" class="absolute left-3 top-2.5 text-slate-400"></app-lucide-icon>
          </div>

          <div class="w-64">
            <app-custom-select
              [options]="categoryOptions"
              [value]="selectedCategory()"
              (valueChange)="selectedCategory.set($event)"
              placeholder="Filter by Category">
            </app-custom-select>
          </div>
        </div>

        <div class="text-xs font-medium text-slate-500">
          Showing <span class="font-bold text-slate-800">{{ filteredConnectors().length }}</span> connectors
        </div>
      </div>

      <!-- Connector Registry Table -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider font-heading">
              <th class="py-3 px-4">Connector Name</th>
              <th class="py-3 px-4">Category</th>
              <th class="py-3 px-4">Version</th>
              <th class="py-3 px-4">Driver Version</th>
              <th class="py-3 px-4">Roles</th>
              <th class="py-3 px-4">Proof Level</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs font-medium text-slate-700">
            @for (item of filteredConnectors(); track item.id) {
              <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-900">
                  <div class="flex items-center gap-2.5">
                    <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span>{{ item.name }}</span>
                  </div>
                </td>
                <td class="py-3.5 px-4 text-slate-600">{{ item.category }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-800 font-semibold">{{ item.version }}</td>
                <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">{{ item.driverVersion }}</td>
                <td class="py-3.5 px-4">
                  <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                    {{ item.applicability === 'SOURCE_AND_TARGET' ? 'Source & Target' : (item.applicability === 'SOURCE_ONLY' ? 'Source Only' : 'Target Only') }}
                  </span>
                </td>
                <td class="py-3.5 px-4">
                  <span
                    [ngClass]="{
                      'bg-emerald-50 text-emerald-700 border-emerald-200': item.certificationLevel === 'LIVE_PROVEN',
                      'bg-blue-50 text-blue-700 border-blue-200': item.certificationLevel === 'INTEGRATION_PROVEN',
                      'bg-slate-50 text-slate-700 border-slate-200': item.certificationLevel === 'UNIT_PROVEN'
                    }"
                    class="px-2 py-0.5 rounded text-[10px] font-bold border font-mono uppercase tracking-wide">
                    {{ item.certificationLevel }}
                  </span>
                </td>
                <td class="py-3.5 px-4 text-right">
                  <a
                    [routerLink]="['/administration/connectors/detail', item.id]"
                    class="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors cursor-pointer">
                    View Details
                  </a>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="7" class="py-8 text-center text-slate-500 text-xs">
                  No connectors match your active search and category filter.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class ConnectorRegistryComponent {
  public service = inject(ConnectorsPluginsService);
  public searchQuery = '';
  public selectedCategory = signal('ALL');

  public categoryOptions: SelectOption[] = [
    { label: 'All Categories', value: 'ALL' },
    { label: 'Relational & Distributed SQL', value: 'Relational & Distributed SQL' },
    { label: 'Warehouse & Lakehouse', value: 'Warehouse & Lakehouse' },
    { label: 'Streaming & Event Broker', value: 'Streaming & Event Broker' },
    { label: 'NoSQL & Document Store', value: 'NoSQL & Document Store' },
    { label: 'Object Storage & Lake', value: 'Object Storage & Lake' },
    { label: 'In-Memory & Cache', value: 'In-Memory & Cache' }
  ];

  public filteredConnectors = computed(() => {
    const list = this.service.connectors();
    const query = this.searchQuery.toLowerCase().trim();
    const category = this.selectedCategory();

    return list.filter(c => {
      const matchSearch = !query || c.name.toLowerCase().includes(query) || c.providerId.toLowerCase().includes(query);
      const matchCategory = category === 'ALL' || c.category === category;
      return matchSearch && matchCategory;
    });
  });
}
