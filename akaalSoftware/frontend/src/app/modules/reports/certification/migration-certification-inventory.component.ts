import { Component, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReportsService } from '../services/reports.service';
import { 
  CertificationSummaryDTO, 
  CertificationDecisionState,
  formatCertificationDecision 
} from '../models/certification.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-migration-certification-inventory',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-5 w-full select-none animate-in fade-in duration-150">
      
      <!-- Header -->
      <div class="flex items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div class="flex flex-col">
          <h2 class="text-lg font-bold text-slate-900 font-heading">
            Migration Certifications
          </h2>
          <p class="text-xs text-slate-500">
            Formal execution outcome assertions, transferred scope accounting, and recovery checkpoint evidence.
          </p>
        </div>

        <div class="text-xs text-slate-500">
          <strong class="text-slate-900">{{ filteredList().length }}</strong> records recorded
        </div>
      </div>

      <!-- Search & Filters Toolbar -->
      <div class="flex items-center justify-between gap-4 flex-wrap bg-white p-3.5 border border-slate-200 rounded-xl shadow-2xs">
        
        <!-- Search Input -->
        <div class="relative flex-1 min-w-[240px] max-w-md">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
            <app-lucide-icon name="search" [size]="14"></app-lucide-icon>
          </span>
          <input
            type="text"
            [ngModel]="searchQuery()"
            (ngModelChange)="onSearchChange($event)"
            placeholder="Search by migration name, subject, or ID..."
            class="w-full h-8 pl-8 pr-3 text-xs rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
          />
        </div>

        <!-- Filter Dropdowns -->
        <div class="flex items-center gap-3 flex-wrap">
          
          <!-- Decision Filter -->
          <div class="flex items-center gap-1.5 text-xs text-slate-500">
            <span class="font-medium">Decision:</span>
            <select
              [ngModel]="decisionFilter()"
              (ngModelChange)="onDecisionFilterChange($event)"
              class="h-8 px-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-xs font-medium text-slate-700 focus:outline-none focus:border-blue-500 cursor-pointer">
              <option value="ALL">All Decisions</option>
              <option value="CERTIFIED">Certified</option>
              <option value="NOT_CERTIFIED">Not Certified</option>
              <option value="PENDING_EVALUATION">Pending Evaluation</option>
              <option value="EXPIRED">Expired</option>
              <option value="REVOKED">Revoked</option>
              <option value="CERTIFICATION_NOT_ISSUED">No Certification Issued</option>
            </select>
          </div>

          <!-- Sort Selector -->
          <div class="flex items-center gap-1.5 text-xs text-slate-500">
            <span class="font-medium">Sort:</span>
            <select
              [ngModel]="sortOrder()"
              (ngModelChange)="onSortChange($event)"
              class="h-8 px-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-xs font-medium text-slate-700 focus:outline-none focus:border-blue-500 cursor-pointer">
              <option value="NEWEST">Issued (Newest First)</option>
              <option value="OLDEST">Issued (Oldest First)</option>
              <option value="SUBJECT_ASC">Subject (A-Z)</option>
            </select>
          </div>

        </div>
      </div>

      <!-- Inventory Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              <th class="py-3 px-4">Subject &amp; Migration</th>
              <th class="py-3 px-4">Summary</th>
              <th class="py-3 px-4 hidden md:table-cell">Issued Timestamp</th>
              <th class="py-3 px-4">Decision State</th>
              <th class="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs">
            @if (paginatedList().length === 0) {
              <tr>
                <td colspan="5" class="py-12 text-center text-slate-400">
                  <div class="flex flex-col items-center justify-center gap-2">
                    <app-lucide-icon name="file-text" [size]="24"></app-lucide-icon>
                    <span class="font-medium">No migration certifications matched your search criteria.</span>
                  </div>
                </td>
              </tr>
            }

            @for (cert of paginatedList(); track cert.id) {
              <tr 
                (click)="onOpenCertification(cert.id)"
                class="hover:bg-slate-50/80 transition-colors group cursor-pointer">
                
                <!-- Subject -->
                <td class="py-3.5 px-4">
                  <div class="flex flex-col gap-0.5 max-w-md">
                    <span class="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                      {{ cert.subject_name }}
                    </span>
                    <span class="text-[11px] text-slate-500 font-medium">
                      {{ cert.title }}
                    </span>
                  </div>
                </td>

                <!-- Summary -->
                <td class="py-3.5 px-4 text-slate-600 max-w-sm">
                  <span class="line-clamp-2 leading-relaxed">{{ cert.summary }}</span>
                </td>

                <!-- Issued -->
                <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px] hidden md:table-cell">
                  {{ cert.issued_at | date:'yyyy-MM-dd HH:mm' }}
                </td>

                <!-- Decision -->
                <td class="py-3.5 px-4">
                  <span 
                    class="px-2.5 py-1 rounded-md text-[11px] font-bold inline-block"
                    [ngClass]="{
                      'bg-emerald-50 text-emerald-700 border border-emerald-200': cert.decision === 'CERTIFIED',
                      'bg-rose-50 text-rose-700 border border-rose-200': cert.decision === 'NOT_CERTIFIED' || cert.decision === 'REVOKED',
                      'bg-amber-50 text-amber-800 border border-amber-200': cert.decision === 'EXPIRED' || cert.decision === 'PENDING_EVALUATION',
                      'bg-slate-50 text-slate-700 border border-slate-200': cert.decision === 'CERTIFICATION_NOT_ISSUED' || cert.decision === 'UNKNOWN'
                    }">
                    {{ formatDecision(cert.decision) }}
                  </span>
                </td>

                <!-- Actions -->
                <td class="py-3.5 px-4 text-right">
                  <button
                    type="button"
                    (click)="onOpenCertification(cert.id); $event.stopPropagation()"
                    class="h-7 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs transition-colors cursor-pointer shadow-2xs">
                    Inspect
                  </button>
                </td>

              </tr>
            }
          </tbody>
        </table>

        <!-- Pagination Footer -->
        <div class="p-4 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs text-slate-600 flex-wrap gap-4">
          <div>
            Showing <strong class="text-slate-900">{{ paginatedList().length }}</strong> of <strong class="text-slate-900">{{ filteredList().length }}</strong> records
          </div>

          <div class="flex items-center gap-2">
            <button
              [disabled]="pageIndex() <= 1"
              (click)="onPrevPage()"
              class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none text-slate-700 font-medium cursor-pointer shadow-2xs">
              Previous
            </button>
            <span class="px-2 font-mono text-slate-700">
              Page {{ pageIndex() }} of {{ totalPages() }}
            </span>
            <button
              [disabled]="pageIndex() >= totalPages()"
              (click)="onNextPage()"
              class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none text-slate-700 font-medium cursor-pointer shadow-2xs">
              Next
            </button>
          </div>
        </div>

      </div>

    </div>
  `
})
export class MigrationCertificationInventoryComponent {
  public rs = inject(ReportsService);

  public searchQuery = signal<string>('');
  public decisionFilter = signal<string>('ALL');
  public sortOrder = signal<'NEWEST' | 'OLDEST' | 'SUBJECT_ASC'>('NEWEST');
  public pageIndex = signal<number>(1);
  public readonly pageSize = 8;

  public formatDecision = formatCertificationDecision;

  public filteredList = computed(() => {
    let list = this.rs.allCertifications().filter(c => c.domain === 'MIGRATION');
    const q = this.searchQuery().toLowerCase().trim();
    const decision = this.decisionFilter();

    if (decision !== 'ALL') {
      list = list.filter(c => c.decision === decision);
    }

    if (q) {
      list = list.filter(c => 
        c.subject_name.toLowerCase().includes(q) ||
        c.title.toLowerCase().includes(q) ||
        c.id.toLowerCase().includes(q)
      );
    }

    if (this.sortOrder() === 'NEWEST') {
      list = [...list].sort((a, b) => new Date(b.issued_at).getTime() - new Date(a.issued_at).getTime());
    } else if (this.sortOrder() === 'OLDEST') {
      list = [...list].sort((a, b) => new Date(a.issued_at).getTime() - new Date(b.issued_at).getTime());
    } else if (this.sortOrder() === 'SUBJECT_ASC') {
      list = [...list].sort((a, b) => a.subject_name.localeCompare(b.subject_name));
    }

    return list;
  });

  public totalPages = computed(() => Math.max(1, Math.ceil(this.filteredList().length / this.pageSize)));

  public paginatedList = computed(() => {
    const start = (this.pageIndex() - 1) * this.pageSize;
    return this.filteredList().slice(start, start + this.pageSize);
  });

  public onSearchChange(q: string): void {
    this.searchQuery.set(q);
    this.pageIndex.set(1);
  }

  public onDecisionFilterChange(d: string): void {
    this.decisionFilter.set(d);
    this.pageIndex.set(1);
  }

  public onSortChange(s: 'NEWEST' | 'OLDEST' | 'SUBJECT_ASC'): void {
    this.sortOrder.set(s);
  }

  public onPrevPage(): void {
    if (this.pageIndex() > 1) {
      this.pageIndex.update(p => p - 1);
    }
  }

  public onNextPage(): void {
    if (this.pageIndex() < this.totalPages()) {
      this.pageIndex.update(p => p + 1);
    }
  }

  public onOpenCertification(certId: string): void {
    this.rs.openCertificationById(certId);
  }
}
