import { Component, Input, Output, EventEmitter, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { MigrationDevFixturesAdapter } from '../../../core/fixtures/migration-dev-fixtures.adapter';
import { PhysicalProviderId, PhysicalProviderMeta } from '../../../core/models/migration-view.models';

@Component({
  selector: 'app-provider-picker',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-3 text-xs select-none">
      
      <!-- Search Input -->
      <div class="relative w-full">
        <input
          type="text"
          [(ngModel)]="searchQuery"
          placeholder="Search 28 physical engines..."
          class="w-full h-8 pl-8 pr-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
        <div class="absolute left-2.5 top-2 text-slate-400 pointer-events-none">
          <app-lucide-icon name="search" [size]="13"></app-lucide-icon>
        </div>
      </div>

      <!-- Category Filter Pills -->
      <div class="flex items-center gap-1.5 flex-wrap">
        @for (cat of categories; track cat.id) {
          <button
            type="button"
            (click)="selectedCategory.set(cat.id)"
            class="px-2.5 py-1 rounded-md text-[11px] font-bold transition-all cursor-pointer"
            [class.bg-blue-600]="selectedCategory() === cat.id"
            [class.text-white]="selectedCategory() === cat.id"
            [class.bg-slate-100]="selectedCategory() !== cat.id"
            [class.text-slate-700]="selectedCategory() !== cat.id"
            [class.hover:bg-slate-200]="selectedCategory() !== cat.id">
            {{ cat.label }} ({{ getCategoryCount(cat.id) }})
          </button>
        }
      </div>

      <!-- 28 Provider Grid (Clean, compact cards without description summaries, using technology-specific Lucide icons) -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[480px] overflow-y-auto pr-1">
        @for (p of filteredProviders(); track p.id) {
          <div
            (click)="selectProvider(p.id)"
            class="p-2.5 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between gap-2 hover:border-blue-400"
            [class.border-blue-600]="selectedProviderId === p.id"
            [class.bg-blue-50]="selectedProviderId === p.id"
            [class.border-slate-200]="selectedProviderId !== p.id"
            [class.bg-white]="selectedProviderId !== p.id">
            
            <div class="flex items-center gap-2.5 min-w-0">
              <div class="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-[11px] shrink-0"
                [class.bg-blue-600]="selectedProviderId === p.id"
                [class.text-white]="selectedProviderId === p.id"
                [class.bg-slate-100]="selectedProviderId !== p.id"
                [class.text-slate-700]="selectedProviderId !== p.id">
                <app-lucide-icon [name]="p.icon" [size]="14"></app-lucide-icon>
              </div>
              <span class="font-bold text-slate-900 text-xs truncate">{{ p.name }}</span>
            </div>

            <span class="text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 shrink-0">
              {{ p.category.substring(0, 3) }}
            </span>
          </div>
        }
      </div>

    </div>
  `
})
export class ProviderPickerComponent {
  @Input() selectedProviderId?: PhysicalProviderId;
  @Output() providerSelect = new EventEmitter<PhysicalProviderId>();

  public searchQuery = '';
  public selectedCategory = signal<string>('ALL');

  public allProviders: PhysicalProviderMeta[] = [];

  public categories: { id: string; label: string }[] = [
    { id: 'ALL', label: 'All' },
    { id: 'RELATIONAL', label: 'Relational' },
    { id: 'WAREHOUSE', label: 'Warehouses' },
    { id: 'NOSQL_GRAPH_SEARCH', label: 'NoSQL & Graph' },
    { id: 'STREAMING', label: 'Streaming' },
    { id: 'STORAGE', label: 'Storage' }
  ];

  public filteredProviders = computed<PhysicalProviderMeta[]>(() => {
    let list = this.allProviders;
    const cat = this.selectedCategory();
    const q = this.searchQuery.trim().toLowerCase();

    if (cat !== 'ALL') {
      list = list.filter(p => p.category === cat);
    }
    if (q) {
      list = list.filter(p => p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q));
    }
    return list;
  });

  constructor() {
    const fixtures = new MigrationDevFixturesAdapter();
    this.allProviders = fixtures.getPhysicalProviders();
  }

  public getCategoryCount(catId: string): number {
    if (catId === 'ALL') return this.allProviders.length;
    return this.allProviders.filter(p => p.category === catId).length;
  }

  public selectProvider(providerId: PhysicalProviderId): void {
    this.selectedProviderId = providerId;
    this.providerSelect.emit(providerId);
  }
}
