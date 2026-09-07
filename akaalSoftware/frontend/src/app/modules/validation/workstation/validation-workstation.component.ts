import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';

import { ValidationWorkstationService } from './validation-workstation.service';
import { WorkstationHeaderComponent } from './components/workstation-header.component';
import { WorkstationNavComponent } from './components/workstation-nav.component';
import { WorkstationStatusPanelComponent } from './components/workstation-status-panel.component';
import { WorkstationSourceTargetDonutComponent } from './components/workstation-source-target-donut.component';
import { WorkstationProofPanelComponent } from './components/workstation-proof-panel.component';
import { WorkstationAttentionPanelComponent } from './components/workstation-attention-panel.component';
import { WorkstationCoveragePanelComponent } from './components/workstation-coverage-panel.component';
import { WorkstationP7bRemediationComponent } from './components/workstation-p7b-remediation.component';
import { WorkstationTechnicalDrawerComponent } from './components/workstation-technical-drawer.component';
import { ValidationDiscrepanciesComponent } from './discrepancies/validation-discrepancies.component';
import { ValidationRepairComponent } from './repair/validation-repair.component';
import { ValidationResultsComponent } from './results/validation-results.component';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-validation-workstation',
  standalone: true,
  imports: [
    CommonModule,
    WorkstationHeaderComponent,
    WorkstationNavComponent,
    WorkstationStatusPanelComponent,
    WorkstationSourceTargetDonutComponent,
    WorkstationProofPanelComponent,
    WorkstationAttentionPanelComponent,
    WorkstationCoveragePanelComponent,
    WorkstationP7bRemediationComponent,
    WorkstationTechnicalDrawerComponent,
    ValidationDiscrepanciesComponent,
    ValidationRepairComponent,
    ValidationResultsComponent
  ],
  template: `
    <div class="min-h-screen bg-slate-50/60 font-sans select-none flex flex-col text-slate-800">
      
      <!-- Top Persistent Identity & Actions Header -->
      <app-workstation-header />

      <!-- Horizontal 4-Workspace Navigation Bar (Underline active, NO pill buttons) -->
      <app-workstation-nav />

      <!-- Main Workspace Viewport -->
      <main class="max-w-[1680px] w-full mx-auto p-6 lg:p-8 flex flex-col gap-6 flex-1">
        
        @switch (store.activeTab()) {
          
          <!-- Workspace 1: OVERVIEW (Fully authorized & comprehensive) -->
          @case ('overview') {
            <div class="flex flex-col gap-6 animate-in fade-in duration-150">
              
              <!-- 1. Wide Status & Controls Banner -->
              <app-workstation-status-panel />

              <!-- 2. Source <-> Target Donut Hero Topology & Progress -->
              <app-workstation-source-target-donut />

              <!-- 3. Validation Proof Framework (4 Tiers with Hostile XOR Guard) -->
              <app-workstation-proof-panel />

              <!-- 4. Operational Attention & Divergence Findings -->
              <app-workstation-attention-panel />

              <!-- 5. Scope Coverage Matrix & Semantic Policy -->
              <app-workstation-coverage-panel />

              <!-- 6. Baseline Integrity & Governed Remediation Context -->
              <app-workstation-p7b-remediation />

            </div>
          }

          <!-- Workspace 2: DISCREPANCIES & RECONCILIATION -->
          @case ('discrepancies') {
            <app-validation-discrepancies />
          }

          <!-- Workspace 3: REPAIR & REVALIDATION -->
          @case ('repair') {
            <app-validation-repair />
          }

          <!-- Workspace 4: RESULTS & EVIDENCE (Full Workspace) -->
          @case ('evidence') {
            <app-validation-results />
          }

        }

      </main>

      <!-- Technical Architecture & Engine Inspection Slide-over Drawer -->
      <app-workstation-technical-drawer />

    </div>
  `
})
export class ValidationWorkstationComponent implements OnInit, OnDestroy {
  readonly store = inject(ValidationWorkstationService);
  private route = inject(ActivatedRoute);
  private sub?: Subscription;

  ngOnInit(): void {
    this.sub = this.route.paramMap.subscribe(params => {
      const id = params.get('validationId');
      if (id) {
        this.store.loadMission(id);
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
