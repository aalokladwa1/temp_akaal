import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0/baseline_captures');

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  const ext = path.extname(reqPath).toLowerCase();
  let filePath = path.join(distDir, reqPath);

  if (ext) {
    if (!fs.existsSync(filePath)) {
      filePath = path.join(distDir, path.basename(reqPath));
    }
  } else {
    filePath = path.join(distDir, 'index.html');
  }

  if (!fs.existsSync(filePath)) {
    filePath = path.join(distDir, 'index.html');
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

const PORT = 4352;
server.listen(PORT, async () => {
  console.log(`Baseline inspection server running on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });
    const context = await browser.newContext();
    const page = await context.newPage();

    const targets = [
      { name: '01_admin_home', url: '/administration' },
      { name: '02_enterprise_home', url: '/administration/enterprise' },
      { name: '03_org_list', url: '/administration/enterprise/structure/organizations' },
      { name: '04_org_detail', url: '/administration/enterprise/structure/organizations/detail/org-01' },
      { name: '05_org_create', url: '/administration/enterprise/structure/organizations/create' },
      { name: '06_people_home', url: '/administration/people' },
      { name: '07_governance_home', url: '/administration/governance-centre' },
      { name: '08_identity_home', url: '/administration/identity' },
      { name: '09_templates_home', url: '/administration/templates-library' },
      { name: '10_connectors_home', url: '/administration/connectors' },
      { name: '11_infra_home', url: '/administration/infrastructure' }
    ];

    const viewports = [
      { width: 1920, height: 1080, suffix: '1920x1080' },
      { width: 1440, height: 900, suffix: '1440x900' }
    ];

    for (const target of targets) {
      for (const vp of viewports) {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.goto(`http://localhost:${PORT}${target.url}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(300);
        const capturePath = path.join(outDir, `${target.name}_${vp.suffix}.png`);
        await page.screenshot({ path: capturePath, fullPage: false });
        console.log(`Captured: ${path.basename(capturePath)}`);
      }
    }

    console.log('All baseline inspection captures completed successfully!');
    await browser.close();
  } catch (err) {
    console.error('Inspection error:', err);
  } finally {
    server.close();
    process.exit(0);
  }
});
