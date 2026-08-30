import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CodeTranspilerItem, TableMappingItem, ColumnMappingRow } from '../../../../core/models/migration-view.models';

@Component({
  selector: 'app-step5-mapping',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent
  ],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
      
      <!-- Header -->
      <div class="flex items-center justify-between pb-2 border-b border-slate-200">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center font-bold">
            <app-lucide-icon name="table-properties" [size]="16"></app-lucide-icon>
          </div>
          <div>
            <h2 class="text-base font-bold text-slate-900">Step 5 &bull; MAPPING &amp; CODE TRANSPILATION</h2>
            <p class="text-xs text-slate-500 font-medium">Table routing, column type coercion, PII masking, deduplication, and code conversion.</p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <span class="text-slate-500 font-medium">Fidelity:</span>
          <span class="px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 font-bold border border-blue-200 font-mono">
            {{ ms.wizardDraft().sourceProvider }} &rarr; {{ ms.wizardDraft().targetProvider }}
          </span>
        </div>
      </div>

      <!-- Studio Dual-Tab Navigation -->
      <div class="flex items-center gap-2 p-1 rounded-xl bg-slate-100/80 border border-slate-200 w-fit">
        <button
          type="button"
          (click)="activeStudioTab.set('MAPPING')"
          class="h-8 px-4 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5"
          [class.bg-white]="activeStudioTab() === 'MAPPING'"
          [class.text-blue-700]="activeStudioTab() === 'MAPPING'"
          [class.shadow-2xs]="activeStudioTab() === 'MAPPING'"
          [class.text-slate-600]="activeStudioTab() !== 'MAPPING'">
          <app-lucide-icon name="table-properties" [size]="14"></app-lucide-icon>
          <span>Table &amp; Column Mapping Studio</span>
        </button>

        <button
          type="button"
          (click)="activeStudioTab.set('TRANSPILER')"
          class="h-8 px-4 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5"
          [class.bg-white]="activeStudioTab() === 'TRANSPILER'"
          [class.text-blue-700]="activeStudioTab() === 'TRANSPILER'"
          [class.shadow-2xs]="activeStudioTab() === 'TRANSPILER'"
          [class.text-slate-600]="activeStudioTab() !== 'TRANSPILER'">
          <app-lucide-icon name="code" [size]="14"></app-lucide-icon>
          <span>Code Transpiler Studio (SCT Workbench)</span>
        </button>
      </div>

      <!-- =============================================================== -->
      <!-- TAB 1: TABLE & COLUMN MAPPING STUDIO (3-COLUMN LAYOUT)          -->
      <!-- =============================================================== -->
      @if (activeStudioTab() === 'MAPPING') {
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          
          <!-- LEFT (22%): Source Table Tree -->
          <div class="lg:col-span-3 flex flex-col gap-3 p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
              <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">Source Objects</span>
              <span class="text-[10px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded font-mono">{{ ms.wizardDraft().sourceProvider }}</span>
            </div>

            <div class="flex flex-col gap-1.5 max-h-[500px] overflow-y-auto">
              @for (tbl of sourceTables; track tbl.name) {
                <div
                  (click)="selectedTableName = tbl.name"
                  class="p-2.5 rounded-lg border-2 cursor-pointer transition-all flex flex-col gap-1 hover:border-blue-300"
                  [class.border-blue-600]="selectedTableName === tbl.name"
                  [class.bg-blue-50]="selectedTableName === tbl.name"
                  [class.border-slate-200]="selectedTableName !== tbl.name"
                  [class.bg-white]="selectedTableName !== tbl.name">
                  
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-1.5">
                      <app-lucide-icon name="table" [size]="13" class="text-slate-500"></app-lucide-icon>
                      <span class="font-bold text-slate-900 text-xs truncate">{{ tbl.name }}</span>
                    </div>
                    <span class="text-[10px] font-mono text-slate-500">{{ tbl.columnsCount }} cols</span>
                  </div>

                  <div class="flex items-center justify-between text-[10.5px] text-slate-400">
                    <span>{{ tbl.rows }} rows</span>
                    <span class="text-emerald-700 font-bold">100% mapped</span>
                  </div>
                </div>
              }
            </div>
          </div>

          <!-- CENTER (56%): Mapping & Policies Canvas -->
          <div class="lg:col-span-6 flex flex-col gap-4 p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <div class="flex flex-col">
                <span class="font-bold text-slate-900 text-xs">Table Mapping: {{ selectedTableName }} &rarr; public.{{ selectedTableName.toLowerCase() }}</span>
                <span class="text-[11px] text-slate-500 font-medium">5 Columns Mapped &bull; 1 PII Redaction Rule &bull; Deduplication Enabled</span>
              </div>

              <!-- Internal Sub-Tabs -->
              <div class="flex items-center gap-1 p-0.5 rounded-lg bg-slate-100 border border-slate-200">
                <button
                  type="button"
                  (click)="mappingSubTab = 'COLUMNS'"
                  class="h-6 px-2.5 rounded text-[11px] font-bold transition-all cursor-pointer"
                  [class.bg-white]="mappingSubTab === 'COLUMNS'"
                  [class.text-blue-700]="mappingSubTab === 'COLUMNS'"
                  [class.shadow-2xs]="mappingSubTab === 'COLUMNS'"
                  [class.text-slate-600]="mappingSubTab !== 'COLUMNS'">
                  Columns
                </button>
                <button
                  type="button"
                  (click)="mappingSubTab = 'PII'"
                  class="h-6 px-2.5 rounded text-[11px] font-bold transition-all cursor-pointer"
                  [class.bg-white]="mappingSubTab === 'PII'"
                  [class.text-blue-700]="mappingSubTab === 'PII'"
                  [class.shadow-2xs]="mappingSubTab === 'PII'"
                  [class.text-slate-600]="mappingSubTab !== 'PII'">
                  PII &amp; Masking
                </button>
                <button
                  type="button"
                  (click)="mappingSubTab = 'DEDUP'"
                  class="h-6 px-2.5 rounded text-[11px] font-bold transition-all cursor-pointer"
                  [class.bg-white]="mappingSubTab === 'DEDUP'"
                  [class.text-blue-700]="mappingSubTab === 'DEDUP'"
                  [class.shadow-2xs]="mappingSubTab === 'DEDUP'"
                  [class.text-slate-600]="mappingSubTab !== 'DEDUP'">
                  Deduplication
                </button>
              </div>
            </div>

            <!-- SUB-TAB 1: COLUMNS TABLE -->
            @if (mappingSubTab === 'COLUMNS') {
              <div class="flex flex-col divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
                <div class="grid grid-cols-12 gap-2 px-3 py-2 bg-slate-50 text-[10.5px] font-bold text-slate-600 uppercase tracking-wider">
                  <div class="col-span-4">Source Column</div>
                  <div class="col-span-2">Source Type</div>
                  <div class="col-span-3">Target Column</div>
                  <div class="col-span-3">Target Type</div>
                </div>

                @for (col of tableMapping.columns; track col.id) {
                  <div class="grid grid-cols-12 gap-2 px-3 py-2.5 items-center hover:bg-slate-50/70 transition-colors text-xs">
                    <div class="col-span-4 flex items-center gap-1.5 font-bold text-slate-900 font-mono">
                      @if (col.isPrimaryKey) {
                        <span class="px-1 py-0.2 rounded bg-amber-100 text-amber-900 text-[9px] font-extrabold">PK</span>
                      }
                      <span class="truncate">{{ col.sourceColumn }}</span>
                    </div>

                    <div class="col-span-2 font-mono text-[11px] text-slate-500 truncate">{{ col.sourceType }}</div>

                    <div class="col-span-3">
                      <input
                        type="text"
                        [(ngModel)]="col.targetColumn"
                        class="h-7 px-2 w-full rounded bg-white border border-slate-200 text-xs font-semibold font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500" />
                    </div>

                    <div class="col-span-3">
                      <input
                        type="text"
                        [(ngModel)]="col.targetType"
                        class="h-7 px-2 w-full rounded bg-white border border-slate-200 text-xs font-semibold font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500" />
                    </div>
                  </div>
                }
              </div>
            }

            <!-- SUB-TAB 2: PII & MASKING POLICIES -->
            @if (mappingSubTab === 'PII') {
              <div class="flex flex-col gap-3">
                <div class="p-3.5 rounded-lg bg-amber-50/70 border border-amber-200/80 flex items-start gap-2.5">
                  <app-lucide-icon name="shield-alert" [size]="16" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
                  <div class="flex flex-col gap-0.5">
                    <span class="font-bold text-amber-950 text-xs">PII Masking &amp; Data Obfuscation</span>
                    <span class="text-amber-900 text-[11px] leading-relaxed">
                      Transformations are applied in-flight inside the stream worker. Raw unmasked values never touch target tables or intermediate journals.
                    </span>
                  </div>
                </div>

                <div class="grid grid-cols-1 gap-2.5">
                  <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
                    <div class="flex flex-col gap-0.5">
                      <span class="font-bold text-slate-900 font-mono">SSN_NO &rarr; ssn_masked</span>
                      <span class="text-[11px] text-slate-500">Pattern: Format-Preserving Redaction (XXX-XX-####)</span>
                    </div>
                    <span class="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-bold text-[10.5px]">SSN_REDACT</span>
                  </div>
                </div>
              </div>
            }

            <!-- SUB-TAB 3: DEDUPLICATION & DATA QUALITY -->
            @if (mappingSubTab === 'DEDUP') {
              <div class="flex flex-col gap-3">
                <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
                  <div class="flex flex-col gap-0.5">
                    <span class="font-bold text-slate-900">In-Flight Row Deduplication</span>
                    <span class="text-[11px] text-slate-500">Deduplicate multiple updates occurring within same micro-batch window.</span>
                  </div>
                  <input type="checkbox" [(ngModel)]="tableMapping.dedupEnabled" class="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer" />
                </div>

                <div class="grid grid-cols-2 gap-3">
                  <div class="flex flex-col gap-1">
                    <label class="font-bold text-slate-800 text-[11px]">Survivor Resolution Rule</label>
                    <select [(ngModel)]="tableMapping.dedupSurvivorRule" class="h-8 px-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold">
                      <option value="LATEST_TIMESTAMP">Latest Commit Timestamp (LWW)</option>
                      <option value="HIGHEST_SEQUENCE">Highest SCN / Sequence Number</option>
                      <option value="SOURCE_PRIORITY">Source System Priority</option>
                    </select>
                  </div>
                  <div class="flex flex-col gap-1">
                    <label class="font-bold text-slate-800 text-[11px]">Target Conflict Policy</label>
                    <select [(ngModel)]="tableMapping.conflictPolicy" class="h-8 px-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold">
                      <option value="OVERWRITE">Upsert / Overwrite Existing Target Row</option>
                      <option value="IGNORE">Ignore Duplicate Target Row</option>
                      <option value="FAIL_ON_CONFLICT">Fail &amp; Divert to Quarantine DLQ</option>
                    </select>
                  </div>
                </div>
              </div>
            }

          </div>

          <!-- RIGHT (22%): Target Table Tree -->
          <div class="lg:col-span-3 flex flex-col gap-3 p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
              <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">Target Schemas</span>
              <span class="text-[10px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded font-mono">{{ ms.wizardDraft().targetProvider }}</span>
            </div>

            <div class="flex flex-col gap-1.5 max-h-[500px] overflow-y-auto">
              <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span class="font-bold text-slate-900 font-mono text-xs">public.accounts</span>
                <span class="text-[10.5px] text-slate-500 font-medium">PostgreSQL Table &bull; 5 columns</span>
                <span class="text-[10px] text-emerald-700 font-bold">1:1 DDL Target Ready</span>
              </div>
              <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span class="font-bold text-slate-900 font-mono text-xs">public.customers</span>
                <span class="text-[10.5px] text-slate-500 font-medium">PostgreSQL Table &bull; 8 columns</span>
              </div>
            </div>
          </div>

        </div>
      }

      <!-- =============================================================== -->
      <!-- TAB 2: CODE TRANSPILER STUDIO (SCT WORKBENCH 3-COLUMN LAYOUT)   -->
      <!-- =============================================================== -->
      @if (activeStudioTab() === 'TRANSPILER') {
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          
          <!-- LEFT (22%): Source Code Tree -->
          <div class="lg:col-span-3 flex flex-col gap-3 p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
              <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">Code Objects (Oracle)</span>
              <span class="text-[10px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded font-mono">PL/SQL</span>
            </div>

            <div class="flex flex-col gap-1.5 max-h-[520px] overflow-y-auto">
              @for (item of transpilerItems; track item.id) {
                <div
                  (click)="selectedTranspilerItem = item"
                  class="p-2.5 rounded-lg border-2 cursor-pointer transition-all flex flex-col gap-1 hover:border-blue-300"
                  [class.border-blue-600]="selectedTranspilerItem.id === item.id"
                  [class.bg-blue-50]="selectedTranspilerItem.id === item.id"
                  [class.border-slate-200]="selectedTranspilerItem.id !== item.id"
                  [class.bg-white]="selectedTranspilerItem.id !== item.id">
                  
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-slate-900 font-mono text-xs truncate">{{ item.name }}</span>
                    <span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-bold text-[9.5px] uppercase">{{ item.objectType }}</span>
                  </div>

                  <div class="flex items-center justify-between text-[10.5px] text-slate-500">
                    <span>Complexity: {{ item.complexityScore }}/10</span>
                    <span class="font-bold text-blue-700">{{ formatConversionStatus(item.conversionStatus) }}</span>
                  </div>
                </div>
              }
            </div>
          </div>

          <!-- CENTER (56%): Dual Stacked Source & Proposed Editors -->
          <div class="lg:col-span-6 flex flex-col gap-4">
            
            <!-- TOP EDITOR: SOURCE SQL -->
            <div class="p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-2">
              <div class="flex items-center justify-between pb-2 border-b border-slate-100">
                <div class="flex items-center gap-2">
                  <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">Source SQL: {{ selectedTranspilerItem.name }}</span>
                  <span class="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-mono font-bold text-[10px]">{{ selectedTranspilerItem.sourceLanguage }}</span>
                </div>
                <span class="text-[11px] text-slate-400 font-mono">Read-Only Abstract Syntax</span>
              </div>

              <textarea
                rows="8"
                readonly
                [value]="selectedTranspilerItem.sourceSql"
                class="p-3 w-full rounded-lg bg-slate-900 text-slate-100 text-xs font-mono font-medium focus:outline-none leading-relaxed resize-none"></textarea>
            </div>

            <!-- BOTTOM EDITOR: TARGET / PROPOSED SQL -->
            <div class="p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-2">
              <div class="flex items-center justify-between pb-2 border-b border-slate-100">
                <div class="flex items-center gap-2">
                  <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">Proposed Target DDL: public.{{ selectedTranspilerItem.name.toLowerCase() }}</span>
                  <span class="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-mono font-bold text-[10px]">{{ selectedTranspilerItem.targetLanguage }}</span>
                </div>
                <span class="text-[11px] text-slate-500 font-medium">Editable Transpiled Proposal</span>
              </div>

              <textarea
                rows="8"
                [(ngModel)]="selectedTranspilerItem.targetSql"
                class="p-3 w-full rounded-lg bg-slate-900 text-emerald-300 text-xs font-mono font-medium focus:outline-none leading-relaxed resize-none"></textarea>

              <!-- AST Findings / Transpiler Warnings -->
              @if (selectedTranspilerItem.findings && selectedTranspilerItem.findings.length > 0) {
                <div class="flex flex-col gap-1.5 pt-2 border-t border-slate-100">
                  <span class="font-bold text-slate-800 text-[11px]">AST Analysis &amp; Semantic Notes:</span>
                  @for (finding of selectedTranspilerItem.findings; track finding.code) {
                    <div class="p-2 rounded bg-amber-50 text-amber-900 border border-amber-200 text-[11px] flex items-start gap-1.5">
                      <app-lucide-icon name="alert-triangle" [size]="13" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
                      <span class="leading-relaxed"><strong>Line {{ finding.line }} [{{ finding.code }}]:</strong> {{ finding.message }}</span>
                    </div>
                  }
                </div>
              }
            </div>

          </div>

          <!-- RIGHT (22%): Target Code Tree -->
          <div class="lg:col-span-3 flex flex-col gap-3 p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
              <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">Target Routines</span>
              <span class="text-[10px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded font-mono">PL/pgSQL</span>
            </div>

            <div class="flex flex-col gap-2 max-h-[520px] overflow-y-auto">
              <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span class="font-bold text-slate-900 font-mono text-xs">public.p_subtype_003</span>
                <span class="text-[10.5px] text-slate-500 font-medium">PostgreSQL Stored Procedure</span>
                <span class="text-[10px] text-blue-700 font-bold">Conversion Proposed</span>
              </div>
            </div>
          </div>

        </div>
      }

    </div>
  `
})
export class Step5MappingComponent {
  public ms = inject(MigrationUiService);

  public activeStudioTab = signal<'MAPPING' | 'TRANSPILER'>('MAPPING');
  public mappingSubTab: 'COLUMNS' | 'PII' | 'DEDUP' = 'COLUMNS';

  public selectedTableName = 'ACCOUNTS';
  public sourceTables = [
    { name: 'ACCOUNTS', columnsCount: 5, rows: '18.6M' },
    { name: 'CUSTOMERS', columnsCount: 8, rows: '14.2M' },
    { name: 'TRANSACTIONS', columnsCount: 12, rows: '16.8M' },
    { name: 'AUDIT_LOGS', columnsCount: 6, rows: '2.8M' }
  ];

  public tableMapping: TableMappingItem = this.ms.wizardDraft().tableMapping;
  public transpilerItems: CodeTranspilerItem[] = this.ms.wizardDraft().codeTranspilerItems;
  public selectedTranspilerItem: CodeTranspilerItem = this.transpilerItems[0];

  public formatConversionStatus(status: string): string {
    switch (status) {
      case 'CONVERSION_PROPOSED': return 'Proposal Generated';
      case 'NEEDS_REVIEW': return 'Needs Review';
      case 'READY_FOR_BACKEND_VALIDATION': return 'Ready for Validation';
      case 'UNSUPPORTED_CONSTRUCT': return 'Unsupported Construct';
      default: return 'Not Evaluated';
    }
  }
}
