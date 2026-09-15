/**
 * AKAAL Administration — 5.6 Connector Detail
 */

import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ConnectorsPluginsService } from '../../services/connectors-plugins.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-connector-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link & Header -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/connectors/registry" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to Connector Registry
          </a>
        </div>

        @if (connector(); as item) {
          <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
            <div class="flex flex-col gap-1">
              <div class="flex items-center gap-3">
                <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ item.name }}</h1>
                <span
                  [ngClass]="{
                    'bg-emerald-50 text-emerald-700 border-emerald-200': item.certificationLevel === 'LIVE_PROVEN',
                    'bg-blue-50 text-blue-700 border-blue-200': item.certificationLevel === 'INTEGRATION_PROVEN',
                    'bg-slate-50 text-slate-700 border-slate-200': item.certificationLevel === 'UNIT_PROVEN'
                  }"
                  class="px-2 py-0.5 rounded text-[10px] font-bold border font-mono uppercase tracking-wide">
                  {{ item.certificationLevel }}
                </span>
              </div>
              <p class="text-sm font-medium text-slate-600 max-w-3xl">
                Provider ID: <span class="font-mono text-slate-800 font-semibold">{{ item.providerId }}</span> &bull; {{ item.category }}
              </p>
            </div>
          </div>
        }
      </div>

      @if (connector(); as item) {
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <!-- Column 1 & 2: Technical Specifications & Capabilities -->
          <div class="lg:col-span-2 flex flex-col gap-6">
            
            <!-- Capabilities Matrix Card -->
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Provider Capability Profile</h2>
              
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                  <span class="text-xs font-medium text-slate-700">Source Extraction</span>
                  <span [class]="item.capabilities.supportsSource ? 'text-emerald-600 font-bold' : 'text-slate-400'">
                    {{ item.capabilities.supportsSource ? 'Supported' : 'No' }}
                  </span>
                </div>

                <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                  <span class="text-xs font-medium text-slate-700">Target Ingestion</span>
                  <span [class]="item.capabilities.supportsTarget ? 'text-emerald-600 font-bold' : 'text-slate-400'">
                    {{ item.capabilities.supportsTarget ? 'Supported' : 'No' }}
                  </span>
                </div>

                <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                  <span class="text-xs font-medium text-slate-700">Change Data Capture</span>
                  <span [class]="item.capabilities.supportsCdc ? 'text-emerald-600 font-bold' : 'text-slate-400'">
                    {{ item.capabilities.supportsCdc ? 'Supported' : 'No' }}
                  </span>
                </div>

                <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                  <span class="text-xs font-medium text-slate-700">High-Speed Bulk</span>
                  <span [class]="item.capabilities.supportsBulk ? 'text-emerald-600 font-bold' : 'text-slate-400'">
                    {{ item.capabilities.supportsBulk ? 'Supported' : 'No' }}
                  </span>
                </div>

                <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                  <span class="text-xs font-medium text-slate-700">Schema Introspection</span>
                  <span [class]="item.capabilities.supportsSchemaIntrospection ? 'text-emerald-600 font-bold' : 'text-slate-400'">
                    {{ item.capabilities.supportsSchemaIntrospection ? 'Supported' : 'No' }}
                  </span>
                </div>

                <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                  <span class="text-xs font-medium text-slate-700">Validation Sampling</span>
                  <span [class]="item.capabilities.supportsValidationSampling ? 'text-emerald-600 font-bold' : 'text-slate-400'">
                    {{ item.capabilities.supportsValidationSampling ? 'Supported' : 'No' }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Supported Dialects & Editions -->
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Supported Dialects &amp; Editions</h2>
              <div class="flex flex-wrap gap-2">
                @for (d of item.supportedDialects; track d) {
                  <span class="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200">
                    {{ d }}
                  </span>
                }
              </div>
            </div>

            <!-- Qualification & Test Evidence Notes -->
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-3">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Internal Qualification Evidence</h2>
              <p class="text-xs text-slate-600 leading-relaxed">{{ item.qualificationNotes }}</p>
              <div class="text-[11px] text-slate-500 pt-2 border-t border-slate-100 flex items-center gap-4">
                <span>Last Verification: <strong class="text-slate-700">{{ item.lastTestedDate }}</strong></span>
                <span>Engine Protocol: <strong class="font-mono text-slate-700">{{ item.engineProtocolVersion }}</strong></span>
              </div>
            </div>

          </div>

          <!-- Column 3: Packaging & Metadata Sidebar -->
          <div class="flex flex-col gap-6">
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-4">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Package Specifications</h2>

              <div class="flex flex-col gap-3 text-xs">
                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-500 font-medium">Connector Version</span>
                  <span class="font-mono font-bold text-slate-900">{{ item.version }}</span>
                </div>

                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-500 font-medium">Underlying Driver</span>
                  <span class="font-mono font-medium text-slate-800">{{ item.driverVersion }}</span>
                </div>

                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-500 font-medium">Packaging Source</span>
                  <span class="font-semibold text-slate-800">{{ item.isBuiltIn ? 'Built-In (Native Core)' : 'External Extension' }}</span>
                </div>

                <div class="flex flex-col gap-0.5">
                  <span class="text-slate-500 font-medium">Supported Roles</span>
                  <span class="font-semibold text-slate-800">{{ item.applicability }}</span>
                </div>
              </div>

              <div class="pt-4 border-t border-slate-100">
                <div class="p-3 bg-blue-50/50 border border-blue-100 rounded-lg text-xs text-blue-800">
                  <span class="font-semibold block mb-0.5">Module Scope Notice</span>
                  This view inspects the connector driver software capability. Real configured source and target endpoints belong in the Connections module.
                </div>
              </div>
            </div>
          </div>

        </div>
      } @else {
        <div class="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 text-xs">
          Connector definition not found.
        </div>
      }

    </div>
  `
})
export class ConnectorDetailComponent {
  private service = inject(ConnectorsPluginsService);
  private route = inject(ActivatedRoute);

  public connector = computed(() => {
    const id = this.route.snapshot.paramMap.get('id');
    return id ? this.service.getConnectorById(id) : undefined;
  });
}
