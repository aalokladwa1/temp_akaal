/**
 * AKAAL Administration — 5.8 Framework Views
 * Focused views across GDPR, PCI-DSS, HIPAA, SOC 2, and ISO 27001.
 * Strictly adheres to rule: Technical control mapping != regulatory certification.
 */

import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ComplianceService } from '../../services/compliance.service';
import { RegulatoryDomain, FrameworkControl } from '../../models/compliance.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-framework-views',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Page Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <a
              routerLink="/administration/compliance"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back</span>
            </a>
            <span class="text-slate-300">/</span>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">COMPLIANCE</span>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">FRAMEWORK PERSPECTIVES</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading mt-2">Framework Views</h1>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Examine mapped technical controls, evidence links, and exceptions across major regulatory frameworks.
          </p>
        </div>
      </div>

      <!-- Regulatory Framework Selector Tabs -->
      <div class="flex items-center gap-2 border-b border-slate-200 pb-px">
        @for (item of domains; track item.key) {
          <button
            type="button"
            (click)="selectDomain(item.key)"
            class="px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors cursor-pointer"
            [ngClass]="selectedDomain() === item.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-600 hover:text-slate-900'">
            {{ item.label }}
          </button>
        }
      </div>

      <!-- Controls for Selected Framework View -->
      <div class="flex flex-col gap-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-slate-900 font-heading">SPECIFICATION CONTROLS</span>
            <span class="text-xs text-slate-500">({{ currentControls().length }} requirements)</span>
          </div>
          <span class="text-[11px] text-slate-500 italic">
            Technical safeguard coverage does not constitute formal legal certification.
          </span>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
                <th class="py-3.5 px-4">Control Code</th>
                <th class="py-3.5 px-4">Requirement</th>
                <th class="py-3.5 px-4">Domain Focus</th>
                <th class="py-3.5 px-4">Mapping Status</th>
                <th class="py-3.5 px-4">Mapped Technical Safeguards</th>
                <th class="py-3.5 px-4 text-right">Evidence Items</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200 text-xs">
              @for (ctrl of currentControls(); track ctrl.id) {
                <tr class="hover:bg-slate-50/80 transition-colors">
                  <td class="py-3.5 px-4 font-mono font-bold text-blue-600">{{ ctrl.controlCode }}</td>
                  <td class="py-3.5 px-4">
                    <div class="flex flex-col">
                      <span class="font-bold text-slate-900">{{ ctrl.title }}</span>
                      <span class="text-[11px] text-slate-500 mt-0.5 max-w-lg line-clamp-1">{{ ctrl.description }}</span>
                    </div>
                  </td>
                  <td class="py-3.5 px-4 text-slate-600">{{ ctrl.domain }}</td>
                  <td class="py-3.5 px-4">
                    <span 
                      class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border-emerald-200': ctrl.mappingState === 'FULLY_MAPPED',
                        'bg-blue-50 text-blue-700 border-blue-200': ctrl.mappingState === 'PARTIALLY_MAPPED',
                        'bg-amber-50 text-amber-700 border-amber-200': ctrl.mappingState === 'EXCEPTION_RECORDED',
                        'bg-slate-100 text-slate-700 border-slate-200': ctrl.mappingState === 'UNMAPPED'
                      }">
                      {{ ctrl.mappingState.replace('_', ' ') }}
                    </span>
                  </td>
                  <td class="py-3.5 px-4">
                    <div class="flex flex-wrap gap-1.5">
                      @for (tech of ctrl.mappedTechnicalControls; track tech) {
                        <span class="inline-flex items-center px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[10px] border border-slate-200">
                          {{ tech }}
                        </span>
                      }
                    </div>
                  </td>
                  <td class="py-3.5 px-4 text-right font-semibold text-slate-900">
                    <a 
                      routerLink="/administration/compliance/evidence"
                      class="text-blue-600 hover:underline">
                      {{ ctrl.evidenceCount }} items
                    </a>
                  </td>
                </tr>
              }
              @if (currentControls().length === 0) {
                <tr>
                  <td colspan="6" class="py-8 text-center text-slate-500 text-xs">
                    No mapped requirements found for this framework view.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class FrameworkViewsComponent {
  public complianceService = inject(ComplianceService);

  public domains: { key: RegulatoryDomain; label: string }[] = [
    { key: 'GDPR', label: 'GDPR Privacy Controls' },
    { key: 'PCI_DSS', label: 'PCI-DSS v4.0' },
    { key: 'HIPAA', label: 'HIPAA Security Rule' },
    { key: 'SOC_2', label: 'SOC 2 Type II' },
    { key: 'ISO_27001', label: 'ISO 27001:2022' }
  ];

  public selectedDomain = signal<RegulatoryDomain>('GDPR');

  public selectDomain(key: RegulatoryDomain): void {
    this.selectedDomain.set(key);
  }

  public currentControls(): FrameworkControl[] {
    const fw = this.complianceService.getFrameworkByDomain(this.selectedDomain());
    return fw ? this.complianceService.getControlsForFramework(fw.id) : [];
  }
}
