/**
 * AKAAL Reports — Part 1: Reports Home Container Component
 * Rebuilt to strictly conserve the accepted AKAAL Home layout system,
 * spacious vertical rhythm, standard card geometry, and clean bounded previews.
 */

import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReportsService } from './services/reports.service';
import { ReportsHeaderComponent } from './components/reports-header.component';
import { ReportsWorkspaceNavComponent } from './components/reports-workspace-nav.component';
import { ReportsOverviewStripComponent } from './components/reports-overview-strip.component';
import { ReportsCertificationAttentionComponent } from './components/reports-certification-attention.component';
import { ReportsRecentTableComponent } from './components/reports-recent-table.component';
import { ReportsEvidenceActivityComponent } from './components/reports-evidence-activity.component';

@Component({
  selector: 'app-reports-home',
  standalone: true,
  imports: [
    CommonModule,
    ReportsHeaderComponent,
    ReportsWorkspaceNavComponent,
    ReportsOverviewStripComponent,
    ReportsCertificationAttentionComponent,
    ReportsRecentTableComponent,
    ReportsEvidenceActivityComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- 0. REPORTS HEADER -->
      <app-reports-header></app-reports-header>

      <!-- 1. SUMMARY METRICS STRIP (3 Bounded Summary Cards) -->
      <app-reports-overview-strip></app-reports-overview-strip>

      <!-- 2. PRIMARY SPECIALIST WORKSPACES (3 Specialist Navigation Cards) -->
      <app-reports-workspace-nav></app-reports-workspace-nav>

      <!-- 3. CERTIFICATION ATTENTION & ASSURANCE GAPS (Needs Attention Preview) -->
      <app-reports-certification-attention></app-reports-certification-attention>

      <!-- 4. RECENT & NOTABLE TECHNICAL REPORTS (Clean Standard Table, 5–8 Rows) -->
      <app-reports-recent-table></app-reports-recent-table>

      <!-- 5. RECENT EVIDENCE & ATTESTATION ACTIVITY (Clean Standard Table) -->
      <app-reports-evidence-activity></app-reports-evidence-activity>

    </div>
  `
})
export class ReportsHomeComponent implements OnInit {
  public rs = inject(ReportsService);

  ngOnInit(): void {
    // Initial check
  }
}
