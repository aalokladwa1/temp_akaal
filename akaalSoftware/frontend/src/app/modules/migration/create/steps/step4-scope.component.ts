import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

export interface ScopeObjectItem {
  id: string;
  name: string;
  type: 'TABLE' | 'VIEW' | 'PROCEDURE' | 'FUNCTION' | 'TRIGGER' | 'SEQUENCE' | 'COLLECTION' | 'TOPIC';
  categoryKey: string;
  schemaId: string;
  dbId: string;
  estimatedRows?: number;
  estimatedSizeBytes?: number;
  columnsCount?: number;
  primaryKey?: string;
  compatibility: 'OPTIMAL' | 'COMPATIBLE' | 'WARNING' | 'BLOCKER';
  isSelected: boolean;
}

export interface ScopeCategoryGroup {
  key: string;
  label: string;
  badge: string;
  badgeClass: string;
  schemaId: string;
  dbId: string;
  isExpanded: boolean;
  objects: ScopeObjectItem[];
}

export interface ScopeSchemaContainer {
  id: string;
  name: string;
  dbId: string;
  isExpanded: boolean;
  categories: ScopeCategoryGroup[];
}

export interface ScopeDbContainer {
  id: string;
  name: string;
  engineLabel: string;
  isExpanded: boolean;
  schemas: ScopeSchemaContainer[];
}

@Component({
  selector: 'app-step4-scope',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-5 animate-in fade-in duration-150 text-xs select-none">
      
      <!-- Top Bar: Discovery Profile & Status Badge -->
      <div class="flex items-center justify-between gap-4 pb-2 border-b border-slate-200 flex-wrap">
        <div class="flex items-center gap-3">
          <span class="font-bold text-slate-700 text-xs">Discovery Profile:</span>
          <div class="flex items-center gap-1">
            @for (prof of discoveryProfiles; track prof) {
              <button
                type="button"
                (click)="selectedProfile.set(prof)"
                class="px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer"
                [class.bg-blue-600]="selectedProfile() === prof"
                [class.text-white]="selectedProfile() === prof"
                [class.shadow-2xs]="selectedProfile() === prof"
                [class.bg-slate-100]="selectedProfile() !== prof"
                [class.text-slate-600]="selectedProfile() !== prof"
                [class.hover:bg-slate-200]="selectedProfile() !== prof">
                {{ prof }}
              </button>
            }
          </div>
        </div>

        <div class="flex items-center gap-2">
          <span class="px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold text-xs flex items-center gap-1.5 shadow-2xs">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>DISCOVERY COMPLETE</span>
          </span>
        </div>
      </div>

      <!-- DISCOVERY SUMMARY COUNTERS RIBBON -->
      <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200/90 flex items-center justify-between gap-6 flex-wrap shadow-2xs">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="bar-chart-3" [size]="16" class="text-blue-600"></app-lucide-icon>
          <span class="font-bold text-slate-900 uppercase tracking-wider text-xs">DISCOVERY SUMMARY</span>
        </div>

        <div class="flex items-center gap-8 flex-wrap">
          <div class="flex items-center gap-2">
            <span class="text-slate-500 font-medium">Databases:</span>
            <span class="font-bold text-slate-900 text-sm">{{ totalDatabases() }}</span>
          </div>

          <div class="flex items-center gap-2">
            <span class="text-slate-500 font-medium">Schemas:</span>
            <span class="font-bold text-slate-900 text-sm">{{ totalSchemas() }}</span>
          </div>

          <div class="flex items-center gap-2">
            <span class="text-slate-500 font-medium">Objects:</span>
            <span class="font-bold text-blue-700 text-sm">{{ totalObjects() }}</span>
          </div>
        </div>
      </div>

      <!-- SCOPE FILTERS & ACTION BAR -->
      <div class="p-3.5 rounded-xl bg-white border border-slate-200/90 flex items-center justify-between gap-3 flex-wrap shadow-2xs">
        
        <div class="flex items-center gap-2.5 flex-wrap flex-1 min-w-[320px]">
          <div class="flex items-center gap-1.5 text-slate-700 font-bold text-xs pr-1">
            <app-lucide-icon name="filter" [size]="14" class="text-blue-600"></app-lucide-icon>
            <span>Filters:</span>
          </div>

          <!-- Filter: Databases -->
          <select
            [(ngModel)]="filterDatabase"
            class="h-8 px-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none cursor-pointer">
            <option value="ALL">All Databases ({{ totalDatabases() }})</option>
            @for (db of databases(); track db.id) {
              <option [value]="db.id">{{ db.name }}</option>
            }
          </select>

          <!-- Filter: Schemas -->
          <select
            [(ngModel)]="filterSchema"
            class="h-8 px-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none cursor-pointer">
            <option value="ALL">All Schemas ({{ totalSchemas() }})</option>
            @for (db of databases(); track db.id) {
              @for (sch of db.schemas; track sch.id) {
                <option [value]="sch.id">{{ db.name }}.{{ sch.name }}</option>
              }
            }
          </select>

          <!-- Filter: Types -->
          <select
            [(ngModel)]="filterType"
            class="h-8 px-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none cursor-pointer">
            <option value="ALL">All Object Types</option>
            <option value="TABLE">Tables [TBL]</option>
            <option value="VIEW">Views [VIEW]</option>
            <option value="PROCEDURE">Procedures [PROC]</option>
            <option value="FUNCTION">Functions [FUNC]</option>
            <option value="TRIGGER">Triggers [TRG]</option>
            <option value="SEQUENCE">Sequences [SEQ]</option>
          </select>

          <!-- Search Object Name -->
          <div class="relative flex-1 min-w-[180px] max-w-xs">
            <input
              type="text"
              [(ngModel)]="searchObjectName"
              placeholder="Search object name..."
              class="w-full h-8 pl-8 pr-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
            <div class="absolute left-2.5 top-2 text-slate-400 pointer-events-none">
              <app-lucide-icon name="search" [size]="13"></app-lucide-icon>
            </div>
          </div>
        </div>

        <!-- Global Selection Actions -->
        <div class="flex items-center gap-1.5 text-xs">
          <button type="button" (click)="selectAll()" class="px-2.5 py-1.5 rounded-lg hover:bg-slate-100 font-bold text-slate-700 cursor-pointer">Select All</button>
          <button type="button" (click)="deselectAll()" class="px-2.5 py-1.5 rounded-lg hover:bg-slate-100 font-bold text-slate-700 cursor-pointer">Deselect All</button>
          <div class="h-4 w-px bg-slate-200"></div>
          <button type="button" (click)="expandAll()" class="px-2.5 py-1.5 rounded-lg hover:bg-slate-100 font-bold text-slate-700 cursor-pointer">Expand All</button>
          <button type="button" (click)="collapseAll()" class="px-2.5 py-1.5 rounded-lg hover:bg-slate-100 font-bold text-slate-700 cursor-pointer">Collapse All</button>
        </div>

      </div>

      <!-- MAIN WORKBENCH: HIERARCHY TABLE (68%) & OBJECT TELEMETRY EXPLORER (32%) -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        
        <!-- LEFT: DATABASE & SCHEMA HIERARCHY TABLE (68%) -->
        <div class="lg:col-span-8 p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-2">
          
          <!-- Table Header with Dedicated EST. ROWS and EST. SIZE Columns -->
          <div class="grid grid-cols-12 gap-2 px-3 py-2 bg-slate-100/90 border border-slate-200 rounded-lg text-[10.5px] font-bold text-slate-700 uppercase tracking-wider">
            <div class="col-span-6">DATABASE &amp; SCHEMA HIERARCHY</div>
            <div class="col-span-2 text-center">OBJ TYPE</div>
            <div class="col-span-2 text-right">EST. ROWS</div>
            <div class="col-span-2 text-right">EST. SIZE</div>
          </div>

          <!-- Hierarchy Tree Rows -->
          <div class="flex flex-col gap-2.5 max-h-[620px] overflow-y-auto pr-1">
            @for (db of filteredDatabases(); track db.id) {
              
              <!-- 1. Database Row (Level 1 - Distinct Box) -->
              <div class="border-2 border-slate-300 rounded-xl overflow-hidden bg-white shadow-2xs">
                
                <div class="p-3 bg-slate-100 hover:bg-slate-200/80 border-b border-slate-300 flex items-center justify-between gap-3 cursor-pointer"
                  (click)="db.isExpanded = !db.isExpanded">
                  
                  <div class="flex items-center gap-2.5 min-w-0" (click)="$event.stopPropagation()">
                    <button type="button" (click)="db.isExpanded = !db.isExpanded" class="p-1 hover:bg-slate-300/80 rounded text-slate-700">
                      <app-lucide-icon [name]="db.isExpanded ? 'chevron-down' : 'chevron-right'" [size]="14"></app-lucide-icon>
                    </button>
                    
                    <input
                      type="checkbox"
                      [checked]="isDbAllSelected(db)"
                      (change)="toggleDbSelection(db, $event)"
                      class="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer" />
                    
                    <app-lucide-icon name="database" [size]="16" class="text-blue-700 shrink-0"></app-lucide-icon>
                    
                    <div class="flex items-center gap-2 truncate">
                      <span class="font-bold text-slate-900 text-xs truncate">{{ db.name }}</span>
                      <span class="text-[11px] text-slate-600 font-medium">({{ db.schemas.length }} Schemas &bull; {{ getDbObjectsCount(db) }} Objects)</span>
                    </div>
                  </div>

                  <div class="flex items-center gap-2 shrink-0">
                    <span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-bold">
                      {{ db.engineLabel }}
                    </span>
                    <span class="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold">
                      OPTIMAL
                    </span>
                  </div>

                </div>

                <!-- 2. Schemas Level (Level 2 - Indented Clean Box) -->
                @if (db.isExpanded) {
                  <div class="flex flex-col divide-y divide-slate-200 bg-slate-50/40 p-1.5 pl-4">
                    @for (sch of db.schemas; track sch.id) {
                      
                      <div class="flex flex-col gap-1 py-1.5">
                        
                        <!-- Schema Header Row -->
                        <div class="p-2 rounded-lg bg-slate-100/70 hover:bg-slate-200/60 border border-slate-200 flex items-center justify-between gap-3 cursor-pointer"
                          (click)="sch.isExpanded = !sch.isExpanded">
                          
                          <div class="flex items-center gap-2 min-w-0" (click)="$event.stopPropagation()">
                            <button type="button" (click)="sch.isExpanded = !sch.isExpanded" class="p-0.5 hover:bg-slate-300/80 rounded text-slate-600">
                              <app-lucide-icon [name]="sch.isExpanded ? 'chevron-down' : 'chevron-right'" [size]="13"></app-lucide-icon>
                            </button>

                            <input
                              type="checkbox"
                              [checked]="isSchemaAllSelected(sch)"
                              (change)="toggleSchemaSelection(sch, $event)"
                              class="w-3.5 h-3.5 rounded text-blue-600 focus:ring-blue-500 cursor-pointer" />

                            <app-lucide-icon name="folder" [size]="14" class="text-amber-600 shrink-0"></app-lucide-icon>

                            <span class="font-bold text-slate-900 text-xs truncate">{{ sch.name }}</span>
                            <span class="text-[10.5px] text-slate-500 font-medium">({{ getCategoryTotalObjects(sch) }} items)</span>
                          </div>

                          <div class="flex items-center gap-1.5">
                            @for (cat of sch.categories; track cat.key) {
                              @if (cat.objects.length > 0) {
                                <span class="px-1.5 py-0.5 rounded text-[9.5px] font-bold" [class]="cat.badgeClass">
                                  {{ cat.badge }}: {{ cat.objects.length }}
                                </span>
                              }
                            }
                          </div>

                        </div>

                        <!-- 3. Categories Level (Level 3 - Expandable Category Groups) -->
                        @if (sch.isExpanded) {
                          <div class="flex flex-col gap-1 pl-4 pt-1">
                            @for (cat of sch.categories; track cat.key) {
                              @if (cat.objects.length > 0) {
                                
                                <div class="border border-slate-200 rounded-lg overflow-hidden bg-white">
                                  
                                  <!-- Category Header -->
                                  <div class="px-2.5 py-1.5 bg-slate-50/90 hover:bg-slate-100 border-b border-slate-100 flex items-center justify-between cursor-pointer"
                                    (click)="cat.isExpanded = !cat.isExpanded">
                                    
                                    <div class="flex items-center gap-2" (click)="$event.stopPropagation()">
                                      <button type="button" (click)="cat.isExpanded = !cat.isExpanded" class="p-0.5 hover:bg-slate-200 rounded text-slate-500">
                                        <app-lucide-icon [name]="cat.isExpanded ? 'chevron-down' : 'chevron-right'" [size]="12"></app-lucide-icon>
                                      </button>

                                      <input
                                        type="checkbox"
                                        [checked]="isCategoryAllSelected(cat)"
                                        (change)="toggleCategorySelection(cat, $event)"
                                        class="w-3.5 h-3.5 rounded text-blue-600 focus:ring-blue-500 cursor-pointer" />

                                      <span class="px-1.5 py-0.2 rounded text-[9.5px] font-extrabold" [class]="cat.badgeClass">
                                        {{ cat.badge }}
                                      </span>

                                      <span class="font-bold text-slate-800 text-[11.5px]">{{ cat.label }}</span>
                                      <span class="text-[10px] text-slate-500 font-medium">({{ cat.objects.length }})</span>
                                    </div>

                                    <div class="text-[10px] font-semibold text-slate-600">
                                      {{ formatNumber(getCategoryRows(cat)) }} rows &bull; {{ formatBytes(getCategorySize(cat)) }}
                                    </div>

                                  </div>

                                  <!-- 4. Objects Level (Level 4 - Individual Object Rows with Type Badge, Est Rows, Est Size) -->
                                  @if (cat.isExpanded) {
                                    <div class="divide-y divide-slate-100">
                                      @for (obj of cat.objects; track obj.id) {
                                        <div
                                          (click)="selectObject(obj)"
                                          class="grid grid-cols-12 gap-2 px-3 py-2 items-center hover:bg-blue-50/60 cursor-pointer transition-colors"
                                          [class.bg-blue-50]="selectedObject?.id === obj.id"
                                          [class.bg-white]="selectedObject?.id !== obj.id">
                                          
                                          <!-- Col 1: Checkbox & Name (Col 6) -->
                                          <div class="col-span-6 flex items-center gap-2.5 min-w-0" (click)="$event.stopPropagation()">
                                            <input
                                              type="checkbox"
                                              [(ngModel)]="obj.isSelected"
                                              class="w-3.5 h-3.5 rounded text-blue-600 focus:ring-blue-500 cursor-pointer" />

                                            <span class="font-bold text-slate-900 text-xs truncate">{{ obj.name }}</span>
                                            
                                            @if (obj.primaryKey) {
                                              <span class="px-1.5 py-0.2 rounded bg-amber-50 text-amber-800 border border-amber-200 text-[9.5px] font-bold shrink-0">
                                                PK
                                              </span>
                                            }
                                          </div>

                                          <!-- Col 2: Object Type Tag (Col 2) -->
                                          <div class="col-span-2 text-center">
                                            <span class="px-2 py-0.5 rounded text-[10px] font-extrabold" [class]="cat.badgeClass">
                                              [{{ cat.badge }}]
                                            </span>
                                          </div>

                                          <!-- Col 3: Est. Rows (Col 2) -->
                                          <div class="col-span-2 text-right font-semibold text-slate-800 text-xs">
                                            {{ obj.estimatedRows !== undefined ? formatNumber(obj.estimatedRows) : '—' }}
                                          </div>

                                          <!-- Col 4: Est. Size (Col 2) -->
                                          <div class="col-span-2 text-right font-semibold text-slate-800 text-xs">
                                            {{ obj.estimatedSizeBytes !== undefined ? formatBytes(obj.estimatedSizeBytes) : '—' }}
                                          </div>

                                        </div>
                                      }
                                    </div>
                                  }

                                </div>

                              }
                            }
                          </div>
                        }

                      </div>

                    }
                  </div>
                }

              </div>

            }
          </div>

        </div>

        <!-- RIGHT: OBJECT TELEMETRY EXPLORER (32% - Focused on Selected Object) -->
        <div class="lg:col-span-4 flex flex-col gap-4">
          
          <div class="p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-4">
            
            <div class="pb-2.5 border-b border-slate-100 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="file-text" [size]="15" class="text-blue-600"></app-lucide-icon>
                <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">Object Telemetry Explorer</span>
              </div>
              @if (selectedObject) {
                <span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-[10px] font-bold">
                  [{{ selectedObject.categoryKey }}]
                </span>
              }
            </div>

            @if (selectedObject) {
              <div class="flex flex-col gap-3 animate-in fade-in duration-150">
                
                <div class="flex items-center gap-3 p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <div class="w-9 h-9 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs">
                    {{ selectedObject.categoryKey }}
                  </div>
                  <div class="flex flex-col min-w-0">
                    <span class="font-bold text-slate-900 text-xs truncate">{{ selectedObject.name }}</span>
                    <span class="text-[11px] text-slate-500 font-medium truncate">{{ selectedObject.dbId }}.{{ selectedObject.schemaId }}</span>
                  </div>
                </div>

                <div class="grid grid-cols-2 gap-2.5 text-xs">
                  <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-0.5">
                    <span class="text-[10px] font-bold text-slate-500 uppercase">Estimated Rows</span>
                    <span class="font-bold text-slate-900 text-sm">{{ formatNumber(selectedObject.estimatedRows) }}</span>
                  </div>

                  <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-0.5">
                    <span class="text-[10px] font-bold text-slate-500 uppercase">Estimated Size</span>
                    <span class="font-bold text-slate-900 text-sm">{{ formatBytes(selectedObject.estimatedSizeBytes) }}</span>
                  </div>

                  <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-0.5">
                    <span class="text-[10px] font-bold text-slate-500 uppercase">Columns Count</span>
                    <span class="font-bold text-slate-900 text-sm">{{ selectedObject.columnsCount || 12 }} Columns</span>
                  </div>

                  <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-0.5">
                    <span class="text-[10px] font-bold text-slate-500 uppercase">Primary Key</span>
                    <span class="font-bold text-amber-800 text-xs truncate">{{ selectedObject.primaryKey || 'ID (PK)' }}</span>
                  </div>
                </div>

                <!-- Object Schema Details / Columns List -->
                <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
                  <span class="font-bold text-slate-800 text-[11px] uppercase tracking-wider">Object Schema Definition:</span>
                  <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1.5 text-[11px]">
                    <div class="flex items-center justify-between text-slate-700">
                      <span class="font-bold">Column Name</span>
                      <span class="font-bold">Engine Type</span>
                    </div>
                    <div class="h-px bg-slate-200"></div>
                    <div class="flex items-center justify-between text-slate-800">
                      <span>id</span>
                      <span class="text-blue-700 font-bold">BIGINT (PK)</span>
                    </div>
                    <div class="flex items-center justify-between text-slate-800">
                      <span>name / title</span>
                      <span class="text-slate-600">VARCHAR(255)</span>
                    </div>
                    <div class="flex items-center justify-between text-slate-800">
                      <span>status</span>
                      <span class="text-slate-600">VARCHAR(32)</span>
                    </div>
                    <div class="flex items-center justify-between text-slate-800">
                      <span>created_at</span>
                      <span class="text-slate-600">TIMESTAMPTZ</span>
                    </div>
                  </div>
                </div>

                <!-- Scope Selection Toggle -->
                <div class="p-3 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-between">
                  <span class="font-bold text-blue-950 text-xs">Included in Migration Scope</span>
                  <input
                    type="checkbox"
                    [(ngModel)]="selectedObject.isSelected"
                    class="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer" />
                </div>

              </div>
            } @else {
              <div class="py-12 flex flex-col items-center justify-center text-center gap-2.5 text-slate-500">
                <app-lucide-icon name="mouse-pointer" [size]="28" class="text-slate-300"></app-lucide-icon>
                <span class="font-bold text-slate-800 text-xs">Select Any Object in the Scope Tree</span>
                <p class="text-[11px] text-slate-500 leading-relaxed max-w-xs">
                  Click on any table, view, or procedure to inspect its telemetry, row count, storage size, and column definition.
                </p>
              </div>
            }

          </div>

        </div>

      </div>

    </div>
  `
})
export class Step4ScopeComponent {
  public ms = inject(MigrationUiService);

  public discoveryProfiles = ['QUICK', 'STANDARD', 'DEEP', 'COMPLIANCE'];
  public selectedProfile = signal<string>('DEEP');

  public filterDatabase = 'ALL';
  public filterSchema = 'ALL';
  public filterType = 'ALL';
  public searchObjectName = '';

  public selectedObject: ScopeObjectItem | null = null;

  public databases = computed<ScopeDbContainer[]>(() => {
    const provider = this.ms.wizardDraft().sourceProvider;
    return this.buildDatabaseTopology(provider);
  });

  public buildDatabaseTopology(provider: string): ScopeDbContainer[] {
    const customDb = this.ms.wizardDraft().sourceDatabase?.trim();
    const primaryDbName = customDb || (provider === 'Microsoft SQL Server' ? 'SalesDB' : (provider === 'PostgreSQL' ? 'production_db' : 'HRDB'));

    if (provider === 'MongoDB') {
      return [
        {
          id: 'db_inventory',
          name: customDb || 'inventory_db',
          engineLabel: 'MongoDB rs0',
          isExpanded: true,
          schemas: [
            {
              id: 'coll_group',
              name: 'Collections (3 Collections)',
              dbId: 'db_inventory',
              isExpanded: true,
              categories: [
                {
                  key: 'COLL',
                  label: 'Collections',
                  badge: 'COLL',
                  badgeClass: 'bg-emerald-100 text-emerald-900',
                  schemaId: 'coll_group',
                  dbId: 'db_inventory',
                  isExpanded: true,
                  objects: [
                    { id: 'coll_orders', name: 'orders', type: 'COLLECTION', categoryKey: 'COLL', schemaId: 'coll_group', dbId: 'db_inventory', estimatedRows: 8400000, estimatedSizeBytes: 6657199308, columnsCount: 14, compatibility: 'OPTIMAL', isSelected: true },
                    { id: 'coll_products', name: 'products', type: 'COLLECTION', categoryKey: 'COLL', schemaId: 'coll_group', dbId: 'db_inventory', estimatedRows: 250000, estimatedSizeBytes: 188743680, columnsCount: 12, compatibility: 'OPTIMAL', isSelected: true },
                    { id: 'coll_users', name: 'users', type: 'COLLECTION', categoryKey: 'COLL', schemaId: 'coll_group', dbId: 'db_inventory', estimatedRows: 1200000, estimatedSizeBytes: 1181116006, columnsCount: 18, compatibility: 'OPTIMAL', isSelected: true }
                  ]
                }
              ]
            }
          ]
        },
        {
          id: 'db_telemetry',
          name: 'telemetry_db',
          engineLabel: 'MongoDB rs0',
          isExpanded: true,
          schemas: [
            {
              id: 'coll_telem_group',
              name: 'Collections (2 Collections)',
              dbId: 'db_telemetry',
              isExpanded: true,
              categories: [
                {
                  key: 'COLL',
                  label: 'Collections',
                  badge: 'COLL',
                  badgeClass: 'bg-emerald-100 text-emerald-900',
                  schemaId: 'coll_telem_group',
                  dbId: 'db_telemetry',
                  isExpanded: true,
                  objects: [
                    { id: 'coll_device_events', name: 'device_events', type: 'COLLECTION', categoryKey: 'COLL', schemaId: 'coll_telem_group', dbId: 'db_telemetry', estimatedRows: 12100000, estimatedSizeBytes: 9019431321, columnsCount: 8, compatibility: 'OPTIMAL', isSelected: true },
                    { id: 'coll_sensor_logs', name: 'sensor_logs', type: 'COLLECTION', categoryKey: 'COLL', schemaId: 'coll_telem_group', dbId: 'db_telemetry', estimatedRows: 2400000, estimatedSizeBytes: 1932735283, columnsCount: 6, compatibility: 'OPTIMAL', isSelected: true }
                  ]
                }
              ]
            }
          ]
        }
      ];
    } else if (provider === 'Apache Kafka') {
      return [
        {
          id: 'cluster_kafka',
          name: customDb || 'kafka-prod-cluster',
          engineLabel: 'Kafka Cluster',
          isExpanded: true,
          schemas: [
            {
              id: 'topic_group',
              name: 'Topics (3 Topics)',
              dbId: 'cluster_kafka',
              isExpanded: true,
              categories: [
                {
                  key: 'TOPIC',
                  label: 'Event Streams',
                  badge: 'STREAM',
                  badgeClass: 'bg-purple-100 text-purple-900',
                  schemaId: 'topic_group',
                  dbId: 'cluster_kafka',
                  isExpanded: true,
                  objects: [
                    { id: 'top_orders', name: 'orders-cdc-stream', type: 'TOPIC', categoryKey: 'TOPIC', schemaId: 'topic_group', dbId: 'cluster_kafka', estimatedRows: 18400000, estimatedSizeBytes: 15032385536, columnsCount: 16, compatibility: 'OPTIMAL', isSelected: true },
                    { id: 'top_payments', name: 'payment-events', type: 'TOPIC', categoryKey: 'TOPIC', schemaId: 'topic_group', dbId: 'cluster_kafka', estimatedRows: 9200000, estimatedSizeBytes: 7516192768, columnsCount: 12, compatibility: 'OPTIMAL', isSelected: true }
                  ]
                }
              ]
            }
          ]
        }
      ];
    } else {
      // Oracle, PostgreSQL, MySQL, SQL Server
      return [
        {
          id: 'primary_db',
          name: primaryDbName,
          engineLabel: `${provider} Instance`,
          isExpanded: true,
          schemas: [
            {
              id: 'main_schema',
              name: provider === 'Microsoft SQL Server' ? 'dbo Schema' : 'HR Schema',
              dbId: 'primary_db',
              isExpanded: true,
              categories: [
                {
                  key: 'TBL',
                  label: 'Tables',
                  badge: 'TBL',
                  badgeClass: 'bg-blue-100 text-blue-900',
                  schemaId: 'main_schema',
                  dbId: 'primary_db',
                  isExpanded: true,
                  objects: [
                    { id: 'tbl_cust', name: 'CUSTOMERS', type: 'TABLE', categoryKey: 'TBL', schemaId: 'main_schema', dbId: 'primary_db', estimatedRows: 14200000, estimatedSizeBytes: 9234186240, columnsCount: 14, primaryKey: 'CUSTOMER_ID (PK)', compatibility: 'OPTIMAL', isSelected: true },
                    { id: 'tbl_orders', name: 'ORDERS', type: 'TABLE', categoryKey: 'TBL', schemaId: 'main_schema', dbId: 'primary_db', estimatedRows: 48000000, estimatedSizeBytes: 31234186240, columnsCount: 16, primaryKey: 'ORDER_ID (PK)', compatibility: 'OPTIMAL', isSelected: true },
                    { id: 'tbl_order_items', name: 'ORDER_ITEMS', type: 'TABLE', categoryKey: 'TBL', schemaId: 'main_schema', dbId: 'primary_db', estimatedRows: 92000000, estimatedSizeBytes: 54834186240, columnsCount: 8, primaryKey: 'ITEM_ID (PK)', compatibility: 'OPTIMAL', isSelected: true },
                    { id: 'tbl_inventory', name: 'INVENTORY', type: 'TABLE', categoryKey: 'TBL', schemaId: 'main_schema', dbId: 'primary_db', estimatedRows: 1400000, estimatedSizeBytes: 1100000000, columnsCount: 6, primaryKey: 'SKU (PK)', compatibility: 'OPTIMAL', isSelected: true }
                  ]
                },
                {
                  key: 'VIEW',
                  label: 'Views',
                  badge: 'VIEW',
                  badgeClass: 'bg-indigo-100 text-indigo-900',
                  schemaId: 'main_schema',
                  dbId: 'primary_db',
                  isExpanded: false,
                  objects: [
                    { id: 'v_emp_det', name: 'V_CUSTOMER_ORDERS', type: 'VIEW', categoryKey: 'VIEW', schemaId: 'main_schema', dbId: 'primary_db', columnsCount: 8, compatibility: 'OPTIMAL', isSelected: true },
                    { id: 'v_dept_sum', name: 'V_DAILY_REVENUE', type: 'VIEW', categoryKey: 'VIEW', schemaId: 'main_schema', dbId: 'primary_db', columnsCount: 5, compatibility: 'OPTIMAL', isSelected: true }
                  ]
                },
                {
                  key: 'PROC',
                  label: 'Procedures',
                  badge: 'PROC',
                  badgeClass: 'bg-amber-100 text-amber-900',
                  schemaId: 'main_schema',
                  dbId: 'primary_db',
                  isExpanded: false,
                  objects: [
                    { id: 'p_settle', name: 'SP_SETTLE_PAYMENTS', type: 'PROCEDURE', categoryKey: 'PROC', schemaId: 'main_schema', dbId: 'primary_db', compatibility: 'OPTIMAL', isSelected: true },
                    { id: 'p_subtype', name: 'SP_GENERATE_INVOICE', type: 'PROCEDURE', categoryKey: 'PROC', schemaId: 'main_schema', dbId: 'primary_db', compatibility: 'OPTIMAL', isSelected: true }
                  ]
                }
              ]
            },
            {
              id: 'audit_schema',
              name: 'audit Schema',
              dbId: 'primary_db',
              isExpanded: false,
              categories: [
                {
                  key: 'TBL',
                  label: 'Tables',
                  badge: 'TBL',
                  badgeClass: 'bg-blue-100 text-blue-900',
                  schemaId: 'audit_schema',
                  dbId: 'primary_db',
                  isExpanded: false,
                  objects: [
                    { id: 'tbl_audit', name: 'AUDIT_LOGS', type: 'TABLE', categoryKey: 'TBL', schemaId: 'audit_schema', dbId: 'primary_db', estimatedRows: 2800000, estimatedSizeBytes: 4613734400, columnsCount: 8, compatibility: 'OPTIMAL', isSelected: true }
                  ]
                }
              ]
            }
          ]
        }
      ];
    }
  }

  public filteredDatabases = computed<ScopeDbContainer[]>(() => {
    let list = this.databases();
    const dbFilter = this.filterDatabase;
    const schFilter = this.filterSchema;
    const typeFilter = this.filterType;
    const search = this.searchObjectName.trim().toLowerCase();

    if (dbFilter !== 'ALL') {
      list = list.filter(db => db.id === dbFilter);
    }

    return list.map(db => {
      const filteredSchemas = db.schemas
        .filter(sch => schFilter === 'ALL' || sch.id === schFilter)
        .map(sch => {
          const filteredCategories = sch.categories
            .filter(cat => typeFilter === 'ALL' || cat.key === typeFilter || (typeFilter === 'TABLE' && cat.key === 'COLL') || (typeFilter === 'TABLE' && cat.key === 'TOPIC'))
            .map(cat => {
              const filteredObjects = cat.objects.filter(obj => {
                if (!search) return true;
                return obj.name.toLowerCase().includes(search);
              });
              return { ...cat, objects: filteredObjects };
            })
            .filter(cat => cat.objects.length > 0);
          return { ...sch, categories: filteredCategories };
        })
        .filter(sch => sch.categories.length > 0);
      return { ...db, schemas: filteredSchemas };
    });
  });

  public selectObject(obj: ScopeObjectItem): void {
    this.selectedObject = obj;
  }

  public totalDatabases(): number {
    return this.databases().length;
  }

  public totalSchemas(): number {
    return this.databases().reduce((sum, db) => sum + db.schemas.length, 0);
  }

  public totalObjects(): number {
    let count = 0;
    for (const db of this.databases()) {
      for (const sch of db.schemas) {
        for (const cat of sch.categories) {
          count += cat.objects.length;
        }
      }
    }
    return count;
  }

  public getDbObjectsCount(db: ScopeDbContainer): number {
    let c = 0;
    for (const sch of db.schemas) {
      for (const cat of sch.categories) {
        c += cat.objects.length;
      }
    }
    return c;
  }

  public getCategoryTotalObjects(sch: ScopeSchemaContainer): number {
    return sch.categories.reduce((acc, cat) => acc + cat.objects.length, 0);
  }

  public getCategoryRows(cat: ScopeCategoryGroup): number {
    return cat.objects.reduce((sum, o) => sum + (o.estimatedRows || 0), 0);
  }

  public getCategorySize(cat: ScopeCategoryGroup): number {
    return cat.objects.reduce((sum, o) => sum + (o.estimatedSizeBytes || 0), 0);
  }

  public isDbAllSelected(db: ScopeDbContainer): boolean {
    for (const sch of db.schemas) {
      for (const cat of sch.categories) {
        for (const obj of cat.objects) {
          if (!obj.isSelected) return false;
        }
      }
    }
    return true;
  }

  public toggleDbSelection(db: ScopeDbContainer, event: any): void {
    const checked = event.target.checked;
    for (const sch of db.schemas) {
      for (const cat of sch.categories) {
        for (const obj of cat.objects) {
          obj.isSelected = checked;
        }
      }
    }
  }

  public isSchemaAllSelected(sch: ScopeSchemaContainer): boolean {
    for (const cat of sch.categories) {
      for (const obj of cat.objects) {
        if (!obj.isSelected) return false;
      }
    }
    return true;
  }

  public toggleSchemaSelection(sch: ScopeSchemaContainer, event: any): void {
    const checked = event.target.checked;
    for (const cat of sch.categories) {
      for (const obj of cat.objects) {
        obj.isSelected = checked;
      }
    }
  }

  public isCategoryAllSelected(cat: ScopeCategoryGroup): boolean {
    return cat.objects.every(o => o.isSelected);
  }

  public toggleCategorySelection(cat: ScopeCategoryGroup, event: any): void {
    const checked = event.target.checked;
    for (const obj of cat.objects) {
      obj.isSelected = checked;
    }
  }

  public selectAll(): void {
    for (const db of this.databases()) {
      for (const sch of db.schemas) {
        for (const cat of sch.categories) {
          for (const obj of cat.objects) {
            obj.isSelected = true;
          }
        }
      }
    }
  }

  public deselectAll(): void {
    for (const db of this.databases()) {
      for (const sch of db.schemas) {
        for (const cat of sch.categories) {
          for (const obj of cat.objects) {
            obj.isSelected = false;
          }
        }
      }
    }
  }

  public expandAll(): void {
    for (const db of this.databases()) {
      db.isExpanded = true;
      for (const sch of db.schemas) {
        sch.isExpanded = true;
        for (const cat of sch.categories) {
          cat.isExpanded = true;
        }
      }
    }
  }

  public collapseAll(): void {
    for (const db of this.databases()) {
      db.isExpanded = false;
      for (const sch of db.schemas) {
        sch.isExpanded = false;
        for (const cat of sch.categories) {
          cat.isExpanded = false;
        }
      }
    }
  }

  public formatNumber(num?: number): string {
    if (num === undefined || num === null) return '—';
    return num.toLocaleString();
  }

  public formatBytes(bytes?: number): string {
    if (bytes === undefined || bytes === null || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}
