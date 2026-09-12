const fs = require('fs');
const path = require('path');

const manifestsDir = path.resolve(__dirname, 'manifests');
const inventoryPath = path.join(manifestsDir, 'inventory_breakdown.json');
const frontendRoot = path.resolve(__dirname, '../../../frontend');

const inventory = JSON.parse(fs.readFileSync(inventoryPath, 'utf8'));

const primitiveUsage = {
  customSelect: [],
  segmentedControl: [],
  codeEditor: [],
  lucideIcon: [],
  metricSurface: [],
  accordion: [],
  nativeInput: [],
  nativeButton: [],
  nativeSelect: [],
  nativeTable: [],
  echarts: [],
  cytoscape: [],
  monaco: [],
  roundedFull: [],
  roundedFullButtons: []
};

inventory.components.forEach(compRelPath => {
  const fullPath = path.resolve(frontendRoot, compRelPath);
  const code = fs.readFileSync(fullPath, 'utf8');

  if (code.includes('<app-custom-select')) primitiveUsage.customSelect.push(compRelPath);
  if (code.includes('<app-segmented-control')) primitiveUsage.segmentedControl.push(compRelPath);
  if (code.includes('<app-code-editor')) primitiveUsage.codeEditor.push(compRelPath);
  if (code.includes('<app-lucide-icon')) primitiveUsage.lucideIcon.push(compRelPath);
  if (code.includes('<app-metric-surface')) primitiveUsage.metricSurface.push(compRelPath);
  if (code.includes('<app-accordion')) primitiveUsage.accordion.push(compRelPath);

  if (code.includes('<input')) primitiveUsage.nativeInput.push(compRelPath);
  if (code.includes('<button')) primitiveUsage.nativeButton.push(compRelPath);
  if (code.includes('<select')) primitiveUsage.nativeSelect.push(compRelPath);
  if (code.includes('<table')) primitiveUsage.nativeTable.push(compRelPath);
  if (code.includes('echarts') || code.includes('chartOption')) primitiveUsage.echarts.push(compRelPath);
  if (code.includes('cytoscape')) primitiveUsage.cytoscape.push(compRelPath);
  if (code.includes('monaco')) primitiveUsage.monaco.push(compRelPath);

  if (code.includes('rounded-full')) {
    primitiveUsage.roundedFull.push(compRelPath);
    if (/<button[^>]*rounded-full/s.test(code)) {
      primitiveUsage.roundedFullButtons.push(compRelPath);
    }
  }
});

console.log('=== PRIMITIVE USAGE SUMMARY ===');
console.log('Shared Primitives:');
console.log('  app-lucide-icon:        ', primitiveUsage.lucideIcon.length, 'components');
console.log('  app-custom-select:      ', primitiveUsage.customSelect.length, 'components');
console.log('  app-segmented-control:  ', primitiveUsage.segmentedControl.length, 'components');
console.log('  app-code-editor:        ', primitiveUsage.codeEditor.length, 'components');
console.log('  app-metric-surface:     ', primitiveUsage.metricSurface.length, 'components');
console.log('  app-accordion:          ', primitiveUsage.accordion.length, 'components');
console.log('Native HTML & Visual Elements:');
console.log('  Native <button>:        ', primitiveUsage.nativeButton.length, 'components');
console.log('  Native <input>:         ', primitiveUsage.nativeInput.length, 'components');
console.log('  Native <select>:        ', primitiveUsage.nativeSelect.length, 'components');
console.log('  Native <table>:         ', primitiveUsage.nativeTable.length, 'components');
console.log('Specialized Canvas / Visual:');
console.log('  ECharts:                ', primitiveUsage.echarts.length, 'components');
console.log('  Cytoscape DAG:          ', primitiveUsage.cytoscape.length, 'components');
console.log('  Monaco Code Editor:     ', primitiveUsage.monaco.length, 'components');
console.log('Styling Observations:');
console.log('  rounded-full total:     ', primitiveUsage.roundedFull.length, 'components (status dots, indicator badges, icon rings)');
console.log('  rounded-full buttons:   ', primitiveUsage.roundedFullButtons.length, 'components (DAG gate insertion buttons; flagged for Pass 4)');

fs.writeFileSync(path.join(manifestsDir, 'primitives_inventory.json'), JSON.stringify(primitiveUsage, null, 2));
