import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TemplateWorkspaceService } from '../template-workspace.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { TemplateActivityCategory, TemplateActivityEvent } from '../template-workspace.models';

@Component({
  selector: 'app-tab-template-activity',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 text-xs font-sans animate-in fade-in duration-150">
      
      @if (ws.template(); as tmpl) {
        
        <!-- SECTION 1: HEADER & CATEGORY FILTER STRIP -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div class="flex flex-col">
            <span class="font-bold text-slate-900 text-sm">Template Activity & Operational Audit</span>
            <span class="text-xs text-slate-500 font-normal">Chronological record of configuration revisions, lifecycle transitions, and migration instantiations.</span>
          </div>

          <!-- Category Filter Buttons (Text-Only Rectangular with Curved Corners) -->
          <div class="flex items-center gap-1.5 flex-wrap">
            @for (cat of categories; track cat.key) {
              <button
                type="button"
                (click)="selectedCategory.set(cat.key)"
                class="h-7.5 px-3 rounded-md text-xs font-semibold transition-all cursor-pointer border"
                [class]="selectedCategory() === cat.key
                  ? 'bg-blue-600 text-white border-blue-600 shadow-2xs'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'">
                {{ cat.label }}
              </button>
            }
          </div>
        </div>

        <!-- SECTION 2: TIMELINE LIST -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900 text-sm">Audit Log Events</span>
            <span class="text-[10px] font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
              {{ filteredEvents().length }} Events
            </span>
          </div>

          <div class="relative flex flex-col gap-4 pl-4 border-l-2 border-slate-200 ml-2">
            
            @for (act of filteredEvents(); track act.id) {
              <div class="relative flex flex-col gap-1.5 p-3.5 bg-slate-50 border border-slate-200 rounded-md">
                
                <!-- Dot on Timeline Line -->
                <div class="absolute -left-[23px] top-4 w-2.5 h-2.5 rounded-full bg-blue-600 border-2 border-white"></div>

                <!-- Event Header Row -->
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/60 pb-2">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="px-2 py-0.5 text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 rounded">
                      {{ act.category }}
                    </span>
                    <span class="font-bold text-slate-900 text-xs">{{ act.summary }}</span>
                    @if (act.affectedVersion) {
                      <span class="px-1.5 py-0.2 text-[9px] font-mono font-bold bg-slate-100 text-slate-700 rounded">
                        {{ act.affectedVersion }}
                      </span>
                    }
                  </div>
                  <span class="text-[10px] font-mono text-slate-500 shrink-0">
                    {{ act.timestamp | date:'medium' }}
                  </span>
                </div>

                <!-- Details & Actor -->
                @if (act.details) {
                  <p class="text-xs text-slate-600 m-0 font-normal leading-relaxed">
                    {{ act.details }}
                  </p>
                }

                <div class="flex items-center gap-2 pt-1 text-[11px] text-slate-500">
                  <app-lucide-icon name="user" [size]="12" class="text-slate-400"></app-lucide-icon>
                  <span><strong>{{ act.actor.name }}</strong> ({{ act.actor.role }}) &middot; {{ act.actor.email }}</span>
                </div>

              </div>
            }

            @if (filteredEvents().length === 0) {
              <div class="py-8 text-center text-slate-400 text-xs">
                No events recorded for category "{{ selectedCategory() }}".
              </div>
            }

          </div>
        </div>

      }

    </div>
  `
})
export class TabTemplateActivityComponent {
  public ws = inject(TemplateWorkspaceService);

  public selectedCategory = signal<TemplateActivityCategory>('ALL');

  public categories: { key: TemplateActivityCategory; label: string }[] = [
    { key: 'ALL', label: 'All Events' },
    { key: 'VERSIONS', label: 'Versions' },
    { key: 'GOVERNANCE', label: 'Governance' },
    { key: 'CONFIGURATION', label: 'Configuration' },
    { key: 'MIGRATION_APPLICATION', label: 'Migration Application' },
    { key: 'LIFECYCLE', label: 'Lifecycle' }
  ];

  public filteredEvents = computed<TemplateActivityEvent[]>(() => {
    const tmpl = this.ws.template();
    if (!tmpl || !tmpl.activities) return [];
    const cat = this.selectedCategory();
    if (cat === 'ALL') return tmpl.activities;
    return tmpl.activities.filter(a => a.category === cat);
  });
}
