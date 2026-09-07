import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationDiscrepanciesService } from './validation-discrepancies.service';
import { ValidationWorkstationService } from '../validation-workstation.service';
import { DiscrepanciesSummaryBandComponent } from './components/discrepancies-summary-band.component';
import { DiscrepanciesFilterBarComponent } from './components/discrepancies-filter-bar.component';
import { DiscrepanciesNavigatorComponent } from './components/discrepancies-navigator.component';
import { DiscrepanciesTableComponent } from './components/discrepancies-table.component';
import { DiscrepanciesInspectorComponent } from './components/discrepancies-inspector.component';
import { DiscrepanciesStatesComponent } from './components/discrepancies-states.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-validation-discrepancies',
  standalone: true,
  imports: [
    CommonModule,
    DiscrepanciesSummaryBandComponent,
    DiscrepanciesFilterBarComponent,
    DiscrepanciesNavigatorComponent,
    DiscrepanciesTableComponent,
    DiscrepanciesInspectorComponent,
    DiscrepanciesStatesComponent
  ],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150">
      
      <!-- Top Summary Band -->
      <app-discrepancies-summary-band></app-discrepancies-summary-band>

      @if (store.viewStatus() === 'READY') {
        
        <!-- Filter & Search Bar -->
        <app-discrepancies-filter-bar></app-discrepancies-filter-bar>

        <!-- Master-Detail Investigation Workspace -->
        <div class="flex flex-col lg:flex-row items-start gap-6">
          
          <!-- Left: Scope / Object Navigator -->
          <app-discrepancies-navigator></app-discrepancies-navigator>

          <!-- Right: Discrepancy Findings Table -->
          <app-discrepancies-table></app-discrepancies-table>

        </div>

        <!-- Selected Discrepancy Inspector (Source <-> Target Comparison) -->
        @if (store.selectedDiscrepancy(); as selectedItem) {
          <app-discrepancies-inspector [item]="selectedItem"></app-discrepancies-inspector>
        }

      } @else {
        <!-- Dedicated State View (EMPTY, NOT_EVALUATED, UNAVAILABLE, LOADING, ERROR) -->
        <app-discrepancies-states
          [status]="store.viewStatus()"
          [errorMessage]="store.errorMessage()"></app-discrepancies-states>
      }

    </div>
  `
})
export class ValidationDiscrepanciesComponent implements OnInit {
  readonly store = inject(ValidationDiscrepanciesService);
  private readonly workstationService = inject(ValidationWorkstationService);

  ngOnInit(): void {
    // If workstation service is in a visual test fixture and discrepancies store is in default state, synchronize
    const currentExecutionState = this.workstationService.executionState();
    if (!this.workstationService.isProductionDefault() && (currentExecutionState === 'RUNNING' || currentExecutionState === 'COMPLETED')) {
      if (this.store.viewStatus() === 'UNAVAILABLE') {
        this.store.setFixture('NORMAL_19_FINDINGS');
      }
    }
  }
}
