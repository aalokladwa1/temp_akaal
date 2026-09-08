import { Routes } from '@angular/router';
import { DashboardComponent } from './modules/dashboard/dashboard.component';
import { MigrationPortfolioComponent } from './modules/migration/portfolio/migration-portfolio.component';
import { CreateMigrationWizardComponent } from './modules/migration/create/create-migration-wizard.component';
import { ProjectsComponent } from './modules/migration/projects/projects.component';
import { CreateInitiativeComponent } from './modules/migration/projects/create/create-initiative.component';
import { InitiativeWorkspaceComponent } from './modules/migration/projects/workspace/initiative-workspace.component';
import { CreateProjectComponent } from './modules/migration/projects/create-project/create-project.component';
import { ProjectWorkspaceComponent } from './modules/migration/projects/project-workspace/project-workspace.component';
import { ConnectionsComponent } from './modules/migration/connections/connections.component';
import { ConnectionsHomeComponent } from './modules/connections/connections-home.component';
import { CreateConnectionWizardComponent } from './modules/connections/create-connection/create-connection-wizard.component';
import { ConnectionWorkspaceComponent } from './modules/connections/workspace/connection-workspace.component';
import { GlobalHistoryComponent } from './modules/migration/history/global-history.component';
import { TemplateBrowserComponent } from './modules/migration/templates/template-browser.component';
import { MigrationWorkspaceComponent } from './modules/migration/workspace/migration-workspace.component';
import { CockpitComponent } from './modules/migration/cockpit/cockpit.component';
import { ValidationPortfolioComponent } from './modules/validation/validation-portfolio.component';
import { NewValidationWizardComponent } from './modules/validation/create/new-validation-wizard.component';
import { ValidationWorkstationComponent } from './modules/validation/workstation/validation-workstation.component';
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
  { path: 'validation/:validationId', component: ValidationWorkstationComponent },
  { path: 'migration/validation', component: ValidationPortfolioComponent },
  { path: 'migration/validation/new', component: NewValidationWizardComponent },
  { path: 'migration/validation/new/:step', component: NewValidationWizardComponent },
  { path: 'migration/validation/:validationId', component: ValidationWorkstationComponent },

  // Connections Inventory, Creation & Workspace (Part A + Part B + Part C)
  { path: 'connections', component: ConnectionsHomeComponent },
  { path: 'connections/new', component: CreateConnectionWizardComponent },
  { path: 'connections/new/:step', component: CreateConnectionWizardComponent },
  { path: 'connections/:connectionId', component: ConnectionWorkspaceComponent },
  { path: 'connections/:connectionId/:tab', component: ConnectionWorkspaceComponent },

  // Migration Operations (2.1 to 2.8)
  { path: 'migration', component: MigrationPortfolioComponent },
  { path: 'migration/portfolio', component: MigrationPortfolioComponent },
  { path: 'migration/create', component: CreateMigrationWizardComponent },
  
  // Projects & Initiatives (Submodule of Migration)
  { path: 'migration/projects', component: ProjectsComponent },
  { path: 'migration/projects/new', component: CreateProjectComponent },
  { path: 'migration/projects/:projectId', component: ProjectWorkspaceComponent },
  { path: 'migration/projects/:projectId/:tab', component: ProjectWorkspaceComponent },
  { path: 'migration/initiatives', component: ProjectsComponent },
  { path: 'migration/initiatives/new', component: CreateInitiativeComponent },
  { path: 'migration/initiatives/:initiativeId', component: InitiativeWorkspaceComponent },
  { path: 'migration/initiatives/:initiativeId/:tab', component: InitiativeWorkspaceComponent },
  { path: 'projects', redirectTo: 'migration/projects', pathMatch: 'full' },
  { path: 'projects/new', redirectTo: 'migration/projects/new', pathMatch: 'full' },
  { path: 'projects/:projectId', redirectTo: 'migration/projects/:projectId', pathMatch: 'full' },
  { path: 'initiatives', redirectTo: 'migration/initiatives', pathMatch: 'full' },
  { path: 'initiatives/new', redirectTo: 'migration/initiatives/new', pathMatch: 'full' },
  { path: 'initiatives/:initiativeId', redirectTo: 'migration/initiatives/:initiativeId', pathMatch: 'full' },
  { path: 'migration/connections', component: ConnectionsHomeComponent },
  { path: 'migration/connections/new', component: CreateConnectionWizardComponent },
  { path: 'migration/connections/new/:step', component: CreateConnectionWizardComponent },
  { path: 'migration/connections/:connectionId', component: ConnectionWorkspaceComponent },
  { path: 'migration/connections/:connectionId/:tab', component: ConnectionWorkspaceComponent },
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
