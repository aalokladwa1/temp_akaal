import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReportsService } from '../services/reports.service';
import { EvidenceItemDTO, formatEvidenceType } from '../models/evidence.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-evidence-explorer',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full animate-in fade-in duration-150">
      
      <!-- Section Title & Restrained Controls -->
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">Evidence Explorer</h2>
          <p class="text-xs text-slate-500 mt-0.5">
            Canonical proof material, validation Merkle roots, partition manifests, and execution journals.
          </p>
        </div>
        
        <div class="text-xs text-slate-500 font-medium self-end">
          Showing <span class="font-semibold text-slate-800">{{ service.paginatedEvidence().total_count }}</span> proof records
        </div>
      </div>

      <!-- Restrained Filter & Search Toolbar -->
      <div class="flex items-center justify-between gap-4 flex-wrap bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
        <div class="flex items-center gap-3 flex-1 min-w-[280px]">
          <div class="relative w-full max-w-md">
            <app-lucide-icon name="search" [size]="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
            <input
              type="text"
              [ngModel]="service.evidenceFilters().search_query"
              (ngModelChange)="onSearchChange($event)"
              placeholder="Search evidence by title, subject, or context..."
              class="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 bg-slate-50 hover:bg-white transition-colors" />
          </div>
        </div>

        <div class="flex items-center gap-3 flex-wrap">
          <!-- Artifact Type Filter -->
          <div class="flex items-center gap-1.5 text-xs text-slate-600">
            <label for="evidence-type-filter" class="font-medium text-slate-500">Type:</label>
            <select
              id="evidence-type-filter"
              [ngModel]="service.evidenceFilters().artifact_type"
              (ngModelChange)="onTypeChange($event)"
              class="h-8 px-2.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none focus:border-blue-500 cursor-pointer">
              <option value="ALL">All Types</option>
              <option value="MANIFEST_SNAPSHOT">Partition Manifest</option>
              <option value="MERKLE_TREE_DIGEST">Merkle Tree Digest</option>
              <option value="GOVERNANCE_LEDGER">Governance Ledger</option>
              <option value="SCHEMA_DIFF">Schema Diff</option>
              <option value="WATERMARK_LOG">CDC Watermark Log</option>
              <option value="INTEGRITY_SCAN">Integrity Scan</option>
              <option value="AUDIT_JOURNAL">Audit Journal</option>
              <option value="RECOVERY_CHECKPOINT">Recovery Checkpoint</option>
            </select>
          </div>

          <!-- Sort Order -->
          <div class="flex items-center gap-1.5 text-xs text-slate-600">
            <label for="evidence-sort-filter" class="font-medium text-slate-500">Sort:</label>
            <select
              id="evidence-sort-filter"
              [ngModel]="service.evidenceFilters().sort_direction"
              (ngModelChange)="onSortDirectionChange($event)"
              class="h-8 px-2.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none focus:border-blue-500 cursor-pointer">
              <option value="desc">Newest First</option>
              <option value="asc">Oldest First</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Spacious Evidence Inventory Table -->
      <div class="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-slate-500 text-[11px] uppercase tracking-wider font-semibold">
              <th class="py-3 px-4">Evidence Artifact</th>
              <th class="py-3 px-4">Artifact Type</th>
              <th class="py-3 px-4">Subject Context</th>
              <th class="py-3 px-4">Created</th>
              <th class="py-3 px-4">Integrity</th>
              <th class="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
            @for (item of service.paginatedEvidence().items; track item.id) {
              <tr 
                (click)="service.openEvidenceDetail(item.id)"
                class="hover:bg-slate-50/80 transition-colors cursor-pointer group">
                
                <!-- Primary Title with Secondary ID -->
                <td class="py-3.5 px-4 font-medium text-slate-900 group-hover:text-blue-600 transition-colors">
                  <div class="flex flex-col gap-0.5">
                    <span class="font-semibold">{{ item.title }}</span>
                    <span class="text-[11px] text-slate-400 font-mono">{{ item.id }}</span>
                  </div>
                </td>

                <!-- Type -->
                <td class="py-3.5 px-4 text-slate-600 font-medium">
                  {{ formatType(item.artifact_type) }}
                </td>

                <!-- Subject -->
                <td class="py-3.5 px-4 text-slate-600">
                  {{ item.subject_name }}
                </td>

                <!-- Created Date -->
                <td class="py-3.5 px-4 text-slate-500 whitespace-nowrap">
                  {{ item.created_at | date:'yyyy-MM-dd HH:mm' }}
                </td>

                <!-- Integrity State -->
                <td class="py-3.5 px-4">
                  @if (item.integrity_status === 'VERIFIED') {
                    <span class="text-emerald-700 font-medium inline-flex items-center gap-1.5">
                      <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                      <span>Verified</span>
                    </span>
                  } @else if (item.integrity_status === 'MISMATCH') {
                    <span class="text-rose-700 font-medium inline-flex items-center gap-1.5">
                      <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                      <span>Mismatch</span>
                    </span>
                  } @else {
                    <span class="text-slate-500 font-medium">Unverified</span>
                  }
                </td>

                <!-- Action Button -->
                <td class="py-3.5 px-4 text-right whitespace-nowrap" (click)="$event.stopPropagation()">
                  <button
                    (click)="service.openEvidenceDetail(item.id)"
                    class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
                    Inspect
                  </button>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="6" class="py-12 px-4 text-center">
                  <div class="flex flex-col items-center justify-center gap-2 max-w-sm mx-auto">
                    <app-lucide-icon name="file-question" [size]="24" class="text-slate-400"></app-lucide-icon>
                    <p class="text-xs font-semibold text-slate-700">No evidence records found</p>
                    <p class="text-xs text-slate-500">
                      No evidence matches the active search query or type filters.
                    </p>
                  </div>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

      <!-- Server/Read-Model Pagination Controls -->
      <div class="flex items-center justify-between gap-4 pt-1 flex-wrap">
        <div class="text-xs text-slate-500">
          Showing <span class="font-medium text-slate-700">{{ service.paginatedEvidence().items.length }}</span> of <span class="font-medium text-slate-700">{{ service.paginatedEvidence().total_count }}</span> records
        </div>

        <div class="flex items-center gap-2">
          <button
            [disabled]="service.paginatedEvidence().page_index === 0"
            (click)="onPageChange(service.paginatedEvidence().page_index - 1)"
            class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-2xs cursor-pointer">
            Previous
          </button>

          <span class="text-xs font-medium text-slate-600 px-2">
            Page {{ service.paginatedEvidence().page_index + 1 }} of {{ service.paginatedEvidence().total_pages || 1 }}
          </span>

          <button
            [disabled]="service.paginatedEvidence().page_index + 1 >= service.paginatedEvidence().total_pages"
            (click)="onPageChange(service.paginatedEvidence().page_index + 1)"
            class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-2xs cursor-pointer">
            Next
          </button>
        </div>
      </div>

    </div>
  `
})
export class EvidenceExplorerComponent {
  public service = inject(ReportsService);

  public formatType(type: string): string {
    return formatEvidenceType(type);
  }

  public onSearchChange(val: string): void {
    this.service.updateEvidenceFilter({ search_query: val, page_index: 0 });
  }

  public onTypeChange(val: string): void {
    this.service.updateEvidenceFilter({ artifact_type: val, page_index: 0 });
  }

  public onSortDirectionChange(val: 'asc' | 'desc'): void {
    this.service.updateEvidenceFilter({ sort_direction: val, page_index: 0 });
  }

  public onPageChange(page: number): void {
    this.service.updateEvidenceFilter({ page_index: page });
  }
}
