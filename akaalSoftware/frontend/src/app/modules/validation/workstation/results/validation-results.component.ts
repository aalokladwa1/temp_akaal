import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResultsService } from './validation-results.service';
import { ValidationWorkstationService } from '../validation-workstation.service';

import { ResultsVerdictBannerComponent } from './components/results-verdict-banner.component';
import { ResultsSourceTargetProofComponent } from './components/results-source-target-proof.component';
import { ResultsAssuranceScopeComponent } from './components/results-assurance-scope.component';
import { ResultsUnresolvedFindingsComponent } from './components/results-unresolved-findings.component';
import { ResultsRemediationHistoryComponent } from './components/results-remediation-history.component';
import { ResultsRunHistoryComponent } from './components/results-run-history.component';
import { ResultsEvidenceIntegrityComponent } from './components/results-evidence-integrity.component';
import { ResultsAuditTimelineComponent } from './components/results-audit-timeline.component';
import { ResultsArtifactsCardComponent } from './components/results-artifacts-card.component';
import { ResultsTechnicalDrawerComponent } from './components/results-technical-drawer.component';
import { ResultsStatesComponent } from './components/results-states.component';

@Component({
  selector: 'app-validation-results',
  standalone: true,
  imports: [
    CommonModule,
    ResultsVerdictBannerComponent,
    ResultsSourceTargetProofComponent,
    ResultsAssuranceScopeComponent,
    ResultsUnresolvedFindingsComponent,
    ResultsRemediationHistoryComponent,
    ResultsRunHistoryComponent,
    ResultsEvidenceIntegrityComponent,
    ResultsAuditTimelineComponent,
    ResultsArtifactsCardComponent,
    ResultsTechnicalDrawerComponent,
    ResultsStatesComponent
  ],
  template: `
    <div class="flex flex-col gap-6 sm:gap-7 animate-in fade-in duration-150">
      
      <!-- 1. Top Formal Verdict Banner (Validation #11 Authority) -->
      <app-results-verdict-banner />

      @if (store.viewStatus() === 'READY') {
        
        <!-- 2. Evaluated Topology & Comparison Proof (Source <-> Mode <-> Target) -->
        <app-results-source-target-proof />

        <!-- 3. Assurance & Proof Framework Results (4 Canonical Tiers) -->
        <app-results-assurance-scope />

        <!-- 4. Unresolved Findings Summary & Discrepancies Navigation Link -->
        <app-results-unresolved-findings />

        <!-- 5. Repair & Revalidation Immutable Lineage -->
        <app-results-remediation-history />

        <!-- 6. Mission Execution History (Multi-run Ledger with Local Horizontal Scroll) -->
        <app-results-run-history />

        <!-- 7. Evidence & Integrity Record (Evidence #12 Authority - Digest !== Signature) -->
        <app-results-evidence-integrity />

        <!-- 8. Chronological Audit Trail -->
        <app-results-audit-timeline />

        <!-- 9. Artifacts & Governed Export Packages -->
        <app-results-artifacts-card />

      } @else {
        
        <!-- Dedicated Surface Fallback States (NOT_EVALUATED, WITHHELD, UNAVAILABLE, LOADING, ERROR) -->
        <app-results-states
          [status]="store.viewStatus()"
          [errorMessage]="store.errorMessage()" />

      }

      <!-- Slide-over Technical Provenance Drawer -->
      <app-results-technical-drawer />

    </div>
  `
})
export class ValidationResultsComponent implements OnInit {
  readonly store = inject(ValidationResultsService);
  private readonly workstationService = inject(ValidationWorkstationService, { optional: true });

  ngOnInit(): void {
    // If workstation service is running in a visual test fixture and results store is in default state, synchronize
    if (this.workstationService && !this.workstationService.isProductionDefault()) {
      const currentExecutionState = this.workstationService.executionState();
      if ((currentExecutionState === 'COMPLETED' || currentExecutionState === 'RUNNING') && this.store.viewStatus() === 'NOT_EVALUATED') {
        this.store.setFixture('PASSED_SYNC');
      }
    }
  }
}
