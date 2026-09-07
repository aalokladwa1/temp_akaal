import { Routes } from '@angular/router';
import { DashboardComponent } from './modules/dashboard/dashboard.component';
import { MigrationPortfolioComponent } from './modules/migration/portfolio/migration-portfolio.component';
import { CreateMigrationWizardComponent } from './modules/migration/create/create-migration-wizard.component';
import { ProjectsComponent } from './modules/migration/projects/projects.component';
import { ConnectionsComponent } from './modules/migration/connections/connections.component';
import { GlobalHistoryComponent } from './modules/migration/history/global-history.component';
import { TemplateBrowserComponent } from './modules/migration/templates/template-browser.component';
import { MigrationWorkspaceComponent } from './modules/migration/workspace/migration-workspace.component';
import { CockpitComponent } from './modules/migration/cockpit/cockpit.component';
import { ValidationPortfolioComponent } from './modules/validation/validation-portfolio.component';
import { NewValidationWizardComponent } from './modules/validation/create/new-validation-wizard.component';
import { ValidationMissionControlComponent } from './modules/validation/mission-control/validation-mission-control.component';
import { MonitoringLandingComponent } from './modules/placeholders/monitoring-landing.component';
import { ReportsLandingComponent } from './modules/placeholders/reports-landing.component';
import { AdminLandingComponent } from './modules/placeholders/admin-landing.component';
import { SettingsLandingComponent } from './modules/placeholders/settings-landing.component';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },

  // Live Execution Cockpit / Mission Control
  { path: 'cockpit', component: CockpitComponent },
  { path: 'cockpit/:migrationId', component: CockpitComponent },
  { path: 'migration/cockpit', component: CockpitComponent },
  { path: 'migration/cockpit/:migrationId', component: CockpitComponent },

  // Validation Operations (M8 Data Synchronization Assurance)
  { path: 'validation', component: ValidationPortfolioComponent },
  { path: 'validation/new', component: NewValidationWizardComponent },
  { path: 'validation/new/:step', component: NewValidationWizardComponent },
  { path: 'validation/:validationId', component: ValidationMissionControlComponent },
  { path: 'migration/validation', component: ValidationPortfolioComponent },
  { path: 'migration/validation/new', component: NewValidationWizardComponent },
  { path: 'migration/validation/new/:step', component: NewValidationWizardComponent },
  { path: 'migration/validation/:validationId', component: ValidationMissionControlComponent },

  // Migration Operations (2.1 to 2.8)
  { path: 'migration', component: MigrationPortfolioComponent },
  { path: 'migration/portfolio', component: MigrationPortfolioComponent },
  { path: 'migration/create', component: CreateMigrationWizardComponent },
  { path: 'migration/projects', component: ProjectsComponent },
  { path: 'migration/projects/:projectId', component: ProjectsComponent },
  { path: 'migration/connections', component: ConnectionsComponent },
  { path: 'migration/history', component: GlobalHistoryComponent },
  { path: 'migration/templates', component: TemplateBrowserComponent },
  { path: 'migration/:migrationId', component: CockpitComponent },
  { path: 'migration/workspace/:migrationId', component: CockpitComponent },
  { path: 'migration/workspace/:migrationId/:tab', component: CockpitComponent },

  // Placeholder Modules
  { path: 'monitoring', component: MonitoringLandingComponent },
  { path: 'reports', component: ReportsLandingComponent },
  { path: 'administration', component: AdminLandingComponent },
  { path: 'settings', component: SettingsLandingComponent },

  { path: '**', redirectTo: 'dashboard' }
];
