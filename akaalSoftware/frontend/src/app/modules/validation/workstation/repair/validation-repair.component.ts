import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationRepairService } from './validation-repair.service';
import { ValidationWorkstationService } from '../validation-workstation.service';

import { RepairSummaryBandComponent } from './components/repair-summary-band.component';
import { RepairSelectedScopeComponent } from './components/repair-selected-scope.component';
import { RepairProposalCardComponent } from './components/repair-proposal-card.component';
import { RepairPreviewCardComponent } from './components/repair-preview-card.component';
import { RepairGovernanceCardComponent } from './components/repair-governance-card.component';
import { RepairExecutionCardComponent } from './components/repair-execution-card.component';
import { RepairRevalidationCardComponent } from './components/repair-revalidation-card.component';
import { RepairStatesComponent } from './components/repair-states.component';
import { RepairConfirmDialogComponent } from './components/repair-confirm-dialog.component';
import { RepairTechnicalDrawerComponent } from './components/repair-technical-drawer.component';

@Component({
  selector: 'app-validation-repair',
  standalone: true,
  imports: [
    CommonModule,
    RepairSummaryBandComponent,
    RepairSelectedScopeComponent,
    RepairProposalCardComponent,
    RepairPreviewCardComponent,
    RepairGovernanceCardComponent,
    RepairExecutionCardComponent,
    RepairRevalidationCardComponent,
    RepairStatesComponent,
    RepairConfirmDialogComponent,
    RepairTechnicalDrawerComponent
  ],
  template: `
    <div class="flex flex-col gap-7 sm:gap-8 animate-in fade-in duration-150">
      
      <!-- Top Summary Band -->
      <app-repair-summary-band></app-repair-summary-band>

      @if (store.viewStatus() === 'READY') {
        
        <!-- 1. Selected Findings Scope -->
        <app-repair-selected-scope></app-repair-selected-scope>

        <!-- 2. Repair Proposal Strategy -->
        <app-repair-proposal-card></app-repair-proposal-card>

        <!-- 3. Impact & Target Preview (3-way comparison) -->
        <app-repair-preview-card></app-repair-preview-card>

        <!-- 4. Governance & Authorization -->
        <app-repair-governance-card></app-repair-governance-card>

        <!-- 5. Controlled Execution & Recovery -->
        <app-repair-execution-card></app-repair-execution-card>

        <!-- 6. Validation #11 Mandatory Revalidation -->
        <app-repair-revalidation-card></app-repair-revalidation-card>

      } @else {
        <!-- Dedicated Full Surface States (UNAVAILABLE, NO_REMEDIATION_REQUIRED, AUDIT_ONLY, LOADING, ERROR) -->
        <app-repair-states
          [status]="store.viewStatus()"
          [errorMessage]="store.errorMessage()"></app-repair-states>
      }

      <!-- Consequential Execution Confirmation Modal -->
      <app-repair-confirm-dialog></app-repair-confirm-dialog>

      <!-- Technical Architecture & Provenance Slide-over Drawer -->
      <app-repair-technical-drawer></app-repair-technical-drawer>

    </div>
  `
})
export class ValidationRepairComponent implements OnInit {
  readonly store = inject(ValidationRepairService);
  private readonly workstationService = inject(ValidationWorkstationService);

  ngOnInit(): void {
    // If workstation service is in a visual test fixture and repair store is in default state, synchronize
    const currentExecutionState = this.workstationService.executionState();
    if (!this.workstationService.isProductionDefault() && (currentExecutionState === 'RUNNING' || currentExecutionState === 'COMPLETED')) {
      if (this.store.viewStatus() === 'UNAVAILABLE') {
        this.store.setFixture('SINGLE_UPDATE_PROPOSAL');
      }
    }
  }
}
