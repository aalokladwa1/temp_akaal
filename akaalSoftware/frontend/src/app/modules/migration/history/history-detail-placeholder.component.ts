import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { HistoryHomeService } from './history-home.service';
import { MigrationHistoryItem } from './history-home.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-history-detail-placeholder',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto pb-16 font-sans select-none animate-in fade-in duration-150">
      
      <!-- Top Breadcrumb Navigation -->
      <div class="flex items-center justify-between gap-4 pb-4 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <a (click)="goBack()" class="hover:text-blue-600 transition-colors cursor-pointer">History &amp; Evidence Home</a>
            <span class="text-slate-300">/</span>
            <span class="text-blue-600 font-bold font-mono">{{ migrationId() }}</span>
          </div>
          <h1 class="text-2xl font-bold font-heading text-slate-900 tracking-tight">
            {{ item()?.migrationName || 'Historical Execution Record' }}
          </h1>
          <p class="text-xs text-slate-600 font-normal">
            Forensic record, sealed execution trace, and validation ledger for execution <span class="font-mono font-semibold">{{ item()?.executionId || 'N/A' }}</span>.
          </p>
        </div>

        <button
          type="button"
          (click)="goBack()"
          class="h-8 px-4 rounded-md bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-800 text-xs font-semibold transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-400">
          Back to History
        </button>
      </div>

      <!-- Execution Overview Card -->
      @if (item(); as hist) {
        <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-6">
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Execution Outcome</span>
              <span class="text-sm font-bold text-slate-900">{{ hist.outcome }}</span>
              <span class="text-[11px] text-slate-500 font-mono">{{ hist.durationString }}</span>
            </div>

            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Validation Verdict</span>
              <span class="text-sm font-bold text-slate-900">{{ hist.validationState }}</span>
              <span class="text-[11px] text-slate-500">{{ hist.validationDiscrepancyCount }} discrepancies</span>
            </div>

            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Evidence Sealing</span>
              <span class="text-sm font-bold text-slate-900">{{ hist.evidenceAvailability }}</span>
              <span class="text-[11px] text-slate-500">{{ hist.evidenceIntegrity }}</span>
            </div>

            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Continuity / Cutover</span>
              <span class="text-sm font-bold text-slate-900">{{ hist.continuity.cutoverStatus }}</span>
              <span class="text-[11px] text-slate-500">{{ hist.continuity.recoveryStatus }}</span>
            </div>

          </div>

          <!-- Cryptographic Digest Info -->
          @if (hist.evidenceDigest) {
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-600 uppercase tracking-wider">Sealed SHA-256 Content Digest</span>
              <span class="font-mono text-xs text-slate-900 font-semibold select-all break-all">{{ hist.evidenceDigest }}</span>
            </div>
          }

          <div class="text-xs text-slate-500">
            Operator: <strong class="text-slate-800">{{ hist.operator }}</strong> • Started: <span class="font-mono">{{ hist.startedAt }}</span> • Completed: <span class="font-mono">{{ hist.completedAt || 'N/A' }}</span>
          </div>
        </div>
      } @else {
        <div class="p-8 rounded-2xl bg-white border border-slate-200 text-center text-xs text-slate-500">
          Execution record not found or unavailable.
        </div>
      }

    </div>
  `
})
export class HistoryDetailPlaceholderComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private hs = inject(HistoryHomeService);

  public migrationId = signal<string>('');
  public item = signal<MigrationHistoryItem | undefined>(undefined);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('migrationId') || '';
    this.migrationId.set(id);
    const found = this.hs.historyItems().find(h => h.migrationId === id || h.id === id || h.executionId === id);
    this.item.set(found);
  }

  goBack(): void {
    const isMigrationPrefix = this.router.url.startsWith('/migration');
    this.router.navigate([isMigrationPrefix ? '/migration/history' : '/history']);
  }
}
