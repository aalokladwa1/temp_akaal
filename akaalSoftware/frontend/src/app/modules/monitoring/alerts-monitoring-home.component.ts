/**
 * AKAAL Monitoring — Part 4 of 4: Alerts Monitoring Home Component
 * Root container for Alerts & Incidents workspace, coordinating route parameters,
 * the contextual alerts header, stable underline tab navigation, and the 6 investigation tabs.
 */

import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';

import { AlertsMonitoringService } from './services/alerts-monitoring.service';
import { AlertsTabKey } from './models/alerts-monitoring.models';

import { AlertsHeaderComponent } from './components/alerts-header.component';
import { AlertsNavComponent } from './components/alerts-nav.component';

import { AlertsActiveTabComponent } from './components/alerts-tabs/alerts-active-tab.component';
import { AlertsEvaluationTabComponent } from './components/alerts-tabs/alerts-evaluation-tab.component';
import { AlertsIncidentsTabComponent } from './components/alerts-tabs/alerts-incidents-tab.component';
import { AlertsCorrelationTabComponent } from './components/alerts-tabs/alerts-correlation-tab.component';
import { AlertsNotificationsTabComponent } from './components/alerts-tabs/alerts-notifications-tab.component';
import { AlertsTimelineTabComponent } from './components/alerts-tabs/alerts-timeline-tab.component';

@Component({
  selector: 'app-alerts-monitoring-home',
  standalone: true,
  imports: [
    CommonModule,
    AlertsHeaderComponent,
    AlertsNavComponent,
    AlertsActiveTabComponent,
    AlertsEvaluationTabComponent,
    AlertsIncidentsTabComponent,
    AlertsCorrelationTabComponent,
    AlertsNotificationsTabComponent,
    AlertsTimelineTabComponent
  ],
  template: `
    <div class="flex flex-col gap-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Contextual Alerts Header -->
      <app-alerts-header></app-alerts-header>

      <!-- 2. Stable Rectangular Underline Navigation Bar (NO pills, NO capsules) -->
      <app-alerts-nav></app-alerts-nav>

      <!-- 3. Active Alerts & Incidents Workspace -->
      @switch (ams.selectedTab()) {
        @case ('active') {
          <app-alerts-active-tab></app-alerts-active-tab>
        }
        @case ('evaluation') {
          <app-alerts-evaluation-tab></app-alerts-evaluation-tab>
        }
        @case ('incidents') {
          <app-alerts-incidents-tab></app-alerts-incidents-tab>
        }
        @case ('correlation') {
          <app-alerts-correlation-tab></app-alerts-correlation-tab>
        }
        @case ('notifications') {
          <app-alerts-notifications-tab></app-alerts-notifications-tab>
        }
        @case ('timeline') {
          <app-alerts-timeline-tab></app-alerts-timeline-tab>
        }
        @default {
          <app-alerts-active-tab></app-alerts-active-tab>
        }
      }

    </div>
  `
})
export class AlertsMonitoringHomeComponent implements OnInit, OnDestroy {
  public ams = inject(AlertsMonitoringService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private sub?: Subscription;

  ngOnInit(): void {
    this.sub = this.route.params.subscribe(params => {
      const tab = params['tab'] as AlertsTabKey;
      const validTabs: AlertsTabKey[] = [
        'active',
        'evaluation',
        'incidents',
        'correlation',
        'notifications',
        'timeline'
      ];

      if (tab && validTabs.includes(tab)) {
        this.ams.selectTab(tab);
      } else if (!tab) {
        // If on /monitoring/incidents alias
        if (this.router.url.includes('/monitoring/incidents')) {
          this.ams.selectTab('incidents');
        } else {
          this.ams.selectTab('active');
        }
      }

      // Check for alert ID or incident ID param
      const id = params['id'];
      if (id) {
        if (id.startsWith('INC-') || id.startsWith('inc-')) {
          this.ams.selectIncident(id);
          this.ams.selectTab('incidents');
        } else if (id.startsWith('alt-') || id.startsWith('ALT-')) {
          this.ams.selectAlert(id);
          this.ams.selectTab('active');
        }
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
