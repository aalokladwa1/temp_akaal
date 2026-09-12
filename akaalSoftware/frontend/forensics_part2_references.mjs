import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0');

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

const PORT = 4326;
server.listen(PORT, async () => {
  console.log(`Forensics server listening on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    const viewports = [
      { name: '1920x1080', width: 1920, height: 1080 },
      { name: '1440x900', width: 1440, height: 900 }
    ];

    const pagesToInspect = [
      { name: 'reports_home', url: '/reports' },
      { name: 'monitoring_home', url: '/monitoring' },
      { name: 'monitoring_migration', url: '/monitoring/migration' },
      { name: 'monitoring_platform', url: '/monitoring/platform' },
      { name: 'monitoring_alerts', url: '/monitoring/alerts' },
      { name: 'migration_home', url: '/migration' },
      { name: 'validation_home', url: '/validation' },
      { name: 'connections_home', url: '/connections' }
    ];

    for (const vp of viewports) {
      console.log(`\n=== Capturing Reference Screens at ${vp.name} ===`);
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: 1
      });
      const page = await context.newPage();

      const navigateTo = async (targetUrl) => {
        await page.evaluate((target) => {
          window.history.pushState({}, '', target);
          window.dispatchEvent(new Event('popstate'));
        }, targetUrl);
        await page.waitForTimeout(600);
      };

      await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);

      for (const p of pagesToInspect) {
        await navigateTo(p.url);
        const screenshotPath = path.join(outDir, `ref_forensics_${p.name}_${vp.name}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: false });
        console.log(`Captured ${p.name} at ${vp.name}`);
      }

      await context.close();
    }

    await browser.close();
    console.log('\nAll pre-implementation reference captures completed successfully!');
  } catch (err) {
    console.error('Error during Playwright reference capture:', err);
  } finally {
    server.close();
    process.exit(0);
  }
});
