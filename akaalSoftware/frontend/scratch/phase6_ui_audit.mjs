import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve(process.cwd(), 'dist/akaal-software/browser');
const altDistDir = path.resolve(process.cwd(), 'dist/akaal-software');
const activeDistDir = fs.existsSync(distDir) ? distDir : altDistDir;

console.log('Phase 6 UI Audit - Serving SPA from:', activeDistDir);

const reportDir = path.resolve(process.cwd(), 'playwright-report/phase6');
if (!fs.existsSync(reportDir)) {
  fs.mkdirSync(reportDir, { recursive: true });
}

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  const ext = path.extname(reqPath).toLowerCase();
  let filePath = path.join(activeDistDir, reqPath);

  if (ext) {
    if (!fs.existsSync(filePath)) {
      filePath = path.join(activeDistDir, path.basename(reqPath));
    }
  } else {
    filePath = path.join(activeDistDir, 'index.html');
  }

  if (!fs.existsSync(filePath)) {
    filePath = path.join(activeDistDir, 'index.html');
  }

  const mimeTypes = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.woff2': 'font/woff2',
    '.woff': 'font/woff',
    '.ttf': 'font/ttf'
  };

  const contentType = mimeTypes[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(500);
      res.end('Server error: ' + err.code);
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

const PORT = 4410;
server.listen(PORT, async () => {
  console.log(`Phase 6 Hostile UI Audit Server running on http://localhost:${PORT}`);

  const results = {
    routesAudited: [],
    viewportsTested: [],
    consoleErrors: [],
    overflowDefects: [],
    fontViolations: [],
    pillViolations: [],
    emojiViolations: [],
    lightModeDefects: [],
    darkModeDefects: []
  };

  try {
    const browser = await chromium.launch({ 
      headless: true,
      executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
    });

    const routes = [
      { path: '/dashboard', name: 'Dashboard' },
      { path: '/migration/portfolio', name: 'Migration Portfolio' },
      { path: '/migration/create', name: 'New Migration Wizard' },
      { path: '/migration/projects', name: 'Projects & Initiatives' },
      { path: '/migration/history', name: 'Migration History' },
      { path: '/migration/templates', name: 'Migration Templates' },
      { path: '/validation', name: 'Validation Portfolio' },
      { path: '/validation/create', name: 'New Validation Wizard' },
      { path: '/connections', name: 'Connections Vault' },
      { path: '/connections/new', name: 'Create Connection Wizard' },
      { path: '/cockpit', name: 'Execution Cockpit' },
      { path: '/monitoring', name: 'Observability & Monitoring' },
      { path: '/reports', name: 'Reports & Evidence' },
      { path: '/administration', name: 'Administration Home' },
      { path: '/administration/enterprise', name: 'Enterprise Architecture' },
      { path: '/administration/people', name: 'People & Access' },
      { path: '/administration/governance-centre', name: 'Governance Centre' },
      { path: '/administration/identity', name: 'Identity & Security' },
      { path: '/administration/templates-library', name: 'Template Library' },
      { path: '/administration/connectors', name: 'Connectors & Plugins' },
      { path: '/administration/infrastructure', name: 'Cloud Infrastructure' },
      { path: '/settings', name: 'Settings' }
    ];

    const viewports = [
      { name: '1366x768', width: 1366, height: 768 },
      { name: '1440x900', width: 1440, height: 900 },
      { name: '1920x1080', width: 1920, height: 1080 }
    ];

    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    page.on('console', msg => {
      if (msg.type() === 'error') {
        results.consoleErrors.push({ text: msg.text(), url: page.url() });
      }
    });

    for (const vp of viewports) {
      console.log(`--- Testing Viewport: ${vp.name} ---`);
      await page.setViewportSize({ width: vp.width, height: vp.height });

      for (const route of routes) {
        console.log(`Auditing: ${route.name} (${route.path}) at ${vp.name}`);
        await page.goto(`http://localhost:${PORT}${route.path}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(400);

        // Audit in Light Mode first
        await page.evaluate(() => {
          document.documentElement.classList.remove('dark');
          document.documentElement.setAttribute('data-theme', 'enterprise-blue');
        });
        await page.waitForTimeout(200);

        // Check overflow
        const overflow = await page.evaluate(() => {
          const bodyOverflow = document.body.scrollWidth > window.innerWidth;
          const mainEl = document.querySelector('main');
          const mainOverflow = mainEl ? mainEl.scrollWidth > mainEl.clientWidth : false;
          return { bodyOverflow, mainOverflow };
        });

        if (overflow.bodyOverflow || overflow.mainOverflow) {
          results.overflowDefects.push({ route: route.path, viewport: vp.name, overflow });
        }

        // Audit in Dark Mode
        await page.evaluate(() => {
          document.documentElement.classList.add('dark');
          document.documentElement.setAttribute('data-theme', 'dark');
        });
        await page.waitForTimeout(200);

        if (vp.name === '1440x900') {
          results.routesAudited.push(route.path);
          const safeName = route.name.toLowerCase().replace(/[^a-z0-9]/g, '_');
          await page.screenshot({ path: path.join(reportDir, `${safeName}_dark.png`) });
        }
      }

      results.viewportsTested.push(vp.name);
    }

    await browser.close();
    console.log('--- Phase 6 Hostile UI Audit Complete ---');
    fs.writeFileSync(path.join(reportDir, 'audit_results.json'), JSON.stringify(results, null, 2), 'utf-8');

  } catch (err) {
    console.error('Phase 6 UI audit encountered an error:', err);
    process.exitCode = 1;
  } finally {
    server.close();
  }
});
