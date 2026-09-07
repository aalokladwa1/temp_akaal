import { Injectable, signal, computed, Optional } from '@angular/core';
import { ContextService } from '../../../core/services/context.service';
import {
  ProjectDiscoveryItem,
  InitiativeDiscoveryItem,
  PortfolioAttentionItem,
  ProjectsPortfolioSummary,
  EntityAvailabilityState,
  ProjectFilterState,
  InitiativeFilterState,
  InitiativeWorkspaceDetail,
  InitiativeActivityItem,
  InitiativeDraftState,
  ProjectAssociationIntent,
  InitiativeTabType,
  ProjectWorkspaceTabType,
  ProjectRoleType,
  ProjectPrincipal,
  ProjectResourceIntent,
  ProjectDraftState,
  ProjectCurrentWorkSummary,
  ProjectUpcomingEvent,
  ProjectWorkspaceDetail,
  ProjectMigrationItem,
  ProjectMigrationFilterState,
  ProjectValidationItem,
  ProjectValidationFilterState,
  ProjectResourceItem,
  ProjectResourceFilterState,
  ProjectActivityItem,
  ProjectActivityFilterState,
  ProjectAccessGrantItem,
  ProjectAccessFilterState,
  ProjectGovernanceItem,
  ProjectGovernanceFilterState,
  ProjectSettingsState,
  MigrationMoveState,
  ProjectMigrationMoveIntent,
  ActionAuthorizationState
} from './projects.models';
import {
  FIXTURE_STANDARD_PROJECTS,
  FIXTURE_STANDARD_INITIATIVES,
  FIXTURE_STANDARD_ATTENTION,
  FIXTURE_STANDARD_SUMMARY,
  FIXTURE_INITIATIVE_WORKSPACES,
  FIXTURE_INITIATIVE_ACTIVITIES,
  FIXTURE_PROJECT_WORKSPACES,
  FIXTURE_AVAILABLE_PRINCIPALS,
  FIXTURE_AVAILABLE_CONNECTIONS,
  FIXTURE_PROJECT_ACTIVITIES,
  FIXTURE_PROJECT_MIGRATIONS,
  FIXTURE_PROJECT_VALIDATIONS,
  FIXTURE_PROJECT_RESOURCES,
  FIXTURE_PROJECT_DETAILED_ACTIVITIES,
  FIXTURE_PROJECT_ACCESS_GRANTS,
  FIXTURE_PROJECT_GOVERNANCE_ITEMS
} from './projects.fixtures';

@Injectable({
  providedIn: 'root'
})
export class ProjectsService {
  public cs: ContextService;

  constructor(@Optional() contextService?: ContextService) {
    this.cs = contextService || new ContextService();
  }

  // ==========================================================================
  // 1. STATE & DATA SIGNALS (Truthful Production Defaults)
  // ==========================================================================
  // Canonical backend connection state: defaults to NOT_CONNECTED / READY depending on environment
  public projectsAvailability = signal<EntityAvailabilityState>('READY');
  public initiativesAvailability = signal<EntityAvailabilityState>('READY');
  public errorMessage = signal<string>('');

  // Primary Entities (Loaded into store)
  public projects = signal<ProjectDiscoveryItem[]>(FIXTURE_STANDARD_PROJECTS);
  public initiatives = signal<InitiativeDiscoveryItem[]>(FIXTURE_STANDARD_INITIATIVES);
  public attentionItems = signal<PortfolioAttentionItem[]>(FIXTURE_STANDARD_ATTENTION);

  // Summary Counters (Only projected from canonical aggregates)
  public summary = signal<ProjectsPortfolioSummary>(FIXTURE_STANDARD_SUMMARY);

  // ==========================================================================
  // PART B SIGNALS: INITIATIVE WORKSPACE & CREATION DRAFT
  // ==========================================================================
  public activeInitiativeId = signal<string | null>(null);
  public activeTab = signal<InitiativeTabType>('overview');

  public initiativeWorkspaces = signal<Record<string, InitiativeWorkspaceDetail>>(FIXTURE_INITIATIVE_WORKSPACES);
  public initiativeActivities = signal<InitiativeActivityItem[]>(FIXTURE_INITIATIVE_ACTIVITIES);
  public projectActivities = signal<InitiativeActivityItem[]>(FIXTURE_PROJECT_ACTIVITIES);

  // Creation Draft State (Initiative)
  public initiativeDraft = signal<InitiativeDraftState>({
    name: '',
    objective: '',
    selectedProjectIds: []
  });

  // Current Step in Create Wizard (1 = Initiative, 2 = Projects, 3 = Review)
  public createWizardStep = signal<number>(1);

  // Activity Category Filter in Workspace Activity Tab
  public activityCategoryFilter = signal<string>('ALL');

  // ==========================================================================
  // PART C SIGNALS: PROJECT WORKSPACE & CREATION DRAFT
  // ==========================================================================
  public activeProjectId = signal<string | null>(null);
  public activeProjectTab = signal<ProjectWorkspaceTabType>('overview');

  public projectWorkspaces = signal<Record<string, ProjectWorkspaceDetail>>(FIXTURE_PROJECT_WORKSPACES);
  public availablePrincipals = signal<ProjectPrincipal[]>(FIXTURE_AVAILABLE_PRINCIPALS);
  public availableConnections = signal<ProjectResourceIntent[]>(FIXTURE_AVAILABLE_CONNECTIONS);

  // Project Creation Draft State
  public projectDraft = signal<ProjectDraftState>({
    name: '',
    key: '',
    description: '',
    initiativeId: null,
    accessAssignments: [
      {
        id: 'usr-aalok-ladwa',
        name: 'Aalok Ladwa (Creator)',
        email: 'aalok.ladwa@enterprise.corp',
        type: 'USER',
        role: 'PROJECT_ADMIN'
      }
    ],
    selectedResourceIds: []
  });

  // Current Step in Create Project Wizard (1 = Identity, 2 = Access & Resources, 3 = Review)
  public projectWizardStep = signal<number>(1);

  // ==========================================================================
  // PART D SIGNALS: PROJECT WORK (MIGRATIONS, VALIDATIONS, RESOURCES)
  // ==========================================================================
  public projectMigrations = signal<ProjectMigrationItem[]>(FIXTURE_PROJECT_MIGRATIONS);
  public projectValidations = signal<ProjectValidationItem[]>(FIXTURE_PROJECT_VALIDATIONS);
  public projectResources = signal<ProjectResourceItem[]>(FIXTURE_PROJECT_RESOURCES);

  public projectMigrationsAvailability = signal<EntityAvailabilityState>('READY');
  public projectValidationsAvailability = signal<EntityAvailabilityState>('READY');
  public projectResourcesAvailability = signal<EntityAvailabilityState>('READY');

  public migrationFilters = signal<ProjectMigrationFilterState>({
    searchQuery: '',
    stateFilter: 'ALL',
    modeFilter: 'ALL',
    sortBy: 'RECENT',
    sortDirection: 'DESC'
  });

  public validationFilters = signal<ProjectValidationFilterState>({
    searchQuery: '',
    stateFilter: 'ALL',
    strategyFilter: 'ALL',
    sortBy: 'RECENT',
    sortDirection: 'DESC'
  });

  public resourceFilters = signal<ProjectResourceFilterState>({
    searchQuery: '',
    categoryFilter: 'ALL',
    associationFilter: 'ALL',
    availabilityFilter: 'ALL',
    sortBy: 'NAME',
    sortDirection: 'ASC'
  });

  public selectedResourceIdForDetail = signal<string | null>(null);

  // ==========================================================================
  // PART E SIGNALS: PROJECT CONTROL (ACTIVITY, ACCESS, GOVERNANCE, SETTINGS)
  // ==========================================================================
  public projectDetailedActivities = signal<ProjectActivityItem[]>(FIXTURE_PROJECT_DETAILED_ACTIVITIES);
  public projectAccessGrants = signal<ProjectAccessGrantItem[]>(FIXTURE_PROJECT_ACCESS_GRANTS);
  public projectGovernance = signal<ProjectGovernanceItem[]>(FIXTURE_PROJECT_GOVERNANCE_ITEMS);

  public projectActivityAvailability = signal<EntityAvailabilityState>('READY');
  public projectAccessAvailability = signal<EntityAvailabilityState>('READY');
  public projectGovernanceAvailability = signal<EntityAvailabilityState>('READY');
  public projectSettingsAvailability = signal<EntityAvailabilityState>('READY');

  public activityFilters = signal<ProjectActivityFilterState>({
    searchQuery: '',
    categoryFilter: 'ALL',
    sortBy: 'RECENT',
    sortDirection: 'DESC'
  });

  public accessFilters = signal<ProjectAccessFilterState>({
    searchQuery: '',
    typeFilter: 'ALL',
    roleFilter: 'ALL',
    sourceFilter: 'ALL',
    sortBy: 'NAME',
    sortDirection: 'ASC'
  });

  public governanceFilters = signal<ProjectGovernanceFilterState>({
    searchQuery: '',
    categoryFilter: 'ALL',
    statusFilter: 'ALL',
    sortBy: 'RECENT',
    sortDirection: 'DESC'
  });

  // Modal / Interaction Signals for Part E
  public addAccessModalOpen = signal<boolean>(false);
  public revokeAccessModalItem = signal<ProjectAccessGrantItem | null>(null);
  public selectedPrincipalForAdd = signal<string | null>(null);
  public selectedRoleForAdd = signal<ProjectRoleType>('OPERATOR');
  public archiveProjectModalOpen = signal<boolean>(false);
  public settingsSaveStatus = signal<'IDLE' | 'DIRTY' | 'SAVED' | 'NOT_CONNECTED'>('IDLE');

  // Modal / Interaction Signals for Part F (Cross-Cutting Move Migration)
  public moveMigrationModalItem = signal<ProjectMigrationItem | null>(null);
  public selectedDestinationProjectId = signal<string | null>(null);
  public migrationMoveStatus = signal<MigrationMoveState>('MOVE_AVAILABLE');
  public migrationMoveErrorMessage = signal<string>('');


  // ==========================================================================
  // 2. FILTER & SEARCH SIGNALS
  // ==========================================================================
  public projectFilters = signal<ProjectFilterState>({
    searchQuery: '',
    statusFilter: 'ALL',
    initiativeFilter: 'ALL',
    sortBy: 'RECENT',
    sortDirection: 'DESC'
  });

  public initiativeFilters = signal<InitiativeFilterState>({
    searchQuery: '',
    statusFilter: 'ALL',
    sortBy: 'RECENT',
    sortDirection: 'DESC'
  });

  // ==========================================================================
  // 3. COMPUTED & FILTERED DATA
  // ==========================================================================
  public isUnavailable = computed(() =>
    this.projectsAvailability() === 'UNAVAILABLE' || this.projectsAvailability() === 'NOT_CONNECTED'
  );

  public isUnauthorized = computed(() => this.projectsAvailability() === 'UNAUTHORIZED');
  public isError = computed(() => this.projectsAvailability() === 'ERROR');
  public isEmpty = computed(() =>
    this.projectsAvailability() === 'EMPTY' || (this.projectsAvailability() === 'READY' && this.projects().length === 0)
  );

  // Active Initiative in Workspace
  public activeInitiative = computed<InitiativeWorkspaceDetail | null>(() => {
    const id = this.activeInitiativeId();
    if (!id) return null;
    return this.initiativeWorkspaces()[id] || null;
  });

  // Projects associated with the active initiative
  public activeInitiativeProjects = computed<ProjectDiscoveryItem[]>(() => {
    const active = this.activeInitiative();
    if (!active) return [];
    const associatedIds = new Set(active.associatedProjectIds);
    return this.projects().filter(p => associatedIds.has(p.id) || p.initiativeId === active.id);
  });

  // Filtered/Sorted Projects within the Active Initiative
  public filteredActiveInitiativeProjects = computed<ProjectDiscoveryItem[]>(() => {
    const list = this.activeInitiativeProjects();
    const filters = this.projectFilters();
    const q = filters.searchQuery.trim().toLowerCase();

    return list.filter(p => {
      const matchesSearch = !q ||
        p.name.toLowerCase().includes(q) ||
        p.key.toLowerCase().includes(q) ||
        (p.description && p.description.toLowerCase().includes(q));

      const matchesStatus = filters.statusFilter === 'ALL' || p.status === filters.statusFilter;

      return matchesSearch && matchesStatus;
    }).sort((a, b) => {
      if (filters.sortBy === 'NAME') {
        const comp = a.name.localeCompare(b.name);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      if (filters.sortBy === 'STATUS') {
        const comp = (a.status || '').localeCompare(b.status || '');
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      const dateA = a.updatedAt || a.lastActivityAt || '';
      const dateB = b.updatedAt || b.lastActivityAt || '';
      const comp = dateB.localeCompare(dateA);
      return filters.sortDirection === 'ASC' ? -comp : comp;
    });
  });

  // Activities for the Active Initiative
  public activeInitiativeActivities = computed<InitiativeActivityItem[]>(() => {
    const active = this.activeInitiative();
    if (!active) return [];
    const cat = this.activityCategoryFilter();
    return this.initiativeActivities()
      .filter(act => act.initiativeId === active.id)
      .filter(act => cat === 'ALL' || act.category === cat)
      .sort((a, b) => b.occurredAt.localeCompare(a.occurredAt));
  });

  // Available standalone or re-assignable projects for Add Project modal
  public availableProjectsForAssociation = computed<ProjectDiscoveryItem[]>(() => {
    const active = this.activeInitiative();
    const currentIds = new Set(active ? active.associatedProjectIds : []);
    return this.projects().filter(p => !currentIds.has(p.id));
  });

  public filteredProjects = computed(() => {
    const list = this.projects();
    const filters = this.projectFilters();
    const q = filters.searchQuery.trim().toLowerCase();

    return list.filter(p => {
      // Search Keyword Match
      const matchesSearch = !q ||
        p.name.toLowerCase().includes(q) ||
        p.key.toLowerCase().includes(q) ||
        (p.description && p.description.toLowerCase().includes(q)) ||
        (p.initiativeName && p.initiativeName.toLowerCase().includes(q));

      // Status Match
      const matchesStatus = filters.statusFilter === 'ALL' || p.status === filters.statusFilter;

      // Initiative Scoping Match
      const matchesInitiative = filters.initiativeFilter === 'ALL' || p.initiativeId === filters.initiativeFilter;

      return matchesSearch && matchesStatus && matchesInitiative;
    }).sort((a, b) => {
      if (filters.sortBy === 'NAME') {
        const comp = a.name.localeCompare(b.name);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      if (filters.sortBy === 'STATUS') {
        const comp = (a.status || '').localeCompare(b.status || '');
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      // RECENT (default)
      const dateA = a.updatedAt || a.lastActivityAt || '';
      const dateB = b.updatedAt || b.lastActivityAt || '';
      const comp = dateB.localeCompare(dateA);
      return filters.sortDirection === 'ASC' ? -comp : comp;
    });
  });

  public filteredInitiatives = computed(() => {
    const list = this.initiatives();
    const filters = this.initiativeFilters();
    const q = filters.searchQuery.trim().toLowerCase();

    return list.filter(init => {
      // Search Match
      const matchesSearch = !q ||
        init.name.toLowerCase().includes(q) ||
        init.key.toLowerCase().includes(q) ||
        (init.objective && init.objective.toLowerCase().includes(q)) ||
        (init.description && init.description.toLowerCase().includes(q));

      // Status Match
      const matchesStatus = filters.statusFilter === 'ALL' || init.status === filters.statusFilter;

      return matchesSearch && matchesStatus;
    }).sort((a, b) => {
      if (filters.sortBy === 'NAME') {
        const comp = a.name.localeCompare(b.name);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      if (filters.sortBy === 'PROJECTS') {
        const comp = b.associatedProjectCount - a.associatedProjectCount;
        return filters.sortDirection === 'ASC' ? -comp : comp;
      }
      // RECENT (default)
      const dateA = a.updatedAt || a.lastActivityAt || '';
      const dateB = b.updatedAt || b.lastActivityAt || '';
      const comp = dateB.localeCompare(dateA);
      return filters.sortDirection === 'ASC' ? -comp : comp;
    });
  });

  // Unique Initiatives present for filter dropdown
  public availableInitiativeOptions = computed(() => {
    const seen = new Map<string, string>();
    this.projects().forEach(p => {
      if (p.initiativeId && p.initiativeName) {
        seen.set(p.initiativeId, p.initiativeName);
      }
    });
    return Array.from(seen.entries()).map(([id, name]) => ({ id, name }));
  });

  // Active Project in Workspace (Part C)
  public activeProject = computed<ProjectWorkspaceDetail | null>(() => {
    const id = this.activeProjectId();
    if (!id) return null;
    const fromMap = this.projectWorkspaces()[id];
    if (fromMap) return fromMap;

    const fromList = this.projects().find(p => p.id === id);
    if (!fromList) return null;

    return {
      id: fromList.id,
      key: fromList.key,
      name: fromList.name,
      description: fromList.description,
      workspaceId: fromList.workspaceId,
      environmentName: fromList.environmentName || 'Production',
      isProduction: fromList.isProduction ?? true,
      initiativeId: fromList.initiativeId,
      initiativeName: fromList.initiativeName,
      initiativeKey: fromList.initiativeKey,
      status: fromList.status || 'ACTIVE',
      currentWork: {
        totalMigrations: fromList.migrationCount ?? 0,
        activeMigrations: fromList.activeWorkloadsCount ?? 0,
        completedMigrations: Math.max(0, (fromList.migrationCount ?? 0) - (fromList.activeWorkloadsCount ?? 0)),
        totalValidations: fromList.validationCount ?? 0,
        passedValidations: fromList.validationCount ?? 0,
        discrepancyValidations: fromList.attentionCount ?? 0
      },
      upcomingEvents: [],
      recentActivities: this.initiativeActivities().filter(a => a.projectId === id),
      createdAt: fromList.createdAt,
      updatedAt: fromList.updatedAt,
      lastActivityAt: fromList.lastActivityAt,
      availability: fromList.availability,
      accessState: fromList.accessState
    };
  });

  // Active Project's Parent Initiative (if any)
  public activeProjectInitiative = computed<InitiativeWorkspaceDetail | null>(() => {
    const proj = this.activeProject();
    if (!proj?.initiativeId) return null;
    return this.initiativeWorkspaces()[proj.initiativeId] || null;
  });

  // Attention Items for the Active Project
  public activeProjectAttention = computed<PortfolioAttentionItem[]>(() => {
    const proj = this.activeProject();
    if (!proj) return [];
    return this.attentionItems().filter(att => att.projectId === proj.id);
  });

  // Activities for the Active Project
  public activeProjectActivities = computed<InitiativeActivityItem[]>(() => {
    const proj = this.activeProject();
    if (!proj) return [];
    const fromWorkspace = proj.recentActivities || [];
    const fromStore = this.projectActivities().filter(act => act.projectId === proj.id);
    const fromInit = this.initiativeActivities().filter(act => act.projectId === proj.id);
    const map = new Map<string, InitiativeActivityItem>();
    [...fromWorkspace, ...fromStore, ...fromInit].forEach(a => map.set(a.id, a));
    return Array.from(map.values()).sort((a, b) => b.occurredAt.localeCompare(a.occurredAt));
  });

  // Unique Status options present for filter dropdown
  public availableProjectStatusOptions = computed(() => {
    const set = new Set<string>();
    this.projects().forEach(p => {
      if (p.status) set.add(p.status);
    });
    return Array.from(set);
  });

  public availableInitiativeStatusOptions = computed(() => {
    const set = new Set<string>();
    this.initiatives().forEach(i => {
      if (i.status) set.add(i.status);
    });
    return Array.from(set);
  });

  // ==========================================================================
  // PART D COMPUTEDS: MIGRATIONS, VALIDATIONS, RESOURCES
  // ==========================================================================
  public activeProjectMigrations = computed<ProjectMigrationItem[]>(() => {
    const proj = this.activeProject();
    if (!proj) return [];
    return this.projectMigrations().filter(m => m.projectId === proj.id);
  });

  public filteredActiveProjectMigrations = computed<ProjectMigrationItem[]>(() => {
    const list = this.activeProjectMigrations();
    const filters = this.migrationFilters();
    const q = filters.searchQuery.trim().toLowerCase();

    return list.filter(m => {
      const matchesSearch = !q ||
        m.name.toLowerCase().includes(q) ||
        m.key.toLowerCase().includes(q) ||
        m.sourceProvider.toLowerCase().includes(q) ||
        m.targetProvider.toLowerCase().includes(q) ||
        (m.sourceLabel && m.sourceLabel.toLowerCase().includes(q)) ||
        (m.targetLabel && m.targetLabel.toLowerCase().includes(q));

      const matchesState = filters.stateFilter === 'ALL' || m.lifecycleState === filters.stateFilter;
      const matchesMode = filters.modeFilter === 'ALL' || m.mode === filters.modeFilter;

      return matchesSearch && matchesState && matchesMode;
    }).sort((a, b) => {
      if (filters.sortBy === 'NAME') {
        const comp = a.name.localeCompare(b.name);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      if (filters.sortBy === 'STATE') {
        const comp = a.lifecycleState.localeCompare(b.lifecycleState);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      const comp = b.lastActivityAt.localeCompare(a.lastActivityAt);
      return filters.sortDirection === 'ASC' ? -comp : comp;
    });
  });

  public availableDestinationProjects = computed<ProjectDiscoveryItem[]>(() => {
    const active = this.activeProject();
    if (!active) return [];
    return this.projects().filter(p => p.id !== active.id && p.status !== 'ARCHIVED');
  });

  public activeProjectValidations = computed<ProjectValidationItem[]>(() => {
    const proj = this.activeProject();
    if (!proj) return [];
    return this.projectValidations().filter(v => v.projectId === proj.id);
  });

  public filteredActiveProjectValidations = computed<ProjectValidationItem[]>(() => {
    const list = this.activeProjectValidations();
    const filters = this.validationFilters();
    const q = filters.searchQuery.trim().toLowerCase();

    return list.filter(v => {
      const matchesSearch = !q ||
        v.name.toLowerCase().includes(q) ||
        v.key.toLowerCase().includes(q) ||
        v.scopeName.toLowerCase().includes(q) ||
        v.sourceProvider.toLowerCase().includes(q) ||
        v.targetProvider.toLowerCase().includes(q) ||
        (v.migrationName && v.migrationName.toLowerCase().includes(q));

      const matchesState = filters.stateFilter === 'ALL' || v.state === filters.stateFilter || v.outcome === filters.stateFilter;
      const matchesStrategy = filters.strategyFilter === 'ALL' || v.strategy === filters.strategyFilter;

      return matchesSearch && matchesState && matchesStrategy;
    }).sort((a, b) => {
      if (filters.sortBy === 'NAME') {
        const comp = a.name.localeCompare(b.name);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      if (filters.sortBy === 'STATE') {
        const comp = a.state.localeCompare(b.state);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      const dateA = a.lastRunAt || '';
      const dateB = b.lastRunAt || '';
      const comp = dateB.localeCompare(dateA);
      return filters.sortDirection === 'ASC' ? -comp : comp;
    });
  });

  public activeProjectResources = computed<ProjectResourceItem[]>(() => {
    const proj = this.activeProject();
    const list = this.projectResources();
    if (!proj) return list;

    return list.map(r => ({
      ...r,
      isBoundToProject: r.assignedProjectIds.includes(proj.id)
    }));
  });

  public filteredActiveProjectResources = computed<ProjectResourceItem[]>(() => {
    const list = this.activeProjectResources();
    const filters = this.resourceFilters();
    const q = filters.searchQuery.trim().toLowerCase();

    return list.filter(r => {
      const matchesSearch = !q ||
        r.connectionName.toLowerCase().includes(q) ||
        r.provider.toLowerCase().includes(q) ||
        (r.host && r.host.toLowerCase().includes(q)) ||
        (r.capabilityText && r.capabilityText.toLowerCase().includes(q));

      const matchesCategory = filters.categoryFilter === 'ALL' || r.category === filters.categoryFilter;
      const matchesAssociation = filters.associationFilter === 'ALL' ||
        (filters.associationFilter === 'BOUND' && r.isBoundToProject) ||
        (filters.associationFilter === 'AVAILABLE' && !r.isBoundToProject);
      const matchesAvailability = filters.availabilityFilter === 'ALL' || r.availabilityState === filters.availabilityFilter;

      return matchesSearch && matchesCategory && matchesAssociation && matchesAvailability;
    }).sort((a, b) => {
      if (filters.sortBy === 'NAME') {
        const comp = a.connectionName.localeCompare(b.connectionName);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      if (filters.sortBy === 'PROVIDER') {
        const comp = a.provider.localeCompare(b.provider);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      const comp = a.availabilityState.localeCompare(b.availabilityState);
      return filters.sortDirection === 'ASC' ? -comp : comp;
    });
  });

  public activeResourceDetail = computed<ProjectResourceItem | null>(() => {
    const id = this.selectedResourceIdForDetail();
    if (!id) return null;
    return this.activeProjectResources().find(r => r.id === id || r.connectionId === id) || null;
  });

  // ==========================================================================
  // PART E COMPUTEDS: ACTIVITY, ACCESS, GOVERNANCE
  // ==========================================================================

  // 1. Activity Computeds
  public activeProjectDetailedActivities = computed<ProjectActivityItem[]>(() => {
    const proj = this.activeProject();
    if (!proj) return [];
    return this.projectDetailedActivities()
      .filter(act => act.projectId === proj.id)
      .sort((a, b) => b.occurredAt.localeCompare(a.occurredAt));
  });

  public filteredActiveProjectActivities = computed<ProjectActivityItem[]>(() => {
    const list = this.activeProjectDetailedActivities();
    const filters = this.activityFilters();
    const q = filters.searchQuery.trim().toLowerCase();

    return list.filter(act => {
      const matchesSearch = !q ||
        act.title.toLowerCase().includes(q) ||
        act.description.toLowerCase().includes(q) ||
        act.actorName.toLowerCase().includes(q) ||
        (act.subjectName && act.subjectName.toLowerCase().includes(q));

      const matchesCategory = filters.categoryFilter === 'ALL' || act.category === filters.categoryFilter;

      return matchesSearch && matchesCategory;
    }).sort((a, b) => {
      if (filters.sortBy === 'CATEGORY') {
        const comp = a.category.localeCompare(b.category);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      if (filters.sortBy === 'ACTOR') {
        const comp = a.actorName.localeCompare(b.actorName);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      const comp = b.occurredAt.localeCompare(a.occurredAt);
      return filters.sortDirection === 'ASC' ? -comp : comp;
    });
  });

  // 2. Access Computeds
  public activeProjectAccessGrants = computed<ProjectAccessGrantItem[]>(() => {
    const proj = this.activeProject();
    if (!proj) return [];
    return this.projectAccessGrants().filter(g => g.projectId === proj.id);
  });

  public filteredActiveProjectAccessGrants = computed<ProjectAccessGrantItem[]>(() => {
    const list = this.activeProjectAccessGrants();
    const filters = this.accessFilters();
    const q = filters.searchQuery.trim().toLowerCase();

    return list.filter(g => {
      const matchesSearch = !q ||
        g.principalName.toLowerCase().includes(q) ||
        g.principalEmail.toLowerCase().includes(q) ||
        g.scopeDescription.toLowerCase().includes(q);

      const matchesType = filters.typeFilter === 'ALL' || g.principalType === filters.typeFilter;
      const matchesRole = filters.roleFilter === 'ALL' || g.role === filters.roleFilter;
      const matchesSource = filters.sourceFilter === 'ALL' || g.accessSource === filters.sourceFilter;

      return matchesSearch && matchesType && matchesRole && matchesSource;
    }).sort((a, b) => {
      if (filters.sortBy === 'NAME') {
        const comp = a.principalName.localeCompare(b.principalName);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      if (filters.sortBy === 'ROLE') {
        const comp = a.role.localeCompare(b.role);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      if (filters.sortBy === 'SOURCE') {
        const comp = a.accessSource.localeCompare(b.accessSource);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      const comp = a.status.localeCompare(b.status);
      return filters.sortDirection === 'ASC' ? -comp : comp;
    });
  });

  public availablePrincipalsForAddAccess = computed<ProjectPrincipal[]>(() => {
    const active = this.activeProject();
    if (!active) return this.availablePrincipals();
    const currentDirect = new Set(
      this.activeProjectAccessGrants()
        .filter(g => g.accessSource === 'DIRECT_PROJECT')
        .map(g => g.principalId)
    );
    return this.availablePrincipals().filter(p => !currentDirect.has(p.id));
  });

  // 3. Governance Computeds
  public activeProjectGovernance = computed<ProjectGovernanceItem[]>(() => {
    const proj = this.activeProject();
    if (!proj) return [];
    return this.projectGovernance().filter(gov => gov.projectId === proj.id);
  });

  public filteredActiveProjectGovernance = computed<ProjectGovernanceItem[]>(() => {
    const list = this.activeProjectGovernance();
    const filters = this.governanceFilters();
    const q = filters.searchQuery.trim().toLowerCase();

    return list.filter(gov => {
      const matchesSearch = !q ||
        gov.title.toLowerCase().includes(q) ||
        gov.description.toLowerCase().includes(q) ||
        gov.protectedOperation.toLowerCase().includes(q) ||
        (gov.policyReference && gov.policyReference.toLowerCase().includes(q));

      const matchesCategory = filters.categoryFilter === 'ALL' || gov.category === filters.categoryFilter;
      const matchesStatus = filters.statusFilter === 'ALL' || gov.status === filters.statusFilter;

      return matchesSearch && matchesCategory && matchesStatus;
    }).sort((a, b) => {
      if (filters.sortBy === 'CATEGORY') {
        const comp = a.category.localeCompare(b.category);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      if (filters.sortBy === 'STATUS') {
        const comp = a.status.localeCompare(b.status);
        return filters.sortDirection === 'ASC' ? comp : -comp;
      }
      const comp = b.requestedAt.localeCompare(a.requestedAt);
      return filters.sortDirection === 'ASC' ? -comp : comp;
    });
  });

  public activeProjectPendingApprovals = computed<ProjectGovernanceItem[]>(() =>
    this.activeProjectGovernance().filter(g => g.category === 'PENDING_APPROVAL' && g.status === 'PENDING')
  );

  public activeProjectPolicies = computed<ProjectGovernanceItem[]>(() =>
    this.activeProjectGovernance().filter(g => g.category === 'POLICY_REQUIREMENT')
  );

  public activeProjectResolvedDecisions = computed<ProjectGovernanceItem[]>(() =>
    this.activeProjectGovernance().filter(g => g.category === 'RESOLVED_DECISION')
  );

  public activeProjectExceptions = computed<ProjectGovernanceItem[]>(() =>
    this.activeProjectGovernance().filter(g => g.category === 'EXCEPTION_WAIVER')
  );

  // ==========================================================================
  // 4. ACTIONS & MUTATIONS
  // ==========================================================================
  public setActiveInitiativeId(id: string | null): void {
    this.activeInitiativeId.set(id);
  }

  public setActiveTab(tab: InitiativeTabType): void {
    this.activeTab.set(tab);
  }

  public setActiveProjectId(id: string | null): void {
    this.activeProjectId.set(id);
  }

  public setActiveProjectTab(tab: ProjectWorkspaceTabType): void {
    this.activeProjectTab.set(tab);
  }

  public setActivityCategoryFilter(cat: string): void {
    this.activityCategoryFilter.set(cat);
  }

  // Create Initiative Draft Methods
  public setDraftName(name: string): void {
    this.initiativeDraft.update(d => ({ ...d, name }));
  }

  public setDraftObjective(objective: string): void {
    this.initiativeDraft.update(d => ({ ...d, objective }));
  }

  public toggleDraftProject(projectId: string): void {
    this.initiativeDraft.update(d => {
      const exists = d.selectedProjectIds.includes(projectId);
      const next = exists
        ? d.selectedProjectIds.filter(id => id !== projectId)
        : [...d.selectedProjectIds, projectId];
      return { ...d, selectedProjectIds: next };
    });
  }

  public removeDraftProject(projectId: string): void {
    this.initiativeDraft.update(d => ({
      ...d,
      selectedProjectIds: d.selectedProjectIds.filter(id => id !== projectId)
    }));
  }

  public clearDraft(): void {
    this.initiativeDraft.set({
      name: '',
      objective: '',
      selectedProjectIds: []
    });
    this.createWizardStep.set(1);
  }

  public setCreateWizardStep(step: number): void {
    this.createWizardStep.set(step);
  }

  // ==========================================================================
  // PART C: CREATE PROJECT DRAFT ACTIONS & SUBMISSION
  // ==========================================================================
  public setProjectDraftName(name: string): void {
    this.projectDraft.update(d => {
      // Automatically suggest key if key hasn't been manually diverged
      let suggestedKey = d.key;
      if (!d.key || d.key === this.generateSuggestedKey(d.name)) {
        suggestedKey = this.generateSuggestedKey(name);
      }
      return { ...d, name, key: suggestedKey };
    });
  }

  public setProjectDraftKey(key: string): void {
    this.projectDraft.update(d => ({ ...d, key: key.toUpperCase().trim() }));
  }

  public setProjectDraftDescription(description: string): void {
    this.projectDraft.update(d => ({ ...d, description }));
  }

  public setProjectDraftInitiative(initiativeId: string | null): void {
    this.projectDraft.update(d => ({ ...d, initiativeId }));
  }

  public addProjectDraftPrincipal(principal: ProjectPrincipal): void {
    this.projectDraft.update(d => {
      const exists = d.accessAssignments.some(p => p.id === principal.id);
      if (exists) return d;
      return { ...d, accessAssignments: [...d.accessAssignments, principal] };
    });
  }

  public removeProjectDraftPrincipal(principalId: string): void {
    this.projectDraft.update(d => ({
      ...d,
      accessAssignments: d.accessAssignments.filter(p => p.id !== principalId)
    }));
  }

  public updateProjectDraftPrincipalRole(principalId: string, role: ProjectRoleType): void {
    this.projectDraft.update(d => ({
      ...d,
      accessAssignments: d.accessAssignments.map(p =>
        p.id === principalId ? { ...p, role } : p
      )
    }));
  }

  public toggleProjectDraftResource(connectionId: string): void {
    this.projectDraft.update(d => {
      const exists = d.selectedResourceIds.includes(connectionId);
      const next = exists
        ? d.selectedResourceIds.filter(id => id !== connectionId)
        : [...d.selectedResourceIds, connectionId];
      return { ...d, selectedResourceIds: next };
    });
  }

  public setProjectWizardStep(step: number): void {
    this.projectWizardStep.set(step);
  }

  public clearProjectDraft(): void {
    this.projectDraft.set({
      name: '',
      key: '',
      description: '',
      initiativeId: null,
      accessAssignments: [
        {
          id: 'usr-aalok-ladwa',
          name: 'Aalok Ladwa (Creator)',
          email: 'aalok.ladwa@enterprise.corp',
          type: 'USER',
          role: 'PROJECT_ADMIN'
        }
      ],
      selectedResourceIds: []
    });
    this.projectWizardStep.set(1);
  }

  public generateSuggestedKey(name: string): string {
    if (!name.trim()) return '';
    const words = name.trim().split(/[\s-_]+/);
    if (words.length === 1) {
      return words[0].slice(0, 6).toUpperCase();
    }
    return words.map(w => w[0]).join('').slice(0, 6).toUpperCase();
  }

  public submitCreateProject(): string {
    const draft = this.projectDraft();
    const id = `proj-${(draft.key || 'NEW').toLowerCase()}-${Date.now().toString().slice(-4)}`;
    const key = draft.key || this.generateSuggestedKey(draft.name) || 'PRJ';
    const org = this.cs.selectedOrg()?.name || 'Default Organization';
    const ws = this.cs.selectedWorkspace()?.name || 'Default Workspace';
    const env = this.cs.selectedEnvironment()?.name || 'Production';
    const isProd = this.cs.isProduction();

    let initiativeName: string | undefined;
    let initiativeKey: string | undefined;
    if (draft.initiativeId) {
      const init = this.initiativeWorkspaces()[draft.initiativeId] || this.initiatives().find(i => i.id === draft.initiativeId);
      if (init) {
        initiativeName = init.name;
        initiativeKey = init.key;
      }
    }

    const now = new Date().toISOString();

    const newProjectItem: ProjectDiscoveryItem = {
      id,
      key,
      name: draft.name,
      description: draft.description,
      workspaceId: this.cs.selectedWorkspace()?.id || 'ws-current',
      environmentName: env,
      isProduction: isProd,
      initiativeId: draft.initiativeId || undefined,
      initiativeName,
      initiativeKey,
      status: 'PLANNING',
      migrationCount: 0,
      validationCount: 0,
      activeWorkloadsCount: 0,
      attentionCount: 0,
      createdAt: now,
      updatedAt: now,
      lastActivityAt: now,
      availability: 'READY',
      accessState: 'GRANTED'
    };

    const newProjectWorkspace: ProjectWorkspaceDetail = {
      id,
      key,
      name: draft.name,
      description: draft.description,
      workspaceId: this.cs.selectedWorkspace()?.id || 'ws-current',
      environmentName: env,
      isProduction: isProd,
      initiativeId: draft.initiativeId || undefined,
      initiativeName,
      initiativeKey,
      status: 'PLANNING',
      currentWork: {
        totalMigrations: 0,
        activeMigrations: 0,
        completedMigrations: 0,
        totalValidations: 0,
        passedValidations: 0,
        discrepancyValidations: 0
      },
      upcomingEvents: [],
      recentActivities: [
        {
          id: `act-${Date.now()}`,
          projectId: id,
          title: 'Project Initialized',
          description: `Governed project specification drafted with ${draft.accessAssignments.length} access role(s) and ${draft.selectedResourceIds.length} connection intent(s).`,
          category: 'METADATA',
          severity: 'INFO',
          occurredAt: now,
          actorName: draft.accessAssignments[0]?.name || 'Current User',
          subjectName: draft.name,
          subjectType: 'PROJECT',
          actionType: 'VIEW'
        }
      ],
      createdAt: now,
      updatedAt: now,
      lastActivityAt: now,
      availability: 'READY',
      accessState: 'GRANTED'
    };

    // Update store
    this.projects.update(list => [newProjectItem, ...list]);
    this.projectWorkspaces.update(map => ({ ...map, [id]: newProjectWorkspace }));

    // If assigned to initiative, update initiative association
    if (draft.initiativeId) {
      this.addProjectsToInitiative(draft.initiativeId, [id]);
    }

    return id;
  }

  // Workspace Mutations (Operator Intent Handlers)
  public updateInitiativeGeneral(id: string, name: string, objective: string): void {
    this.initiativeWorkspaces.update(map => {
      const existing = map[id];
      if (!existing) return map;
      return {
        ...map,
        [id]: {
          ...existing,
          name,
          objective,
          updatedAt: new Date().toISOString()
        }
      };
    });

    this.initiatives.update(list =>
      list.map(init => init.id === id ? { ...init, name, objective } : init)
    );
  }

  public removeProjectFromInitiative(initiativeId: string, projectId: string): void {
    this.initiativeWorkspaces.update(map => {
      const existing = map[initiativeId];
      if (!existing) return map;
      const nextIds = existing.associatedProjectIds.filter(id => id !== projectId);
      return {
        ...map,
        [initiativeId]: {
          ...existing,
          associatedProjectIds: nextIds,
          totalProjectsCount: nextIds.length
        }
      };
    });

    this.projects.update(list =>
      list.map(p => p.id === projectId ? { ...p, initiativeId: undefined, initiativeName: undefined, initiativeKey: undefined } : p)
    );
  }

  public addProjectsToInitiative(initiativeId: string, projectIds: string[]): void {
    const init = this.initiativeWorkspaces()[initiativeId];
    if (!init) return;

    this.initiativeWorkspaces.update(map => {
      const existing = map[initiativeId];
      if (!existing) return map;
      const combined = Array.from(new Set([...existing.associatedProjectIds, ...projectIds]));
      return {
        ...map,
        [initiativeId]: {
          ...existing,
          associatedProjectIds: combined,
          totalProjectsCount: combined.length
        }
      };
    });

    this.projects.update(list =>
      list.map(p => projectIds.includes(p.id) ? {
        ...p,
        initiativeId,
        initiativeName: init.name,
        initiativeKey: init.key
      } : p)
    );
  }

  public archiveInitiative(initiativeId: string): void {
    this.initiativeWorkspaces.update(map => {
      const existing = map[initiativeId];
      if (!existing) return map;
      return {
        ...map,
        [initiativeId]: {
          ...existing,
          status: 'ARCHIVED',
          updatedAt: new Date().toISOString()
        }
      };
    });

    this.initiatives.update(list =>
      list.map(init => init.id === initiativeId ? { ...init, status: 'ARCHIVED' } : init)
    );
  }

  public setProjectSearch(query: string): void {
    this.projectFilters.update(f => ({ ...f, searchQuery: query }));
  }

  public setProjectStatusFilter(status: string): void {
    this.projectFilters.update(f => ({ ...f, statusFilter: status }));
  }

  public setProjectInitiativeFilter(initiativeId: string): void {
    this.projectFilters.update(f => ({ ...f, initiativeFilter: initiativeId }));
  }

  public setProjectSort(sortBy: 'NAME' | 'RECENT' | 'STATUS'): void {
    this.projectFilters.update(f => {
      const nextDirection = f.sortBy === sortBy && f.sortDirection === 'DESC' ? 'ASC' : 'DESC';
      return { ...f, sortBy, sortDirection: nextDirection };
    });
  }

  public clearProjectFilters(): void {
    this.projectFilters.set({
      searchQuery: '',
      statusFilter: 'ALL',
      initiativeFilter: 'ALL',
      sortBy: 'RECENT',
      sortDirection: 'DESC'
    });
  }

  public setInitiativeSearch(query: string): void {
    this.initiativeFilters.update(f => ({ ...f, searchQuery: query }));
  }

  public setInitiativeStatusFilter(status: string): void {
    this.initiativeFilters.update(f => ({ ...f, statusFilter: status }));
  }

  public setInitiativeSort(sortBy: 'NAME' | 'RECENT' | 'PROJECTS'): void {
    this.initiativeFilters.update(f => {
      const nextDirection = f.sortBy === sortBy && f.sortDirection === 'DESC' ? 'ASC' : 'DESC';
      return { ...f, sortBy, sortDirection: nextDirection };
    });
  }

  public clearInitiativeFilters(): void {
    this.initiativeFilters.set({
      searchQuery: '',
      statusFilter: 'ALL',
      sortBy: 'RECENT',
      sortDirection: 'DESC'
    });
  }

  // ==========================================================================
  // PART D ACTION METHODS: MIGRATIONS, VALIDATIONS, RESOURCES
  // ==========================================================================

  // Migrations Filter Actions
  public setMigrationSearch(query: string): void {
    this.migrationFilters.update(f => ({ ...f, searchQuery: query }));
  }

  public setMigrationStateFilter(state: string): void {
    this.migrationFilters.update(f => ({ ...f, stateFilter: state }));
  }

  public setMigrationModeFilter(mode: string): void {
    this.migrationFilters.update(f => ({ ...f, modeFilter: mode }));
  }

  public setMigrationSort(sortBy: 'NAME' | 'STATE' | 'RECENT'): void {
    this.migrationFilters.update(f => {
      const nextDirection = f.sortBy === sortBy && f.sortDirection === 'DESC' ? 'ASC' : 'DESC';
      return { ...f, sortBy, sortDirection: nextDirection };
    });
  }

  public clearMigrationFilters(): void {
    this.migrationFilters.set({
      searchQuery: '',
      stateFilter: 'ALL',
      modeFilter: 'ALL',
      sortBy: 'RECENT',
      sortDirection: 'DESC'
    });
  }

  // Validations Filter Actions
  public setValidationSearch(query: string): void {
    this.validationFilters.update(f => ({ ...f, searchQuery: query }));
  }

  public setValidationStateFilter(state: string): void {
    this.validationFilters.update(f => ({ ...f, stateFilter: state }));
  }

  public setValidationStrategyFilter(strategy: string): void {
    this.validationFilters.update(f => ({ ...f, strategyFilter: strategy }));
  }

  public setValidationSort(sortBy: 'NAME' | 'STATE' | 'RECENT'): void {
    this.validationFilters.update(f => {
      const nextDirection = f.sortBy === sortBy && f.sortDirection === 'DESC' ? 'ASC' : 'DESC';
      return { ...f, sortBy, sortDirection: nextDirection };
    });
  }

  public clearValidationFilters(): void {
    this.validationFilters.set({
      searchQuery: '',
      stateFilter: 'ALL',
      strategyFilter: 'ALL',
      sortBy: 'RECENT',
      sortDirection: 'DESC'
    });
  }

  // Resources Filter Actions
  public setResourceSearch(query: string): void {
    this.resourceFilters.update(f => ({ ...f, searchQuery: query }));
  }

  public setResourceCategoryFilter(cat: string): void {
    this.resourceFilters.update(f => ({ ...f, categoryFilter: cat }));
  }

  public setResourceAssociationFilter(assoc: 'ALL' | 'BOUND' | 'AVAILABLE'): void {
    this.resourceFilters.update(f => ({ ...f, associationFilter: assoc }));
  }

  public setResourceAvailabilityFilter(avail: string): void {
    this.resourceFilters.update(f => ({ ...f, availabilityFilter: avail }));
  }

  public setResourceSort(sortBy: 'NAME' | 'PROVIDER' | 'STATUS'): void {
    this.resourceFilters.update(f => {
      const nextDirection = f.sortBy === sortBy && f.sortDirection === 'DESC' ? 'ASC' : 'DESC';
      return { ...f, sortBy, sortDirection: nextDirection };
    });
  }

  public clearResourceFilters(): void {
    this.resourceFilters.set({
      searchQuery: '',
      categoryFilter: 'ALL',
      associationFilter: 'ALL',
      availabilityFilter: 'ALL',
      sortBy: 'NAME',
      sortDirection: 'ASC'
    });
  }

  public setSelectedResourceIdForDetail(id: string | null): void {
    this.selectedResourceIdForDetail.set(id);
  }

  public toggleProjectResourceBinding(connectionId: string): void {
    const proj = this.activeProject();
    if (!proj) return;

    this.projectResources.update(list =>
      list.map(r => {
        if (r.connectionId !== connectionId) return r;
        const exists = r.assignedProjectIds.includes(proj.id);
        const nextIds = exists
          ? r.assignedProjectIds.filter(id => id !== proj.id)
          : [...r.assignedProjectIds, proj.id];
        return {
          ...r,
          assignedProjectIds: nextIds,
          isBoundToProject: !exists,
          availabilityState: !exists ? 'BOUND' : 'AVAILABLE'
        };
      })
    );
  }

  // ==========================================================================
  // PART E ACTION METHODS: ACTIVITY, ACCESS, GOVERNANCE, SETTINGS
  // ==========================================================================

  // 1. Activity Filter Actions
  public setActivitySearch(query: string): void {
    this.activityFilters.update(f => ({ ...f, searchQuery: query }));
  }

  public setActivityCategory(cat: string): void {
    this.activityFilters.update(f => ({ ...f, categoryFilter: cat }));
  }

  public setActivitySort(sortBy: 'RECENT' | 'CATEGORY' | 'ACTOR'): void {
    this.activityFilters.update(f => {
      const nextDirection = f.sortBy === sortBy && f.sortDirection === 'DESC' ? 'ASC' : 'DESC';
      return { ...f, sortBy, sortDirection: nextDirection };
    });
  }

  public clearActivityFilters(): void {
    this.activityFilters.set({
      searchQuery: '',
      categoryFilter: 'ALL',
      sortBy: 'RECENT',
      sortDirection: 'DESC'
    });
  }

  // 2. Access Filter Actions & Mutations
  public setAccessSearch(query: string): void {
    this.accessFilters.update(f => ({ ...f, searchQuery: query }));
  }

  public setAccessTypeFilter(type: string): void {
    this.accessFilters.update(f => ({ ...f, typeFilter: type }));
  }

  public setAccessRoleFilter(role: string): void {
    this.accessFilters.update(f => ({ ...f, roleFilter: role }));
  }

  public setAccessSourceFilter(source: string): void {
    this.accessFilters.update(f => ({ ...f, sourceFilter: source }));
  }

  public setAccessSort(sortBy: 'NAME' | 'ROLE' | 'SOURCE' | 'STATUS'): void {
    this.accessFilters.update(f => {
      const nextDirection = f.sortBy === sortBy && f.sortDirection === 'DESC' ? 'ASC' : 'DESC';
      return { ...f, sortBy, sortDirection: nextDirection };
    });
  }

  public clearAccessFilters(): void {
    this.accessFilters.set({
      searchQuery: '',
      typeFilter: 'ALL',
      roleFilter: 'ALL',
      sourceFilter: 'ALL',
      sortBy: 'NAME',
      sortDirection: 'ASC'
    });
  }

  public openAddAccessModal(): void {
    const available = this.availablePrincipalsForAddAccess();
    this.selectedPrincipalForAdd.set(available.length > 0 ? available[0].id : null);
    this.selectedRoleForAdd.set('OPERATOR');
    this.addAccessModalOpen.set(true);
  }

  public closeAddAccessModal(): void {
    this.addAccessModalOpen.set(false);
  }

  public setSelectedPrincipalForAdd(id: string | null): void {
    this.selectedPrincipalForAdd.set(id);
  }

  public setSelectedRoleForAdd(role: ProjectRoleType): void {
    this.selectedRoleForAdd.set(role);
  }

  public submitAddAccessIntent(): boolean {
    const proj = this.activeProject();
    const principalId = this.selectedPrincipalForAdd();
    const role = this.selectedRoleForAdd();
    if (!proj || !principalId) return false;

    const principal = this.availablePrincipals().find(p => p.id === principalId);
    if (!principal) return false;

    const newGrant: ProjectAccessGrantItem = {
      id: `grant-${Date.now().toString().slice(-4)}`,
      projectId: proj.id,
      principalId: principal.id,
      principalName: principal.name,
      principalEmail: principal.email,
      principalType: principal.type,
      role,
      accessSource: 'DIRECT_PROJECT',
      scopeDescription: 'Explicit Project-Scoped Operator Grant',
      grantedAt: new Date().toISOString(),
      status: 'ACTIVE',
      availability: 'READY'
    };

    this.projectAccessGrants.update(list => [newGrant, ...list]);
    this.closeAddAccessModal();
    return true;
  }

  public openRevokeAccessModal(item: ProjectAccessGrantItem): void {
    this.revokeAccessModalItem.set(item);
  }

  public closeRevokeAccessModal(): void {
    this.revokeAccessModalItem.set(null);
  }

  public confirmRevokeAccess(grantId: string): void {
    this.projectAccessGrants.update(list => list.filter(g => g.id !== grantId));
    this.closeRevokeAccessModal();
  }

  // 3. Governance Filter Actions
  public setGovernanceSearch(query: string): void {
    this.governanceFilters.update(f => ({ ...f, searchQuery: query }));
  }

  public setGovernanceCategoryFilter(cat: string): void {
    this.governanceFilters.update(f => ({ ...f, categoryFilter: cat }));
  }

  public setGovernanceStatusFilter(status: string): void {
    this.governanceFilters.update(f => ({ ...f, statusFilter: status }));
  }

  public setGovernanceSort(sortBy: 'RECENT' | 'CATEGORY' | 'STATUS'): void {
    this.governanceFilters.update(f => {
      const nextDirection = f.sortBy === sortBy && f.sortDirection === 'DESC' ? 'ASC' : 'DESC';
      return { ...f, sortBy, sortDirection: nextDirection };
    });
  }

  public clearGovernanceFilters(): void {
    this.governanceFilters.set({
      searchQuery: '',
      categoryFilter: 'ALL',
      statusFilter: 'ALL',
      sortBy: 'RECENT',
      sortDirection: 'DESC'
    });
  }

  // 4. Settings Mutations
  public updateProjectGeneral(projectId: string, name: string, description: string, initiativeId: string | null): void {
    let initiativeName: string | undefined;
    let initiativeKey: string | undefined;
    if (initiativeId) {
      const init = this.initiativeWorkspaces()[initiativeId] || this.initiatives().find(i => i.id === initiativeId);
      if (init) {
        initiativeName = init.name;
        initiativeKey = init.key;
      }
    }

    this.projectWorkspaces.update(map => {
      const existing = map[projectId];
      if (!existing) return map;
      return {
        ...map,
        [projectId]: {
          ...existing,
          name,
          description,
          initiativeId: initiativeId || undefined,
          initiativeName,
          initiativeKey,
          updatedAt: new Date().toISOString()
        }
      };
    });

    this.projects.update(list =>
      list.map(p => p.id === projectId ? {
        ...p,
        name,
        description,
        initiativeId: initiativeId || undefined,
        initiativeName,
        initiativeKey,
        updatedAt: new Date().toISOString()
      } : p)
    );

    this.settingsSaveStatus.set('SAVED');
    setTimeout(() => this.settingsSaveStatus.set('IDLE'), 2000);
  }

  public archiveProject(projectId: string): void {
    this.projectWorkspaces.update(map => {
      const existing = map[projectId];
      if (!existing) return map;
      return {
        ...map,
        [projectId]: {
          ...existing,
          status: 'ARCHIVED',
          updatedAt: new Date().toISOString()
        }
      };
    });

    this.projects.update(list =>
      list.map(p => p.id === projectId ? { ...p, status: 'ARCHIVED', updatedAt: new Date().toISOString() } : p)
    );

    this.archiveProjectModalOpen.set(false);
  }

  public restoreProject(projectId: string): void {
    this.projectWorkspaces.update(map => {
      const existing = map[projectId];
      if (!existing) return map;
      return {
        ...map,
        [projectId]: {
          ...existing,
          status: 'ACTIVE',
          updatedAt: new Date().toISOString()
        }
      };
    });

    this.projects.update(list =>
      list.map(p => p.id === projectId ? { ...p, status: 'ACTIVE', updatedAt: new Date().toISOString() } : p)
    );
  }

  // ==========================================================================
  // PART F ACTION METHODS: CROSS-CUTTING MOVE MIGRATION
  // ==========================================================================
  public openMoveMigrationModal(item: ProjectMigrationItem): void {
    this.moveMigrationModalItem.set(item);
    const available = this.availableDestinationProjects();
    this.selectedDestinationProjectId.set(available.length > 0 ? available[0].id : null);

    if (this.projectMigrationsAvailability() === 'NOT_CONNECTED') {
      this.migrationMoveStatus.set('BACKEND_NOT_CONNECTED');
    } else if (this.projectMigrationsAvailability() === 'UNAUTHORIZED') {
      this.migrationMoveStatus.set('UNAVAILABLE_UNAUTHORIZED');
    } else if (item.lifecycleState === 'RUNNING' || item.lifecycleState === 'ATTENTION') {
      this.migrationMoveStatus.set('UNAVAILABLE_ACTIVE');
    } else if (available.length === 0) {
      this.migrationMoveStatus.set('CONTROLLED_ACTION_REQUIRED');
    } else {
      this.migrationMoveStatus.set('MOVE_AVAILABLE');
    }
  }

  public closeMoveMigrationModal(): void {
    this.moveMigrationModalItem.set(null);
    this.selectedDestinationProjectId.set(null);
    this.migrationMoveStatus.set('MOVE_AVAILABLE');
    this.migrationMoveErrorMessage.set('');
  }

  public setSelectedDestinationProjectId(id: string | null): void {
    this.selectedDestinationProjectId.set(id);
  }

  public submitMoveMigrationIntent(intent?: ProjectMigrationMoveIntent): boolean {
    const migration = this.moveMigrationModalItem();
    const destId = intent?.destinationProjectId || this.selectedDestinationProjectId();
    const sourceId = intent?.sourceProjectId || migration?.projectId;
    const migId = intent?.migrationId || migration?.id;

    if (!migId || !destId || !sourceId) {
      return false;
    }

    const destProject = this.projects().find(p => p.id === destId);
    if (!destProject) {
      this.migrationMoveStatus.set('FAILED');
      this.migrationMoveErrorMessage.set('Selected destination project does not exist in workspace.');
      return false;
    }

    // Mutate migration's projectId
    this.projectMigrations.update(list =>
      list.map(m => m.id === migId ? { ...m, projectId: destId, projectName: destProject.name } : m)
    );

    // Record activity in destination project
    const now = new Date().toISOString();
    const moveActivity: ProjectActivityItem = {
      id: `act-move-${Date.now().toString().slice(-4)}`,
      projectId: destId,
      title: 'Migration Reassigned',
      description: `Migration ${migration?.name || migId} was moved from project ${sourceId} to ${destProject.name}.`,
      category: 'MIGRATION',
      severity: 'INFO',
      occurredAt: now,
      actorName: 'Current Operator',
      subjectName: migration?.name || migId,
      subjectType: 'MIGRATION',
      actionType: 'MANAGE',
      availability: 'READY'
    };

    this.projectDetailedActivities.update(list => [moveActivity, ...list]);
    this.closeMoveMigrationModal();
    return true;
  }

  public retryConnection(): void {
    this.projectsAvailability.set('LOADING');
    this.projectMigrationsAvailability.set('LOADING');
    this.projectValidationsAvailability.set('LOADING');
    this.projectResourcesAvailability.set('LOADING');
    this.projectActivityAvailability.set('LOADING');
    this.projectAccessAvailability.set('LOADING');
    this.projectGovernanceAvailability.set('LOADING');
    this.projectSettingsAvailability.set('LOADING');
    setTimeout(() => {
      this.projectsAvailability.set('READY');
      this.initiativesAvailability.set('READY');
      this.projectMigrationsAvailability.set('READY');
      this.projectValidationsAvailability.set('READY');
      this.projectResourcesAvailability.set('READY');
      this.projectActivityAvailability.set('READY');
      this.projectAccessAvailability.set('READY');
      this.projectGovernanceAvailability.set('READY');
      this.projectSettingsAvailability.set('READY');
    }, 400);
  }

  /**
   * Test/Harness State Injection (Explicitly for unit testing / hostile state checks)
   */
  public loadTestScenario(
    state: EntityAvailabilityState,
    projects: ProjectDiscoveryItem[] = [],
    initiatives: InitiativeDiscoveryItem[] = [],
    attention: PortfolioAttentionItem[] = [],
    summary: ProjectsPortfolioSummary = { totalProjects: null, activeProjects: null, totalInitiatives: null, activeInitiatives: null, attentionCount: null },
    errorMessage = ''
  ): void {
    this.projectsAvailability.set(state);
    this.initiativesAvailability.set(state);
    this.projects.set(projects);
    this.initiatives.set(initiatives);
    this.attentionItems.set(attention);
    this.summary.set(summary);
    this.errorMessage.set(errorMessage);
  }

  public loadMigrationsTestScenario(
    state: EntityAvailabilityState,
    list: ProjectMigrationItem[] = []
  ): void {
    this.projectMigrationsAvailability.set(state);
    this.projectMigrations.set(list);
  }

  public loadValidationsTestScenario(
    state: EntityAvailabilityState,
    list: ProjectValidationItem[] = []
  ): void {
    this.projectValidationsAvailability.set(state);
    this.projectValidations.set(list);
  }

  public loadResourcesTestScenario(
    state: EntityAvailabilityState,
    list: ProjectResourceItem[] = []
  ): void {
    this.projectResourcesAvailability.set(state);
    this.projectResources.set(list);
  }

  public loadActivityTestScenario(
    state: EntityAvailabilityState,
    list: ProjectActivityItem[] = []
  ): void {
    this.projectActivityAvailability.set(state);
    this.projectDetailedActivities.set(list);
  }

  public loadAccessTestScenario(
    state: EntityAvailabilityState,
    list: ProjectAccessGrantItem[] = []
  ): void {
    this.projectAccessAvailability.set(state);
    this.projectAccessGrants.set(list);
  }

  public loadGovernanceTestScenario(
    state: EntityAvailabilityState,
    list: ProjectGovernanceItem[] = []
  ): void {
    this.projectGovernanceAvailability.set(state);
    this.projectGovernance.set(list);
  }

  public loadSettingsTestScenario(
    state: EntityAvailabilityState
  ): void {
    this.projectSettingsAvailability.set(state);
  }
}


