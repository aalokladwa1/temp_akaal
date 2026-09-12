import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReportsService } from '../services/reports.service';
import { ExportFormat } from '../models/reports.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-reports-export-modal',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (service.isExportModalOpen()) {
      <div 
        (click)="onBackdropClick($event)"
        class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4 animate-in fade-in duration-150 select-none">
        
        <div 
          (click)="$event.stopPropagation()"
          class="w-full max-w-lg bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col animate-in zoom-in-95 duration-150">
          
          <!-- Modal Header -->
          <div class="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                <app-lucide-icon name="download" [size]="16"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900 font-heading">Export Report Archive</h3>
                <span class="text-xs text-slate-500 font-mono">{{ targetReport?.id }}</span>
              </div>
            </div>

            <button
              (click)="onClose()"
              class="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition-colors cursor-pointer">
              <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
            </button>
          </div>

          <!-- Modal Body -->
          <div class="p-6 flex flex-col gap-5">
            
            <!-- Target Report Summary -->
            <div class="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex flex-col gap-1">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">Report Title</span>
              <span class="text-xs font-bold text-slate-900">{{ targetReport?.title }}</span>
              <div class="flex items-center gap-2 pt-1 text-[11px] text-slate-500">
                <span>{{ targetReport?.subject_name }}</span>
                <span>•</span>
                <span class="font-medium text-blue-600">{{ targetReport?.category_label }}</span>
              </div>
            </div>

            <!-- Exporting State -->
            @if (service.isExporting()) {
              <div class="py-8 flex flex-col items-center justify-center gap-3 text-center">
                <div class="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                <div class="flex flex-col gap-0.5">
                  <span class="text-xs font-bold text-slate-800 font-heading">Packaging Report Archive</span>
                  <span class="text-[11px] text-slate-500">Compiling cryptographic signatures and artifact payload...</span>
                </div>
              </div>
            }

            <!-- Export Success Result -->
            @else if (service.lastExportResult()) {
              <div class="py-4 flex flex-col gap-4">
                <div class="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3">
                  <div class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                    <app-lucide-icon name="check" [size]="16"></app-lucide-icon>
                  </div>
                  <div class="flex flex-col">
                    <span class="text-xs font-bold text-emerald-900 font-heading">Export Ready for Download</span>
                    <span class="text-[11px] text-emerald-700 font-mono">{{ service.lastExportResult()?.file_name }}</span>
                  </div>
                </div>

                <div class="flex items-center justify-between text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200">
                  <span class="text-slate-500">Archive Size:</span>
                  <span class="font-mono font-semibold text-slate-900">
                    {{ ((service.lastExportResult()?.byte_size || 0) / 1024) | number:'1.1-1' }} KB
                  </span>
                </div>
              </div>
            }

            <!-- Format Selector Choices -->
            @else {
              <div class="flex flex-col gap-2.5">
                <span class="text-xs font-bold text-slate-700 font-heading">Select Export Format</span>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  
                  <!-- PDF Format Button -->
                  <button
                    (click)="onSelectFormat('PDF')"
                    class="p-3.5 bg-white border border-slate-200 hover:border-blue-400 rounded-xl flex items-center gap-3 cursor-pointer text-left transition-colors group shadow-2xs">
                    <div class="w-8 h-8 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 group-hover:bg-rose-600 group-hover:text-white transition-colors">
                      <app-lucide-icon name="file-text" [size]="16"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col">
                      <span class="text-xs font-bold text-slate-900 group-hover:text-blue-600 font-heading">PDF Document</span>
                      <span class="text-[10px] text-slate-500">Formatted assurance report</span>
                    </div>
                  </button>

                  <!-- JSON Format Button -->
                  <button
                    (click)="onSelectFormat('JSON')"
                    class="p-3.5 bg-white border border-slate-200 hover:border-blue-400 rounded-xl flex items-center gap-3 cursor-pointer text-left transition-colors group shadow-2xs">
                    <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                      <app-lucide-icon name="file-code" [size]="16"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col">
                      <span class="text-xs font-bold text-slate-900 group-hover:text-blue-600 font-heading">JSON Raw Data</span>
                      <span class="text-[10px] text-slate-500">Canonical machine schema</span>
                    </div>
                  </button>

                  <!-- CSV Format Button -->
                  <button
                    (click)="onSelectFormat('CSV')"
                    class="p-3.5 bg-white border border-slate-200 hover:border-blue-400 rounded-xl flex items-center gap-3 cursor-pointer text-left transition-colors group shadow-2xs">
                    <div class="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                      <app-lucide-icon name="table" [size]="16"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col">
                      <span class="text-xs font-bold text-slate-900 group-hover:text-blue-600 font-heading">CSV Table Data</span>
                      <span class="text-[10px] text-slate-500">Tabular metrics &amp; findings</span>
                    </div>
                  </button>

                  <!-- ZIP Format Button -->
                  <button
                    (click)="onSelectFormat('ZIP')"
                    class="p-3.5 bg-white border border-slate-200 hover:border-blue-400 rounded-xl flex items-center gap-3 cursor-pointer text-left transition-colors group shadow-2xs">
                    <div class="w-8 h-8 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600 group-hover:bg-purple-600 group-hover:text-white transition-colors">
                      <app-lucide-icon name="archive" [size]="16"></app-lucide-icon>
                    </div>
                    <div class="flex flex-col">
                      <span class="text-xs font-bold text-slate-900 group-hover:text-blue-600 font-heading">Evidence ZIP</span>
                      <span class="text-[10px] text-slate-500">Signatures &amp; manifest bundle</span>
                    </div>
                  </button>

                </div>
              </div>
            }

          </div>

          <!-- Modal Footer -->
          <div class="p-4 bg-slate-50/80 border-t border-slate-200 flex items-center justify-end gap-2">
            <button
              (click)="onClose()"
              class="h-8 px-4 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs transition-colors cursor-pointer shadow-2xs">
              {{ service.lastExportResult() ? 'Done' : 'Cancel' }}
            </button>
          </div>

        </div>

      </div>
    }
  `
})
export class ReportsExportModalComponent {
  constructor(public service: ReportsService) {}

  public get targetReport() {
    return this.service.exportTargetReport();
  }

  public onClose(): void {
    this.service.closeExportModal();
  }

  public onBackdropClick(event: MouseEvent): void {
    this.service.closeExportModal();
  }

  public onSelectFormat(format: ExportFormat): void {
    this.service.dispatchExport(format);
  }
}
