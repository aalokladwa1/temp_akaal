const fs = require('fs');
const content = fs.readFileSync('./src/app/core/models/provider-form-schemas.ts', 'utf8');

// Parse keys in ALL_48_PROVIDER_SCHEMAS
const lines = content.split('\n');
const providers = [];
let currentKey = null;
let currentCategory = null;
let currentIcon = null;
let currentName = null;

for (const line of lines) {
  const keyMatch = line.match(/^\s{2}'([^']+)':\s*\{/);
  if (keyMatch) {
    if (currentKey) {
      providers.push({ id: currentKey, name: currentName, category: currentCategory, icon: currentIcon });
    }
    currentKey = keyMatch[1];
    currentCategory = null;
    currentIcon = null;
    currentName = null;
  }
  const nameMatch = line.match(/"name":\s*"([^"]+)"/);
  if (nameMatch && !currentName) {
    currentName = nameMatch[1];
  }
  const catMatch = line.match(/"category":\s*"([^"]+)"/);
  if (catMatch && !currentCategory) {
    currentCategory = catMatch[1];
  }
  const iconMatch = line.match(/"icon":\s*"([^"]+)"/);
  if (iconMatch && !currentIcon) {
    currentIcon = iconMatch[1];
  }
}
if (currentKey) {
  providers.push({ id: currentKey, name: currentName, category: currentCategory, icon: currentIcon });
}

console.log('Total Providers parsed:', providers.length);
console.log(JSON.stringify(providers, null, 2));

const byCat = {};
for (const p of providers) {
  byCat[p.category] = (byCat[p.category] || 0) + 1;
}
console.log('By Category:', byCat);
