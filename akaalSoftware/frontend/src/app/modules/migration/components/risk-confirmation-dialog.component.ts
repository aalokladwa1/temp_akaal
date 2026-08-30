import { Component, Input, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DialogModule } from 'primeng/dialog';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

export type ConfirmationTier =
  | 'NORMAL'
  | 'IMPORTANT'
  | 'DESTRUCTIVE'
  | 'GOVERNED'
  | 'INVALID';

@Component({
  selector: 'app-risk-confirmation-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, DialogModule, LucideIconComponent],
  template: `
    <p-dialog
      [(visible)]="isOpen"
      [modal]="true"
      [closable]="true"
      [draggable]="false"
      [resizable]="false"
      [style]="{ width: '90vw', maxWidth: '520px' }"
      (onHide)="cancel.emit()">
      
      <ng-template #header>
        <div class="flex items-center gap-3">
          <div
            class="w-9 h-9 rounded-xl flex items-center justify-center"
            [class.bg-blue-50]="tier === 'NORMAL'"
            [class.text-blue-600]="tier === 'NORMAL'"
            [class.bg-amber-50]="tier === 'IMPORTANT' || tier === 'GOVERNED'"
            [class.text-amber-600]="tier === 'IMPORTANT' || tier === 'GOVERNED'"
            [class.bg-rose-50]="tier === 'DESTRUCTIVE' || tier === 'INVALID'"
            [class.text-rose-600]="tier === 'DESTRUCTIVE' || tier === 'INVALID'">
            @switch (tier) {
              @case ('NORMAL') { <app-lucide-icon name="info" [size]="18"></app-lucide-icon> }
              @case ('IMPORTANT') { <app-lucide-icon name="triangle-alert" [size]="18"></app-lucide-icon> }
              @case ('GOVERNED') { <app-lucide-icon name="lock" [size]="18"></app-lucide-icon> }
              @case ('DESTRUCTIVE') { <app-lucide-icon name="shield-alert" [size]="18"></app-lucide-icon> }
              @case ('INVALID') { <app-lucide-icon name="circle-alert" [size]="18"></app-lucide-icon> }
            }
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 leading-snug">{{ title }}</h3>
            <span class="text-[11px] font-bold tracking-wider uppercase"
              [class.text-blue-600]="tier === 'NORMAL'"
              [class.text-amber-600]="tier === 'IMPORTANT' || tier === 'GOVERNED'"
              [class.text-rose-600]="tier === 'DESTRUCTIVE' || tier === 'INVALID'">
              {{ tier }} CONFIRMATION
            </span>
          </div>
        </div>
      </ng-template>

      <div class="flex flex-col gap-4 pt-2">
        <p class="text-xs text-slate-700 font-medium leading-relaxed">{{ description }}</p>

        @if (impactDetails.length > 0) {
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1.5 text-xs">
            <span class="font-bold text-slate-800">Operational Impacts:</span>
            <ul class="list-disc pl-4 space-y-1 text-slate-600">
              @for (imp of impactDetails; track imp) {
                <li>{{ imp }}</li>
              }
            </ul>
          </div>
        }

        @if (requiredConfirmationText) {
          <div class="flex flex-col gap-1.5 pt-1">
            <label class="text-xs font-semibold text-slate-800">
              Type <strong class="font-mono text-rose-700">{{ requiredConfirmationText }}</strong> to proceed:
            </label>
            <input
              type="text"
              [(ngModel)]="userInputText"
              [placeholder]="requiredConfirmationText"
              class="px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 font-mono text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-rose-500/20" />
          </div>
        }
      </div>

      <ng-template #footer>
        <div class="flex items-center justify-end gap-2.5 pt-2">
          <button
            type="button"
            (click)="cancel.emit()"
            class="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors cursor-pointer">
            Cancel
          </button>

          <button
            type="button"
            [disabled]="isConfirmDisabled()"
            (click)="confirm.emit()"
            class="px-4 py-2 rounded-xl text-white text-xs font-bold transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-xs"
            [class.bg-blue-600]="tier === 'NORMAL'"
            [class.hover:bg-blue-700]="tier === 'NORMAL'"
            [class.bg-amber-600]="tier === 'IMPORTANT' || tier === 'GOVERNED'"
            [class.hover:bg-amber-700]="tier === 'IMPORTANT' || tier === 'GOVERNED'"
            [class.bg-rose-600]="tier === 'DESTRUCTIVE'"
            [class.hover:bg-rose-700]="tier === 'DESTRUCTIVE'">
            {{ confirmLabel }}
          </button>
        </div>
      </ng-template>

    </p-dialog>
  `
})
export class RiskConfirmationDialogComponent {
  @Input() isOpen = false;
  @Input() tier: ConfirmationTier = 'NORMAL';
  @Input() title = 'Confirm Operation';
  @Input() description = '';
  @Input() impactDetails: string[] = [];
  @Input() confirmLabel = 'Confirm';
  @Input() requiredConfirmationText?: string;

  @Output() confirm = new EventEmitter<void>();
  @Output() cancel = new EventEmitter<void>();

  public userInputText = '';

  public isConfirmDisabled(): boolean {
    if (this.tier === 'INVALID') return true;
    if (this.requiredConfirmationText) {
      return this.userInputText.trim() !== this.requiredConfirmationText;
    }
    return false;
  }
}
