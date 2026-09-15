import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { ReportsService, EvidenceTabMode } from './services/reports.service';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';
import { EvidenceExplorerComponent } from './evidence/evidence-explorer.component';
import { DossiersInventoryComponent } from './evidence/dossiers-inventory.component';
import { CertificatesInventoryComponent } from './evidence/certificates-inventory.component';
import { PackagesInventoryComponent } from './evidence/packages-inventory.component';
import { EvidenceDetailFrameComponent } from './evidence/evidence-detail-frame.component';
import { EvidenceVerificationWorkspaceComponent } from './evidence/evidence-verification-workspace.component';

@Component({
  selector: 'app-reports-evidence',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LucideIconComponent,
    EvidenceExplorerComponent,
    DossiersInventoryComponent,
    CertificatesInventoryComponent,
    PackagesInventoryComponent,
    EvidenceDetailFrameComponent,
    EvidenceVerificationWorkspaceComponent
  ],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Top Header & Breadcrumb (when not in full evidence detail) -->
      @if (!service.selectedEvidenceEnvelope()) {
        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <a routerLink="/reports" class="text-xs font-semibold text-slate-500 hover:text-slate-800 uppercase tracking-wider font-heading transition-colors">REPORTS</a>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">SPECIALIST WORKSPACE</span>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Evidence Portal</h1>
            <p class="text-sm font-medium text-slate-600">
              Canonical proof material, validation Merkle roots, partition manifests, and execution journals.
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
            (click)="onSelectTab('EXPLORER')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="service.activeEvidenceTab() === 'EXPLORER' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Evidence Explorer
          </button>

          <button
            (click)="onSelectTab('DOSSIERS')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="service.activeEvidenceTab() === 'DOSSIERS' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Dossiers
          </button>

          <button
            (click)="onSelectTab('CERTIFICATES')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="service.activeEvidenceTab() === 'CERTIFICATES' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Certificates
          </button>

          <button
            (click)="onSelectTab('PACKAGES')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="service.activeEvidenceTab() === 'PACKAGES' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Evidence Packages
          </button>

          <button
            (click)="onSelectTab('VERIFICATION')"
            class="pb-3 text-xs tracking-wide transition-colors cursor-pointer shrink-0"
            [ngClass]="service.activeEvidenceTab() === 'VERIFICATION' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
            Integrity Verification
          </button>
        </div>
      }

      <!-- VIEW SWITCHER -->
      
      <!-- 1. Selected Evidence Detail Frame -->
      @if (service.selectedEvidenceEnvelope(); as envelope) {
        <app-evidence-detail-frame [envelope]="envelope"></app-evidence-detail-frame>
      }

      <!-- 2. Evidence Explorer Tab -->
      @else if (service.activeEvidenceTab() === 'EXPLORER') {
        <app-evidence-explorer></app-evidence-explorer>
      }

      <!-- 3. Dossiers Tab -->
      @else if (service.activeEvidenceTab() === 'DOSSIERS') {
        <app-dossiers-inventory></app-dossiers-inventory>
      }

      <!-- 4. Certificates Tab -->
      @else if (service.activeEvidenceTab() === 'CERTIFICATES') {
        <app-certificates-inventory></app-certificates-inventory>
      }

      <!-- 5. Packages Tab -->
      @else if (service.activeEvidenceTab() === 'PACKAGES') {
        <app-packages-inventory></app-packages-inventory>
      }

      <!-- 6. Integrity Verification Tab -->
      @else if (service.activeEvidenceTab() === 'VERIFICATION') {
        <app-evidence-verification-workspace></app-evidence-verification-workspace>
      }

    </div>
  `
})
export class ReportsEvidenceComponent implements OnInit {
  public service = inject(ReportsService);
  private route = inject(ActivatedRoute);

  public ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      if (params['evidenceId']) {
        this.service.openEvidenceDetail(params['evidenceId']);
      } else if (params['dossierId']) {
        this.service.selectDossier(params['dossierId']);
        this.service.setEvidenceTab('DOSSIERS');
      } else if (params['packageId']) {
        this.service.selectEvidencePackage(params['packageId']);
        this.service.setEvidenceTab('PACKAGES');
      } else if (params['certId']) {
        this.service.selectCertificateArtifact(params['certId']);
        this.service.setEvidenceTab('CERTIFICATES');
      } else if (params['tab']) {
        const tab = params['tab'].toUpperCase();
        if (tab === 'EXPLORER' || tab === 'DOSSIERS' || tab === 'CERTIFICATES' || tab === 'PACKAGES' || tab === 'VERIFICATION') {
          this.service.setEvidenceTab(tab as EvidenceTabMode);
        }
      }
    });
  }

  public onSelectTab(tab: EvidenceTabMode): void {
    this.service.setEvidenceTab(tab);
  }
}
