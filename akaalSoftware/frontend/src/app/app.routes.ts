import { Routes } from '@angular/router';
import { DashboardComponent } from './modules/dashboard/dashboard.component';
import { MigrationPortfolioComponent } from './modules/migration/portfolio/migration-portfolio.component';
import { CreateMigrationWizardComponent } from './modules/migration/create/create-migration-wizard.component';
import { ProjectsComponent } from './modules/migration/projects/projects.component';
import { CreateInitiativeComponent } from './modules/migration/projects/create/create-initiative.component';
import { InitiativeWorkspaceComponent } from './modules/migration/projects/workspace/initiative-workspace.component';
import { CreateProjectComponent } from './modules/migration/projects/create-project/create-project.component';
import { ProjectWorkspaceComponent } from './modules/migration/projects/project-workspace/project-workspace.component';
import { ConnectionsHomeComponent } from './modules/connections/connections-home.component';
import { CreateConnectionWizardComponent } from './modules/connections/create-connection/create-connection-wizard.component';
import { ConnectionWorkspaceComponent } from './modules/connections/workspace/connection-workspace.component';
import { HistoryHomeComponent } from './modules/migration/history/history-home.component';
import { HistoryWorkspaceComponent } from './modules/migration/history/history-workspace/history-workspace.component';
import { TemplatesHomeComponent } from './modules/migration/templates/templates-home.component';
import { CreateTemplateComponent } from './modules/migration/templates/create-template/create-template.component';
import { TemplateWorkspaceComponent } from './modules/migration/templates/template-workspace/template-workspace.component';
import { CockpitComponent } from './modules/migration/cockpit/cockpit.component';
import { ValidationPortfolioComponent } from './modules/validation/validation-portfolio.component';
import { NewValidationWizardComponent } from './modules/validation/create/new-validation-wizard.component';
import { ValidationWorkstationComponent } from './modules/validation/workstation/validation-workstation.component';
import { MonitoringHomeComponent } from './modules/monitoring/monitoring-home.component';
import { MigrationMonitoringHomeComponent } from './modules/monitoring/migration-monitoring-home.component';
import { PlatformMonitoringHomeComponent } from './modules/monitoring/platform-monitoring-home.component';
import { AlertsMonitoringHomeComponent } from './modules/monitoring/alerts-monitoring-home.component';
import { MonitoringLandingComponent } from './modules/placeholders/monitoring-landing.component';
import { ReportsHomeComponent } from './modules/reports/reports-home.component';
import { ReportsLibraryComponent } from './modules/reports/reports-library.component';
import { ReportsCertificationComponent } from './modules/reports/reports-certification.component';
import { ReportsEvidenceComponent } from './modules/reports/reports-evidence.component';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },

  // Live Execution Cockpit / Mission Control
  { path: 'cockpit', component: CockpitComponent },
  { path: 'cockpit/:migrationId', component: CockpitComponent },
  { path: 'migration/cockpit', component: CockpitComponent },
  { path: 'migration/cockpit/:migrationId', component: CockpitComponent },
  { path: 'migration/:migrationId', component: CockpitComponent },
  { path: 'migration/workspace/:migrationId', component: CockpitComponent },
  { path: 'migration/workspace/:migrationId/:tab', component: CockpitComponent },

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
  { path: 'migration/connections', component: ConnectionsHomeComponent },
  { path: 'migration/connections/new', component: CreateConnectionWizardComponent },
  { path: 'migration/connections/new/:step', component: CreateConnectionWizardComponent },
  { path: 'migration/connections/:connectionId', component: ConnectionWorkspaceComponent },
  { path: 'migration/connections/:connectionId/:tab', component: ConnectionWorkspaceComponent },

  // Migration Operations (2.1 to 2.8)
  { path: 'migration', component: MigrationPortfolioComponent },
  { path: 'migration/portfolio', component: MigrationPortfolioComponent },
  { path: 'migration/create', component: CreateMigrationWizardComponent },
  
  // Multi-Level Project Hierarchy (Portfolio -> Initiatives -> Projects)
  { path: 'migration/projects', component: ProjectsComponent },
  { path: 'migration/initiatives/new', component: CreateInitiativeComponent },
  { path: 'migration/initiatives/:initiativeId', component: InitiativeWorkspaceComponent },
  { path: 'migration/initiatives/:initiativeId/new-project', component: CreateProjectComponent },
  { path: 'migration/projects/:projectId', component: ProjectWorkspaceComponent },

  // Execution & Historical Audit
  { path: 'migration/history', component: HistoryHomeComponent },
  { path: 'migration/history/:runId', component: HistoryWorkspaceComponent },
  { path: 'migration/templates', component: TemplatesHomeComponent },
  { path: 'migration/templates/new', component: CreateTemplateComponent },
  { path: 'migration/templates/:templateId', component: TemplateWorkspaceComponent },

  // System Observability & Telemetry (Part A, B, C)
  { path: 'monitoring', component: MonitoringHomeComponent },
  { path: 'monitoring/overview', component: MonitoringHomeComponent },
  { path: 'monitoring/migration', component: MigrationMonitoringHomeComponent },
  { path: 'monitoring/platform', component: PlatformMonitoringHomeComponent },
  { path: 'monitoring/alerts', component: AlertsMonitoringHomeComponent },

  // Compliance, Certification & Artifacts (Part A, B, C)
  { path: 'reports', component: ReportsHomeComponent },
  { path: 'reports/overview', component: ReportsHomeComponent },
  { path: 'reports/library', component: ReportsLibraryComponent },
  { path: 'reports/certification', component: ReportsCertificationComponent },
  { path: 'reports/evidence', component: ReportsEvidenceComponent },

  // =========================================================================
  // MODULE 5: ADMINISTRATION & PLATFORM GOVERNANCE
  // =========================================================================
  { 
    path: 'administration', 
    loadComponent: () => import('./modules/admin/admin-home.component').then(m => m.AdminHomeComponent) 
  },

  // 5.1 ENTERPRISE ARCHITECTURE
  { 
    path: 'administration/enterprise', 
    loadComponent: () => import('./modules/admin/enterprise/enterprise-home.component').then(m => m.EnterpriseHomeComponent) 
  },
  { 
    path: 'administration/enterprise/settings', 
    loadComponent: () => import('./modules/admin/enterprise/settings/enterprise-settings.component').then(m => m.EnterpriseSettingsComponent) 
  },
  { 
    path: 'administration/enterprise/settings/edit', 
    loadComponent: () => import('./modules/admin/enterprise/settings/enterprise-settings-edit.component').then(m => m.EnterpriseSettingsEditComponent) 
  },

  // Enterprise Organizations
  { 
    path: 'administration/enterprise/organizations', 
    loadComponent: () => import('./modules/admin/enterprise/structure/orgs/org-list.component').then(m => m.OrgListComponent) 
  },
  { 
    path: 'administration/enterprise/organizations/create', 
    loadComponent: () => import('./modules/admin/enterprise/structure/orgs/org-create.component').then(m => m.OrgCreateComponent) 
  },
  { 
    path: 'administration/enterprise/organizations/:id', 
    loadComponent: () => import('./modules/admin/enterprise/structure/orgs/org-detail.component').then(m => m.OrgDetailComponent) 
  },
  { 
    path: 'administration/enterprise/organizations/:id/edit', 
    loadComponent: () => import('./modules/admin/enterprise/structure/orgs/org-edit.component').then(m => m.OrgEditComponent) 
  },
  { path: 'administration/enterprise/orgs', redirectTo: 'administration/enterprise/organizations', pathMatch: 'full' },

  // Enterprise Workspaces
  { 
    path: 'administration/enterprise/workspaces', 
    loadComponent: () => import('./modules/admin/enterprise/structure/workspaces/workspace-list.component').then(m => m.WorkspaceListComponent) 
  },
  { 
    path: 'administration/enterprise/workspaces/create', 
    loadComponent: () => import('./modules/admin/enterprise/structure/workspaces/workspace-create.component').then(m => m.WorkspaceCreateComponent) 
  },
  { 
    path: 'administration/enterprise/workspaces/:id', 
    loadComponent: () => import('./modules/admin/enterprise/structure/workspaces/workspace-detail.component').then(m => m.WorkspaceDetailComponent) 
  },
  { 
    path: 'administration/enterprise/workspaces/:id/edit', 
    loadComponent: () => import('./modules/admin/enterprise/structure/workspaces/workspace-edit.component').then(m => m.WorkspaceEditComponent) 
  },

  // Enterprise Environments
  { 
    path: 'administration/enterprise/environments', 
    loadComponent: () => import('./modules/admin/enterprise/structure/environments/env-list.component').then(m => m.EnvListComponent) 
  },
  { 
    path: 'administration/enterprise/environments/create', 
    loadComponent: () => import('./modules/admin/enterprise/structure/environments/env-create.component').then(m => m.EnvCreateComponent) 
  },
  { 
    path: 'administration/enterprise/environments/:id', 
    loadComponent: () => import('./modules/admin/enterprise/structure/environments/env-detail.component').then(m => m.EnvDetailComponent) 
  },
  { 
    path: 'administration/enterprise/environments/:id/edit', 
    loadComponent: () => import('./modules/admin/enterprise/structure/environments/env-edit.component').then(m => m.EnvEditComponent) 
  },

  // Enterprise Resource Boundaries
  { 
    path: 'administration/enterprise/boundaries', 
    loadComponent: () => import('./modules/admin/enterprise/governance/boundaries/boundary-list.component').then(m => m.BoundaryListComponent) 
  },
  { 
    path: 'administration/enterprise/boundaries/create', 
    loadComponent: () => import('./modules/admin/enterprise/governance/boundaries/boundary-create.component').then(m => m.BoundaryCreateComponent) 
  },
  { 
    path: 'administration/enterprise/boundaries/:id', 
    loadComponent: () => import('./modules/admin/enterprise/governance/boundaries/boundary-detail.component').then(m => m.BoundaryDetailComponent) 
  },
  { 
    path: 'administration/enterprise/boundaries/:id/edit', 
    loadComponent: () => import('./modules/admin/enterprise/governance/boundaries/boundary-edit.component').then(m => m.BoundaryEditComponent) 
  },

  // Enterprise Resource Ownership
  { 
    path: 'administration/enterprise/ownership', 
    loadComponent: () => import('./modules/admin/enterprise/governance/ownership/ownership-list.component').then(m => m.OwnershipListComponent) 
  },
  { 
    path: 'administration/enterprise/ownership/:id', 
    loadComponent: () => import('./modules/admin/enterprise/governance/ownership/ownership-detail.component').then(m => m.OwnershipDetailComponent) 
  },
  { 
    path: 'administration/enterprise/ownership/:id/transfer', 
    loadComponent: () => import('./modules/admin/enterprise/governance/ownership/ownership-transfer.component').then(m => m.OwnershipTransferComponent) 
  },

  // Enterprise Resource Quotas
  { 
    path: 'administration/enterprise/quotas', 
    loadComponent: () => import('./modules/admin/enterprise/governance/quotas/quota-list.component').then(m => m.QuotaListComponent) 
  },
  { 
    path: 'administration/enterprise/quotas/:id', 
    loadComponent: () => import('./modules/admin/enterprise/governance/quotas/quota-detail.component').then(m => m.QuotaDetailComponent) 
  },
  { 
    path: 'administration/enterprise/quotas/:id/edit', 
    loadComponent: () => import('./modules/admin/enterprise/governance/quotas/quota-edit.component').then(m => m.QuotaEditComponent) 
  },

  // Enterprise Metadata
  { 
    path: 'administration/enterprise/metadata', 
    loadComponent: () => import('./modules/admin/enterprise/governance/metadata/metadata-list.component').then(m => m.MetadataListComponent) 
  },
  { 
    path: 'administration/enterprise/metadata/create', 
    loadComponent: () => import('./modules/admin/enterprise/governance/metadata/metadata-create.component').then(m => m.MetadataCreateComponent) 
  },
  { 
    path: 'administration/enterprise/metadata/:id', 
    loadComponent: () => import('./modules/admin/enterprise/governance/metadata/metadata-detail.component').then(m => m.MetadataDetailComponent) 
  },
  { 
    path: 'administration/enterprise/metadata/:id/edit', 
    loadComponent: () => import('./modules/admin/enterprise/governance/metadata/metadata-edit.component').then(m => m.MetadataEditComponent) 
  },

  // 5.2 PEOPLE & ACCESS
  { 
    path: 'administration/people', 
    loadComponent: () => import('./modules/admin/people/people-home.component').then(m => m.PeopleHomeComponent) 
  },
  // Directory
  { 
    path: 'administration/people/users', 
    loadComponent: () => import('./modules/admin/people/directory/users-list.component').then(m => m.UsersListComponent) 
  },
  { 
    path: 'administration/people/users/new', 
    loadComponent: () => import('./modules/admin/people/directory/user-form.component').then(m => m.UserFormComponent) 
  },
  { 
    path: 'administration/people/users/:id', 
    loadComponent: () => import('./modules/admin/people/directory/user-detail.component').then(m => m.UserDetailComponent) 
  },
  { 
    path: 'administration/people/users/:id/edit', 
    loadComponent: () => import('./modules/admin/people/directory/user-form.component').then(m => m.UserFormComponent) 
  },
  { 
    path: 'administration/people/teams', 
    loadComponent: () => import('./modules/admin/people/directory/teams-list.component').then(m => m.TeamsListComponent) 
  },
  { 
    path: 'administration/people/teams/new', 
    loadComponent: () => import('./modules/admin/people/directory/team-form.component').then(m => m.TeamFormComponent) 
  },
  { 
    path: 'administration/people/teams/:id', 
    loadComponent: () => import('./modules/admin/people/directory/team-detail.component').then(m => m.TeamDetailComponent) 
  },
  { 
    path: 'administration/people/teams/:id/edit', 
    loadComponent: () => import('./modules/admin/people/directory/team-form.component').then(m => m.TeamFormComponent) 
  },
  { 
    path: 'administration/people/service-accounts', 
    loadComponent: () => import('./modules/admin/people/directory/service-accounts-list.component').then(m => m.ServiceAccountsListComponent) 
  },
  { 
    path: 'administration/people/service-accounts/new', 
    loadComponent: () => import('./modules/admin/people/directory/service-account-form.component').then(m => m.ServiceAccountFormComponent) 
  },
  { 
    path: 'administration/people/service-accounts/:id', 
    loadComponent: () => import('./modules/admin/people/directory/service-account-detail.component').then(m => m.ServiceAccountDetailComponent) 
  },
  { 
    path: 'administration/people/service-accounts/:id/edit', 
    loadComponent: () => import('./modules/admin/people/directory/service-account-form.component').then(m => m.ServiceAccountFormComponent) 
  },

  // Access Control
  { 
    path: 'administration/people/roles', 
    loadComponent: () => import('./modules/admin/people/access-control/roles-list.component').then(m => m.RolesListComponent) 
  },
  { 
    path: 'administration/people/roles/new', 
    loadComponent: () => import('./modules/admin/people/access-control/role-form.component').then(m => m.RoleFormComponent) 
  },
  { 
    path: 'administration/people/roles/:id', 
    loadComponent: () => import('./modules/admin/people/access-control/role-detail.component').then(m => m.RoleDetailComponent) 
  },
  { 
    path: 'administration/people/roles/:id/edit', 
    loadComponent: () => import('./modules/admin/people/access-control/role-form.component').then(m => m.RoleFormComponent) 
  },
  { 
    path: 'administration/people/assignments', 
    loadComponent: () => import('./modules/admin/people/access-control/assignments-list.component').then(m => m.AssignmentsListComponent) 
  },
  { 
    path: 'administration/people/assignments/new', 
    loadComponent: () => import('./modules/admin/people/access-control/assignment-form.component').then(m => m.AssignmentFormComponent) 
  },
  { 
    path: 'administration/people/conditional-access', 
    loadComponent: () => import('./modules/admin/people/access-control/conditional-access-list.component').then(m => m.ConditionalAccessListComponent) 
  },
  { 
    path: 'administration/people/conditional-access/new', 
    loadComponent: () => import('./modules/admin/people/access-control/conditional-access-form.component').then(m => m.ConditionalAccessFormComponent) 
  },
  { 
    path: 'administration/people/conditional-access/:id', 
    loadComponent: () => import('./modules/admin/people/access-control/conditional-access-detail.component').then(m => m.ConditionalAccessDetailComponent) 
  },
  { 
    path: 'administration/people/conditional-access/:id/edit', 
    loadComponent: () => import('./modules/admin/people/access-control/conditional-access-form.component').then(m => m.ConditionalAccessFormComponent) 
  },

  // Privileged Access
  { 
    path: 'administration/people/jit-access', 
    loadComponent: () => import('./modules/admin/people/privileged/jit-access-list.component').then(m => m.JitAccessListComponent) 
  },
  { 
    path: 'administration/people/jit-access/request', 
    loadComponent: () => import('./modules/admin/people/privileged/jit-request-form.component').then(m => m.JitRequestFormComponent) 
  },
  { 
    path: 'administration/people/jit-access/:id', 
    loadComponent: () => import('./modules/admin/people/privileged/jit-detail.component').then(m => m.JitDetailComponent) 
  },
  { 
    path: 'administration/people/access-conflicts', 
    loadComponent: () => import('./modules/admin/people/privileged/access-conflicts-list.component').then(m => m.AccessConflictsListComponent) 
  },
  { 
    path: 'administration/people/access-conflicts/:id', 
    loadComponent: () => import('./modules/admin/people/privileged/access-conflict-detail.component').then(m => m.AccessConflictDetailComponent) 
  },

  // Access Lifecycle
  { 
    path: 'administration/people/sessions', 
    loadComponent: () => import('./modules/admin/people/lifecycle/sessions-list.component').then(m => m.SessionsListComponent) 
  },
  { 
    path: 'administration/people/access-reviews', 
    loadComponent: () => import('./modules/admin/people/lifecycle/access-reviews-list.component').then(m => m.AccessReviewsListComponent) 
  },
  { 
    path: 'administration/people/access-reviews/new', 
    loadComponent: () => import('./modules/admin/people/lifecycle/access-review-form.component').then(m => m.AccessReviewFormComponent) 
  },
  { 
    path: 'administration/people/access-reviews/:id', 
    loadComponent: () => import('./modules/admin/people/lifecycle/access-review-detail.component').then(m => m.AccessReviewDetailComponent) 
  },

  // 5.3 GOVERNANCE CENTRE
  { 
    path: 'administration/governance-centre', 
    loadComponent: () => import('./modules/admin/governance/governance-home.component').then(m => m.GovernanceHomeComponent) 
  },
  // Policies & Simulation
  { 
    path: 'administration/governance-centre/policies', 
    loadComponent: () => import('./modules/admin/governance/policies/policies-list.component').then(m => m.PoliciesListComponent) 
  },
  { 
    path: 'administration/governance-centre/policies/new', 
    loadComponent: () => import('./modules/admin/governance/policies/policy-form.component').then(m => m.PolicyFormComponent) 
  },
  { 
    path: 'administration/governance-centre/policies/:id', 
    loadComponent: () => import('./modules/admin/governance/policies/policy-detail.component').then(m => m.PolicyDetailComponent) 
  },
  { 
    path: 'administration/governance-centre/policies/:id/edit', 
    loadComponent: () => import('./modules/admin/governance/policies/policy-form.component').then(m => m.PolicyFormComponent) 
  },
  { 
    path: 'administration/governance-centre/policy-simulation', 
    loadComponent: () => import('./modules/admin/governance/policies/policy-simulation.component').then(m => m.PolicySimulationComponent) 
  },

  // Approvals & Dual Control
  { 
    path: 'administration/governance-centre/approval-chains', 
    loadComponent: () => import('./modules/admin/governance/approvals/approval-chains-list.component').then(m => m.ApprovalChainsListComponent) 
  },
  { 
    path: 'administration/governance-centre/approval-chains/new', 
    loadComponent: () => import('./modules/admin/governance/approvals/approval-chain-form.component').then(m => m.ApprovalChainFormComponent) 
  },
  { 
    path: 'administration/governance-centre/approval-chains/:id', 
    loadComponent: () => import('./modules/admin/governance/approvals/approval-chain-detail.component').then(m => m.ApprovalChainDetailComponent) 
  },
  { 
    path: 'administration/governance-centre/approval-chains/:id/edit', 
    loadComponent: () => import('./modules/admin/governance/approvals/approval-chain-form.component').then(m => m.ApprovalChainFormComponent) 
  },
  { 
    path: 'administration/governance-centre/approver-groups', 
    loadComponent: () => import('./modules/admin/governance/approvals/approver-groups-list.component').then(m => m.ApproverGroupsListComponent) 
  },
  { 
    path: 'administration/governance-centre/approver-groups/new', 
    loadComponent: () => import('./modules/admin/governance/approvals/approver-group-form.component').then(m => m.ApproverGroupFormComponent) 
  },
  { 
    path: 'administration/governance-centre/approver-groups/:id', 
    loadComponent: () => import('./modules/admin/governance/approvals/approver-group-detail.component').then(m => m.ApproverGroupDetailComponent) 
  },
  { 
    path: 'administration/governance-centre/approver-groups/:id/edit', 
    loadComponent: () => import('./modules/admin/governance/approvals/approver-group-form.component').then(m => m.ApproverGroupFormComponent) 
  },
  { 
    path: 'administration/governance-centre/maker-checker', 
    loadComponent: () => import('./modules/admin/governance/approvals/maker-checker-list.component').then(m => m.MakerCheckerListComponent) 
  },

  // Privileged Governance
  { 
    path: 'administration/governance-centre/sod', 
    loadComponent: () => import('./modules/admin/governance/privileged/sod-list.component').then(m => m.SodListComponent) 
  },
  { 
    path: 'administration/governance-centre/sod/new', 
    loadComponent: () => import('./modules/admin/governance/privileged/sod-form.component').then(m => m.SodFormComponent) 
  },
  { 
    path: 'administration/governance-centre/sod/:id', 
    loadComponent: () => import('./modules/admin/governance/privileged/sod-detail.component').then(m => m.SodDetailComponent) 
  },
  { 
    path: 'administration/governance-centre/sod/:id/edit', 
    loadComponent: () => import('./modules/admin/governance/privileged/sod-form.component').then(m => m.SodFormComponent) 
  },
  { 
    path: 'administration/governance-centre/privileged-ops', 
    loadComponent: () => import('./modules/admin/governance/privileged/privileged-ops-list.component').then(m => m.PrivilegedOpsListComponent) 
  },
  { 
    path: 'administration/governance-centre/waivers', 
    loadComponent: () => import('./modules/admin/governance/privileged/waivers-list.component').then(m => m.WaiversListComponent) 
  },
  { 
    path: 'administration/governance-centre/waivers/new', 
    loadComponent: () => import('./modules/admin/governance/privileged/waiver-form.component').then(m => m.WaiverFormComponent) 
  },
  { 
    path: 'administration/governance-centre/break-glass', 
    loadComponent: () => import('./modules/admin/governance/privileged/break-glass-list.component').then(m => m.BreakGlassListComponent) 
  },

  // Governance History
  { 
    path: 'administration/governance-centre/history', 
    loadComponent: () => import('./modules/admin/governance/history/governance-history.component').then(m => m.GovernanceHistoryComponent) 
  },

  // 5.4 IDENTITY & SECURITY
  { 
    path: 'administration/identity', 
    loadComponent: () => import('./modules/admin/identity/identity-home.component').then(m => m.IdentityHomeComponent) 
  },
  // Auth
  { 
    path: 'administration/identity/auth', 
    loadComponent: () => import('./modules/admin/identity/auth/auth-home.component').then(m => m.AuthHomeComponent) 
  },
  { 
    path: 'administration/identity/auth/policies', 
    loadComponent: () => import('./modules/admin/identity/auth/auth-policies.component').then(m => m.AuthPoliciesComponent) 
  },
  { 
    path: 'administration/identity/auth/mfa', 
    loadComponent: () => import('./modules/admin/identity/auth/mfa.component').then(m => m.MfaComponent) 
  },
  { 
    path: 'administration/identity/auth/sso', 
    loadComponent: () => import('./modules/admin/identity/auth/sso-home.component').then(m => m.SsoHomeComponent) 
  },
  { 
    path: 'administration/identity/auth/sso/create', 
    loadComponent: () => import('./modules/admin/identity/auth/sso-create.component').then(m => m.SsoCreateComponent) 
  },
  // Directory & Federation
  { 
    path: 'administration/identity/directory', 
    loadComponent: () => import('./modules/admin/identity/directory/directory-home.component').then(m => m.DirectoryHomeComponent) 
  },
  { 
    path: 'administration/identity/directory/ldap', 
    loadComponent: () => import('./modules/admin/identity/directory/ldap.component').then(m => m.LdapComponent) 
  },
  { 
    path: 'administration/identity/directory/scim', 
    loadComponent: () => import('./modules/admin/identity/directory/scim.component').then(m => m.ScimComponent) 
  },
  { 
    path: 'administration/identity/directory/federation', 
    loadComponent: () => import('./modules/admin/identity/directory/federation.component').then(m => m.FederationComponent) 
  },
  // Workload Identity
  { 
    path: 'administration/identity/workload', 
    loadComponent: () => import('./modules/admin/identity/workload/workload-home.component').then(m => m.WorkloadHomeComponent) 
  },
  { 
    path: 'administration/identity/workload/services', 
    loadComponent: () => import('./modules/admin/identity/workload/workload-services.component').then(m => m.WorkloadServicesComponent) 
  },
  { 
    path: 'administration/identity/workload/spiffe', 
    loadComponent: () => import('./modules/admin/identity/workload/spiffe.component').then(m => m.SpiffeComponent) 
  },
  // Cryptography & Secrets
  { 
    path: 'administration/identity/crypto', 
    loadComponent: () => import('./modules/admin/identity/crypto/crypto-home.component').then(m => m.CryptoHomeComponent) 
  },
  { 
    path: 'administration/identity/crypto/certificates', 
    loadComponent: () => import('./modules/admin/identity/crypto/certificates.component').then(m => m.CertificatesComponent) 
  },
  { 
    path: 'administration/identity/crypto/vault', 
    loadComponent: () => import('./modules/admin/identity/crypto/vault.component').then(m => m.VaultComponent) 
  },
  { 
    path: 'administration/identity/crypto/kms', 
    loadComponent: () => import('./modules/admin/identity/crypto/kms.component').then(m => m.KmsComponent) 
  },
  { 
    path: 'administration/identity/crypto/rotation', 
    loadComponent: () => import('./modules/admin/identity/crypto/rotation.component').then(m => m.RotationComponent) 
  },

  // 5.5 TEMPLATE & CONFIGURATION LIBRARY
  { 
    path: 'administration/templates-library', 
    loadComponent: () => import('./modules/admin/templates-library/templates-config-home.component').then(m => m.TemplatesConfigHomeComponent) 
  },
  { 
    path: 'administration/templates-library/migration', 
    data: { family: 'MIGRATION_TEMPLATE' },
    loadComponent: () => import('./modules/admin/templates-library/family-list.component').then(m => m.FamilyListComponent) 
  },
  { 
    path: 'administration/templates-library/mapping', 
    data: { family: 'MAPPING_TEMPLATE' },
    loadComponent: () => import('./modules/admin/templates-library/family-list.component').then(m => m.FamilyListComponent) 
  },
  { 
    path: 'administration/templates-library/transformation', 
    data: { family: 'TRANSFORMATION_TEMPLATE' },
    loadComponent: () => import('./modules/admin/templates-library/family-list.component').then(m => m.FamilyListComponent) 
  },
  { 
    path: 'administration/templates-library/privacy', 
    data: { family: 'PRIVACY_POLICY' },
    loadComponent: () => import('./modules/admin/templates-library/family-list.component').then(m => m.FamilyListComponent) 
  },
  { 
    path: 'administration/templates-library/quality', 
    data: { family: 'DATA_QUALITY_POLICY' },
    loadComponent: () => import('./modules/admin/templates-library/family-list.component').then(m => m.FamilyListComponent) 
  },
  { 
    path: 'administration/templates-library/configuration', 
    data: { family: 'CONFIGURATION_PROFILE' },
    loadComponent: () => import('./modules/admin/templates-library/family-list.component').then(m => m.FamilyListComponent) 
  },
  { 
    path: 'administration/templates-library/create', 
    loadComponent: () => import('./modules/admin/templates-library/template-create.component').then(m => m.TemplateCreateComponent) 
  },
  { 
    path: 'administration/templates-library/asset/:id', 
    loadComponent: () => import('./modules/admin/templates-library/template-detail.component').then(m => m.TemplateDetailComponent) 
  },
  { 
    path: 'administration/templates-library/asset/:id/promote', 
    loadComponent: () => import('./modules/admin/templates-library/lifecycle/asset-promote.component').then(m => m.AssetPromoteComponent) 
  },
  { 
    path: 'administration/templates-library/import', 
    loadComponent: () => import('./modules/admin/templates-library/lifecycle/asset-import.component').then(m => m.AssetImportComponent) 
  },

  // 5.6 CONNECTOR & PLUGIN CENTER
  { 
    path: 'administration/connectors', 
    loadComponent: () => import('./modules/admin/connectors-plugins/connectors-plugins-home.component').then(m => m.ConnectorsPluginsHomeComponent) 
  },
  { 
    path: 'administration/connectors-plugins', 
    redirectTo: 'administration/connectors' 
  },
  { 
    path: 'administration/connectors/connectors-hub', 
    loadComponent: () => import('./modules/admin/connectors-plugins/connectors/connectors-hub.component').then(m => m.ConnectorsHubComponent) 
  },
  { 
    path: 'administration/connectors/registry', 
    loadComponent: () => import('./modules/admin/connectors-plugins/connectors/connector-registry.component').then(m => m.ConnectorRegistryComponent) 
  },
  { 
    path: 'administration/connectors/builtin', 
    loadComponent: () => import('./modules/admin/connectors-plugins/connectors/builtin-connectors.component').then(m => m.BuiltinConnectorsComponent) 
  },
  { 
    path: 'administration/connectors/external', 
    loadComponent: () => import('./modules/admin/connectors-plugins/connectors/external-connectors.component').then(m => m.ExternalConnectorsComponent) 
  },
  { 
    path: 'administration/connectors/external/register', 
    loadComponent: () => import('./modules/admin/connectors-plugins/connectors/external-register.component').then(m => m.ExternalRegisterComponent) 
  },
  { 
    path: 'administration/connectors/detail/:id', 
    loadComponent: () => import('./modules/admin/connectors-plugins/connectors/connector-detail.component').then(m => m.ConnectorDetailComponent) 
  },
  { 
    path: 'administration/connectors/intelligence-hub', 
    loadComponent: () => import('./modules/admin/connectors-plugins/intelligence/intelligence-hub.component').then(m => m.IntelligenceHubComponent) 
  },
  { 
    path: 'administration/connectors/capabilities', 
    loadComponent: () => import('./modules/admin/connectors-plugins/intelligence/capabilities-view.component').then(m => m.CapabilitiesViewComponent) 
  },
  { 
    path: 'administration/connectors/compatibility', 
    loadComponent: () => import('./modules/admin/connectors-plugins/intelligence/compatibility-view.component').then(m => m.CompatibilityViewComponent) 
  },
  { 
    path: 'administration/connectors/versions', 
    loadComponent: () => import('./modules/admin/connectors-plugins/intelligence/versions-view.component').then(m => m.VersionsViewComponent) 
  },
  { 
    path: 'administration/connectors/certification', 
    loadComponent: () => import('./modules/admin/connectors-plugins/intelligence/certification-view.component').then(m => m.CertificationViewComponent) 
  },
  { 
    path: 'administration/connectors/extensions-hub', 
    loadComponent: () => import('./modules/admin/connectors-plugins/extensions/extensions-hub.component').then(m => m.ExtensionsHubComponent) 
  },
  { 
    path: 'administration/connectors/plugins', 
    loadComponent: () => import('./modules/admin/connectors-plugins/extensions/plugins-list.component').then(m => m.PluginsListComponent) 
  },
  { 
    path: 'administration/connectors/plugins/detail/:id', 
    loadComponent: () => import('./modules/admin/connectors-plugins/extensions/plugin-detail.component').then(m => m.PluginDetailComponent) 
  },
  { 
    path: 'administration/connectors/plugins/security', 
    loadComponent: () => import('./modules/admin/connectors-plugins/extensions/plugin-security.component').then(m => m.PluginSecurityComponent) 
  },
  { 
    path: 'administration/connectors/sdk', 
    loadComponent: () => import('./modules/admin/connectors-plugins/extensions/sdk-config.component').then(m => m.SdkConfigComponent) 
  },

  // 5.7 CLOUD & INFRASTRUCTURE CONFIGURATION
  { 
    path: 'administration/infrastructure', 
    loadComponent: () => import('./modules/admin/infrastructure/infrastructure-home.component').then(m => m.InfrastructureHomeComponent) 
  },
  { 
    path: 'administration/cloud-infra', 
    redirectTo: 'administration/infrastructure' 
  },
  { 
    path: 'administration/infrastructure/cloud-hub', 
    loadComponent: () => import('./modules/admin/infrastructure/cloud/cloud-hub.component').then(m => m.CloudHubComponent) 
  },
  { 
    path: 'administration/infrastructure/cloud/environments', 
    loadComponent: () => import('./modules/admin/infrastructure/cloud/cloud-environments-list.component').then(m => m.CloudEnvironmentsListComponent) 
  },
  { 
    path: 'administration/infrastructure/cloud/environments/create', 
    loadComponent: () => import('./modules/admin/infrastructure/cloud/cloud-environment-create.component').then(m => m.CloudEnvironmentCreateComponent) 
  },
  { 
    path: 'administration/infrastructure/cloud/environments/detail/:id', 
    loadComponent: () => import('./modules/admin/infrastructure/cloud/cloud-environment-detail.component').then(m => m.CloudEnvironmentDetailComponent) 
  },
  { 
    path: 'administration/infrastructure/compute-hub', 
    loadComponent: () => import('./modules/admin/infrastructure/compute/compute-hub.component').then(m => m.ComputeHubComponent) 
  },
  { 
    path: 'administration/infrastructure/compute/kubernetes', 
    loadComponent: () => import('./modules/admin/infrastructure/compute/kubernetes-list.component').then(m => m.KubernetesListComponent) 
  },
  { 
    path: 'administration/infrastructure/compute/kubernetes/create', 
    loadComponent: () => import('./modules/admin/infrastructure/compute/kubernetes-create.component').then(m => m.KubernetesCreateComponent) 
  },
  { 
    path: 'administration/infrastructure/compute/sites', 
    loadComponent: () => import('./modules/admin/infrastructure/compute/sites-list.component').then(m => m.SitesListComponent) 
  },
  { 
    path: 'administration/infrastructure/compute/sites/create', 
    loadComponent: () => import('./modules/admin/infrastructure/compute/site-create.component').then(m => m.SiteCreateComponent) 
  },
  { 
    path: 'administration/infrastructure/connectivity-hub', 
    loadComponent: () => import('./modules/admin/infrastructure/connectivity/connectivity-hub.component').then(m => m.ConnectivityHubComponent) 
  },
  { 
    path: 'administration/infrastructure/connectivity/private', 
    loadComponent: () => import('./modules/admin/infrastructure/connectivity/private-connectivity-list.component').then(m => m.PrivateConnectivityListComponent) 
  },
  { 
    path: 'administration/infrastructure/connectivity/private/create', 
    loadComponent: () => import('./modules/admin/infrastructure/connectivity/private-connectivity-create.component').then(m => m.PrivateConnectivityCreateComponent) 
  },
  { 
    path: 'administration/infrastructure/connectivity/routing', 
    loadComponent: () => import('./modules/admin/infrastructure/connectivity/routing-list.component').then(m => m.RoutingListComponent) 
  },
  { 
    path: 'administration/infrastructure/connectivity/routing/create', 
    loadComponent: () => import('./modules/admin/infrastructure/connectivity/routing-create.component').then(m => m.RoutingCreateComponent) 
  },
  { 
    path: 'administration/infrastructure/connectivity/hybrid', 
    loadComponent: () => import('./modules/admin/infrastructure/connectivity/hybrid-environments.component').then(m => m.HybridEnvironmentsComponent) 
  },
  { 
    path: 'administration/infrastructure/placement-hub', 
    loadComponent: () => import('./modules/admin/infrastructure/placement/placement-hub.component').then(m => m.PlacementHubComponent) 
  },
  { 
    path: 'administration/infrastructure/placement/regions', 
    loadComponent: () => import('./modules/admin/infrastructure/placement/regions-list.component').then(m => m.RegionsListComponent) 
  },
  { 
    path: 'administration/infrastructure/placement/sovereignty', 
    loadComponent: () => import('./modules/admin/infrastructure/placement/sovereignty-policies.component').then(m => m.SovereigntyPoliciesComponent) 
  },
  { 
    path: 'administration/infrastructure/automation-hub', 
    loadComponent: () => import('./modules/admin/infrastructure/automation/automation-hub.component').then(m => m.AutomationHubComponent) 
  },
  { 
    path: 'administration/infrastructure/automation/iac', 
    loadComponent: () => import('./modules/admin/infrastructure/automation/iac-config.component').then(m => m.IacConfigComponent) 
  },
  { 
    path: 'administration/infrastructure/automation/gitops', 
    loadComponent: () => import('./modules/admin/infrastructure/automation/gitops-config.component').then(m => m.GitOpsConfigComponent) 
  },

  // 5.8 COMPLIANCE
  { 
    path: 'administration/compliance', 
    loadComponent: () => import('./modules/admin/compliance/compliance-home.component').then(m => m.ComplianceHomeComponent) 
  },
  { 
    path: 'administration/compliance/frameworks/catalog', 
    loadComponent: () => import('./modules/admin/compliance/frameworks/control-frameworks-list.component').then(m => m.ControlFrameworksListComponent) 
  },
  { 
    path: 'administration/compliance/frameworks/detail/:id', 
    loadComponent: () => import('./modules/admin/compliance/frameworks/framework-detail.component').then(m => m.FrameworkDetailComponent) 
  },
  { 
    path: 'administration/compliance/frameworks/views', 
    loadComponent: () => import('./modules/admin/compliance/frameworks/framework-views.component').then(m => m.FrameworkViewsComponent) 
  },
  { 
    path: 'administration/compliance/frameworks/custom', 
    loadComponent: () => import('./modules/admin/compliance/frameworks/custom-frameworks-list.component').then(m => m.CustomFrameworksListComponent) 
  },
  { 
    path: 'administration/compliance/frameworks/custom/create', 
    loadComponent: () => import('./modules/admin/compliance/frameworks/custom-framework-create.component').then(m => m.CustomFrameworkCreateComponent) 
  },
  { 
    path: 'administration/compliance/controls/mapping', 
    loadComponent: () => import('./modules/admin/compliance/controls/control-mapping-list.component').then(m => m.ControlMappingListComponent) 
  },
  { 
    path: 'administration/compliance/controls/exceptions', 
    loadComponent: () => import('./modules/admin/compliance/controls/exceptions-list.component').then(m => m.ExceptionsListComponent) 
  },
  { 
    path: 'administration/compliance/controls/exceptions/request', 
    loadComponent: () => import('./modules/admin/compliance/controls/exception-request.component').then(m => m.ExceptionRequestComponent) 
  },
  { 
    path: 'administration/compliance/evidence', 
    loadComponent: () => import('./modules/admin/compliance/evidence/compliance-evidence-list.component').then(m => m.ComplianceEvidenceListComponent) 
  },
  { 
    path: 'administration/compliance/evidence/detail/:id', 
    loadComponent: () => import('./modules/admin/compliance/evidence/compliance-evidence-detail.component').then(m => m.ComplianceEvidenceDetailComponent) 
  },

  // 5.9 AUDIT
  { 
    path: 'administration/audit', 
    loadComponent: () => import('./modules/admin/audit/audit-home.component').then(m => m.AuditHomeComponent) 
  },
  { 
    path: 'administration/audit/policies', 
    loadComponent: () => import('./modules/admin/audit/configuration/audit-policies-list.component').then(m => m.AuditPoliciesListComponent) 
  },
  { 
    path: 'administration/audit/policies/create', 
    loadComponent: () => import('./modules/admin/audit/configuration/audit-policy-create.component').then(m => m.AuditPolicyCreateComponent) 
  },
  { 
    path: 'administration/audit/policies/detail/:id', 
    loadComponent: () => import('./modules/admin/audit/configuration/audit-policy-detail.component').then(m => m.AuditPolicyDetailComponent) 
  },
  { 
    path: 'administration/audit/destinations', 
    loadComponent: () => import('./modules/admin/audit/configuration/audit-destinations-list.component').then(m => m.AuditDestinationsListComponent) 
  },
  { 
    path: 'administration/audit/destinations/create', 
    loadComponent: () => import('./modules/admin/audit/configuration/audit-destination-create.component').then(m => m.AuditDestinationCreateComponent) 
  },
  { 
    path: 'administration/audit/trail', 
    loadComponent: () => import('./modules/admin/audit/trail/audit-trail-list.component').then(m => m.AuditTrailListComponent) 
  },
  { 
    path: 'administration/audit/trail/detail/:id', 
    loadComponent: () => import('./modules/admin/audit/trail/audit-event-detail.component').then(m => m.AuditEventDetailComponent) 
  },
  { 
    path: 'administration/audit/retention', 
    loadComponent: () => import('./modules/admin/audit/governance/evidence-retention-list.component').then(m => m.EvidenceRetentionListComponent) 
  },
  { 
    path: 'administration/audit/legal-hold', 
    loadComponent: () => import('./modules/admin/audit/governance/legal-hold-list.component').then(m => m.LegalHoldListComponent) 
  },
  { 
    path: 'administration/audit/legal-hold/create', 
    loadComponent: () => import('./modules/admin/audit/governance/legal-hold-create.component').then(m => m.LegalHoldCreateComponent) 
  },
  { 
    path: 'administration/audit/integrity', 
    loadComponent: () => import('./modules/admin/audit/governance/audit-integrity-verification.component').then(m => m.AuditIntegrityVerificationComponent) 
  },
  { 
    path: 'administration/audit/export', 
    loadComponent: () => import('./modules/admin/audit/export/audit-export.component').then(m => m.AuditExportComponent) 
  },

  // 5.10 PLATFORM ADMINISTRATION
  { 
    path: 'administration/platform-admin', 
    loadComponent: () => import('./modules/admin/platform-admin/platform-admin-home.component').then(m => m.PlatformAdminHomeComponent) 
  },
  { 
    path: 'administration/platform-admin/platform/config', 
    loadComponent: () => import('./modules/admin/platform-admin/platform/platform-config.component').then(m => m.PlatformConfigComponent) 
  },
  { 
    path: 'administration/platform-admin/platform/services', 
    loadComponent: () => import('./modules/admin/platform-admin/platform/services-nodes-list.component').then(m => m.ServicesNodesListComponent) 
  },
  { 
    path: 'administration/platform-admin/platform/deployment', 
    loadComponent: () => import('./modules/admin/platform-admin/platform/deployment-config.component').then(m => m.DeploymentConfigComponent) 
  },
  { 
    path: 'administration/platform-admin/lifecycle/versions', 
    loadComponent: () => import('./modules/admin/platform-admin/lifecycle/versions-view.component').then(m => m.VersionsViewComponent) 
  },
  { 
    path: 'administration/platform-admin/lifecycle/updates', 
    loadComponent: () => import('./modules/admin/platform-admin/lifecycle/updates-management.component').then(m => m.UpdatesManagementComponent) 
  },
  { 
    path: 'administration/platform-admin/lifecycle/maintenance', 
    loadComponent: () => import('./modules/admin/platform-admin/lifecycle/maintenance-windows-list.component').then(m => m.MaintenanceWindowsListComponent) 
  },
  { 
    path: 'administration/platform-admin/lifecycle/maintenance/create', 
    loadComponent: () => import('./modules/admin/platform-admin/lifecycle/maintenance-window-create.component').then(m => m.MaintenanceWindowCreateComponent) 
  },
  { 
    path: 'administration/platform-admin/commercial/licensing', 
    loadComponent: () => import('./modules/admin/platform-admin/commercial/licensing-entitlements.component').then(m => m.LicensingEntitlementsComponent) 
  },
  { 
    path: 'administration/platform-admin/resilience/backup-restore', 
    loadComponent: () => import('./modules/admin/platform-admin/resilience/backup-restore.component').then(m => m.BackupRestoreComponent) 
  },
  { 
    path: 'administration/platform-admin/support/diagnostics', 
    loadComponent: () => import('./modules/admin/platform-admin/support/diagnostics-support.component').then(m => m.DiagnosticsSupportComponent) 
  },

  // 5.11 INTEGRATIONS & NOTIFICATIONS
  { 
    path: 'administration/integrations', 
    loadComponent: () => import('./modules/admin/integrations/integrations-home.component').then(m => m.IntegrationsHomeComponent) 
  },
  { 
    path: 'administration/integrations-notifications', 
    redirectTo: 'administration/integrations' 
  },
  { 
    path: 'administration/integrations/notifications/channels', 
    loadComponent: () => import('./modules/admin/integrations/notifications/channels-list.component').then(m => m.ChannelsListComponent) 
  },
  { 
    path: 'administration/integrations/notifications/channels/create', 
    loadComponent: () => import('./modules/admin/integrations/notifications/channel-create.component').then(m => m.ChannelCreateComponent) 
  },
  { 
    path: 'administration/integrations/notifications/channels/detail/:id', 
    loadComponent: () => import('./modules/admin/integrations/notifications/channel-detail.component').then(m => m.ChannelDetailComponent) 
  },
  { 
    path: 'administration/integrations/notifications/policies', 
    loadComponent: () => import('./modules/admin/integrations/notifications/policies-list.component').then(m => m.PoliciesListComponent) 
  },
  { 
    path: 'administration/integrations/notifications/policies/create', 
    loadComponent: () => import('./modules/admin/integrations/notifications/policy-create.component').then(m => m.PolicyCreateComponent) 
  },
  { 
    path: 'administration/integrations/events/routing', 
    loadComponent: () => import('./modules/admin/integrations/event-delivery/event-routing-list.component').then(m => m.EventRoutingListComponent) 
  },
  { 
    path: 'administration/integrations/events/routing/create', 
    loadComponent: () => import('./modules/admin/integrations/event-delivery/event-routing-create.component').then(m => m.EventRoutingCreateComponent) 
  },
  { 
    path: 'administration/integrations/enterprise/siem', 
    loadComponent: () => import('./modules/admin/integrations/enterprise/siem-integrations-list.component').then(m => m.SiemIntegrationsListComponent) 
  },
  { 
    path: 'administration/integrations/enterprise/siem/create', 
    loadComponent: () => import('./modules/admin/integrations/enterprise/siem-create.component').then(m => m.SiemCreateComponent) 
  },
  { 
    path: 'administration/integrations/enterprise/itsm', 
    loadComponent: () => import('./modules/admin/integrations/enterprise/itsm-integrations-list.component').then(m => m.ItsmIntegrationsListComponent) 
  },
  { 
    path: 'administration/integrations/enterprise/itsm/create', 
    loadComponent: () => import('./modules/admin/integrations/enterprise/itsm-create.component').then(m => m.ItsmCreateComponent) 
  },
  { 
    path: 'administration/integrations/credentials', 
    loadComponent: () => import('./modules/admin/integrations/credentials/credential-references-list.component').then(m => m.CredentialReferencesListComponent) 
  },

  {
    path: 'settings',
    loadComponent: () => import('./modules/settings/settings-shell.component').then(m => m.SettingsShellComponent),
    children: [
      { path: '', redirectTo: 'general', pathMatch: 'full' },
      { path: 'general', loadComponent: () => import('./modules/settings/general/settings-general.component').then(m => m.SettingsGeneralComponent) },
      { path: 'appearance', loadComponent: () => import('./modules/settings/appearance/settings-appearance.component').then(m => m.SettingsAppearanceComponent) },
      { path: 'runtime-migration', loadComponent: () => import('./modules/settings/runtime-migration/settings-runtime-migration.component').then(m => m.SettingsRuntimeMigrationComponent) },
      { path: 'connectors', loadComponent: () => import('./modules/settings/connectors/settings-connectors.component').then(m => m.SettingsConnectorsComponent) },
      { path: 'storage', loadComponent: () => import('./modules/settings/storage/settings-storage.component').then(m => m.SettingsStorageComponent) },
      { path: 'notifications', loadComponent: () => import('./modules/settings/notifications/settings-notifications.component').then(m => m.SettingsNotificationsComponent) },
      { path: 'integrations', loadComponent: () => import('./modules/settings/integrations/settings-integrations.component').then(m => m.SettingsIntegrationsComponent) },
      { path: 'ai-intelligence', loadComponent: () => import('./modules/settings/ai-intelligence/settings-ai-intelligence.component').then(m => m.SettingsAiIntelligenceComponent) },
      { path: 'logging', loadComponent: () => import('./modules/settings/logging/settings-logging.component').then(m => m.SettingsLoggingComponent) },
      { path: 'advanced', loadComponent: () => import('./modules/settings/advanced/settings-advanced.component').then(m => m.SettingsAdvancedComponent) }
    ]
  },

  { path: '**', redirectTo: 'dashboard' }
];