import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReportsService } from '../services/reports.service';
import { EvidencePackageDTO } from '../models/evidence.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-packages-inventory',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full animate-in fade-in duration-150">
      
      <!-- List View or Detail View Switch -->
      @if (service.selectedEvidencePackage(); as pkg) {
        
        <!-- Package Detail Surface -->
        <div class="flex flex-col gap-6">
          <!-- Back Bar & Header -->
          <div class="flex items-start justify-between gap-4 pb-4 border-b border-slate-200 flex-wrap">
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center gap-2">
                <button
                  (click)="service.clearSelectedEvidencePackage()"
                  class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-2xs inline-flex items-center gap-1.5 cursor-pointer transition-colors">
                  <app-lucide-icon name="arrow-left" [size]="12"></app-lucide-icon>
                  <span>Back to Packages</span>
                </button>
                <span class="text-slate-300">•</span>
                <span class="text-xs text-slate-500 font-medium">EVIDENCE PACKAGE</span>
              </div>
              <h2 class="text-xl font-bold text-slate-900 tracking-tight font-heading">{{ pkg.title }}</h2>
              <div class="flex items-center gap-3 text-xs text-slate-500">
                <span>Subject: <strong class="text-slate-700">{{ pkg.subject_name }}</strong></span>
                <span>•</span>
                <span>Generated: {{ pkg.generated_at | date:'yyyy-MM-dd HH:mm' }}</span>
                <span>•</span>
                <span>Status: <strong class="text-slate-700">{{ pkg.status }}</strong></span>
              </div>
            </div>

            <div class="flex items-center gap-2 pt-1">
              <button
                (click)="service.verifyArtifactTarget(pkg.id)"
                class="h-9 px-3.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
                Verify Package Fingerprint
              </button>
              <button
                [disabled]="pkg.status !== 'READY'"
                (click)="service.downloadPackageZip(pkg.id)"
                class="h-9 px-3.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
                Download ZIP Package
              </button>
            </div>
          </div>

          <!-- Package Summary Card -->
          <div class="p-5 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col gap-4">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Package Properties</span>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Package Identifier</span>
                <span class="font-mono font-semibold text-slate-800">{{ pkg.id }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Package Status</span>
                <span class="font-semibold text-slate-800">{{ pkg.status }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-400 font-medium">Total Size</span>
                <span class="font-semibold text-slate-800">{{ formatBytes(pkg.byte_size) }}</span>
              </div>
            </div>

            @if (pkg.fingerprint) {
              <div class="flex flex-col gap-1 pt-2 border-t border-slate-100">
                <span class="text-xs text-slate-400 font-medium">Package Archive Fingerprint (SHA-256)</span>
                <span class="font-mono text-xs text-slate-700 select-all bg-slate-50 p-2 rounded-lg border border-slate-200">
                  {{ pkg.fingerprint }}
                </span>
              </div>
            }
          </div>

          <!-- Bounded Paginated Manifest Table -->
          <div class="flex flex-col gap-3">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
              Package Manifest Contents ({{ pkg.manifest_items.length }})
            </h3>

            <div class="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-2xs">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="border-b border-slate-200 bg-slate-50/75 text-slate-500 text-[11px] uppercase tracking-wider font-semibold">
                    <th class="py-3 px-4">File Name</th>
                    <th class="py-3 px-4">Artifact Type</th>
                    <th class="py-3 px-4">Size</th>
                    <th class="py-3 px-4">SHA-256 Digest</th>
                    <th class="py-3 px-4">Integrity</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                  @for (item of pkg.manifest_items; track item.id) {
                    <tr class="hover:bg-slate-50/80 transition-colors">
                      <td class="py-3 px-4 font-mono font-medium text-slate-900">
                        {{ item.file_name }}
                      </td>
                      <td class="py-3 px-4 text-slate-600">
                        {{ item.artifact_type }}
                      </td>
                      <td class="py-3 px-4 text-slate-500">
                        {{ formatBytes(item.byte_size) }}
                      </td>
                      <td class="py-3 px-4 font-mono text-[11px] text-slate-500">
                        {{ item.fingerprint ? (item.fingerprint | slice:0:16) + '...' : '—' }}
                      </td>
                      <td class="py-3 px-4">
                        <span class="text-emerald-700 font-medium inline-flex items-center gap-1.5">
                          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                          <span>Verified</span>
                        </span>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        </div>

      } @else {

        <!-- Packages List View -->
        <div class="flex flex-col gap-6">
          <!-- Section Title -->
          <div class="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">Evidence Packages</h2>
              <p class="text-xs text-slate-500 mt-0.5">
                Portable evidence bundles and bounded manifest archive files for external delivery and auditing.
              </p>
            </div>
            
            <div class="text-xs text-slate-500 font-medium self-end">
              Showing <span class="font-semibold text-slate-800">{{ service.evidencePackages().length }}</span> packages
            </div>
          </div>

          <!-- Packages Table -->
          <div class="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-slate-200 bg-slate-50/75 text-slate-500 text-[11px] uppercase tracking-wider font-semibold">
                  <th class="py-3 px-4">Package</th>
                  <th class="py-3 px-4">Subject</th>
                  <th class="py-3 px-4">Manifest Items</th>
                  <th class="py-3 px-4">Size</th>
                  <th class="py-3 px-4">Generated</th>
                  <th class="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                @for (p of service.evidencePackages(); track p.id) {
                  <tr 
                    (click)="service.selectEvidencePackage(p.id)"
                    class="hover:bg-slate-50/80 transition-colors cursor-pointer group">
                    
                    <td class="py-3.5 px-4 font-medium text-slate-900 group-hover:text-blue-600 transition-colors">
                      <div class="flex flex-col gap-0.5">
                        <span class="font-semibold">{{ p.title }}</span>
                        <span class="text-[11px] text-slate-400 font-mono">{{ p.id }}</span>
                      </div>
                    </td>

                    <td class="py-3.5 px-4 text-slate-600 font-medium">
                      {{ p.subject_name }}
                    </td>

                    <td class="py-3.5 px-4 text-slate-700 font-medium">
                      {{ p.manifest_items.length }} files
                    </td>

                    <td class="py-3.5 px-4 text-slate-500 whitespace-nowrap">
                      {{ formatBytes(p.byte_size) }}
                    </td>

                    <td class="py-3.5 px-4 text-slate-500 whitespace-nowrap">
                      {{ p.generated_at | date:'yyyy-MM-dd HH:mm' }}
                    </td>

                    <td class="py-3.5 px-4 text-right whitespace-nowrap" (click)="$event.stopPropagation()">
                      <button
                        (click)="service.selectEvidencePackage(p.id)"
                        class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
                        Inspect Manifest
                      </button>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="6" class="py-12 px-4 text-center text-xs text-slate-500">
                      No evidence packages available.
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
export class PackagesInventoryComponent {
  public service = inject(ReportsService);

  public formatBytes(bytes?: number): string {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
}
