import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ReportsService } from '../services/reports.service';
import { 
  CertificationSummaryDTO, 
  CertificationExceptionDTO,
  VerificationResultDTO,
  formatCertificationDecision
} from '../models/certification.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-certification-overview',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full select-none animate-in fade-in duration-150">
      
      <!-- 1. Certification Attention / Conditions (Bounded 5–8 items max) -->
      @if (rs.certAttentionItems().length > 0) {
        <div class="flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="alert-triangle" [size]="15" class="text-amber-600"></app-lucide-icon>
              <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
                CERTIFICATION ATTENTION
              </span>
              <span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-amber-100 text-amber-800">
                {{ rs.certAttentionItems().length }}
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            @for (item of rs.certAttentionItems().slice(0, 6); track item.id) {
              <div class="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col justify-between gap-3 hover:border-slate-300 transition-colors">
                <div class="flex flex-col gap-1.5">
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-xs font-bold text-slate-900 leading-snug">
                      {{ item.condition }}
                    </span>
                    <span class="text-[10px] font-mono text-slate-400">
                      {{ item.updated_at | date:'yyyy-MM-dd' }}
                    </span>
                  </div>

                  <p class="text-xs text-slate-600 leading-relaxed">
                    {{ item.detail }}
                  </p>
                </div>

                <div class="pt-2 border-t border-slate-100 flex items-center justify-end text-xs">
                  <button
                    (click)="onOpenAttentionTarget(item)"
                    class="h-7 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs">
                    <span>Inspect Condition</span>
                    <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                  </button>
                </div>
              </div>
            }
          </div>
        </div>
      }

      <!-- 3. Recent Certifications Preview Table (Bounded to 5–8 rows max) -->
      <div class="flex flex-col gap-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
              RECENT CERTIFICATIONS
            </span>
            <span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">
              {{ rs.recentCertifications().length }}
            </span>
          </div>

          <button
            (click)="onNavigateTab('MIGRATION')"
            class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 transition-all cursor-pointer shrink-0">
            <span>View All Records</span>
            <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
          </button>
        </div>

        @if (rs.recentCertifications().length === 0) {
          <div class="p-8 rounded-xl bg-white border border-slate-200 text-center flex flex-col items-center justify-center gap-2 shadow-2xs">
            <app-lucide-icon name="award" [size]="28" class="text-slate-400"></app-lucide-icon>
            <span class="text-xs font-bold text-slate-800">No formal certifications issued yet</span>
            <p class="text-xs text-slate-500 max-w-sm">Formal migration and validation certification records will appear here as evaluation criteria complete.</p>
          </div>
        } @else {
          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Subject &amp; Certification</th>
                  <th class="py-3 px-4">Domain</th>
                  <th class="py-3 px-4 hidden md:table-cell">Issued</th>
                  <th class="py-3 px-4">Decision</th>
                  <th class="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (cert of rs.recentCertifications().slice(0, 6); track cert.id) {
                  <tr class="hover:bg-slate-50/80 transition-colors group cursor-pointer" (click)="onOpenCertification(cert.id)">
                    
                    <!-- Subject & Title -->
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

                    <!-- Domain -->
                    <td class="py-3.5 px-4 text-slate-700 font-medium">
                      <span class="text-[11px] uppercase tracking-wide font-mono text-slate-500">
                        {{ cert.domain }}
                      </span>
                    </td>

                    <!-- Issued Timestamp -->
                    <td class="py-3.5 px-4 text-slate-500 hidden md:table-cell font-mono text-[11px]">
                      {{ cert.issued_at | date:'yyyy-MM-dd HH:mm' }}
                    </td>

                    <!-- Canonical Decision Badge -->
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

                    <!-- Action -->
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
          </div>
        }
      </div>

      <!-- 4. Recent Verification Activity (Bounded to 5–8 items max) -->
      <div class="flex flex-col gap-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
              RECENT VERIFICATION ACTIVITY
            </span>
            @if (rs.recentVerifications().length > 0) {
              <span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">
                {{ rs.recentVerifications().length }}
              </span>
            }
          </div>

          <button
            (click)="onNavigateTab('VERIFICATION')"
            class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 transition-all cursor-pointer shrink-0">
            <span>Open Verification Console</span>
            <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
          </button>
        </div>

        @if (rs.recentVerifications().length === 0) {
          <div class="p-6 rounded-xl bg-white border border-slate-200 text-center text-xs text-slate-500 shadow-2xs">
            No recent cryptographic fingerprint verifications performed.
          </div>
        } @else {
          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Artifact / Certification Target</th>
                  <th class="py-3 px-4 hidden md:table-cell">Verified At</th>
                  <th class="py-3 px-4">Result</th>
                  <th class="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (ver of rs.recentVerifications().slice(0, 5); track ver.target_identifier) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      <div class="flex flex-col gap-0.5">
                        <span>{{ ver.target_identifier }}</span>
                        <span class="text-[11px] text-slate-400 font-normal">{{ ver.detail_notes }}</span>
                      </div>
                    </td>

                    <td class="py-3.5 px-4 text-slate-500 hidden md:table-cell font-mono text-[11px]">
                      {{ ver.verified_at | date:'yyyy-MM-dd HH:mm' }}
                    </td>

                    <td class="py-3.5 px-4">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="{
                          'bg-emerald-50 text-emerald-700 border border-emerald-200': ver.result_status === 'VERIFIED',
                          'bg-rose-50 text-rose-700 border border-rose-200': ver.result_status === 'MISMATCH',
                          'bg-slate-100 text-slate-700': ver.result_status === 'UNAVAILABLE' || ver.result_status === 'ERROR'
                        }">
                        {{ ver.result_status === 'VERIFIED' ? 'Fingerprint Verified' : (ver.result_status === 'MISMATCH' ? 'Fingerprint Mismatch' : 'Verification Unavailable') }}
                      </span>
                    </td>

                    <td class="py-3.5 px-4 text-right">
                      <button
                        (click)="onInspectVerification(ver.target_identifier)"
                        class="h-7 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center gap-1 cursor-pointer transition-colors shadow-2xs">
                        <span>Details</span>
                        <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                      </button>
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>

    </div>
  `
})
export class CertificationOverviewComponent {
  public rs = inject(ReportsService);
  private router = inject(Router);

  public formatDecision = formatCertificationDecision;

  public onNavigateTab(tab: 'MIGRATION' | 'VALIDATION' | 'VERIFICATION'): void {
    this.rs.selectCertificationTab(tab);
  }

  public onOpenCertification(certId: string): void {
    this.rs.openCertificationById(certId);
  }

  public onOpenAttentionTarget(item: CertificationExceptionDTO): void {
    this.rs.openCertificationById(item.id);
  }

  public onInspectVerification(targetId: string): void {
    this.rs.verifyArtifactTarget(targetId);
  }
}
