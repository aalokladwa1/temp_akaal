import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { DialogModule } from 'primeng/dialog';
import { MigrationUiService } from '../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { ProviderPickerComponent } from '../components/provider-picker.component';
import { ConnectionItem, PhysicalProviderId } from '../../../core/models/migration-view.models';

@Component({
  selector: 'app-connections',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TableModule,
    TagModule,
    DialogModule,
    LucideIconComponent,
    ProviderPickerComponent
  ],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto pb-16 font-sans select-none animate-in fade-in duration-150">
      
      <!-- Header -->
      <div class="flex items-center justify-between gap-4 pb-4 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <span class="text-xs font-semibold text-slate-500">Infrastructure Security</span>
          <h1 class="text-2xl font-bold font-heading text-slate-900 tracking-tight">Database Connections Vault</h1>
          <p class="text-xs text-slate-600 font-medium">Enterprise database, lakehouse, streaming, and storage credentials across 28 physical engines.</p>
        </div>

        <button
          type="button"
          (click)="isCreateModalOpen.set(true)"
          class="h-9 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs flex items-center gap-2 transition-colors cursor-pointer">
          <app-lucide-icon name="plus" [size]="15"></app-lucide-icon>
          <span>New Connection Profile</span>
        </button>
      </div>

      <!-- Main Connections Table -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        
        <div class="flex items-center justify-between gap-4 flex-wrap pb-3 border-b border-slate-100">
          <div class="flex items-center gap-3">
            <span class="text-xs font-bold text-slate-800">Connections ({{ ms.connections().length }})</span>
          </div>

          <div class="relative w-80">
            <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <app-lucide-icon name="search" [size]="15"></app-lucide-icon>
            </div>
            <input
              type="text"
              [(ngModel)]="searchQuery"
              placeholder="Search host, database, provider..."
              class="w-full h-10 pl-10 pr-3.5 rounded-xl bg-slate-50 hover:bg-slate-100/70 border border-slate-200 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs" />
          </div>
        </div>

        <p-table
          [value]="ms.connections()"
          [paginator]="true"
          [rows]="10"
          styleClass="p-datatable-sm">
          
          <ng-template #header>
            <tr class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              <th>Connection Name</th>
              <th>Provider Engine</th>
              <th>Endpoint &amp; Network Route</th>
              <th>Secret Vault Ref</th>
              <th>Status</th>
              <th>Verification Freshness</th>
              <th class="text-right">Actions</th>
            </tr>
          </ng-template>

          <ng-template #body let-c>
            <tr class="h-16 hover:bg-slate-50 text-xs font-medium">
              <td>
                <div class="flex flex-col">
                  <span class="font-bold text-slate-900">{{ c.name }}</span>
                  <span class="text-[11px] text-slate-500">{{ c.environment }} &bull; DB: {{ c.databaseName }}</span>
                </div>
              </td>

              <td>
                <span class="px-2.5 py-1 rounded-lg text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
                  {{ c.provider }}
                </span>
              </td>

              <td>
                <div class="flex flex-col font-mono text-[11px]">
                  <span class="text-slate-800">{{ c.host }}:{{ c.port }}</span>
                  <span class="text-slate-500">{{ c.networkRoute }}</span>
                </div>
              </td>

              <td>
                <span class="font-mono text-[11px] text-slate-600 bg-slate-100 px-2 py-0.5 rounded">{{ c.secretRef }}</span>
              </td>

              <td>
                <p-tag severity="success" value="CONNECTED" styleClass="text-[10px] font-bold"></p-tag>
              </td>

              <td>
                <span class="text-[11px] text-slate-500">{{ c.verificationFreshness }} ({{ c.latencyMs }}ms)</span>
              </td>

              <td class="text-right">
                <button
                  type="button"
                  (click)="selectedConnection.set(c)"
                  class="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-colors cursor-pointer">
                  Inspect
                </button>
              </td>
            </tr>
          </ng-template>

        </p-table>

      </div>

      <!-- Detail Drawer / Modal for Inspected Connection -->
      @if (selectedConnection()) {
        <p-dialog
          [visible]="true"
          [modal]="true"
          [closable]="true"
          [draggable]="false"
          [style]="{ width: '90vw', maxWidth: '680px' }"
          (onHide)="selectedConnection.set(null)">
          
          <ng-template #header>
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                <app-lucide-icon name="database" [size]="18"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900">{{ selectedConnection()?.name }}</h3>
                <span class="text-xs text-slate-500">{{ selectedConnection()?.provider }} &bull; {{ selectedConnection()?.environment }}</span>
              </div>
            </div>
          </ng-template>

          <div class="flex flex-col gap-4 text-xs font-medium">
            <div class="grid grid-cols-2 gap-3 p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div>
                <span class="text-slate-500">Host / Port:</span>
                <p class="font-mono font-bold text-slate-900">{{ selectedConnection()?.host }}:{{ selectedConnection()?.port }}</p>
              </div>
              <div>
                <span class="text-slate-500">Database:</span>
                <p class="font-bold text-slate-900">{{ selectedConnection()?.databaseName }}</p>
              </div>
              <div>
                <span class="text-slate-500">Network Route:</span>
                <p class="font-bold text-blue-700">{{ selectedConnection()?.networkRoute }}</p>
              </div>
              <div>
                <span class="text-slate-500">Vault Reference:</span>
                <p class="font-mono text-slate-700">{{ selectedConnection()?.secretRef }}</p>
              </div>
            </div>

            <div class="flex flex-col gap-2">
              <span class="font-bold text-slate-800">Native Engine Capabilities:</span>
              <div class="flex flex-wrap gap-1.5">
                @for (cap of selectedConnection()?.capabilities; track cap) {
                  <span class="px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 font-mono text-[10px] font-bold border border-blue-200">{{ cap }}</span>
                }
              </div>
            </div>
          </div>

          <ng-template #footer>
            <button
              type="button"
              (click)="selectedConnection.set(null)"
              class="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold">
              Close
            </button>
          </ng-template>

        </p-dialog>
      }

      <!-- Create New Connection Modal -->
      <p-dialog
        [(visible)]="isCreateModalOpen"
        [modal]="true"
        [closable]="true"
        [draggable]="false"
        [style]="{ width: '90vw', maxWidth: '720px' }">
        
        <ng-template #header>
          <div class="flex items-center gap-2">
            <app-lucide-icon name="plus" [size]="18" class="text-blue-600"></app-lucide-icon>
            <h3 class="text-sm font-bold text-slate-900">Create Physical Connection Profile</h3>
          </div>
        </ng-template>

        <div class="flex flex-col gap-4 text-xs">
          <app-provider-picker
            [selectedProviderId]="newProvider"
            (providerSelect)="newProvider = $event">
          </app-provider-picker>
        </div>

        <ng-template #footer>
          <div class="flex items-center justify-end gap-2">
            <button type="button" (click)="isCreateModalOpen.set(false)" class="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-bold">Cancel</button>
            <button type="button" (click)="isCreateModalOpen.set(false)" class="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold">Save Connection</button>
          </div>
        </ng-template>
      </p-dialog>

    </div>
  `
})
export class ConnectionsComponent {
  public ms = inject(MigrationUiService);
  public searchQuery = '';
  public selectedConnection = signal<ConnectionItem | null>(null);
  public isCreateModalOpen = signal<boolean>(false);
  public newProvider: PhysicalProviderId = 'Oracle';
}
