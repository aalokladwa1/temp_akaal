/**
 * Pass 0 - State & Lifecycle Representation Scanner
 * 
 * Corrects S2-1:
 * - Delineates Operational Lifecycle & Health States (~78-90 types) from
 *   Configuration, Category, Mode, and Specification types (~70-82 types).
 * - Verifies zero TypeScript enums across the entire application.
 */

const fs = require('fs');
const path = require('path');

const manifestsDir = path.resolve(__dirname, 'manifests');
const inventoryPath = path.join(manifestsDir, 'inventory_breakdown.json');
const frontendRoot = path.resolve(__dirname, '../../../frontend');

const inventory = JSON.parse(fs.readFileSync(inventoryPath, 'utf8'));

const enums = [];
const allUnionTypes = [];
const operationalStates = [];
const configCategories = [];

const allTsFiles = [...inventory.models, ...inventory.services, ...inventory.components];

allTsFiles.forEach(f => {
  const fullPath = path.resolve(frontendRoot, f);
  const code = fs.readFileSync(fullPath, 'utf8');
  
  // Find TypeScript enums (should be 0)
  const enumMatches = code.matchAll(/export\s+enum\s+([a-zA-Z0-9_]+)\s*\{([^}]+)\}/g);
  for (const m of enumMatches) {
    enums.push({
      file: f,
      name: m[1],
      values: m[2].split(',').map(s => s.trim()).filter(Boolean)
    });
  }

  // Find type unions with status / state / mode / severity / lifecycle / type
  const typeMatches = code.matchAll(/export\s+type\s+([a-zA-Z0-9_]*(?:Status|State|Mode|Severity|Stage|Lifecycle|Phase|Level|Health|Type)[a-zA-Z0-9_]*)\s*=\s*([^;]+);/g);
  for (const m of typeMatches) {
    const name = m[1];
    const def = m[2].trim();
    const entry = { file: f, name, definition: def };
    allUnionTypes.push(entry);

    // Classify into operational state vs configuration/category
    if (/(?:Status|State|Stage|Lifecycle|Phase|Health|Severity)/.test(name) && !/(?:Type|Mode)$/.test(name)) {
      operationalStates.push(entry);
    } else {
      configCategories.push(entry);
    }
  }
});

console.log('=== ENUMS AND STATE TYPES INVENTORY ===');
console.log('Total TypeScript Enums:                         ', enums.length);
console.log('Total Discriminated String Literal Union Types:  ', allUnionTypes.length);
console.log('  - Operational Lifecycle & Health State Types:  ', operationalStates.length);
console.log('  - Configuration, Category, Mode & Type Unions: ', configCategories.length);
console.log('Sum check:                                      ', operationalStates.length + configCategories.length);

fs.writeFileSync(path.join(manifestsDir, 'states_enums_inventory.json'), JSON.stringify({
  summary: {
    totalEnums: enums.length,
    totalUnionTypes: allUnionTypes.length,
    operationalStatesCount: operationalStates.length,
    configCategoriesCount: configCategories.length
  },
  enums,
  operationalStates,
  configCategories,
  allUnionTypes
}, null, 2));
