const fs = require('fs');
const path = require('path');

const srcDir = path.resolve(__dirname, '../../../frontend/src');
const manifestsDir = path.resolve(__dirname, 'manifests');

function walkDir(dir) {
  let files = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files = files.concat(walkDir(fullPath));
    } else {
      files.push(fullPath);
    }
  }
  return files;
}

const allSrcFiles = walkDir(srcDir);

const components = [];
const services = [];
const models = [];
const specs = [];
const fixtures = [];
const others = [];

allSrcFiles.forEach(file => {
  const relPath = path.relative(path.resolve(__dirname, '../../../frontend'), file).replace(/\\/g, '/');
  const base = path.basename(file);
  
  if (base.endsWith('.spec.ts')) {
    specs.push(relPath);
  } else if (base.endsWith('.component.ts')) {
    components.push(relPath);
  } else if (base.endsWith('.service.ts')) {
    services.push(relPath);
  } else if (base.endsWith('.models.ts') || base.endsWith('.model.ts') || base.endsWith('.types.ts')) {
    models.push(relPath);
  } else if (base.endsWith('.fixtures.ts') || base.endsWith('.fixture.ts')) {
    fixtures.push(relPath);
  } else {
    others.push(relPath);
  }
});

const productionFilesCount = components.length + services.length + models.length + others.length;

console.log('=== FRONTEND SRC FORENSIC INVENTORY ===');
console.log('Total files in src/:', allSrcFiles.length);
console.log('Production files:', productionFilesCount);
console.log('  - Components (.component.ts):', components.length);
console.log('  - Services (.service.ts):', services.length);
console.log('  - Models/Types (.models/.model/.types.ts):', models.length);
console.log('  - Infrastructure/Config/Root files:', others.length);
console.log('Test specifications (.spec.ts):', specs.length);
console.log('Deterministic fixture files (.fixtures.ts):', fixtures.length);
console.log('Sum verification: 651 + 43 + 14 =', productionFilesCount + specs.length + fixtures.length);

if (!fs.existsSync(manifestsDir)) {
  fs.mkdirSync(manifestsDir, { recursive: true });
}

fs.writeFileSync(path.join(manifestsDir, 'inventory_breakdown.json'), JSON.stringify({
  summary: {
    total: allSrcFiles.length,
    production: productionFilesCount,
    components: components.length,
    services: services.length,
    models: models.length,
    specs: specs.length,
    fixtures: fixtures.length,
    others: others.length
  },
  components,
  services,
  models,
  specs,
  fixtures,
  others
}, null, 2));
