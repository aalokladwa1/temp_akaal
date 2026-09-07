import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AttributeComparisonItem, AttributeDifferenceType, AttributeValueKind } from '../validation-discrepancies.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-discrepancies-attribute-diff',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-3">
      
      <!-- Table Viewport -->
      <div class="overflow-x-auto min-w-0 max-w-full border border-slate-200/80 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="bg-slate-50/90 border-b border-slate-200 text-[10.5px] font-bold text-slate-500 uppercase tracking-wider">
              <th class="py-3.5 px-4 min-w-[180px] w-1/4">Attribute</th>
              <th class="py-3.5 px-4 min-w-[240px] w-1/3">
                <div class="flex items-center gap-1.5 text-blue-700">
                  <app-lucide-icon name="database" [size]="13"></app-lucide-icon>
                  <span>Source Logical Value</span>
                </div>
              </th>
              <th class="py-3.5 px-4 min-w-[240px] w-1/3">
                <div class="flex items-center gap-1.5 text-emerald-700">
                  <app-lucide-icon name="database" [size]="13"></app-lucide-icon>
                  <span>Target Logical Value</span>
                </div>
              </th>
              <th class="py-3.5 px-4 min-w-[140px] text-right">Result</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 bg-white">
            @for (attr of displayedAttributes(); track attr.attributeName) {
              <tr
                [class.bg-rose-50]="attr.diffType !== 'MATCH'"
                [class.bg-white]="attr.diffType === 'MATCH'"
                class="hover:bg-slate-50 transition-colors">
                
                <!-- Attribute Name -->
                <td class="py-4 px-4 align-top">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <span class="font-mono font-bold text-slate-900 text-[11.5px]">
                      {{ attr.attributeName }}
                    </span>
                    @if (attr.isKey) {
                      <span class="px-1.5 py-0.5 text-[9.5px] font-bold uppercase rounded bg-amber-100 text-amber-800 border border-amber-300">
                        PK
                      </span>
                    }
                    @if (attr.isSensitive) {
                      <span class="px-1.5 py-0.5 text-[9.5px] font-bold uppercase rounded bg-slate-100 text-slate-700 border border-slate-300">
                        Protected
                      </span>
                    }
                  </div>
                  @if (attr.transformationNote) {
                    <p class="text-[10.5px] text-blue-600 mt-1 leading-snug">
                      {{ attr.transformationNote }}
                    </p>
                  }
                </td>

                <!-- Source Logical Value -->
                <td class="py-4 px-4 align-top">
                  <div class="flex items-start justify-between gap-2 group/src">
                    <div class="flex flex-col gap-1.5 flex-1 min-w-0">
                      @switch (attr.sourceValueKind) {
                        @case ('PROTECTED') {
                          <div class="flex items-center gap-2">
                            <span class="font-mono font-bold text-slate-500 tracking-widest text-[13px]">••••••••••••</span>
                            <span class="inline-flex items-center px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-medium text-[10px] border border-slate-200">
                              Protected Value
                            </span>
                          </div>
                        }
                        @case ('NULL') {
                          <span class="inline-flex items-center px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[11px] font-bold border border-slate-200">
                            NULL
                          </span>
                        }
                        @case ('EMPTY_STRING') {
                          <span class="inline-flex items-center px-2 py-0.5 rounded bg-amber-50 text-amber-700 font-mono text-[11px] font-bold border border-amber-200">
                            "" (Empty String)
                          </span>
                        }
                        @case ('WHITESPACE') {
                          <span class="inline-flex items-center px-2 py-0.5 rounded bg-amber-50 text-amber-700 font-medium text-[10.5px] border border-amber-200">
                            Whitespace Only
                          </span>
                        }
                        @case ('ABSENT') {
                          <span class="inline-flex items-center px-2 py-0.5 rounded bg-rose-50 text-rose-700 font-medium text-[10.5px] border border-rose-200">
                            Missing in Source
                          </span>
                        }
                        @case ('LOB_TRUNCATED') {
                          <div class="flex flex-col gap-1.5">
                            <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 font-mono text-[11px] text-slate-800 break-all max-h-28 overflow-y-auto leading-relaxed">
                              {{ attr.sourceValue }}
                            </div>
                            @if (attr.lobMetadata) {
                              <div class="flex items-center gap-2 text-[10.5px] text-slate-500 font-mono">
                                <span class="font-semibold">{{ formatBytes(attr.lobMetadata.byteLength) }}</span>
                                <span>·</span>
                                <span>{{ attr.lobMetadata.mimeType }}</span>
                              </div>
                            }
                          </div>
                        }
                        @default {
                          <div class="font-mono text-slate-900 text-xs break-all leading-relaxed">
                            {{ attr.sourceValue }}
                          </div>
                        }
                      }

                      <!-- Datatype pill -->
                      @if (attr.sourceType) {
                        <span class="text-[10px] font-mono text-slate-400">
                          {{ attr.sourceType }}
                        </span>
                      }
                    </div>

                    <!-- Source Copy Button -->
                    @if (attr.sourceValue !== null && attr.sourceValue !== undefined && attr.sourceValueKind !== 'PROTECTED') {
                      <button
                        type="button"
                        (click)="copyToClipboard(attr.sourceValue, 'src_' + attr.attributeName)"
                        [title]="copiedKey() === 'src_' + attr.attributeName ? 'Copied to clipboard' : 'Copy source logical value'"
                        class="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 cursor-pointer shrink-0 transition-opacity group-hover/src:opacity-100"
                        [class.opacity-100]="copiedKey() === 'src_' + attr.attributeName"
                        [class.opacity-0]="copiedKey() !== 'src_' + attr.attributeName">
                        <app-lucide-icon
                          [name]="copiedKey() === 'src_' + attr.attributeName ? 'check' : 'copy'"
                          [size]="12"
                          [class]="copiedKey() === 'src_' + attr.attributeName ? 'text-emerald-600' : 'text-slate-400'"></app-lucide-icon>
                      </button>
                    }
                  </div>
                </td>

                <!-- Target Logical Value -->
                <td class="py-4 px-4 align-top">
                  <div class="flex items-start justify-between gap-2 group/tgt">
                    <div class="flex flex-col gap-1.5 flex-1 min-w-0">
                      @switch (attr.targetValueKind) {
                        @case ('PROTECTED') {
                          <div class="flex items-center gap-2">
                            <span class="font-mono font-bold text-slate-500 tracking-widest text-[13px]">••••••••••••</span>
                            <span class="inline-flex items-center px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-medium text-[10px] border border-slate-200">
                              Protected Value
                            </span>
                          </div>
                        }
                        @case ('NULL') {
                          <span class="inline-flex items-center px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[11px] font-bold border border-slate-200">
                            NULL
                          </span>
                        }
                        @case ('EMPTY_STRING') {
                          <span class="inline-flex items-center px-2 py-0.5 rounded bg-amber-50 text-amber-700 font-mono text-[11px] font-bold border border-amber-200">
                            "" (Empty String)
                          </span>
                        }
                        @case ('WHITESPACE') {
                          <span class="inline-flex items-center px-2 py-0.5 rounded bg-amber-50 text-amber-700 font-medium text-[10.5px] border border-amber-200">
                            Whitespace Only
                          </span>
                        }
                        @case ('ABSENT') {
                          <span class="inline-flex items-center px-2 py-0.5 rounded bg-rose-50 text-rose-700 font-medium text-[10.5px] border border-rose-200">
                            Missing in Target
                          </span>
                        }
                        @case ('LOB_TRUNCATED') {
                          <div class="flex flex-col gap-1.5">
                            <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 font-mono text-[11px] text-slate-800 break-all max-h-28 overflow-y-auto leading-relaxed">
                              {{ attr.targetValue }}
                            </div>
                            @if (attr.lobMetadata) {
                              <div class="flex items-center gap-2 text-[10.5px] text-slate-500 font-mono">
                                <span class="font-semibold">{{ formatBytes(attr.lobMetadata.byteLength) }}</span>
                                <span>·</span>
                                <span>{{ attr.lobMetadata.mimeType }}</span>
                              </div>
                            }
                          </div>
                        }
                        @default {
                          <div class="font-mono text-slate-900 text-xs break-all leading-relaxed">
                            {{ attr.targetValue }}
                          </div>
                        }
                      }

                      <!-- Datatype pill -->
                      @if (attr.targetType) {
                        <span class="text-[10px] font-mono text-slate-400">
                          {{ attr.targetType }}
                        </span>
                      }
                    </div>

                    <!-- Target Copy Button -->
                    @if (attr.targetValue !== null && attr.targetValue !== undefined && attr.targetValueKind !== 'PROTECTED') {
                      <button
                        type="button"
                        (click)="copyToClipboard(attr.targetValue, 'tgt_' + attr.attributeName)"
                        [title]="copiedKey() === 'tgt_' + attr.attributeName ? 'Copied to clipboard' : 'Copy target logical value'"
                        class="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 cursor-pointer shrink-0 transition-opacity group-hover/tgt:opacity-100"
                        [class.opacity-100]="copiedKey() === 'tgt_' + attr.attributeName"
                        [class.opacity-0]="copiedKey() !== 'tgt_' + attr.attributeName">
                        <app-lucide-icon
                          [name]="copiedKey() === 'tgt_' + attr.attributeName ? 'check' : 'copy'"
                          [size]="12"
                          [class]="copiedKey() === 'tgt_' + attr.attributeName ? 'text-emerald-600' : 'text-slate-400'"></app-lucide-icon>
                      </button>
                    }
                  </div>
                </td>

                <!-- Result Badge -->
                <td class="py-4 px-4 text-right align-top">
                  @switch (attr.diffType) {
                    @case ('MATCH') {
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10.5px] font-semibold bg-slate-50 text-slate-600 border border-slate-200">
                        <app-lucide-icon name="check" [size]="11" class="text-emerald-600"></app-lucide-icon>
                        <span>Match</span>
                      </span>
                    }
                    @case ('DIFFERENT') {
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10.5px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                        <app-lucide-icon name="alert-circle" [size]="11"></app-lucide-icon>
                        <span>Differing</span>
                      </span>
                    }
                    @case ('SOURCE_ONLY') {
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10.5px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                        <app-lucide-icon name="minus-square" [size]="11"></app-lucide-icon>
                        <span>Source Only</span>
                      </span>
                    }
                    @case ('TARGET_ONLY') {
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10.5px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                        <app-lucide-icon name="plus-square" [size]="11"></app-lucide-icon>
                        <span>Target Only</span>
                      </span>
                    }
                    @case ('TYPE_MISMATCH') {
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10.5px] font-bold bg-orange-50 text-orange-700 border border-orange-200">
                        <app-lucide-icon name="type" [size]="11"></app-lucide-icon>
                        <span>Type Mismatch</span>
                      </span>
                    }
                  }
                </td>

              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class DiscrepanciesAttributeDiffComponent {
  @Input({ required: true }) attributes: AttributeComparisonItem[] = [];
  @Input() showDifferencesOnly: boolean = true;

  copiedKey = signal<string | null>(null);

  displayedAttributes(): AttributeComparisonItem[] {
    if (this.showDifferencesOnly) {
      return this.attributes.filter(a => a.diffType !== 'MATCH');
    }
    return this.attributes;
  }

  formatBytes(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  }

  copyToClipboard(val: any, key: string): void {
    const textToCopy = typeof val === 'object' ? JSON.stringify(val, null, 2) : String(val);
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(textToCopy);
      this.copiedKey.set(key);
      setTimeout(() => {
        if (this.copiedKey() === key) {
          this.copiedKey.set(null);
        }
      }, 2000);
    }
  }
}
