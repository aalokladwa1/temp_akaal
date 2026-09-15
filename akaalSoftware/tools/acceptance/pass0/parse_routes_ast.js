const path = require('path');
const ts = require(path.resolve(__dirname, '../../../frontend/node_modules/typescript'));
const fs = require('fs');

const routesFile = path.resolve(__dirname, '../../../frontend/src/app/app.routes.ts');
const manifestsDir = path.resolve(__dirname, 'manifests');

const sourceCode = fs.readFileSync(routesFile, 'utf8');
const sourceFile = ts.createSourceFile('app.routes.ts', sourceCode, ts.ScriptTarget.Latest, true);

const routesList = [];

function extractRoutes(arrayLiteral, parentPath = '') {
  arrayLiteral.elements.forEach(element => {
    if (!ts.isObjectLiteralExpression(element)) return;

    let routePath = '';
    let redirectTo = null;
    let component = null;
    let loadComponent = null;
    let children = null;
    let pathMatch = null;

    element.properties.forEach(prop => {
      if (!ts.isPropertyAssignment(prop)) return;
      const name = prop.name.getText(sourceFile).replace(/['"]/g, '');
      const val = prop.initializer;

      if (name === 'path') routePath = val.getText(sourceFile).replace(/['"]/g, '');
      if (name === 'redirectTo') redirectTo = val.getText(sourceFile).replace(/['"]/g, '');
      if (name === 'pathMatch') pathMatch = val.getText(sourceFile).replace(/['"]/g, '');
      if (name === 'component') component = val.getText(sourceFile);
      if (name === 'loadComponent') {
        const text = val.getText(sourceFile);
        const match = text.match(/import\(['"]([^'"]+)['"]\)\.then\(m\s*=>\s*m\.([a-zA-Z0-9_]+)\)/);
        if (match) {
          loadComponent = { file: match[1], componentName: match[2] };
        } else {
          loadComponent = { file: 'unknown', componentName: text };
        }
      }
      if (name === 'children' && ts.isArrayLiteralExpression(val)) children = val;
    });

    const fullPath = parentPath ? (parentPath + (routePath ? '/' + routePath : '')) : routePath;

    // Determine domain/module
    let moduleDomain = 'root';
    if (fullPath.startsWith('dashboard')) moduleDomain = 'dashboard';
    else if (fullPath.startsWith('cockpit')) moduleDomain = 'cockpit';
    else if (fullPath.startsWith('validation')) moduleDomain = 'validation';
    else if (fullPath.startsWith('connections')) moduleDomain = 'connections';
    else if (fullPath.startsWith('migration/cockpit')) moduleDomain = 'cockpit';
    else if (fullPath.startsWith('migration/validation')) moduleDomain = 'validation';
    else if (fullPath.startsWith('migration')) moduleDomain = 'migration';
    else if (fullPath.startsWith('monitoring')) moduleDomain = 'monitoring';
    else if (fullPath.startsWith('reports')) moduleDomain = 'reports';
    else if (fullPath.startsWith('administration')) moduleDomain = 'administration';
    else if (fullPath.startsWith('settings')) moduleDomain = 'settings';

    routesList.push({
      path: routePath,
      parentPath: parentPath || null,
      fullPath,
      moduleDomain,
      hasParams: routePath.includes(':'),
      params: (routePath.match(/:[a-zA-Z0-9_]+/g) || []).map(p => p.slice(1)),
      isRedirect: !!redirectTo,
      redirectTo,
      pathMatch,
      isEager: !!component,
      component,
      isLazy: !!loadComponent,
      loadComponent,
      hasChildren: !!children
    });

    if (children) {
      extractRoutes(children, fullPath);
    }
  });
}

ts.forEachChild(sourceFile, node => {
  if (ts.isVariableStatement(node)) {
    node.declarationList.declarations.forEach(decl => {
      if (decl.name.getText(sourceFile) === 'routes' && decl.initializer && ts.isArrayLiteralExpression(decl.initializer)) {
        extractRoutes(decl.initializer);
      }
    });
  }
});

if (!fs.existsSync(manifestsDir)) {
  fs.mkdirSync(manifestsDir, { recursive: true });
}

fs.writeFileSync(path.join(manifestsDir, 'parsed_routes.json'), JSON.stringify(routesList, null, 2));

console.log('=== ROUTE PARSING COMPLETE ===');
console.log('Total Route Objects:', routesList.length);
console.log('Eager Routes:', routesList.filter(r => r.isEager).length);
console.log('Lazy Routes:', routesList.filter(r => r.isLazy).length);
console.log('Redirect Routes:', routesList.filter(r => r.isRedirect).length);
console.log('Sum: 42 + 213 + 7 =', routesList.filter(r => r.isEager).length + routesList.filter(r => r.isLazy).length + routesList.filter(r => r.isRedirect).length);
console.log('Parent Container Routes:', routesList.filter(r => r.hasChildren).length);
console.log('Parameterized Routes (Orthogonal attribute):', routesList.filter(r => r.hasParams).length);

const moduleCounts = {};
routesList.forEach(r => {
  moduleCounts[r.moduleDomain] = (moduleCounts[r.moduleDomain] || 0) + 1;
});
console.log('Module Breakdown:', moduleCounts);
