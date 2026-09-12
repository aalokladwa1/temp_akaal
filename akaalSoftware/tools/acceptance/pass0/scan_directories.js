const fs = require('fs');
const path = require('path');

const akaalRoot = path.resolve(__dirname, '../../..');
const manifestsDir = path.resolve(__dirname, 'manifests');

function analyzeDir(dirPath, rel = '') {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });
  const subdirs = [];
  let fileCount = 0;
  let totalSize = 0;

  for (const entry of entries) {
    const full = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      subdirs.push(entry.name);
    } else {
      fileCount++;
      try {
        totalSize += fs.statSync(full).size;
      } catch (e) {}
    }
  }

  return {
    relPath: rel || '.',
    fileCount,
    totalSize,
    subdirs
  };
}

const prodDirs = [];
function walkTree(curr, rel = '') {
  const res = analyzeDir(curr, rel);
  prodDirs.push(res);
  for (const sub of res.subdirs) {
    // Exclude build/cache artifacts and acceptance tooling
    if (['node_modules', '.git', '.angular', 'dist', 'tools'].includes(sub)) continue;
    walkTree(path.join(curr, sub), rel ? rel + '/' + sub : sub);
  }
}

walkTree(akaalRoot);
console.log('Production non-ignored directories scanned under akaalSoftware/:', prodDirs.length);

if (!fs.existsSync(manifestsDir)) {
  fs.mkdirSync(manifestsDir, { recursive: true });
}
fs.writeFileSync(path.join(manifestsDir, 'dir_tree_analysis.json'), JSON.stringify(prodDirs, null, 2));
