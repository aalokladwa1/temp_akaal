import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReportsService } from '../services/reports.service';
import { DossierDTO } from '../models/evidence.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-dossiers-inventory',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full animate-in fade-in duration-150">
      
      <!-- List View or Detail View Switch -->
      @if (service.selectedDossier(); as dossier) {
        
        <!-- Dossier Detail Surface -->
        <div class="flex flex-col gap-6">
          <!-- Back Bar & Header -->
          <div class="flex items-start justify-between gap-4 pb-4 border-b border-slate-200 flex-wrap">
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center gap-2">
                <button
                  (click)="service.clearSelectedDossier()"
                  class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 cursor-pointer transition-colors">
                  <app-lucide-icon name="arrow-left" [size]="12"></app-lucide-icon>
                  <span>Back to Dossiers</span>
                </button>
                <span class="text-slate-300">•</span>
                <span class="text-xs text-slate-500 font-medium">EVIDENCE DOSSIER</span>
              </div>
              <h2 class="text-xl font-bold text-slate-900 tracking-tight font-heading">{{ dossier.title }}</h2>
              <div class="flex items-center gap-3 text-xs text-slate-500">
                <span>Subject: <strong class="text-slate-700">{{ dossier.subject_name }}</strong></span>
                <span>•</span>
                <span>Domain: <strong class="text-slate-700">{{ dossier.domain }}</strong></span>
                <span>•</span>
                <span>Created: {{ dossier.created_at | date:'yyyy-MM-dd HH:mm' }}</span>
              </div>
            </div>

            <div class="flex items-center gap-2 pt-1">
              <button
                (click)="service.downloadDossierBundle(dossier.id)"
                class="h-9 px-3.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
                Export Dossier Bundle
              </button>
            </div>
          </div>

          <!-- Dossier Purpose & Scope -->
          <div class="p-5 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-2">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Dossier Context &amp; Purpose</h3>
            <p class="text-xs text-slate-600 leading-relaxed">
              {{ dossier.description }}
            </p>
          </div>

          <!-- Included Evidence Items Table -->
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                Included Evidence Proofs ({{ dossier.evidence_items.length }})
              </h3>
            </div>

            <div class="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-2xs">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="border-b border-slate-200 bg-slate-50/75 text-slate-500 text-[11px] uppercase tracking-wider font-semibold">
                    <th class="py-3 px-4">Evidence Artifact</th>
                    <th class="py-3 px-4">Type</th>
                    <th class="py-3 px-4">Subject</th>
                    <th class="py-3 px-4">Created</th>
                    <th class="py-3 px-4">Integrity</th>
                    <th class="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                  @for (ev of dossier.evidence_items; track ev.id) {
                    <tr 
                      (click)="service.openEvidenceDetail(ev.id)"
                      class="hover:bg-slate-50/80 transition-colors cursor-pointer group">
                      
                      <td class="py-3.5 px-4 font-medium text-slate-900 group-hover:text-blue-600 transition-colors">
                        <div class="flex flex-col gap-0.5">
                          <span class="font-semibold">{{ ev.title }}</span>
                          <span class="text-[11px] text-slate-400 font-mono">{{ ev.id }}</span>
                        </div>
                      </td>

                      <td class="py-3.5 px-4 text-slate-600">
                        {{ ev.artifact_type }}
                      </td>

                      <td class="py-3.5 px-4 text-slate-600">
                        {{ ev.subject_name }}
                      </td>

                      <td class="py-3.5 px-4 text-slate-500 whitespace-nowrap">
                        {{ ev.created_at | date:'yyyy-MM-dd HH:mm' }}
                      </td>

                      <td class="py-3.5 px-4">
                        @if (ev.integrity_status === 'VERIFIED') {
                          <span class="text-emerald-700 font-medium inline-flex items-center gap-1.5">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                            <span>Verified</span>
                          </span>
                        } @else {
                          <span class="text-slate-500 font-medium">Unverified</span>
                        }
                      </td>

                      <td class="py-3.5 px-4 text-right whitespace-nowrap" (click)="$event.stopPropagation()">
                        <button
                          (click)="service.openEvidenceDetail(ev.id)"
                          class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
                          Inspect
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        </div>

      } @else {

        <!-- Dossiers List View -->
        <div class="flex flex-col gap-6">
          <!-- Section Title -->
          <div class="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">Evidence Dossiers</h2>
              <p class="text-xs text-slate-500 mt-0.5">
                Organized collections of related evidence grouped around meaningful migration and compliance subjects.
              </p>
            </div>
            
            <div class="text-xs text-slate-500 font-medium self-end">
              Showing <span class="font-semibold text-slate-800">{{ service.dossiers().length }}</span> dossiers
            </div>
          </div>

          <!-- Dossiers Table -->
          <div class="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-slate-200 bg-slate-50/75 text-slate-500 text-[11px] uppercase tracking-wider font-semibold">
                  <th class="py-3 px-4">Dossier</th>
                  <th class="py-3 px-4">Subject</th>
                  <th class="py-3 px-4">Domain</th>
                  <th class="py-3 px-4">Proofs Count</th>
                  <th class="py-3 px-4">Created</th>
                  <th class="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                @for (d of service.dossiers(); track d.id) {
                  <tr 
                    (click)="service.selectDossier(d.id)"
                    class="hover:bg-slate-50/80 transition-colors cursor-pointer group">
                    
                    <td class="py-3.5 px-4 font-medium text-slate-900 group-hover:text-blue-600 transition-colors">
                      <div class="flex flex-col gap-0.5">
                        <span class="font-semibold">{{ d.title }}</span>
                        <span class="text-[11px] text-slate-400 line-clamp-1 max-w-md">{{ d.description }}</span>
                      </div>
                    </td>

                    <td class="py-3.5 px-4 text-slate-600 font-medium">
                      {{ d.subject_name }}
                    </td>

                    <td class="py-3.5 px-4 text-slate-600">
                      {{ d.domain }}
                    </td>

                    <td class="py-3.5 px-4 text-slate-700 font-medium">
                      {{ d.evidence_count }} proofs
                    </td>

                    <td class="py-3.5 px-4 text-slate-500 whitespace-nowrap">
                      {{ d.created_at | date:'yyyy-MM-dd HH:mm' }}
                    </td>

                    <td class="py-3.5 px-4 text-right whitespace-nowrap" (click)="$event.stopPropagation()">
                      <button
                        (click)="service.selectDossier(d.id)"
                        class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
                        Inspect Dossier
                      </button>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="6" class="py-12 px-4 text-center text-xs text-slate-500">
                      No evidence dossiers available.
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
export class DossiersInventoryComponent {
  public service = inject(ReportsService);
}
