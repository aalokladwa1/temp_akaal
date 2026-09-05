import { Component, Input, Output, EventEmitter, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { MigrationDevFixturesAdapter } from '../../../core/fixtures/migration-dev-fixtures.adapter';
import { PhysicalProviderId, PhysicalProviderMeta, ProviderCategory } from '../../../core/models/migration-view.models';

@Component({
  selector: 'app-provider-picker',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-3 text-xs select-none antialiased">
      
      <!-- Search Input -->
      <div class="relative w-full">
        <input
          type="text"
          [ngModel]="searchQuery()"
          (ngModelChange)="searchQuery.set($event)"
          placeholder="Search 28 physical engines..."
          class="w-full h-9 pl-9 pr-3 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors" />
        <div class="absolute left-3 top-2.5 text-slate-400 pointer-events-none">
          <app-lucide-icon name="search" [size]="14"></app-lucide-icon>
        </div>
      </div>

      <!-- Category Filter Pills (No 'All' tab - strictly segregated) -->
      <div class="flex items-center gap-1.5 flex-wrap">
        @for (cat of categories; track cat.id) {
          <button
            type="button"
            (click)="selectedCategory.set(cat.id)"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer focus:outline-none flex items-center gap-1.5"
            [class.bg-blue-600]="selectedCategory() === cat.id && !searchQuery()"
            [class.text-white]="selectedCategory() === cat.id && !searchQuery()"
            [class.bg-slate-100]="selectedCategory() !== cat.id || !!searchQuery()"
            [class.text-slate-700]="selectedCategory() !== cat.id || !!searchQuery()"
            [class.hover:bg-slate-200]="selectedCategory() !== cat.id || !!searchQuery()">
            <app-lucide-icon [name]="getCategoryIcon(cat.id)" [size]="13"></app-lucide-icon>
            <span>{{ cat.label }} ({{ getCategoryCount(cat.id) }})</span>
          </button>
        }
      </div>

      <!-- Provider Grid (Clean cards with category-specific Lucide icon) -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-[380px] overflow-y-auto pr-1">
        @for (p of filteredProviders(); track p.id) {
          <button
            type="button"
            (click)="selectProvider(p.id)"
            class="p-2.5 rounded-xl border text-left cursor-pointer transition-colors flex items-center justify-between gap-2 focus:outline-none"
            [class.border-blue-600]="selectedProviderId === p.id"
            [class.bg-blue-50]="selectedProviderId === p.id"
            [class.border-slate-200]="selectedProviderId !== p.id"
            [class.bg-white]="selectedProviderId !== p.id"
            [class.hover:border-slate-300]="selectedProviderId !== p.id"
            [class.hover:bg-slate-50]="selectedProviderId !== p.id">
            
            <div class="flex items-center gap-2.5 min-w-0">
              <div class="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-[11px] shrink-0"
                [class.bg-blue-600]="selectedProviderId === p.id"
                [class.text-white]="selectedProviderId === p.id"
                [class.bg-slate-100]="selectedProviderId !== p.id"
                [class.text-slate-700]="selectedProviderId !== p.id">
                <app-lucide-icon [name]="getCategoryIcon(p.category)" [size]="14"></app-lucide-icon>
              </div>
              <span
                class="font-semibold text-xs truncate"
                [class.text-blue-700]="selectedProviderId === p.id"
                [class.text-slate-900]="selectedProviderId !== p.id">
                {{ p.name }}
              </span>
            </div>

            <span
              class="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded shrink-0"
              [class.bg-blue-100]="selectedProviderId === p.id"
              [class.text-blue-800]="selectedProviderId === p.id"
              [class.bg-slate-100]="selectedProviderId !== p.id"
              [class.text-slate-600]="selectedProviderId !== p.id">
              {{ getCategoryBadge(p.category) }}
            </span>
          </button>
        }
      </div>

    </div>
  `
})
export class ProviderPickerComponent {
  @Input() selectedProviderId?: PhysicalProviderId;
  @Output() providerSelect = new EventEmitter<PhysicalProviderId>();

  public searchQuery = signal<string>('');
  public selectedCategory = signal<ProviderCategory>('RELATIONAL');

  public allProviders: PhysicalProviderMeta[] = [];

  public categories: { id: ProviderCategory; label: string }[] = [
    { id: 'RELATIONAL', label: 'Relational' },
    { id: 'WAREHOUSE', label: 'Warehouses' },
    { id: 'NOSQL_GRAPH_SEARCH', label: 'NoSQL & Search' },
    { id: 'STREAMING', label: 'Streaming' },
    { id: 'STORAGE', label: 'Storage' }
  ];

  public filteredProviders = computed<PhysicalProviderMeta[]>(() => {
    const q = this.searchQuery().trim().toLowerCase();
    const cat = this.selectedCategory();

    if (q) {
      // When actively searching, search across all 28 engines
      return this.allProviders.filter(p =>
        p.name.toLowerCase().includes(q) ||
        p.id.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q)
      );
    }

    return this.allProviders.filter(p => p.category === cat);
  });

  constructor() {
    const fixtures = new MigrationDevFixturesAdapter();
    this.allProviders = fixtures.getPhysicalProviders();
  }

  public getCategoryCount(catId: ProviderCategory): number {
    return this.allProviders.filter(p => p.category === catId).length;
  }

  public getCategoryIcon(cat: string): string {
    switch (cat) {
      case 'RELATIONAL':
        return 'database';
      case 'WAREHOUSE':
        return 'server';
      case 'NOSQL_GRAPH_SEARCH':
        return 'cpu';
      case 'STREAMING':
        return 'activity';
      case 'STORAGE':
        return 'hard-drive';
      default:
        return 'database';
    }
  }

  public getCategoryBadge(cat: string): string {
    switch (cat) {
      case 'RELATIONAL':
        return 'REL';
      case 'WAREHOUSE':
        return 'WAR';
      case 'NOSQL_GRAPH_SEARCH':
        return 'NOS';
      case 'STREAMING':
        return 'STR';
      case 'STORAGE':
        return 'STO';
      default:
        return cat.substring(0, 3);
    }
  }

  public selectProvider(providerId: PhysicalProviderId): void {
    this.selectedProviderId = providerId;
    this.providerSelect.emit(providerId);
  }
}
