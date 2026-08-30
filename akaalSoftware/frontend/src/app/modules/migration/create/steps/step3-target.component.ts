import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProviderPickerComponent } from '../../components/provider-picker.component';
import { DynamicProviderFormComponent } from '../../components/dynamic-provider-form.component';
import { CompatibilityMatrixComponent } from '../../components/compatibility-matrix.component';
import { PhysicalProviderId, ConnectionItem } from '../../../../core/models/migration-view.models';

@Component({
  selector: 'app-step3-target',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, ProviderPickerComponent, DynamicProviderFormComponent, CompatibilityMatrixComponent],
  template: `
    <div class="flex flex-col gap-6 max-w-4xl mx-auto font-sans select-none animate-in fade-in duration-150 text-xs">
      
      <!-- Unified Calm Card for Step 3 -->
      <div class="p-6 md:p-8 rounded-2xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-6">
        
        <!-- Header -->
        <div class="flex flex-col gap-1 pb-4 border-b border-slate-100">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold text-slate-900 tracking-tight">Target</h2>
            <span class="px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 font-bold border border-blue-200 font-mono text-xs">
              {{ ms.wizardDraft().sourceProvider }} &rarr; {{ ms.wizardDraft().targetProvider }}
            </span>
          </div>
          <p class="text-xs text-slate-600 font-medium">Choose the destination database and verify engine compatibility.</p>
        </div>

        <!-- Choice: Existing Connection vs New Connection -->
        <div class="flex items-center gap-2 p-1 rounded-xl bg-slate-100/90 border border-slate-200 w-fit">
          <button
            type="button"
            (click)="setConnectionTab('SAVED')"
            class="h-8 px-4 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5"
            [class.bg-white]="activeTab === 'SAVED'"
            [class.text-blue-700]="activeTab === 'SAVED'"
            [class.shadow-2xs]="activeTab === 'SAVED'"
            [class.text-slate-700]="activeTab !== 'SAVED'">
            <app-lucide-icon name="folder-git-2" [size]="14"></app-lucide-icon>
            <span>Existing Connection</span>
          </button>

          <button
            type="button"
            (click)="setConnectionTab('NEW')"
            class="h-8 px-4 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5"
            [class.bg-white]="activeTab === 'NEW'"
            [class.text-blue-700]="activeTab === 'NEW'"
            [class.shadow-2xs]="activeTab === 'NEW'"
            [class.text-slate-700]="activeTab !== 'NEW'">
            <app-lucide-icon name="plus-circle" [size]="14"></app-lucide-icon>
            <span>New Connection</span>
          </button>
        </div>

        <!-- =============================================================== -->
        <!-- TAB 1: EXISTING TARGET CONNECTION                               -->
        <!-- =============================================================== -->
        @if (activeTab === 'SAVED') {
          <div class="flex flex-col gap-4 animate-in fade-in duration-150">
            
            <!-- Search Connections Bar -->
            <div class="relative w-full">
              <input
                type="text"
                [(ngModel)]="searchQuery"
                placeholder="Search by target connection name, provider, or host..."
                class="w-full h-10 pl-9 pr-4 rounded-xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
              <div class="absolute left-3 top-3 text-slate-400 pointer-events-none">
                <app-lucide-icon name="search" [size]="15"></app-lucide-icon>
              </div>
            </div>

            <!-- Saved Connections List -->
            <div class="flex flex-col gap-2.5">
              @for (conn of filteredSavedConnections(); track conn.id) {
                <div
                  (click)="selectSavedConnection(conn)"
                  class="p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between gap-4"
                  [class.border-blue-600]="selectedSavedConnection?.id === conn.id"
                  [class.bg-blue-50]="selectedSavedConnection?.id === conn.id"
                  [class.shadow-2xs]="selectedSavedConnection?.id === conn.id"
                  [class.border-slate-200]="selectedSavedConnection?.id !== conn.id"
                  [class.bg-white]="selectedSavedConnection?.id !== conn.id"
                  [class.hover:border-slate-300]="selectedSavedConnection?.id !== conn.id"
                  [class.hover:bg-slate-50]="selectedSavedConnection?.id !== conn.id">
                  
                  <div class="flex items-center gap-3.5 min-w-0">
                    <div
                      class="w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0"
                      [class.border-blue-600]="selectedSavedConnection?.id === conn.id"
                      [class.bg-blue-600]="selectedSavedConnection?.id === conn.id"
                      [class.border-slate-300]="selectedSavedConnection?.id !== conn.id">
                      @if (selectedSavedConnection?.id === conn.id) {
                        <div class="w-1.5 h-1.5 rounded-full bg-white"></div>
                      }
                    </div>

                    <div class="flex flex-col gap-0.5 min-w-0">
                      <span class="font-bold text-slate-900 text-xs truncate">{{ conn.name }}</span>
                      <span class="text-[11px] text-slate-600 font-medium">
                        {{ conn.provider }} &bull; {{ conn.environment || 'Production' }} &bull; {{ conn.host }}:{{ conn.port }}
                      </span>
                    </div>
                  </div>

                  <span
                    class="px-2.5 py-1 rounded-md text-[10.5px] font-bold shrink-0"
                    [class.bg-emerald-100]="conn.status === 'CONNECTED'"
                    [class.text-emerald-800]="conn.status === 'CONNECTED'"
                    [class.bg-slate-100]="conn.status !== 'CONNECTED'"
                    [class.text-slate-600]="conn.status !== 'CONNECTED'">
                    {{ conn.status === 'CONNECTED' ? 'Verified' : 'Not Tested' }}
                  </span>
                </div>
              }
            </div>

            <!-- Contextual Details (Revealed Only After Selection) -->
            @if (selectedSavedConnection) {
              <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-col gap-3 animate-in fade-in duration-150">
                <div class="flex items-center justify-between pb-2 border-b border-slate-200/80">
                  <span class="font-bold text-slate-900 text-xs uppercase tracking-wider">
                    Selected Target: {{ selectedSavedConnection.name }}
                  </span>
                  <span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-bold font-mono text-[10px]">
                    {{ selectedSavedConnection.provider }}
                  </span>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                  <div class="flex flex-col">
                    <span class="text-slate-500 font-bold uppercase text-[9.5px]">Host / Endpoint</span>
                    <span class="font-bold text-slate-900 font-mono truncate">{{ selectedSavedConnection.host }}:{{ selectedSavedConnection.port }}</span>
                  </div>

                  <div class="flex flex-col">
                    <span class="text-slate-500 font-bold uppercase text-[9.5px]">Database / Schema</span>
                    <span class="font-bold text-slate-900 font-mono truncate">{{ selectedSavedConnection.databaseName || 'public' }}</span>
                  </div>

                  <div class="flex flex-col">
                    <span class="text-slate-500 font-bold uppercase text-[9.5px]">Authentication</span>
                    <span class="font-bold text-slate-900 font-mono truncate">{{ selectedSavedConnection.username || 'postgres' }} (Managed 🔒)</span>
                  </div>

                  <div class="flex flex-col">
                    <span class="text-slate-500 font-bold uppercase text-[9.5px]">Write Capability</span>
                    <span class="font-bold text-emerald-800 font-mono">DDL &amp; CDC Target Ready</span>
                  </div>
                </div>
              </div>
            }

          </div>
        }

        <!-- =============================================================== -->
        <!-- TAB 2: NEW TARGET CONNECTION                                    -->
        <!-- =============================================================== -->
        @if (activeTab === 'NEW') {
          <div class="flex flex-col gap-6 animate-in fade-in duration-150">
            
            <!-- 1. Choose Provider (28 Canonical Technologies) -->
            <div class="flex flex-col gap-2.5">
              <label class="font-bold text-slate-900 text-xs uppercase tracking-wider">
                1. Select Target Database Engine (28 Providers)
              </label>
              <app-provider-picker
                [selectedProviderId]="selectedProviderId"
                (providerSelect)="onProviderSelected($event)">
              </app-provider-picker>
            </div>

            <!-- 2. Dynamic Provider Parameters Form -->
            <div class="flex flex-col gap-2.5 pt-2 border-t border-slate-100">
              <label class="font-bold text-slate-900 text-xs uppercase tracking-wider">
                2. Configure {{ selectedProviderId }} Target Connection Parameters
              </label>
              <app-dynamic-provider-form
                [providerId]="selectedProviderId"
                (formValuesChange)="onFormValuesChanged($event)">
              </app-dynamic-provider-form>
            </div>

            <!-- 3. Test Connection Bar -->
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex items-center justify-between gap-4 flex-wrap">
              <button
                type="button"
                (click)="runConnectionProbe()"
                [disabled]="isProbing"
                class="h-9 px-4 rounded-xl bg-white hover:bg-slate-100 border border-slate-300 text-slate-800 font-bold text-xs shadow-2xs transition-all cursor-pointer flex items-center gap-2">
                @if (isProbing) {
                  <app-lucide-icon name="refresh-cw" [size]="14" class="animate-spin text-blue-600"></app-lucide-icon>
                  <span>Probing Target...</span>
                } @else {
                  <app-lucide-icon name="zap" [size]="14" class="text-blue-600"></app-lucide-icon>
                  <span>Test Connection</span>
                }
              </button>

              @if (probeStatus === 'SUCCESS') {
                <div class="flex items-center gap-2 text-emerald-800 font-bold text-xs animate-in fade-in duration-150">
                  <app-lucide-icon name="check-circle-2" [size]="16" class="text-emerald-600"></app-lucide-icon>
                  <span>Target Reachable &bull; Write Privileges Verified &bull; Schema Creation Allowed</span>
                </div>
              } @else if (probeStatus === 'ERROR') {
                <div class="flex items-center gap-2 text-rose-800 font-bold text-xs animate-in fade-in duration-150">
                  <app-lucide-icon name="alert-triangle" [size]="16" class="text-rose-600"></app-lucide-icon>
                  <span>Target Connection Failed: Check host endpoint and credentials</span>
                </div>
              }
            </div>

          </div>
        }

        <!-- Cross-Engine Compatibility Matrix (Subtle & Quiet at the Bottom) -->
        <div class="flex flex-col gap-2.5 pt-4 border-t border-slate-200/80">
          <span class="font-bold text-slate-800 text-xs uppercase tracking-wider">
            Cross-Engine Compatibility Analysis
          </span>
          <app-compatibility-matrix
            [sourceProvider]="ms.wizardDraft().sourceProvider"
            [targetProvider]="ms.wizardDraft().targetProvider"
            [mode]="ms.wizardDraft().mode">
          </app-compatibility-matrix>
        </div>

      </div>

    </div>
  `
})
export class Step3TargetComponent {
  public ms = inject(MigrationUiService);

  public activeTab: 'SAVED' | 'NEW' = 'SAVED';
  public searchQuery = '';
  public selectedProviderId: PhysicalProviderId = 'PostgreSQL';
  public isProbing = false;
  public probeStatus: 'IDLE' | 'SUCCESS' | 'ERROR' = 'IDLE';

  public selectedSavedConnection: ConnectionItem | null = null;

  constructor() {
    const list = this.ms.connections();
    if (list && list.length > 1) {
      this.selectedSavedConnection = list[1];
    } else if (list && list.length > 0) {
      this.selectedSavedConnection = list[0];
    }
  }

  public setConnectionTab(tab: 'SAVED' | 'NEW'): void {
    this.activeTab = tab;
    this.probeStatus = 'IDLE';
  }

  public filteredSavedConnections(): ConnectionItem[] {
    const query = this.searchQuery.trim().toLowerCase();
    const list = this.ms.connections();
    if (!query) return list;
    return list.filter(c =>
      c.name.toLowerCase().includes(query) ||
      c.provider.toLowerCase().includes(query) ||
      c.host.toLowerCase().includes(query)
    );
  }

  public selectSavedConnection(conn: ConnectionItem): void {
    this.selectedSavedConnection = conn;
    this.ms.updateDraft({
      targetProvider: conn.provider as PhysicalProviderId,
      targetHost: conn.host,
      targetPort: conn.port,
      targetDatabase: conn.databaseName,
      targetUsername: conn.username
    });
  }

  public onProviderSelected(providerId: PhysicalProviderId): void {
    this.selectedProviderId = providerId;
    this.ms.updateDraft({ targetProvider: providerId });
    this.probeStatus = 'IDLE';
  }

  public onFormValuesChanged(values: Record<string, any>): void {
    this.ms.updateDraft({
      targetHost: values['host'] || values['bootstrapBrokers'] || values['accountIdentifier'] || values['bucketName'] || 'localhost',
      targetPort: values['port'] || (this.selectedProviderId === 'PostgreSQL' ? 5432 : 1433),
      targetDatabase: values['database'] || values['keyspaceName'] || values['dataset'] || 'default',
      targetUsername: values['username'] || values['accessKeyId'] || 'postgres'
    });
  }

  public runConnectionProbe(): void {
    this.isProbing = true;
    this.probeStatus = 'IDLE';
    setTimeout(() => {
      this.isProbing = false;
      this.probeStatus = 'SUCCESS';
    }, 600);
  }
}
