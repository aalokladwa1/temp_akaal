import {
  Component,
  Input,
  Output,
  EventEmitter,
  signal,
  computed,
  ElementRef,
  HostListener,
  OnChanges,
  OnInit,
  OnDestroy,
  SimpleChanges
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from './lucide-icon.component';

export interface CustomSelectOption {
  label: string;
  value: any;
  desc?: string;
  icon?: string;
  group?: string;
  disabled?: boolean;
  badge?: string;
}

export interface GroupedSelectOption {
  groupName: string;
  options: CustomSelectOption[];
}

@Component({
  selector: 'app-custom-select',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="relative w-full text-xs select-none antialiased">
      
      <!-- Trigger Button -->
      <button
        type="button"
        (click)="toggleOpen($event)"
        [disabled]="disabled"
        class="w-full bg-white border border-slate-200 flex items-center justify-between text-left text-xs font-medium text-slate-800 hover:border-slate-300 transition-colors cursor-pointer focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        [class.h-7]="size === 'sm'"
        [class.px-2]="size === 'sm'"
        [class.rounded]="size === 'sm'"
        [class.h-9]="size !== 'sm'"
        [class.px-3]="size !== 'sm'"
        [class.rounded-lg]="size !== 'sm'"
        [class.border-blue-500]="isOpen()">
        
        <div class="flex items-center gap-1.5 min-w-0 flex-1">
          @if (selectedOption()?.icon; as iconName) {
            <app-lucide-icon [name]="iconName" [size]="size === 'sm' ? 12 : 14" class="text-slate-500 shrink-0"></app-lucide-icon>
          }
          <span class="truncate" [class.text-slate-400]="!selectedOption()">
            {{ selectedLabel() }}
          </span>
          @if (selectedOption()?.badge; as badgeText) {
            <span class="px-1.5 py-0.2 text-[9px] font-mono font-bold bg-slate-100 text-slate-600 rounded shrink-0">
              {{ badgeText }}
            </span>
          }
        </div>

        <app-lucide-icon
          name="chevron-down"
          [size]="size === 'sm' ? 12 : 14"
          class="text-slate-400 shrink-0 ml-1 transition-transform duration-150"
          [class.rotate-180]="isOpen()"></app-lucide-icon>
      </button>

      <!-- Dropdown Floating Popup -->
      @if (isOpen()) {
        <div
          class="absolute left-0 z-50 bg-white border border-slate-200 rounded-xl p-1.5 flex flex-col gap-1 animate-in fade-in zoom-in-95 duration-100 max-h-72 overflow-y-auto min-w-[280px] w-full max-w-lg whitespace-normal shadow-none"
          [class.top-full]="!openUpward()"
          [class.mt-1.5]="!openUpward()"
          [class.bottom-full]="openUpward()"
          [class.mb-1.5]="openUpward()"
          (click)="$event.stopPropagation()">
          
          <!-- Optional Search Bar -->
          @if (searchable) {
            <div class="relative px-1 pb-1 pt-0.5 border-b border-slate-100 mb-0.5">
              <input
                type="text"
                [(ngModel)]="searchQuery"
                [placeholder]="searchPlaceholder"
                class="w-full h-8 pl-8 pr-7 bg-slate-50 border border-slate-200 focus:border-blue-500 rounded-lg text-xs font-medium text-slate-900 focus:outline-none transition-all placeholder:text-slate-400" />
              <app-lucide-icon name="search" [size]="13" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
              @if (searchQuery()) {
                <button
                  type="button"
                  (click)="searchQuery.set('')"
                  class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer">
                  <app-lucide-icon name="x-circle" [size]="13"></app-lucide-icon>
                </button>
              }
            </div>
          }

          <!-- Option List: Grouped vs Flat -->
          @if (hasGroups()) {
            @for (grp of filteredGroupedOptions(); track grp.groupName) {
              <div class="flex flex-col gap-0.5">
                <div class="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                  <span>{{ grp.groupName }}</span>
                  <span class="text-[9px] font-mono text-slate-400">{{ grp.options.length }}</span>
                </div>
                @for (opt of grp.options; track opt.value) {
                  <ng-container *ngTemplateOutlet="optionTemplate; context: { $implicit: opt }"></ng-container>
                }
              </div>
            }
            @if (filteredGroupedOptions().length === 0) {
              <div class="py-6 text-center text-slate-400 text-xs">No matching options found</div>
            }
          } @else {
            @for (opt of filteredOptions(); track opt.value) {
              <ng-container *ngTemplateOutlet="optionTemplate; context: { $implicit: opt }"></ng-container>
            }
            @if (filteredOptions().length === 0) {
              <div class="py-6 text-center text-slate-400 text-xs">No matching options found</div>
            }
          }

          <!-- Template for single option item -->
          <ng-template #optionTemplate let-opt>
            <button
              type="button"
              [disabled]="opt.disabled"
              (click)="selectOption(opt.value, $event)"
              class="px-2.5 py-2 rounded-lg text-left transition-colors flex items-start justify-between cursor-pointer w-full gap-2.5 disabled:opacity-40 disabled:cursor-not-allowed"
              [class.bg-blue-50]="isSelected(opt.value)"
              [class.hover:bg-slate-50]="!isSelected(opt.value) && !opt.disabled">
              
              <div class="flex items-start gap-2.5 min-w-0 flex-1">
                @if (opt.icon) {
                  <app-lucide-icon [name]="opt.icon" [size]="14" class="text-slate-500 shrink-0 mt-0.5"></app-lucide-icon>
                }
                <div class="flex flex-col min-w-0 flex-1">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <span class="font-semibold text-xs text-slate-900 leading-snug">
                      {{ opt.label }}
                    </span>
                    @if (opt.badge) {
                      <span class="px-1.5 py-0.2 text-[9px] font-mono font-bold bg-slate-100 text-slate-600 rounded">
                        {{ opt.badge }}
                      </span>
                    }
                  </div>
                  @if (opt.desc) {
                    <span class="text-[11px] text-slate-500 font-normal leading-relaxed mt-0.5">
                      {{ opt.desc }}
                    </span>
                  }
                </div>
              </div>

              @if (isSelected(opt.value)) {
                <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
              }
            </button>
          </ng-template>

        </div>
      }

    </div>
  `
})
export class CustomSelectComponent implements OnInit, OnChanges, OnDestroy {
  @Input() options: CustomSelectOption[] = [];
  @Input() value: any;
  @Input() placeholder: string = 'Select an option...';
  @Input() disabled: boolean = false;
  @Input() size: 'sm' | 'md' = 'md';
  @Input() searchable: boolean = false;
  @Input() searchPlaceholder: string = 'Search options...';

  @Output() valueChange = new EventEmitter<any>();

  public isOpen = signal<boolean>(false);
  public openUpward = signal<boolean>(false);
  public optionsSignal = signal<CustomSelectOption[]>([]);
  public valueSignal = signal<any>(undefined);
  public searchQuery = signal<string>('');

  public hasGroups = computed<boolean>(() => {
    return this.optionsSignal().some(o => !!o.group);
  });

  public filteredOptions = computed<CustomSelectOption[]>(() => {
    const q = this.searchQuery().trim().toLowerCase();
    const opts = this.optionsSignal();
    if (!q) return opts;
    return opts.filter(o =>
      o.label.toLowerCase().includes(q) ||
      (o.desc && o.desc.toLowerCase().includes(q)) ||
      (o.group && o.group.toLowerCase().includes(q))
    );
  });

  public filteredGroupedOptions = computed<GroupedSelectOption[]>(() => {
    const opts = this.filteredOptions();
    const map = new Map<string, CustomSelectOption[]>();

    for (const opt of opts) {
      const g = opt.group || 'Other';
      if (!map.has(g)) {
        map.set(g, []);
      }
      map.get(g)!.push(opt);
    }

    const groups: GroupedSelectOption[] = [];
    for (const [groupName, options] of map.entries()) {
      groups.push({ groupName, options });
    }
    return groups;
  });

  public selectedOption = computed<CustomSelectOption | undefined>(() => {
    const val = this.valueSignal();
    const opts = this.optionsSignal();
    return opts.find(o => o.value === val);
  });

  public selectedLabel = computed<string>(() => {
    const opt = this.selectedOption();
    if (!opt) {
      return this.placeholder || 'Select an option...';
    }
    return opt.label;
  });

  constructor(private elementRef: ElementRef) {}

  ngOnInit(): void {
    this.optionsSignal.set(this.options || []);
    this.valueSignal.set(this.value);

    if (typeof window !== 'undefined') {
      window.addEventListener('akaal-dropdown-open', this.onOtherDropdownOpen);
    }
  }

  ngOnDestroy(): void {
    if (typeof window !== 'undefined') {
      window.removeEventListener('akaal-dropdown-open', this.onOtherDropdownOpen);
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['options']) {
      this.optionsSignal.set(changes['options'].currentValue || []);
    }
    if (changes['value']) {
      this.valueSignal.set(changes['value'].currentValue);
    }
  }

  public isSelected(optValue: any): boolean {
    return this.valueSignal() === optValue;
  }

  public toggleOpen(event: MouseEvent): void {
    event.stopPropagation();
    if (!this.disabled) {
      const nextState = !this.isOpen();
      if (nextState) {
        this.searchQuery.set('');
        if (typeof window !== 'undefined') {
          const rect = this.elementRef.nativeElement.getBoundingClientRect();
          const spaceBelow = window.innerHeight - rect.bottom;
          const spaceAbove = rect.top;
          this.openUpward.set(spaceBelow < 280 && spaceAbove > spaceBelow);
          window.dispatchEvent(new CustomEvent('akaal-dropdown-open', { detail: this }));
        }
      }
      this.isOpen.set(nextState);
    }
  }

  private onOtherDropdownOpen = (e: Event) => {
    const customEvent = e as CustomEvent;
    if (customEvent.detail !== this) {
      this.isOpen.set(false);
    }
  };

  public selectOption(val: any, event: MouseEvent): void {
    event.stopPropagation();
    this.value = val;
    this.valueSignal.set(val);
    this.valueChange.emit(val);
    this.isOpen.set(false);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isOpen.set(false);
    }
  }
}
