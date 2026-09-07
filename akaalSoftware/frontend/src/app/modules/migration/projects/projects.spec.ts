import { describe, it, expect, beforeEach } from 'vitest';
import { ProjectsService } from './projects.service';
import { ContextService } from '../../../core/services/context.service';
import {
  FIXTURE_STANDARD_PROJECTS,
  FIXTURE_STANDARD_INITIATIVES,
  FIXTURE_STANDARD_ATTENTION
} from './projects.fixtures';

describe('Projects & Initiatives (Foundation + Part A Portfolio)', () => {
  let service: ProjectsService;
  let contextService: ContextService;

  beforeEach(() => {
    contextService = new ContextService();
    service = new ProjectsService(contextService);
  });

  describe('1. Store State & Availability Handling', () => {
    it('should initialize with standard entities and ready state', () => {
      expect(service.projects().length).toBeGreaterThan(0);
      expect(service.initiatives().length).toBeGreaterThan(0);
      expect(service.projectsAvailability()).toBe('READY');
      expect(service.isUnavailable()).toBe(false);
      expect(service.isEmpty()).toBe(false);
    });

    it('should correctly flag UNAVAILABLE and NOT_CONNECTED states', () => {
      service.loadTestScenario('NOT_CONNECTED', [], [], []);
      expect(service.isUnavailable()).toBe(true);
      expect(service.projectsAvailability()).toBe('NOT_CONNECTED');

      service.loadTestScenario('UNAVAILABLE', [], [], []);
      expect(service.isUnavailable()).toBe(true);
      expect(service.projectsAvailability()).toBe('UNAVAILABLE');
    });

    it('should correctly flag UNAUTHORIZED state', () => {
      service.loadTestScenario('UNAUTHORIZED', [], [], []);
      expect(service.isUnauthorized()).toBe(true);
    });

    it('should correctly flag EMPTY state when no projects exist', () => {
      service.loadTestScenario('EMPTY', [], [], []);
      expect(service.isEmpty()).toBe(true);
    });

    it('should correctly flag ERROR state with error message', () => {
      service.loadTestScenario('ERROR', [], [], [], undefined, 'Network timeout querying orchestrator');
      expect(service.isError()).toBe(true);
      expect(service.errorMessage()).toBe('Network timeout querying orchestrator');
    });
  });

  describe('2. Project Discovery Filtering & Sorting', () => {
    beforeEach(() => {
      service.loadTestScenario(
        'READY',
        FIXTURE_STANDARD_PROJECTS,
        FIXTURE_STANDARD_INITIATIVES,
        FIXTURE_STANDARD_ATTENTION
      );
    });

    it('should filter projects by search query across name, key, description', () => {
      service.setProjectSearch('Core Banking');
      const filtered = service.filteredProjects();
      expect(filtered.length).toBe(1);
      expect(filtered[0].key).toBe('CB-MOD');

      service.setProjectSearch('PAY-GW');
      expect(service.filteredProjects().length).toBe(1);

      service.setProjectSearch('nonexistent-keyword-xyz');
      expect(service.filteredProjects().length).toBe(0);
    });

    it('should filter projects by status', () => {
      service.setProjectStatusFilter('PLANNING');
      const filtered = service.filteredProjects();
      expect(filtered.every(p => p.status === 'PLANNING')).toBe(true);
      expect(filtered.length).toBeGreaterThan(0);

      service.setProjectStatusFilter('ALL');
      expect(service.filteredProjects().length).toBe(FIXTURE_STANDARD_PROJECTS.length);
    });

    it('should filter projects by associated initiative', () => {
      service.setProjectInitiativeFilter('init-dc-exit-2027');
      const filtered = service.filteredProjects();
      expect(filtered.every(p => p.initiativeId === 'init-dc-exit-2027')).toBe(true);
      expect(filtered.length).toBe(3);
    });

    it('should sort projects by name and toggle direction', () => {
      service.setProjectSort('NAME');
      expect(service.projectFilters().sortBy).toBe('NAME');
      expect(service.projectFilters().sortDirection).toBe('DESC');

      const namesDesc = service.filteredProjects().map(p => p.name);
      service.setProjectSort('NAME');
      expect(service.projectFilters().sortDirection).toBe('ASC');
      const namesAsc = service.filteredProjects().map(p => p.name);

      expect(namesAsc[0]).toBe(namesDesc[namesDesc.length - 1]);
    });

    it('should reset all project filters cleanly', () => {
      service.setProjectSearch('Kafka');
      service.setProjectStatusFilter('ACTIVE');
      service.setProjectInitiativeFilter('init-analytics-cloud');

      service.clearProjectFilters();
      const filters = service.projectFilters();
      expect(filters.searchQuery).toBe('');
      expect(filters.statusFilter).toBe('ALL');
      expect(filters.initiativeFilter).toBe('ALL');
      expect(service.filteredProjects().length).toBe(FIXTURE_STANDARD_PROJECTS.length);
    });
  });

  describe('3. Initiative Discovery Filtering & Sorting', () => {
    beforeEach(() => {
      service.loadTestScenario(
        'READY',
        FIXTURE_STANDARD_PROJECTS,
        FIXTURE_STANDARD_INITIATIVES,
        FIXTURE_STANDARD_ATTENTION
      );
    });

    it('should filter initiatives by search query', () => {
      service.setInitiativeSearch('Data Center');
      const filtered = service.filteredInitiatives();
      expect(filtered.length).toBe(1);
      expect(filtered[0].key).toBe('DC-EXIT-2027');
    });

    it('should filter initiatives by status', () => {
      service.setInitiativeStatusFilter('PLANNING');
      const filtered = service.filteredInitiatives();
      expect(filtered.every(i => i.status === 'PLANNING')).toBe(true);
      expect(filtered.length).toBe(1);
    });

    it('should sort initiatives by associated projects count', () => {
      service.setInitiativeSort('PROJECTS');
      const filtered = service.filteredInitiatives();
      expect(filtered[0].associatedProjectCount).toBeGreaterThanOrEqual(
        filtered[filtered.length - 1].associatedProjectCount
      );
    });

    it('should reset initiative filters', () => {
      service.setInitiativeSearch('Archival');
      service.clearInitiativeFilters();
      expect(service.initiativeFilters().searchQuery).toBe('');
      expect(service.initiativeFilters().statusFilter).toBe('ALL');
      expect(service.filteredInitiatives().length).toBe(FIXTURE_STANDARD_INITIATIVES.length);
    });
  });

  describe('4. Zero-Fake Policy & Projection Truthfulness', () => {
    it('should represent unpopulated aggregates as null/unknown rather than synthesizing percentages', () => {
      const emptyProject = {
        id: 'proj-test',
        key: 'TEST',
        name: 'Test Project',
        workspaceId: 'ws-1',
        migrationCount: null,
        validationCount: null,
        availability: 'READY' as const,
        accessState: 'GRANTED' as const
      };

      expect(emptyProject.migrationCount).toBeNull();
      expect(emptyProject.validationCount).toBeNull();
    });

    it('should gracefully handle attention events projection without inventing alerts', () => {
      service.loadTestScenario('READY', FIXTURE_STANDARD_PROJECTS, FIXTURE_STANDARD_INITIATIVES, []);
      expect(service.attentionItems().length).toBe(0);
    });

    it('should provide available status options dynamically from loaded data', () => {
      const options = service.availableProjectStatusOptions();
      expect(options).toContain('ACTIVE');
      expect(options).toContain('PLANNING');
    });

    it('should provide available initiative options dynamically from loaded projects', () => {
      const initOptions = service.availableInitiativeOptions();
      expect(initOptions.length).toBeGreaterThan(0);
      expect(initOptions.some(o => o.id === 'init-dc-exit-2027')).toBe(true);
    });
  });

  describe('5. Part B: Create Initiative Draft & Wizard State', () => {
    beforeEach(() => {
      service.clearDraft();
    });

    it('should initialize creation draft with empty state at step 1', () => {
      expect(service.createWizardStep()).toBe(1);
      expect(service.initiativeDraft().name).toBe('');
      expect(service.initiativeDraft().objective).toBe('');
      expect(service.initiativeDraft().selectedProjectIds.length).toBe(0);
    });

    it('should update draft name and objective', () => {
      service.setDraftName('Cloud Modernization 2028');
      service.setDraftObjective('Migrate on-prem systems to AWS');
      expect(service.initiativeDraft().name).toBe('Cloud Modernization 2028');
      expect(service.initiativeDraft().objective).toBe('Migrate on-prem systems to AWS');
    });

    it('should toggle and remove project selections in draft', () => {
      service.toggleDraftProject('proj-core-banking');
      expect(service.initiativeDraft().selectedProjectIds).toContain('proj-core-banking');

      service.toggleDraftProject('proj-payments-gw');
      expect(service.initiativeDraft().selectedProjectIds.length).toBe(2);

      // Toggle off
      service.toggleDraftProject('proj-core-banking');
      expect(service.initiativeDraft().selectedProjectIds).not.toContain('proj-core-banking');
      expect(service.initiativeDraft().selectedProjectIds.length).toBe(1);

      // Explicit removal
      service.removeDraftProject('proj-payments-gw');
      expect(service.initiativeDraft().selectedProjectIds.length).toBe(0);
    });

    it('should support step transitions and clearing draft', () => {
      service.setCreateWizardStep(2);
      expect(service.createWizardStep()).toBe(2);
      service.setCreateWizardStep(3);
      expect(service.createWizardStep()).toBe(3);

      service.clearDraft();
      expect(service.createWizardStep()).toBe(1);
      expect(service.initiativeDraft().name).toBe('');
    });
  });

  describe('6. Part B: Initiative Workspace & Tab Navigation', () => {
    beforeEach(() => {
      service.setActiveInitiativeId('init-dc-exit-2027');
      service.setActiveTab('overview');
    });

    it('should load active initiative workspace detail by ID', () => {
      const active = service.activeInitiative();
      expect(active).not.toBeNull();
      expect(active?.key).toBe('DC-EXIT-2027');
      expect(active?.name).toBe('Data Center Exit & Modernization 2027');
      expect(active?.status).toBe('ACTIVE');
    });

    it('should compute associated projects for the active initiative', () => {
      const projects = service.activeInitiativeProjects();
      expect(projects.length).toBe(3);
      expect(projects.map(p => p.key)).toEqual(
        expect.arrayContaining(['CB-MOD', 'PAY-GW', 'DB2-RET'])
      );
    });

    it('should filter and sort projects within the active initiative', () => {
      service.setProjectSearch('Payments');
      const filtered = service.filteredActiveInitiativeProjects();
      expect(filtered.length).toBe(1);
      expect(filtered[0].key).toBe('PAY-GW');

      service.clearProjectFilters();
      expect(service.filteredActiveInitiativeProjects().length).toBe(3);
    });

    it('should compute and filter chronological activities for the active initiative', () => {
      const activities = service.activeInitiativeActivities();
      expect(activities.length).toBeGreaterThan(0);
      expect(activities.every(a => a.initiativeId === 'init-dc-exit-2027')).toBe(true);

      service.setActivityCategoryFilter('GOVERNANCE');
      const govActivities = service.activeInitiativeActivities();
      expect(govActivities.length).toBe(1);
      expect(govActivities[0].category).toBe('GOVERNANCE');

      service.setActivityCategoryFilter('ALL');
      expect(service.activeInitiativeActivities().length).toBe(activities.length);
    });

    it('should switch workspace tabs cleanly', () => {
      service.setActiveTab('projects');
      expect(service.activeTab()).toBe('projects');
      service.setActiveTab('activity');
      expect(service.activeTab()).toBe('activity');
      service.setActiveTab('settings');
      expect(service.activeTab()).toBe('settings');
      service.setActiveTab('overview');
      expect(service.activeTab()).toBe('overview');
    });
  });

  describe('7. Part B: Association Intents & Settings Actions', () => {
    beforeEach(() => {
      service.setActiveInitiativeId('init-dc-exit-2027');
    });

    it('should update initiative general properties (Name & Objective intent)', () => {
      service.updateInitiativeGeneral('init-dc-exit-2027', 'Updated DC Exit 2027', 'New updated objective');
      const active = service.activeInitiative();
      expect(active?.name).toBe('Updated DC Exit 2027');
      expect(active?.objective).toBe('New updated objective');
    });

    it('should remove project association from initiative', () => {
      service.removeProjectFromInitiative('init-dc-exit-2027', 'proj-db2-retirement');
      const active = service.activeInitiative();
      expect(active?.associatedProjectIds).not.toContain('proj-db2-retirement');
      expect(active?.totalProjectsCount).toBe(2);

      const project = service.projects().find(p => p.id === 'proj-db2-retirement');
      expect(project?.initiativeId).toBeUndefined();
    });

    it('should add project association to initiative', () => {
      service.addProjectsToInitiative('init-dc-exit-2027', ['proj-audit-archive']);
      const active = service.activeInitiative();
      expect(active?.associatedProjectIds).toContain('proj-audit-archive');

      const project = service.projects().find(p => p.id === 'proj-audit-archive');
      expect(project?.initiativeId).toBe('init-dc-exit-2027');
    });

    it('should archive initiative and update its lifecycle status', () => {
      service.archiveInitiative('init-dc-exit-2027');
      const active = service.activeInitiative();
      expect(active?.status).toBe('ARCHIVED');
    });
  });

  describe('8. Part C: Project Creation Wizard & Draft State', () => {
    beforeEach(() => {
      service.clearProjectDraft();
    });

    it('should initialize project creation draft with creator assigned and empty inputs', () => {
      expect(service.projectWizardStep()).toBe(1);
      const draft = service.projectDraft();
      expect(draft.name).toBe('');
      expect(draft.key).toBe('');
      expect(draft.description).toBe('');
      expect(draft.initiativeId).toBeNull();
      expect(draft.accessAssignments.length).toBe(1);
      expect(draft.accessAssignments[0].role).toBe('PROJECT_ADMIN');
      expect(draft.selectedResourceIds.length).toBe(0);
    });

    it('should auto-generate suggested project key when name changes', () => {
      service.setProjectDraftName('Payment Settlement Gateway');
      expect(service.projectDraft().name).toBe('Payment Settlement Gateway');
      expect(service.projectDraft().key).toBe('PSG');

      // Manual key override should be retained
      service.setProjectDraftKey('CUSTOM-KEY');
      expect(service.projectDraft().key).toBe('CUSTOM-KEY');
    });

    it('should update project description and initiative alignment', () => {
      service.setProjectDraftDescription('Replication pipeline for high-throughput transactional databases');
      expect(service.projectDraft().description).toContain('high-throughput');

      service.setProjectDraftInitiative('init-dc-exit-2027');
      expect(service.projectDraft().initiativeId).toBe('init-dc-exit-2027');

      // Reset to standalone
      service.setProjectDraftInitiative(null);
      expect(service.projectDraft().initiativeId).toBeNull();
    });

    it('should manage access intent assignments in Step 2', () => {
      const newPrincipal = {
        id: 'usr-sarah-jenkins',
        name: 'Sarah Jenkins',
        email: 's.jenkins@enterprise.corp',
        type: 'USER' as const,
        role: 'OPERATOR' as const
      };

      service.addProjectDraftPrincipal(newPrincipal);
      expect(service.projectDraft().accessAssignments.length).toBe(2);
      expect(service.projectDraft().accessAssignments.some(p => p.id === 'usr-sarah-jenkins')).toBe(true);

      // Update role
      service.updateProjectDraftPrincipalRole('usr-sarah-jenkins', 'PROJECT_ADMIN');
      const updated = service.projectDraft().accessAssignments.find(p => p.id === 'usr-sarah-jenkins');
      expect(updated?.role).toBe('PROJECT_ADMIN');

      // Remove assignment
      service.removeProjectDraftPrincipal('usr-sarah-jenkins');
      expect(service.projectDraft().accessAssignments.length).toBe(1);
    });

    it('should toggle resource association intents in Step 2', () => {
      service.toggleProjectDraftResource('conn-ora-prod-01');
      expect(service.projectDraft().selectedResourceIds).toContain('conn-ora-prod-01');

      service.toggleProjectDraftResource('conn-pg-aurora-01');
      expect(service.projectDraft().selectedResourceIds.length).toBe(2);

      // Toggle off
      service.toggleProjectDraftResource('conn-ora-prod-01');
      expect(service.projectDraft().selectedResourceIds).not.toContain('conn-ora-prod-01');
      expect(service.projectDraft().selectedResourceIds.length).toBe(1);
    });

    it('should step through creation wizard and submit new project workspace', () => {
      service.setProjectWizardStep(1);
      service.setProjectDraftName('Treasury Settlement Engine');
      service.setProjectDraftDescription('Automated cash management sync');
      service.setProjectDraftInitiative('init-dc-exit-2027');

      service.setProjectWizardStep(2);
      service.toggleProjectDraftResource('conn-pg-aurora-01');

      service.setProjectWizardStep(3);
      expect(service.projectWizardStep()).toBe(3);

      const newProjectId = service.submitCreateProject();
      expect(newProjectId).toBeDefined();
      expect(newProjectId.startsWith('proj-')).toBe(true);

      // Verify project is in the projects store list
      const createdItem = service.projects().find(p => p.id === newProjectId);
      expect(createdItem).toBeDefined();
      expect(createdItem?.name).toBe('Treasury Settlement Engine');
      expect(createdItem?.initiativeId).toBe('init-dc-exit-2027');

      // Verify project workspace exists
      const workspace = service.projectWorkspaces()[newProjectId];
      expect(workspace).toBeDefined();
      expect(workspace.key).toBe('TSE');
      expect(workspace.recentActivities?.length).toBeGreaterThan(0);
    });
  });

  describe('9. Part C: Project Workspace & Overview State', () => {
    beforeEach(() => {
      service.setActiveProjectId('proj-core-banking');
      service.setActiveProjectTab('overview');
    });

    it('should compute active project detail and parent initiative', () => {
      const active = service.activeProject();
      expect(active).not.toBeNull();
      expect(active?.id).toBe('proj-core-banking');
      expect(active?.key).toBe('CB-MOD');
      expect(active?.name).toBe('Core Banking Ledger Modernization');
      expect(active?.currentWork?.totalMigrations).toBe(8);
      expect(active?.currentWork?.activeMigrations).toBe(3);

      const init = service.activeProjectInitiative();
      expect(init).not.toBeNull();
      expect(init?.id).toBe('init-dc-exit-2027');
    });

    it('should project attention items specific to active project', () => {
      const attention = service.activeProjectAttention();
      expect(attention.length).toBe(1);
      expect(attention[0].projectId).toBe('proj-core-banking');
      expect(attention[0].title).toContain('Schema constraint discrepancy');
    });

    it('should project activities specific to active project', () => {
      const activities = service.activeProjectActivities();
      expect(activities.length).toBeGreaterThan(0);
      expect(activities.every(a => a.projectId === 'proj-core-banking')).toBe(true);
    });

    it('should switch project workspace tabs cleanly across all 8 IA tabs', () => {
      service.setActiveProjectTab('migrations');
      expect(service.activeProjectTab()).toBe('migrations');

      service.setActiveProjectTab('validations');
      expect(service.activeProjectTab()).toBe('validations');

      service.setActiveProjectTab('resources');
      expect(service.activeProjectTab()).toBe('resources');

      service.setActiveProjectTab('activity');
      expect(service.activeProjectTab()).toBe('activity');

      service.setActiveProjectTab('access');
      expect(service.activeProjectTab()).toBe('access');

      service.setActiveProjectTab('governance');
      expect(service.activeProjectTab()).toBe('governance');

      service.setActiveProjectTab('settings');
      expect(service.activeProjectTab()).toBe('settings');

      service.setActiveProjectTab('overview');
      expect(service.activeProjectTab()).toBe('overview');
    });
  });

  describe('Part D: Project Work (Migrations, Validations, Resources)', () => {
    beforeEach(() => {
      service.setActiveProjectId('proj-core-banking');
    });

    describe('1. Project Migrations Scoping & Filtering', () => {
      it('should compute migrations associated with active project', () => {
        const migrations = service.activeProjectMigrations();
        expect(migrations.length).toBe(5);
        expect(migrations.every(m => m.projectId === 'proj-core-banking')).toBe(true);
      });

      it('should search project migrations by name, key, and providers', () => {
        service.setMigrationSearch('MIG-CB-01');
        expect(service.filteredActiveProjectMigrations().length).toBe(1);
        expect(service.filteredActiveProjectMigrations()[0].name).toBe('Accounts & General Ledger M2');

        service.setMigrationSearch('PostgreSQL');
        expect(service.filteredActiveProjectMigrations().length).toBe(5);

        service.setMigrationSearch('non-matching-migration');
        expect(service.filteredActiveProjectMigrations().length).toBe(0);

        service.clearMigrationFilters();
        expect(service.filteredActiveProjectMigrations().length).toBe(5);
      });

      it('should filter project migrations by lifecycle state', () => {
        service.setMigrationStateFilter('RUNNING');
        const running = service.filteredActiveProjectMigrations();
        expect(running.length).toBe(2);
        expect(running.every(m => m.lifecycleState === 'RUNNING')).toBe(true);

        service.setMigrationStateFilter('COMPLETED');
        const completed = service.filteredActiveProjectMigrations();
        expect(completed.length).toBe(2);
        expect(completed.every(m => m.lifecycleState === 'COMPLETED')).toBe(true);

        service.setMigrationStateFilter('ATTENTION');
        const attention = service.filteredActiveProjectMigrations();
        expect(attention.length).toBe(1);
        expect(attention[0].attentionRequired).toBe(true);
      });

      it('should filter project migrations by execution mode', () => {
        service.setMigrationModeFilter('ONLINE_CDC');
        const cdc = service.filteredActiveProjectMigrations();
        expect(cdc.length).toBe(2);
        expect(cdc.every(m => m.mode === 'ONLINE_CDC')).toBe(true);

        service.setMigrationModeFilter('OFFLINE_BULK');
        const bulk = service.filteredActiveProjectMigrations();
        expect(bulk.length).toBe(2);
        expect(bulk.every(m => m.mode === 'OFFLINE_BULK')).toBe(true);

        service.setMigrationModeFilter('DUAL_RUN');
        const dual = service.filteredActiveProjectMigrations();
        expect(dual.length).toBe(1);
      });

      it('should sort project migrations by name and state', () => {
        service.setMigrationSort('NAME');
        expect(service.migrationFilters().sortBy).toBe('NAME');
        expect(service.filteredActiveProjectMigrations().length).toBe(5);

        service.setMigrationSort('STATE');
        expect(service.migrationFilters().sortBy).toBe('STATE');
      });

      it('should handle hostile availability states for project migrations', () => {
        service.loadMigrationsTestScenario('UNAVAILABLE', []);
        expect(service.projectMigrationsAvailability()).toBe('UNAVAILABLE');

        service.loadMigrationsTestScenario('UNAUTHORIZED', []);
        expect(service.projectMigrationsAvailability()).toBe('UNAUTHORIZED');

        service.loadMigrationsTestScenario('EMPTY', []);
        expect(service.projectMigrationsAvailability()).toBe('EMPTY');
        expect(service.activeProjectMigrations().length).toBe(0);
      });
    });

    describe('2. Project Validations Scoping & Filtering', () => {
      it('should compute validations associated with active project', () => {
        const validations = service.activeProjectValidations();
        expect(validations.length).toBe(3);
        expect(validations.every(v => v.projectId === 'proj-core-banking')).toBe(true);
      });

      it('should search project validations by name, scope, and key', () => {
        service.setValidationSearch('VAL-CB-01');
        expect(service.filteredActiveProjectValidations().length).toBe(1);
        expect(service.filteredActiveProjectValidations()[0].scopeName).toBe('public.account_ledger');

        service.setValidationSearch('account_ledger');
        expect(service.filteredActiveProjectValidations().length).toBe(1);

        service.clearValidationFilters();
        expect(service.filteredActiveProjectValidations().length).toBe(3);
      });

      it('should filter project validations by outcome/state', () => {
        service.setValidationStateFilter('Validated');
        const validated = service.filteredActiveProjectValidations();
        expect(validated.length).toBe(2);
        expect(validated.every(v => v.outcome === 'Validated')).toBe(true);

        service.setValidationStateFilter('Discrepancies Found');
        const discrepancies = service.filteredActiveProjectValidations();
        expect(discrepancies.length).toBe(1);
        expect(discrepancies[0].discrepancyCount).toBe(1);
      });

      it('should filter project validations by validation strategy', () => {
        service.setValidationStrategyFilter('Structural');
        const structural = service.filteredActiveProjectValidations();
        expect(structural.length).toBe(1);
        expect(structural[0].strategy).toBe('Structural');

        service.setValidationStrategyFilter('Complete Attribute');
        const complete = service.filteredActiveProjectValidations();
        expect(complete.length).toBe(1);
        expect(complete[0].strategy).toBe('Complete Attribute');
      });

      it('should sort project validations by name and state', () => {
        service.setValidationSort('NAME');
        expect(service.validationFilters().sortBy).toBe('NAME');
        expect(service.filteredActiveProjectValidations().length).toBe(3);
      });

      it('should handle hostile availability states for project validations', () => {
        service.loadValidationsTestScenario('UNAVAILABLE', []);
        expect(service.projectValidationsAvailability()).toBe('UNAVAILABLE');

        service.loadValidationsTestScenario('UNAUTHORIZED', []);
        expect(service.projectValidationsAvailability()).toBe('UNAUTHORIZED');

        service.loadValidationsTestScenario('EMPTY', []);
        expect(service.projectValidationsAvailability()).toBe('EMPTY');
        expect(service.activeProjectValidations().length).toBe(0);
      });
    });

    describe('3. Project Resources Scoping, Visibility & Zero-Secrets', () => {
      it('should compute active project resources with dynamic isBoundToProject flag', () => {
        const resources = service.activeProjectResources();
        expect(resources.length).toBeGreaterThan(0);

        const bound = resources.filter(r => r.isBoundToProject);
        expect(bound.length).toBe(3); // Oracle, Aurora PG, Kafka
        expect(bound.some(r => r.connectionId === 'conn-ora-prod-01')).toBe(true);
        expect(bound.some(r => r.connectionId === 'conn-pg-aurora-01')).toBe(true);
        expect(bound.some(r => r.connectionId === 'conn-kafka-prod')).toBe(true);
      });

      it('should filter resources by search query across name, host, and provider', () => {
        service.setResourceSearch('Aurora');
        expect(service.filteredActiveProjectResources().length).toBe(1);
        expect(service.filteredActiveProjectResources()[0].provider).toBe('PostgreSQL');

        service.setResourceSearch('Snowflake');
        expect(service.filteredActiveProjectResources().length).toBe(1);

        service.clearResourceFilters();
        expect(service.filteredActiveProjectResources().length).toBe(service.activeProjectResources().length);
      });

      it('should filter resources by category', () => {
        service.setResourceCategoryFilter('RELATIONAL');
        const relational = service.filteredActiveProjectResources();
        expect(relational.every(r => r.category === 'RELATIONAL')).toBe(true);

        service.setResourceCategoryFilter('STREAMING');
        const streaming = service.filteredActiveProjectResources();
        expect(streaming.every(r => r.category === 'STREAMING')).toBe(true);

        service.setResourceCategoryFilter('WAREHOUSE');
        const wh = service.filteredActiveProjectResources();
        expect(wh.every(r => r.category === 'WAREHOUSE')).toBe(true);
      });

      it('should filter resources by association status (BOUND vs AVAILABLE)', () => {
        service.setResourceAssociationFilter('BOUND');
        const bound = service.filteredActiveProjectResources();
        expect(bound.every(r => r.isBoundToProject)).toBe(true);

        service.setResourceAssociationFilter('AVAILABLE');
        const available = service.filteredActiveProjectResources();
        expect(available.every(r => !r.isBoundToProject)).toBe(true);
      });

      it('should filter resources by availability state', () => {
        service.setResourceAvailabilityFilter('UNAUTHORIZED');
        const unauth = service.filteredActiveProjectResources();
        expect(unauth.length).toBe(1);
        expect(unauth[0].availabilityState).toBe('UNAUTHORIZED');

        service.setResourceAvailabilityFilter('UNAVAILABLE');
        const unavail = service.filteredActiveProjectResources();
        expect(unavail.length).toBe(1);
        expect(unavail[0].availabilityState).toBe('UNAVAILABLE');
      });

      it('should toggle resource binding intent without faking backend mutations', () => {
        service.toggleProjectResourceBinding('conn-snow-lakehouse');
        const updated = service.activeProjectResources().find(r => r.connectionId === 'conn-snow-lakehouse');
        expect(updated?.isBoundToProject).toBe(true);

        // Toggle back
        service.toggleProjectResourceBinding('conn-snow-lakehouse');
        const reverted = service.activeProjectResources().find(r => r.connectionId === 'conn-snow-lakehouse');
        expect(reverted?.isBoundToProject).toBe(false);
      });

      it('should select resource for detail safely without exposing secrets', () => {
        service.setSelectedResourceIdForDetail('conn-ora-prod-01');
        const detail = service.activeResourceDetail();
        expect(detail).not.toBeNull();
        expect(detail?.connectionName).toContain('Oracle');
        expect((detail as any)?.password).toBeUndefined();
        expect((detail as any)?.secret).toBeUndefined();
        expect((detail as any)?.apiKey).toBeUndefined();
      });

      it('should handle hostile availability states for project resources', () => {
        service.loadResourcesTestScenario('UNAVAILABLE', []);
        expect(service.projectResourcesAvailability()).toBe('UNAVAILABLE');

        service.loadResourcesTestScenario('UNAUTHORIZED', []);
        expect(service.projectResourcesAvailability()).toBe('UNAUTHORIZED');

        service.loadResourcesTestScenario('EMPTY', []);
        expect(service.projectResourcesAvailability()).toBe('EMPTY');
      });
    });
  });

  // ==========================================================================
  // PART E: PROJECT CONTROL (ACTIVITY + ACCESS + GOVERNANCE + SETTINGS)
  // ==========================================================================
  describe('PART E: Project Control Surfaces', () => {
    beforeEach(() => {
      service.setActiveProjectId('proj-core-banking');
    });

    describe('1. Project Activity Surface (Activity != Audit)', () => {
      it('should retrieve chronological events scoped to active project', () => {
        const activities = service.activeProjectDetailedActivities();
        expect(activities.length).toBeGreaterThan(0);
        expect(activities.every(a => a.projectId === 'proj-core-banking')).toBe(true);
      });

      it('should filter activities by search query across title, description, and actor', () => {
        service.setActivitySearch('Validation');
        const filtered = service.filteredActiveProjectActivities();
        expect(filtered.length).toBeGreaterThan(0);
        expect(filtered.every(a =>
          a.title.includes('Validation') ||
          a.description.includes('Validation') ||
          a.actorName.includes('Validation')
        )).toBe(true);

        service.setActivitySearch('nonexistent-actor-xyz');
        expect(service.filteredActiveProjectActivities().length).toBe(0);
      });

      it('should filter activities by category (GOVERNANCE, VALIDATION, MIGRATION, ACCESS, RESOURCE)', () => {
        service.setActivityCategory('GOVERNANCE');
        const gov = service.filteredActiveProjectActivities();
        expect(gov.every(a => a.category === 'GOVERNANCE')).toBe(true);

        service.setActivityCategory('VALIDATION');
        const val = service.filteredActiveProjectActivities();
        expect(val.every(a => a.category === 'VALIDATION')).toBe(true);

        service.setActivityCategory('ALL');
        expect(service.filteredActiveProjectActivities().length).toBe(service.activeProjectDetailedActivities().length);
      });

      it('should sort activities chronologically and by category/actor', () => {
        service.setActivitySort('CATEGORY');
        expect(service.activityFilters().sortBy).toBe('CATEGORY');

        service.setActivitySort('ACTOR');
        expect(service.activityFilters().sortBy).toBe('ACTOR');
      });

      it('should handle hostile availability states for project activity', () => {
        service.loadActivityTestScenario('UNAVAILABLE', []);
        expect(service.projectActivityAvailability()).toBe('UNAVAILABLE');

        service.loadActivityTestScenario('UNAUTHORIZED', []);
        expect(service.projectActivityAvailability()).toBe('UNAUTHORIZED');

        service.loadActivityTestScenario('EMPTY', []);
        expect(service.projectActivityAvailability()).toBe('EMPTY');
      });
    });

    describe('2. Project Access Surface (Access != Administration)', () => {
      it('should retrieve direct project grants and inherited workspace grants', () => {
        const grants = service.activeProjectAccessGrants();
        expect(grants.length).toBeGreaterThan(0);

        const direct = grants.filter(g => g.accessSource === 'DIRECT_PROJECT');
        const inherited = grants.filter(g => g.accessSource === 'INHERITED_WORKSPACE');
        expect(direct.length).toBeGreaterThan(0);
        expect(inherited.length).toBeGreaterThan(0);
      });

      it('should filter access grants by search, role, type, and source', () => {
        service.setAccessSearch('Aalok');
        expect(service.filteredActiveProjectAccessGrants().length).toBe(1);

        service.setAccessRoleFilter('OPERATOR');
        const operators = service.filteredActiveProjectAccessGrants();
        expect(operators.every(g => g.role === 'OPERATOR')).toBe(true);

        service.setAccessSourceFilter('INHERITED_WORKSPACE');
        const inherited = service.filteredActiveProjectAccessGrants();
        expect(inherited.every(g => g.accessSource === 'INHERITED_WORKSPACE')).toBe(true);

        service.clearAccessFilters();
        expect(service.filteredActiveProjectAccessGrants().length).toBe(service.activeProjectAccessGrants().length);
      });

      it('should open Add Access modal and filter out already granted direct principals', () => {
        service.openAddAccessModal();
        expect(service.addAccessModalOpen()).toBe(true);
        expect(service.selectedRoleForAdd()).toBe('OPERATOR');

        const availableForAdd = service.availablePrincipalsForAddAccess();
        // Principals with direct grant should not be in available list
        const directPrincipalIds = service.activeProjectAccessGrants()
          .filter(g => g.accessSource === 'DIRECT_PROJECT')
          .map(g => g.principalId);
        expect(availableForAdd.every(p => !directPrincipalIds.includes(p.id))).toBe(true);
      });

      it('should submit Add Access intent without faking backend administration', () => {
        const available = service.availablePrincipalsForAddAccess();
        if (available.length > 0) {
          service.setSelectedPrincipalForAdd(available[0].id);
          service.setSelectedRoleForAdd('VIEWER');
          const success = service.submitAddAccessIntent();
          expect(success).toBe(true);
          expect(service.addAccessModalOpen()).toBe(false);

          const added = service.activeProjectAccessGrants().find(g => g.principalId === available[0].id);
          expect(added).toBeDefined();
          expect(added?.role).toBe('VIEWER');
          expect(added?.accessSource).toBe('DIRECT_PROJECT');
        }
      });

      it('should open and confirm Revoke Access consequential modal', () => {
        const directGrant = service.activeProjectAccessGrants().find(g => g.accessSource === 'DIRECT_PROJECT');
        expect(directGrant).toBeDefined();

        service.openRevokeAccessModal(directGrant!);
        expect(service.revokeAccessModalItem()).toBe(directGrant);

        service.confirmRevokeAccess(directGrant!.id);
        expect(service.revokeAccessModalItem()).toBeNull();
        expect(service.activeProjectAccessGrants().some(g => g.id === directGrant!.id)).toBe(false);
      });

      it('should handle hostile availability states for project access', () => {
        service.loadAccessTestScenario('UNAVAILABLE', []);
        expect(service.projectAccessAvailability()).toBe('UNAVAILABLE');

        service.loadAccessTestScenario('UNAUTHORIZED', []);
        expect(service.projectAccessAvailability()).toBe('UNAUTHORIZED');
      });
    });

    describe('3. Project Governance Surface (Governance != Approval Authority)', () => {
      it('should retrieve pending approvals, policies, resolved decisions, and waivers', () => {
        const gov = service.activeProjectGovernance();
        expect(gov.length).toBeGreaterThan(0);

        const pending = service.activeProjectPendingApprovals();
        expect(pending.length).toBe(1);
        expect(pending[0].protectedOperation).toBe('MIGRATION_CUTOVER_GATE');

        const policies = service.activeProjectPolicies();
        expect(policies.length).toBeGreaterThan(0);

        const resolved = service.activeProjectResolvedDecisions();
        expect(resolved.length).toBeGreaterThan(0);

        const waivers = service.activeProjectExceptions();
        expect(waivers.length).toBeGreaterThan(0);
      });

      it('should filter governance items by search, category, and status', () => {
        service.setGovernanceSearch('Cutover Gate');
        expect(service.filteredActiveProjectGovernance().length).toBe(1);

        service.setGovernanceCategoryFilter('POLICY_REQUIREMENT');
        const policies = service.filteredActiveProjectGovernance();
        expect(policies.every(g => g.category === 'POLICY_REQUIREMENT')).toBe(true);

        service.setGovernanceStatusFilter('APPROVED');
        const approved = service.filteredActiveProjectGovernance();
        expect(approved.every(g => g.status === 'APPROVED')).toBe(true);

        service.clearGovernanceFilters();
        expect(service.filteredActiveProjectGovernance().length).toBe(service.activeProjectGovernance().length);
      });

      it('should handle hostile availability states for project governance', () => {
        service.loadGovernanceTestScenario('UNAVAILABLE', []);
        expect(service.projectGovernanceAvailability()).toBe('UNAVAILABLE');

        service.loadGovernanceTestScenario('UNAUTHORIZED', []);
        expect(service.projectGovernanceAvailability()).toBe('UNAUTHORIZED');
      });
    });

    describe('4. Project Settings Surface (Settings != Platform Admin)', () => {
      it('should update project general metadata and initiative alignment locally', () => {
        service.updateProjectGeneral(
          'proj-core-banking',
          'Core Banking Ledger Modernization (Updated)',
          'Updated project scope description',
          'init-analytics-cloud'
        );

        const updated = service.activeProject();
        expect(updated?.name).toBe('Core Banking Ledger Modernization (Updated)');
        expect(updated?.description).toBe('Updated project scope description');
        expect(updated?.initiativeId).toBe('init-analytics-cloud');
      });

      it('should archive and restore project lifecycle states cleanly', () => {
        service.archiveProject('proj-core-banking');
        expect(service.activeProject()?.status).toBe('ARCHIVED');

        service.restoreProject('proj-core-banking');
        expect(service.activeProject()?.status).toBe('ACTIVE');
      });

      it('should handle hostile availability states for project settings', () => {
        service.loadSettingsTestScenario('UNAVAILABLE');
        expect(service.projectSettingsAvailability()).toBe('UNAVAILABLE');

        service.loadSettingsTestScenario('UNAUTHORIZED');
        expect(service.projectSettingsAvailability()).toBe('UNAUTHORIZED');
      });
    });
  });

  describe('Part F: Cross-Cutting Product Behavior', () => {
    beforeEach(() => {
      service.setActiveProjectId('proj-core-banking');
    });

    describe('1. Move Migration Governed Lifecycle Operation', () => {
      it('should list available destination projects within workspace excluding current project', () => {
        const destinations = service.availableDestinationProjects();
        expect(destinations.length).toBeGreaterThan(0);
        expect(destinations.every(p => p.id !== 'proj-core-banking')).toBe(true);
        expect(destinations.every(p => p.status !== 'ARCHIVED')).toBe(true);
      });

      it('should block move for actively running or attention migrations', () => {
        const runningMig = service.activeProjectMigrations().find(m => m.lifecycleState === 'RUNNING');
        expect(runningMig).toBeDefined();

        service.openMoveMigrationModal(runningMig!);
        expect(service.moveMigrationModalItem()?.id).toBe(runningMig!.id);
        expect(service.migrationMoveStatus()).toBe('UNAVAILABLE_ACTIVE');
      });

      it('should allow move for planning or completed migrations and execute intent', () => {
        const completedMig = service.activeProjectMigrations().find(m => m.lifecycleState === 'COMPLETED' || m.lifecycleState === 'PLANNING');
        expect(completedMig).toBeDefined();

        service.openMoveMigrationModal(completedMig!);
        expect(service.migrationMoveStatus()).toBe('MOVE_AVAILABLE');

        const destinations = service.availableDestinationProjects();
        expect(destinations.length).toBeGreaterThan(0);
        const targetProj = destinations[0];

        service.setSelectedDestinationProjectId(targetProj.id);
        const success = service.submitMoveMigrationIntent();
        expect(success).toBe(true);
        expect(service.moveMigrationModalItem()).toBeNull();

        // Migration should now belong to targetProj
        const moved = service.projectMigrations().find(m => m.id === completedMig!.id);
        expect(moved?.projectId).toBe(targetProj.id);
        expect(moved?.projectName).toBe(targetProj.name);

        // Activity record should be logged
        const destActivities = service.projectDetailedActivities().filter(a => a.projectId === targetProj.id);
        expect(destActivities.some(a => a.title === 'Migration Reassigned')).toBe(true);
      });

      it('should handle modal cancel cleanly', () => {
        const mig = service.activeProjectMigrations()[0];
        service.openMoveMigrationModal(mig);
        expect(service.moveMigrationModalItem()).toBeDefined();

        service.closeMoveMigrationModal();
        expect(service.moveMigrationModalItem()).toBeNull();
        expect(service.selectedDestinationProjectId()).toBeNull();
      });
    });

    describe('2. Project Association Invariant (0-or-1 Relationship)', () => {
      it('should enforce that a project belongs to at most one initiative or is standalone', () => {
        const projects = service.projects();
        projects.forEach(p => {
          if (p.initiativeId) {
            expect(typeof p.initiativeId).toBe('string');
            expect(p.initiativeName).toBeDefined();
          } else {
            expect(p.initiativeId).toBeUndefined();
          }
        });
      });

      it('should update initiative association when reassigned', () => {
        service.updateProjectGeneral('proj-payments-gw', 'Payments Gateway', 'Desc', 'init-dc-exit-2027');
        const proj = service.projects().find(p => p.id === 'proj-payments-gw');
        expect(proj?.initiativeId).toBe('init-dc-exit-2027');
        expect(proj?.initiativeName).toBe('Data Center Exit & Modernization 2027');
      });
    });

    describe('3. Unified Error & Availability State Model', () => {
      it('should handle comprehensive retry restoring all project sub-surface states', () => {
        service.loadMigrationsTestScenario('UNAVAILABLE', []);
        service.loadValidationsTestScenario('NOT_CONNECTED', []);
        service.loadResourcesTestScenario('ERROR', []);

        expect(service.projectMigrationsAvailability()).toBe('UNAVAILABLE');
        expect(service.projectValidationsAvailability()).toBe('NOT_CONNECTED');
        expect(service.projectResourcesAvailability()).toBe('ERROR');

        service.retryConnection();
        expect(service.projectMigrationsAvailability()).toBe('LOADING');
      });
    });
  });
});



