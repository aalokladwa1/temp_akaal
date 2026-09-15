/**
 * Pass 0 - Cross-Reference Relationship Graph Builder
 */

const fs = require('fs');
const path = require('path');

const manifestsDir = path.resolve(__dirname, 'manifests');

const routes = JSON.parse(fs.readFileSync(path.join(manifestsDir, 'parsed_routes.json'), 'utf8'));
const surfaces = JSON.parse(fs.readFileSync(path.join(manifestsDir, 'surfaces_analyzed.json'), 'utf8'));
const actions = JSON.parse(fs.readFileSync(path.join(manifestsDir, 'actions_inventory.json'), 'utf8'));
const primitives = JSON.parse(fs.readFileSync(path.join(manifestsDir, 'primitives_inventory.json'), 'utf8'));
const states = JSON.parse(fs.readFileSync(path.join(manifestsDir, 'states_enums_inventory.json'), 'utf8'));
const concepts = JSON.parse(fs.readFileSync(path.join(manifestsDir, 'domain_concepts_inventory.json'), 'utf8'));
const inventory = JSON.parse(fs.readFileSync(path.join(manifestsDir, 'inventory_breakdown.json'), 'utf8'));

const graph = {
  domainToSurfaces: {},
  moduleToRoutes: {},
  primitiveToSurfaces: {},
  workflowChains: [],
  testMapping: {}
};

// 1. Module to Routes
routes.forEach(r => {
  graph.moduleToRoutes[r.moduleDomain] = graph.moduleToRoutes[r.moduleDomain] || [];
  graph.moduleToRoutes[r.moduleDomain].push({
    fullPath: r.fullPath,
    component: r.component || (r.loadComponent ? r.loadComponent.componentName : null),
    isLazy: r.isLazy,
    hasParams: r.hasParams
  });
});

// 2. Domain Concept Mapping
concepts.primaryFamilies.forEach(c => {
  graph.domainToSurfaces[c.term] = {
    category: c.category,
    totalFiles: c.fileCount,
    sampleComponents: c.sampleFiles.filter(f => f.endsWith('.component.ts')).slice(0, 5)
  };
});

// 3. UI Primitive to Surfaces
graph.primitiveToSurfaces = {
  'CustomSelectComponent': primitives.customSelect.length,
  'SegmentedControlComponent': primitives.segmentedControl.length,
  'CodeEditorComponent': primitives.codeEditor.length,
  'LucideIconComponent': primitives.lucideIcon.length,
  'MetricSurfaceComponent': primitives.metricSurface.length,
  'AccordionComponent': primitives.accordion.length,
  'NativeTables': primitives.nativeTable.length,
  'NativeForms': primitives.nativeInput.length,
  'NativeButtons': primitives.nativeButton.length,
  'MonacoEditor': primitives.monaco.length,
  'RoundedFullTotal': primitives.roundedFull.length,
  'RoundedFullButtons': primitives.roundedFullButtons.length
};

// 4. Major Workflows
graph.workflowChains = [
  {
    workflow: 'Enterprise Migration Creation (9 Steps)',
    chain: [
      'Dashboard / Portfolio (/migration)',
      'Step 1: Definition (/migration/create)',
      'Step 2: Source Instance & Probes',
      'Step 3: Target Instance & Probes',
      'Step 4: Discovery & Advanced Scope',
      'Step 5: Mapping & Data Controls Studio',
      'Step 6: Enterprise Configuration Center',
      'Step 7: Dynamic Migration Plan (DAG)',
      'Step 8: Governance & Readiness Sign-off',
      'Step 9: Review, Schedule & Initialize',
      'Execution Cockpit (/migration/cockpit/:id)'
    ]
  },
  {
    workflow: 'Database Connection Creation & Verification (4 Steps)',
    chain: [
      'Connections Inventory (/connections)',
      'Step 1: Basic & Provider Selection (/connections/new)',
      'Step 2: Authentication & Host Configuration',
      'Step 3: Security & Network Routing (TLS/Bastion)',
      'Step 4: Verification Probes & Summary',
      'Connection Workspace (/connections/:connectionId)'
    ]
  },
  {
    workflow: 'Data Validation & Discrepancy Remediation (8 Steps)',
    chain: [
      'Validation Portfolio (/validation)',
      'Step 1: Definition (/validation/new)',
      'Step 2: Source Instance Selection',
      'Step 3: Target Instance Selection',
      'Step 4: Scope & Table Filter',
      'Step 5: Boundary & Sampling Policy',
      'Step 6: Strategy & Rule Selection',
      'Step 7: Readiness & Policy Gates',
      'Step 8: Review & Execution Launch',
      'Validation Workstation (/validation/:validationId)',
      'Discrepancies Analysis & Repair (/validation/:validationId/discrepancies)'
    ]
  },
  {
    workflow: 'Strategic Project & Initiative Management',
    chain: [
      'Projects Portfolio (/migration/projects)',
      'Create Initiative (/migration/initiatives/new)',
      'Initiative Workspace (/migration/initiatives/:initiativeId)',
      'Create Project (/migration/initiatives/:initiativeId/new-project)',
      'Project Workspace (/migration/projects/:projectId)',
      'Milestone Tracking & Execution Allocation'
    ]
  },
  {
    workflow: 'Audit Dossier & Certification Assembly',
    chain: [
      'Reports Home (/reports)',
      'Reports Library (/reports/library)',
      'Report Generation / Export Modal',
      'Certification Center (/reports/certification)',
      'Evidence Manifest & Hash Verification (/reports/evidence)'
    ]
  }
];

// 5. Test mapping: match spec files to module areas
inventory.specs.forEach(s => {
  const parts = s.split('/');
  const area = parts[2] === 'modules' ? parts[3] : parts[2];
  graph.testMapping[area] = (graph.testMapping[area] || 0) + 1;
});

fs.writeFileSync(path.join(manifestsDir, 'cross_reference_graph.json'), JSON.stringify(graph, null, 2));
console.log('=== RELATIONSHIP GRAPH GENERATED ===');
console.log('Modules Mapped:', Object.keys(graph.moduleToRoutes).length);
console.log('Workflows Mapped:', graph.workflowChains.length);
console.log('Test Coverage per Area:', graph.testMapping);
