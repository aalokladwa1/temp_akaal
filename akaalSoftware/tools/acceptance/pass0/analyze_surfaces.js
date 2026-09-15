/**
 * Pass 0 - Automated Structural Surface Analysis
 * 
 * NOTE: The categorization below is an automated structural heuristic based on:
 * - AST Route attachments from app.routes.ts
 * - Feature directory conventions (/steps/, /tabs/, /drawers/)
 * - Template DOM modal and slide-over markers (fixed inset-0, z-50, w-[380px])
 * - Viewport naming conventions (*home, *workspace, *cockpit)
 * It is not an arbitrary or exclusive semantic taxonomy; rather it provides an
 * initial structural baseline for Pass 1 (Product Fidelity) and Pass 4 (Design Review).
 */

const fs = require('fs');
const path = require('path');

const manifestsDir = path.resolve(__dirname, 'manifests');
const inventoryPath = path.join(manifestsDir, 'inventory_breakdown.json');
const routesPath = path.join(manifestsDir, 'parsed_routes.json');
const frontendRoot = path.resolve(__dirname, '../../../frontend');

const inventory = JSON.parse(fs.readFileSync(inventoryPath, 'utf8'));
const routes = JSON.parse(fs.readFileSync(routesPath, 'utf8'));

const surfaces = [];

inventory.components.forEach(compRelPath => {
  const fullPath = path.resolve(frontendRoot, compRelPath);
  const code = fs.readFileSync(fullPath, 'utf8');
  const baseName = path.basename(compRelPath, '.component.ts');
  
  // Extract selector
  const selMatch = code.match(/selector:\s*['"]([^'"]+)['"]/);
  const selector = selMatch ? selMatch[1] : 'unknown';

  // Extract class name
  const classMatch = code.match(/export\s+class\s+([a-zA-Z0-9_]+)/);
  const className = classMatch ? classMatch[1] : 'unknown';

  // Check if routable via route AST
  const matchedRoute = routes.find(r => {
    if (r.component && r.component.includes(className)) return true;
    if (r.loadComponent && r.loadComponent.componentName === className) return true;
    return false;
  });

  // Automated structural heuristic categorization
  let heuristicCategory = 'embedded-widget';
  let heuristicReason = 'Sub-component embedded in parent templates';

  if (matchedRoute) {
    heuristicCategory = 'page';
    heuristicReason = `Directly bound to route: ${matchedRoute.fullPath}`;
  } else if (compRelPath.includes('/steps/')) {
    heuristicCategory = 'wizard-step';
    heuristicReason = 'Located in /steps/ directory of multi-step wizard';
  } else if (compRelPath.includes('/tabs/')) {
    heuristicCategory = 'tab-view';
    heuristicReason = 'Located in /tabs/ directory of tabbed workstation';
  } else if (code.includes('fixed inset-0') && (code.includes('z-50') || code.includes('modal'))) {
    heuristicCategory = 'modal-dialog';
    heuristicReason = 'Declares fixed inset-0 z-50 modal backdrop structure';
  } else if (compRelPath.includes('/drawers/') || code.includes('w-[380px]') || code.includes('drawer')) {
    heuristicCategory = 'drawer';
    heuristicReason = 'Declares slide-over drawer structure or located in /drawers/';
  } else if (baseName.includes('home') || baseName.includes('dashboard') || baseName.includes('cockpit') || baseName.includes('workspace') || baseName.includes('portfolio')) {
    heuristicCategory = 'major-surface';
    heuristicReason = 'Named workspace/home/cockpit/portfolio console';
  }

  // Detect major interactive controls
  const hasTable = code.includes('<table') || code.includes('tableRow') || code.includes('p-table');
  const hasForm = code.includes('<form') || code.includes('formGroup') || code.includes('ngModel') || code.includes('input');
  const hasTabs = code.includes('tabContainer') || code.includes('segmented-control');
  const hasModal = code.includes('modalBackdrop') || code.includes('fixed inset-0');
  const hasChart = code.includes('echarts') || code.includes('chart') || code.includes('cytoscape');
  const hasMonaco = code.includes('monaco-editor') || code.includes('app-code-editor');

  surfaces.push({
    file: compRelPath,
    className,
    selector,
    heuristicCategory,
    heuristicReason,
    route: matchedRoute ? matchedRoute.fullPath : null,
    hasTable,
    hasForm,
    hasTabs,
    hasModal,
    hasChart,
    hasMonaco
  });
});

fs.writeFileSync(path.join(manifestsDir, 'surfaces_analyzed.json'), JSON.stringify(surfaces, null, 2));

console.log('=== STRUCTURAL SURFACE ANALYSIS COMPLETE ===');
console.log('Total Standalone Components Analyzed:', surfaces.length);
const catCount = {};
surfaces.forEach(s => {
  catCount[s.heuristicCategory] = (catCount[s.heuristicCategory] || 0) + 1;
});
console.log('Structural Categories (Automated Heuristic):', catCount);

console.log('Feature Counts across Components:');
console.log('  - Components with Tables:', surfaces.filter(s => s.hasTable).length);
console.log('  - Components with Forms/Inputs:', surfaces.filter(s => s.hasForm).length);
console.log('  - Components with Tabs/Sliders:', surfaces.filter(s => s.hasTabs).length);
console.log('  - Components with Modal Backdrops:', surfaces.filter(s => s.hasModal).length);
console.log('  - Components with Charts/Graphs:', surfaces.filter(s => s.hasChart).length);
console.log('  - Components with Monaco Editors:', surfaces.filter(s => s.hasMonaco).length);
