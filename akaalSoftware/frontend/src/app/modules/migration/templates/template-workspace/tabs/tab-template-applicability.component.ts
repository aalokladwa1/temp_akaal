import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TemplateWorkspaceService } from '../template-workspace.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { TEMPLATE_MODE_DESCRIPTORS } from '../../templates.models';

@Component({
  selector: 'app-tab-template-applicability',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 text-xs font-sans animate-in fade-in duration-150">
      
      @if (ws.template(); as tmpl) {
        
        <!-- SECTION 1: SOURCE & TARGET ENGINE DIALECTS -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div class="flex flex-col">
              <span class="font-bold text-slate-900 text-sm">Source & Target Engine Applicability</span>
              <span class="text-xs text-slate-500 font-normal">Dialect support and engine family boundaries for extraction and ingestion.</span>
            </div>
            <span class="px-2.5 py-0.5 text-[10px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200 rounded-md">
              {{ tmpl.applicability.sourceProviderName }} &rarr; {{ tmpl.applicability.targetProviderName }}
            </span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            <!-- Source Engine -->
            <div class="p-4 bg-slate-50 border border-slate-200 rounded-md flex flex-col gap-2">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Source Engine (Extraction)</span>
                <span class="px-2 py-0.5 text-[10px] font-semibold bg-white text-slate-700 border border-slate-200 rounded">
                  {{ tmpl.applicability.sourceProviderName }}
                </span>
              </div>
              <span class="font-bold text-slate-900 text-xs">{{ tmpl.applicabilityDetails.sourceDialect }}</span>
              <p class="text-[11px] text-slate-600 font-normal m-0 leading-relaxed">
                Family: {{ tmpl.applicabilityDetails.sourceFamily }}. Extraction drivers and transaction log listeners are bound to this dialect.
              </p>
            </div>

            <!-- Target Engine -->
            <div class="p-4 bg-slate-50 border border-slate-200 rounded-md flex flex-col gap-2">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Target Engine (Ingestion)</span>
                <span class="px-2 py-0.5 text-[10px] font-semibold bg-white text-slate-700 border border-slate-200 rounded">
                  {{ tmpl.applicability.targetProviderName }}
                </span>
              </div>
              <span class="font-bold text-slate-900 text-xs">{{ tmpl.applicabilityDetails.targetDialect }}</span>
              <p class="text-[11px] text-slate-600 font-normal m-0 leading-relaxed">
                Family: {{ tmpl.applicabilityDetails.targetFamily }}. Ingestion interface, DDL converters, and bulk loaders are bound to this target.
              </p>
            </div>

          </div>
        </div>

        <!-- SECTION 2: COMPATIBILITY ASSESSMENT & CAPABILITIES -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Provider Pair Compatibility Status -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3">
            <div class="flex items-center justify-between border-b border-slate-100 pb-2">
              <span class="font-bold text-slate-900">Provider-Pair Compatibility</span>
              <span
                class="px-2 py-0.5 text-[10px] font-bold rounded-md"
                [class]="tmpl.applicabilityDetails.compatibility.status === 'VERIFIED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-700 border border-slate-200'">
                {{ tmpl.applicabilityDetails.compatibility.status }}
              </span>
            </div>

            <div class="flex flex-col gap-2">
              <span class="font-bold text-slate-900 text-xs">{{ tmpl.applicabilityDetails.compatibility.statusLabel }}</span>
              <p class="text-xs text-slate-600 font-normal m-0 leading-relaxed">
                {{ tmpl.applicabilityDetails.compatibility.notes || 'Engine dialects tested and verified across standard benchmark suites.' }}
              </p>
            </div>
          </div>

          <!-- Required Engine Capabilities & Privileges -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3">
            <div class="flex items-center justify-between border-b border-slate-100 pb-2">
              <span class="font-bold text-slate-900">Required Capabilities & Privileges</span>
              <span class="text-[10px] text-slate-400">Pre-flight verified</span>
            </div>

            <div class="flex flex-col gap-2">
              <div class="flex flex-wrap gap-1.5">
                @for (priv of tmpl.applicabilityDetails.requiredCapabilities.sourcePrivileges; track priv) {
                  <span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-slate-50 text-slate-800 border border-slate-200 rounded">
                    {{ priv }}
                  </span>
                }
                @for (priv of tmpl.applicabilityDetails.requiredCapabilities.targetPrivileges; track priv) {
                  <span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-blue-50 text-blue-800 border border-blue-200 rounded">
                    {{ priv }}
                  </span>
                }
              </div>
            </div>
          </div>

        </div>

        <!-- SECTION 3: REQUIRED-AT-USE CONTRACT VALUES -->
        <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3.5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <div class="flex flex-col">
              <span class="font-bold text-slate-900">Required-at-Use Values Contract</span>
              <span class="text-xs text-slate-500 font-normal">Values that operators are mandated to provide during migration provisioning.</span>
            </div>
            <span class="text-[10px] font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-700">Enforced at Provisioning</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            
            <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2">
              <span
                class="w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold"
                [class]="tmpl.applicabilityDetails.requiredAtUse.targetDatabaseRequired ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'">
                {{ tmpl.applicabilityDetails.requiredAtUse.targetDatabaseRequired ? '✓' : '—' }}
              </span>
              <span class="font-medium text-slate-800">Target Database / Schema Name</span>
            </div>

            <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2">
              <span
                class="w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold"
                [class]="tmpl.applicabilityDetails.requiredAtUse.scheduleRequired ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'">
                {{ tmpl.applicabilityDetails.requiredAtUse.scheduleRequired ? '✓' : '—' }}
              </span>
              <span class="font-medium text-slate-800">Execution Schedule Binding</span>
            </div>

            <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2">
              <span
                class="w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold"
                [class]="tmpl.applicabilityDetails.requiredAtUse.secretBindingsRequired ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'">
                {{ tmpl.applicabilityDetails.requiredAtUse.secretBindingsRequired ? '✓' : '—' }}
              </span>
              <span class="font-medium text-slate-800">Secret Vault Reference Authentication</span>
            </div>

          </div>
        </div>

        <!-- SECTION 4: CONSTRAINTS & KNOWN LIMITATIONS -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Environment Constraints -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3">
            <div class="flex items-center gap-2 border-b border-slate-100 pb-2">
              <app-lucide-icon name="shield" [size]="15" class="text-slate-700"></app-lucide-icon>
              <span class="font-bold text-slate-900">Environment & Security Constraints</span>
            </div>

            <ul class="m-0 pl-4 space-y-1.5 text-xs text-slate-600">
              @for (c of tmpl.applicabilityDetails.environmentConstraints; track c) {
                <li>{{ c }}</li>
              }
            </ul>
          </div>

          <!-- Known Limitations -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-3">
            <div class="flex items-center gap-2 border-b border-slate-100 pb-2">
              <app-lucide-icon name="alert-circle" [size]="15" class="text-amber-600"></app-lucide-icon>
              <span class="font-bold text-slate-900">Known Operational Limitations</span>
            </div>

            <ul class="m-0 pl-4 space-y-1.5 text-xs text-slate-600">
              @for (lim of tmpl.applicabilityDetails.knownLimitations; track lim) {
                <li>{{ lim }}</li>
              }
            </ul>
          </div>

        </div>

      }

    </div>
  `
})
export class TabTemplateApplicabilityComponent {
  public ws = inject(TemplateWorkspaceService);
}
