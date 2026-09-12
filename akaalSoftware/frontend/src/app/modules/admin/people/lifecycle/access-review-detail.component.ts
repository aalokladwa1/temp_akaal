import { Component, inject, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-access-review-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150" *ngIf="review(); else notFound">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/people/access-reviews" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Access Reviews
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">{{ review()?.name }}</h1>
            <span class="rounded px-2 py-0.5 text-[11px] font-semibold bg-amber-50 text-amber-700">
              {{ review()?.status }}
            </span>
          </div>
          <p class="text-sm font-medium text-slate-600 max-w-3xl">
            Lead Reviewer: {{ review()?.reviewerName }} ({{ review()?.reviewerEmail }})
          </p>
        </div>
      </div>

      <!-- Details -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-white border border-slate-200 rounded-xl p-6 flex flex-col gap-4 shadow-2xs md:col-span-2">
          <h2 class="text-base font-bold text-slate-900 font-heading border-b border-slate-100 pb-3">Campaign Overview</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Scope Target</span>
              <span class="font-bold text-slate-900">{{ review()?.scopeName }} ({{ review()?.scopeType }})</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Deadline</span>
              <span class="font-bold text-slate-900">{{ review()?.deadline | date:'mediumDate' }}</span>
            </div>
          </div>
        </div>
      </div>

    </div>
    <ng-template #notFound>
      <div class="p-8 text-center text-slate-500 text-sm">
        Review campaign not found. <a routerLink="/administration/people/access-reviews" class="text-blue-600 underline">Back</a>
      </div>
    </ng-template>
  `
})
export class AccessReviewDetailComponent {
  private route = inject(ActivatedRoute);
  private peopleService = inject(PeopleService);

  public rId = signal<string>(this.route.snapshot.paramMap.get('id') || '');
  public review = computed(() => this.peopleService.accessReviews().find(r => r.id === this.rId()));
}