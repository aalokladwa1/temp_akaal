import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HistoryWorkspaceService } from '../history-workspace.service';
import { HistoryMode, HistoryOutcome } from '../../history-home.models';

@Component({
  selector: 'app-history-workspace-header',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (hws.currentRecord(); as record) {
      <header class="bg-white border-b border-slate-200 px-6 py-4">
        <!-- Breadcrumbs and Back Action -->
        <div class="flex items-center justify-between gap-4 mb-3">
          <nav aria-label="Breadcrumb" class="flex items-center gap-2 text-xs text-slate-500">
            <button 
              type="button" 
              (click)="navigateToPortfolio()" 
              class="hover:text-slate-800 transition-colors font-medium cursor-pointer">
              Migration Portfolio
            </button>
            <span class="text-slate-400">/</span>
            <button 
              type="button" 
              (click)="navigateToHistoryHome()" 
              class="hover:text-slate-800 transition-colors font-medium cursor-pointer">
              History &amp; Evidence
            </button>
            <span class="text-slate-400">/</span>
            <span class="text-slate-900 font-semibold truncate max-w-[320px]" [title]="record.migrationName">
              {{ record.migrationName }}
            </span>
          </nav>

          <div class="flex items-center gap-3">
            <button 
              type="button"
              (click)="navigateToHistoryHome()"
              class="h-8 px-3 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-sm transition-colors cursor-pointer">
              Back to History
            </button>
          </div>
        </div>

        <!-- Main Workspace Title & Primary Context Header -->
        <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <!-- Left: Identity & Badges -->
          <div class="space-y-1.5 min-w-0">
            <div class="flex items-center gap-2.5 flex-wrap">
              <h1 class="text-xl font-bold text-slate-900 tracking-tight truncate max-w-[500px]" [title]="record.migrationName">
                {{ record.migrationName }}
              </h1>
              
              <!-- Clean Mode Badge -->
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-semibold border"
                [ngClass]="getModeBadgeClass(record.mode)">
                {{ getModeLabel(record.mode) }}
              </span>

              <!-- Outcome Badge -->
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-bold border"
                [ngClass]="getOutcomeBadgeClass(record.outcome)">
                {{ record.outcome }}
              </span>

              <!-- Execution ID Tag -->
              <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-mono font-medium bg-slate-100 text-slate-700 border border-slate-200" [title]="record.executionId">
                {{ record.executionId }}
              </span>
            </div>

            <!-- Project & Initiative & Topology Context -->
            <div class="flex items-center gap-3 text-xs text-slate-600 flex-wrap">
              <span class="font-medium text-slate-800">{{ record.projectName }}</span>
              @if (record.initiativeName) {
                <span class="text-slate-300">•</span>
                <span class="text-slate-500">{{ record.initiativeName }}</span>
              }
              <span class="text-slate-300">•</span>
              <!-- Source -> Target -->
              <div class="inline-flex items-center gap-1.5 font-medium text-slate-800">
                <span class="text-slate-600">{{ record.sourceProvider }}</span>
                <span class="text-slate-400 font-normal">&rarr;</span>
                <span class="text-slate-900 font-semibold">{{ record.targetProvider }}</span>
              </div>
            </div>
          </div>

          <!-- Right: Key Timing & Operator Context Strip -->
          <div class="flex items-center gap-6 text-xs text-slate-600 bg-slate-50/80 px-4 py-2.5 rounded-md border border-slate-200 self-start lg:self-auto shrink-0">
            <div>
              <div class="text-[10px] uppercase font-bold text-slate-600 tracking-wider">Duration</div>
              <div class="font-semibold text-slate-900">{{ record.durationString }}</div>
            </div>
            <div class="h-6 w-px bg-slate-200"></div>
            <div>
              <div class="text-[10px] uppercase font-bold text-slate-600 tracking-wider">Total Processed</div>
              <div class="font-semibold text-slate-900">{{ record.totalRowsProcessed.toLocaleString() }} rows</div>
            </div>
            <div class="h-6 w-px bg-slate-200"></div>
            <div>
              <div class="text-[10px] uppercase font-bold text-slate-600 tracking-wider">Avg Throughput</div>
              <div class="font-semibold text-slate-900">{{ record.throughputFormatted }}</div>
            </div>
            <div class="h-6 w-px bg-slate-200"></div>
            <div>
              <div class="text-[10px] uppercase font-bold text-slate-600 tracking-wider">Operator</div>
              <div class="font-medium text-slate-800 truncate max-w-[140px]" [title]="record.operator">{{ record.operator }}</div>
            </div>
          </div>
        </div>
      </header>
    }
  `
})
export class HistoryWorkspaceHeaderComponent {
  public hws = inject(HistoryWorkspaceService);
  private router = inject(Router);

  public navigateToHistoryHome(): void {
    const isMigrationPrefix = this.router.url.startsWith('/migration');
    this.router.navigate([isMigrationPrefix ? '/migration/history' : '/history']);
  }

  public navigateToPortfolio(): void {
    this.router.navigate(['/migration/portfolio']);
  }

  public getModeLabel(mode: HistoryMode): string {
    switch (mode) {
      case 'M1_BULK': return 'Bulk Data Load';
      case 'M2_BULK_CDC': return 'Bulk + CDC Stream';
      case 'M3_CDC': return 'CDC Stream';
      case 'M4_INCREMENTAL': return 'Incremental Watermark';
      case 'M5_STATE_SYNC': return 'State Synchronization';
      case 'M6_SCHEMA_ONLY': return 'Schema Only';
      case 'M7_DATA_ONLY': return 'Data Only';
      case 'M8_VALIDATION_ONLY': return 'Validation Only';
      default: return mode;
    }
  }

  public getModeBadgeClass(mode: HistoryMode): string {
    switch (mode) {
      case 'M1_BULK': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'M2_BULK_CDC': return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'M3_CDC': return 'bg-cyan-50 text-cyan-800 border-cyan-200';
      case 'M4_INCREMENTAL': return 'bg-teal-50 text-teal-800 border-teal-200';
      case 'M5_STATE_SYNC': return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'M6_SCHEMA_ONLY': return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'M7_DATA_ONLY': return 'bg-emerald-50 text-emerald-800 border-emerald-200';
      case 'M8_VALIDATION_ONLY': return 'bg-sky-50 text-sky-800 border-sky-300 font-bold';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  }

  public getOutcomeBadgeClass(outcome: HistoryOutcome): string {
    switch (outcome) {
      case 'SUCCEEDED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'FAILED':
      case 'ABORTED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'RUNNING': return 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  }
}
