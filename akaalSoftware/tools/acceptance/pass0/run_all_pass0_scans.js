/**
 * Master Pass 0 Scanner Orchestrator
 * Executes all forensic scanner scripts in sequence and verifies manifest integrity.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const pass0Dir = __dirname;
const manifestsDir = path.join(pass0Dir, 'manifests');

const scripts = [
  'scan_directories.js',
  'forensic_inventory.js',
  'parse_routes_ast.js',
  'analyze_surfaces.js',
  'scan_actions.js',
  'scan_primitives.js',
  'scan_states_and_enums.js',
  'scan_domain_concepts.js',
  'build_relationship_graph.js'
];

console.log('================================================================');
console.log('STARTING PASS 0 FORENSIC SCAN EXECUTION');
console.log('Working Directory:', pass0Dir);
console.log('Manifests Output:', manifestsDir);
console.log('================================================================\n');

for (const script of scripts) {
  console.log(`>>> Running ${script}...`);
  try {
    const output = execSync(`node ${script}`, { cwd: pass0Dir, encoding: 'utf8' });
    console.log(output);
  } catch (err) {
    console.error(`ERROR running ${script}:`, err.message);
    process.exit(1);
  }
}

console.log('================================================================');
console.log('PASS 0 FORENSIC SCANS COMPLETE. VERIFYING GENERATED MANIFESTS:');
const expectedManifests = [
  'dir_tree_analysis.json',
  'inventory_breakdown.json',
  'parsed_routes.json',
  'surfaces_analyzed.json',
  'actions_inventory.json',
  'primitives_inventory.json',
  'states_enums_inventory.json',
  'domain_concepts_inventory.json',
  'cross_reference_graph.json'
];

let allPresent = true;
expectedManifests.forEach(m => {
  const p = path.join(manifestsDir, m);
  if (fs.existsSync(p)) {
    const size = fs.statSync(p).size;
    console.log(` [OK] ${m.padEnd(32)} (${size.toLocaleString()} bytes)`);
  } else {
    console.error(` [MISSING] ${m}`);
    allPresent = false;
  }
});

if (!allPresent) {
  console.error('\nFAIL: Some manifests are missing!');
  process.exit(1);
} else {
  console.log('\nSUCCESS: All Pass 0 manifests successfully generated and verified.');
}
