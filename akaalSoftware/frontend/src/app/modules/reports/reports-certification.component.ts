import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { ReportsService, CertificationViewMode } from './services/reports.service';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';
import { CertificationOverviewComponent } from './certification/certification-overview.component';
import { MigrationCertificationInventoryComponent } from './certification/migration-certification-inventory.component';
import { ValidationCertificationInventoryComponent } from './certification/validation-certification-inventory.component';
import { CertificationDetailFrameComponent } from './certification/detail/certification-detail-frame.component';
import { VerificationWorkspaceComponent } from './certification/verification/verification-workspace.component';

@Component({
  selector: 'app-reports-certification',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LucideIconComponent,
    CertificationOverviewComponent,
    MigrationCertificationInventoryComponent,
    ValidationCertificationInventoryComponent,
    CertificationDetailFrameComponent,
    VerificationWorkspaceComponent
  ],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Top Header & Breadcrumb (when not in detail view) -->
      @if (!service.selectedCertification()) {
        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <a routerLink="/reports" class="text-xs font-semibold text-slate-500 hover:text-slate-800 uppercase tracking-wider font-heading transition-colors">REPORTS</a>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">SPECIALIST WORKSPACE</span>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Trust &amp; Certification</h1>
            <p class="text-sm font-medium text-slate-600">
              Formal migration and validation certification registers, criteria assertions, and cryptographic digest verification.
            </p>
          </div>

          <div class="flex items-center gap-3 pt-1">
            <a
              routerLink="/reports"
              class="h-9 px-3.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-2xs">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back to Reports Home</span>
            </a>
          </div>
        </div>

        <!-- Local Navigation Tabs -->
        <div class="flex items-center gap-6 border-b border-slate-200 -mt-2 overflow-x-auto">
          <button
            (click)="onSelectTab('OVERVIEW')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="service.activeCertTab() === 'OVERVIEW' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Overview
          </button>

          <button
            (click)="onSelectTab('MIGRATION')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="service.activeCertTab() === 'MIGRATION' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Migration Certification
          </button>

          <button
            (click)="onSelectTab('VALIDATION')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="service.activeCertTab() === 'VALIDATION' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Validation Certification
          </button>

          <button
            (click)="onSelectTab('VERIFICATION')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="service.activeCertTab() === 'VERIFICATION' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Verification Console
          </button>
        </div>
      }

      <!-- MAIN CONTENT SWITCH -->
      
      <!-- 1. Selected Certification Detail View -->
      @if (service.selectedCertification()) {
        <app-certification-detail-frame [cert]="service.selectedCertification()!"></app-certification-detail-frame>
      }

      <!-- 2. Overview Tab -->
      @else if (service.activeCertTab() === 'OVERVIEW') {
        <app-certification-overview></app-certification-overview>
      }

      <!-- 3. Migration Certification Inventory -->
      @else if (service.activeCertTab() === 'MIGRATION') {
        <app-migration-certification-inventory></app-migration-certification-inventory>
      }

      <!-- 4. Validation Certification Inventory -->
      @else if (service.activeCertTab() === 'VALIDATION') {
        <app-validation-certification-inventory></app-validation-certification-inventory>
      }

      <!-- 5. Verification Workspace -->
      @else if (service.activeCertTab() === 'VERIFICATION') {
        <app-verification-workspace></app-verification-workspace>
      }

    </div>
  `
})
export class ReportsCertificationComponent implements OnInit {
  public service = inject(ReportsService);
  private route = inject(ActivatedRoute);

  public ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      if (params['certId']) {
        this.service.openCertificationById(params['certId']);
      } else if (params['tab']) {
        const tab = params['tab'].toUpperCase();
        if (tab === 'MIGRATION' || tab === 'VALIDATION' || tab === 'VERIFICATION' || tab === 'OVERVIEW') {
          this.service.selectCertificationTab(tab as CertificationViewMode);
        }
      }
    });
  }

  public onSelectTab(tab: CertificationViewMode): void {
    this.service.selectCertificationTab(tab);
  }
}
