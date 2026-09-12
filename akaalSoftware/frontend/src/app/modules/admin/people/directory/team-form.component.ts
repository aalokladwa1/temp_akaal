import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PeopleService } from '../../services/people.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { AdminTeam } from '../../models/people.models';

@Component({
  selector: 'app-team-form',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans py-4 pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Button -->
      <div class="flex items-center justify-between gap-4">
        <a routerLink="/administration/people/teams" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
          <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
          Back to Teams
        </a>
      </div>

      <!-- Header -->
      <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">
            {{ isEditMode ? 'Edit Team Unit' : 'Create Team Unit' }}
          </h1>
          <p class="text-sm font-medium text-slate-600 max-w-2xl">
            Configure team properties, ownership lead, and organizational bindings.
          </p>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs w-full">
        <form (ngSubmit)="saveTeam()" class="flex flex-col gap-5 text-xs">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Team Name *</label>
              <input type="text" [(ngModel)]="formData.name" name="name" required placeholder="e.g. Migration Core Squad" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Team Code *</label>
              <input type="text" [(ngModel)]="formData.code" name="code" required placeholder="e.g. TEAM-MIG-CORE" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="font-semibold text-slate-700">Description</label>
            <textarea [(ngModel)]="formData.description" name="description" rows="3" placeholder="Describe the team responsibilities..." class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white"></textarea>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Lead Owner Name</label>
              <input type="text" [(ngModel)]="formData.leadOwnerName" name="leadOwnerName" placeholder="e.g. Aalok Ladwa" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-700">Lead Owner Email</label>
              <input type="email" [(ngModel)]="formData.leadOwnerEmail" name="leadOwnerEmail" placeholder="e.g. aalok.ladwa@akaaltech.internal" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:border-blue-500 focus:bg-white" />
            </div>
          </div>

          <div class="flex items-center gap-3 pt-4 border-t border-slate-100">
            <button type="submit" class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors shadow-2xs cursor-pointer">
              {{ isEditMode ? 'Update Team' : 'Create Team' }}
            </button>
            <a routerLink="/administration/people/teams" class="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-lg">
              Cancel
            </a>
          </div>
        </form>
      </div>

    </div>
  `
})
export class TeamFormComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private peopleService = inject(PeopleService);

  public isEditMode = false;
  public teamId = '';

  public formData: Partial<AdminTeam> = {
    name: '',
    code: '',
    description: '',
    leadOwnerName: 'Aalok Ladwa',
    leadOwnerEmail: 'aalok.ladwa@akaaltech.internal',
    orgId: 'org-global-corp',
    orgName: 'Akaal Corporate Global',
    status: 'ACTIVE'
  };

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode = true;
      this.teamId = id;
      const found = this.peopleService.teams().find(t => t.id === id);
      if (found) this.formData = { ...found };
    }
  }

  public saveTeam(): void {
    if (this.isEditMode) {
      this.peopleService.updateTeam(this.teamId, this.formData);
      this.router.navigate(['/administration/people/teams', this.teamId]);
    } else {
      const created = this.peopleService.createTeam(this.formData);
      this.router.navigate(['/administration/people/teams', created.id]);
    }
  }
}