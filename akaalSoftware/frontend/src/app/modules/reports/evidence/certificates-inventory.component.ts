import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ReportsService } from '../services/reports.service';
import { CertificateArtifactDTO } from '../models/evidence.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-certificates-inventory',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full animate-in fade-in duration-150">
      
      <!-- List View or Detail View Switch -->
      @if (service.selectedCertificateArtifact(); as cert) {
        
        <!-- Certificate Artifact Detail View -->
        <div class="flex flex-col gap-6">
          <!-- Back Bar & Header -->
          <div class="flex items-start justify-between gap-4 pb-4 border-b border-slate-200 flex-wrap">
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center gap-2">
                <button
                  (click)="service.clearSelectedCertificateArtifact()"
                  class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 cursor-pointer transition-colors">
                  <app-lucide-icon name="arrow-left" [size]="12"></app-lucide-icon>
                  <span>Back to Certificates</span>
                </button>
                <span class="text-slate-300">•</span>
                <span class="text-xs text-slate-500 font-medium">CERTIFICATE ARTIFACT</span>
              </div>
              <h2 class="text-xl font-bold text-slate-900 tracking-tight font-heading">{{ cert.title }}</h2>
              <div class="flex items-center gap-3 text-xs text-slate-500">
                <span>Subject: <strong class="text-slate-700">{{ cert.subject_name }}</strong></span>
                <span>•</span>
                <span>Authority: <strong class="text-slate-700">{{ cert.producer_authority }}</strong></span>
                <span>•</span>
                <span>Issued: {{ cert.issued_at | date:'yyyy-MM-dd HH:mm' }}</span>
              </div>
            </div>

            <div class="flex items-center gap-2 pt-1">
              @if (cert.certification_id) {
                <a
                  [routerLink]="['/reports/certification']"
                  [queryParams]="{ certId: cert.certification_id }"
                  class="h-9 px-3.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
                  View Certification Reasoning
                </a>
              }
              <button
                (click)="service.verifyArtifactTarget(cert.id)"
                class="h-9 px-3.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
                Verify Integrity
              </button>
            </div>
          </div>

          <!-- Metadata & Decision Card -->
          <div class="p-5 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-4">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Certification Decision</span>
              <div>
                @if (cert.decision === 'CERTIFIED') {
                  <span class="text-emerald-700 font-semibold text-xs inline-flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    <span>Certified</span>
                  </span>
                } @else {
                  <span class="text-rose-700 font-semibold text-xs inline-flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                    <span>{{ cert.decision }}</span>
                  </span>
                }
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Domain</span>
                <span class="font-semibold text-slate-800">{{ cert.domain }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Producer Authority</span>
                <span class="font-semibold text-slate-800">{{ cert.producer_authority }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Issued Timestamp</span>
                <span class="font-semibold text-slate-800">{{ cert.issued_at | date:'yyyy-MM-dd HH:mm:ss' }}</span>
              </div>
            </div>

            @if (cert.fingerprint) {
              <div class="flex flex-col gap-1 pt-2 border-t border-slate-100">
                <span class="text-xs text-slate-400 font-medium">SHA-256 Digest Fingerprint</span>
                <span class="font-mono text-xs text-slate-700 select-all bg-slate-50 p-2 rounded-lg border border-slate-200">
                  {{ cert.fingerprint }}
                </span>
              </div>
            }
          </div>

          <!-- Evidence Basis Reference List -->
          <div class="flex flex-col gap-3">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
              Evidence Basis References ({{ cert.evidence_refs.length }})
            </h3>
            
            <div class="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-2xs">
              <div class="divide-y divide-slate-100">
                @for (ref of cert.evidence_refs; track ref) {
                  <div 
                    (click)="service.openEvidenceDetail(ref)"
                    class="p-3.5 flex items-center justify-between hover:bg-slate-50 transition-colors cursor-pointer text-xs">
                    <div class="flex items-center gap-3">
                      <span class="font-mono text-slate-500 font-medium">{{ ref }}</span>
                      <span class="text-slate-700 font-medium">Referenced Canonical Evidence Proof</span>
                    </div>
                    <button
                      (click)="service.openEvidenceDetail(ref); $event.stopPropagation()"
                      class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 transition-all cursor-pointer">
                      <span>Inspect Evidence Proof</span>
                      <app-lucide-icon name="arrow-right" [size]="12"></app-lucide-icon>
                    </button>
                  </div>
                }
              </div>
            </div>
          </div>
        </div>

      } @else {

        <!-- Certificates List View -->
        <div class="flex flex-col gap-6">
          <!-- Section Title -->
          <div class="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">Certificates Register</h2>
              <p class="text-xs text-slate-500 mt-0.5">
                Canonical certificate records and formal compliance assertions.
              </p>
            </div>
            
            <div class="text-xs text-slate-500 font-medium self-end">
              Showing <span class="font-semibold text-slate-800">{{ service.certificateArtifacts().length }}</span> certificate records
            </div>
          </div>

          <!-- Certificates Table -->
          <div class="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-slate-200 bg-slate-50/75 text-slate-500 text-[11px] uppercase tracking-wider font-semibold">
                  <th class="py-3 px-4">Certificate Artifact</th>
                  <th class="py-3 px-4">Subject</th>
                  <th class="py-3 px-4">Domain</th>
                  <th class="py-3 px-4">Issued</th>
                  <th class="py-3 px-4">Decision</th>
                  <th class="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                @for (c of service.certificateArtifacts(); track c.id) {
                  <tr 
                    (click)="service.selectCertificateArtifact(c.id)"
                    class="hover:bg-slate-50/80 transition-colors cursor-pointer group">
                    
                    <td class="py-3.5 px-4 font-medium text-slate-900 group-hover:text-blue-600 transition-colors">
                      <div class="flex flex-col gap-0.5">
                        <span class="font-semibold">{{ c.title }}</span>
                        <span class="text-[11px] text-slate-400 font-mono">{{ c.id }}</span>
                      </div>
                    </td>

                    <td class="py-3.5 px-4 text-slate-600 font-medium">
                      {{ c.subject_name }}
                    </td>

                    <td class="py-3.5 px-4 text-slate-600">
                      {{ c.domain }}
                    </td>

                    <td class="py-3.5 px-4 text-slate-500 whitespace-nowrap">
                      {{ c.issued_at | date:'yyyy-MM-dd HH:mm' }}
                    </td>

                    <td class="py-3.5 px-4">
                      @if (c.decision === 'CERTIFIED') {
                        <span class="text-emerald-700 font-medium inline-flex items-center gap-1.5">
                          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                          <span>Certified</span>
                        </span>
                      } @else {
                        <span class="text-rose-700 font-medium inline-flex items-center gap-1.5">
                          <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                          <span>{{ c.decision }}</span>
                        </span>
                      }
                    </td>

                    <td class="py-3.5 px-4 text-right whitespace-nowrap" (click)="$event.stopPropagation()">
                      <button
                        (click)="service.selectCertificateArtifact(c.id)"
                        class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
                        Inspect
                      </button>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="6" class="py-12 px-4 text-center text-xs text-slate-500">
                      No certificate records available.
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

      }

    </div>
  `
})
export class CertificatesInventoryComponent {
  public service = inject(ReportsService);
}
