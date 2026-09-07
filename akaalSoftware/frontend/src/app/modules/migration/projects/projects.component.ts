import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { ProjectsService } from './projects.service';
import { ProjectsHeaderComponent } from './components/projects-header.component';
import { ProjectsAttentionComponent } from './components/projects-attention.component';
import { ProjectsNavBarComponent, ProjectsTabType } from './components/projects-nav-bar.component';
import { PortfolioHomeComponent } from './components/portfolio-home.component';
import { ProjectDiscoveryComponent } from './components/project-discovery.component';
import { InitiativeDiscoveryComponent } from './components/initiative-discovery.component';

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [
    CommonModule,
    ProjectsHeaderComponent,
    ProjectsAttentionComponent,
    ProjectsNavBarComponent,
    PortfolioHomeComponent,
    ProjectDiscoveryComponent,
    InitiativeDiscoveryComponent
  ],
  template: `
    <div class="flex flex-col gap-6 lg:gap-7 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- 1. Header (Title, Subtitle, Context Breadcrumb, Actions) -->
      <app-projects-header></app-projects-header>

      <!-- 2. Attention Projection (Actionable alerts banner if present) -->
      <app-projects-attention></app-projects-attention>

      <!-- 3. Navigation Bar (Segmented GDS Tab Slider) -->
      <app-projects-nav-bar
        [activeTab]="activeTab()"
        (tabChange)="onTabChange($event)">
      </app-projects-nav-bar>

      <!-- 4. Active Module Surface -->
      @switch (activeTab()) {
        @case ('portfolio') {
          <app-portfolio-home (navigateTab)="onTabChange($event)"></app-portfolio-home>
        }
        @case ('projects') {
          <app-project-discovery></app-project-discovery>
        }
        @case ('initiatives') {
          <app-initiative-discovery></app-initiative-discovery>
        }
      }

    </div>
  `
})
export class ProjectsComponent implements OnInit, OnDestroy {
  public ps = inject(ProjectsService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  public activeTab = signal<ProjectsTabType>('portfolio');
  private sub?: Subscription;

  public ngOnInit(): void {
    // Synchronize route and query parameters with active tab
    this.sub = this.route.url.subscribe(() => {
      const url = this.router.url;
      if (url.includes('/initiatives')) {
        this.activeTab.set('initiatives');
      } else if (url.includes('/projects/list') || url.includes('tab=projects')) {
        this.activeTab.set('projects');
      } else if (url.includes('tab=initiatives')) {
        this.activeTab.set('initiatives');
      } else {
        // Default to portfolio if on /migration/projects
        this.activeTab.set('portfolio');
      }
    });
  }

  public ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  public onTabChange(tab: ProjectsTabType): void {
    this.activeTab.set(tab);
    if (tab === 'initiatives') {
      this.router.navigate([], { relativeTo: this.route, queryParams: { tab: 'initiatives' }, queryParamsHandling: 'merge' });
    } else if (tab === 'projects') {
      this.router.navigate([], { relativeTo: this.route, queryParams: { tab: 'projects' }, queryParamsHandling: 'merge' });
    } else {
      this.router.navigate([], { relativeTo: this.route, queryParams: { tab: null }, queryParamsHandling: 'merge' });
    }
  }
}
