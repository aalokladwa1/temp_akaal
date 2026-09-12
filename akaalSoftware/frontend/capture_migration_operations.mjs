import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0');

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

// Static HTTP server for Angular SPA handling deep client-side routes
const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  const ext = path.extname(reqPath).toLowerCase();

  let filePath = path.join(distDir, reqPath);

  // If request has a file extension (asset/bundle), try direct then fallback to flat in distDir
  if (ext) {
    if (!fs.existsSync(filePath)) {
      filePath = path.join(distDir, path.basename(reqPath));
    }
  } else {
    // SPA deep routes fallback to index.html
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

const PORT = 4305;
server.listen(PORT, async () => {
  console.log(`Static server listening on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    const resolutions = [
      { name: '1920x1080', width: 1920, height: 1080 },
      { name: '1440x900', width: 1440, height: 900 }
    ];

    for (const res of resolutions) {
      console.log(`\n--- Capturing Migration Operations at resolution ${res.name} ---`);
      const context = await browser.newContext({
        viewport: { width: res.width, height: res.height },
        deviceScaleFactor: 1
      });
      const page = await context.newPage();

      // Navigate to base
      await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(600);

      // Helper to navigate client-side via links or URL
      const navigateTo = async (url) => {
        await page.evaluate((target) => {
          window.history.pushState({}, '', target);
          window.dispatchEvent(new Event('popstate'));
        }, url);
        await page.waitForTimeout(700);
      };

      // 1. Fleet View
      await navigateTo('/monitoring/migrations');
      await page.screenshot({
        path: path.join(outDir, `migration_ops_01_fleet_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured migration_ops_01_fleet_${res.name}.png`);

      // 2. Selected Migration - Overview Tab
      await navigateTo('/monitoring/migrations/mig-core-banking-01/overview');
      await page.screenshot({
        path: path.join(outDir, `migration_ops_02_overview_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured migration_ops_02_overview_${res.name}.png`);

      // 3. Selected Migration - Execution Tab
      await navigateTo('/monitoring/migrations/mig-core-banking-01/execution');
      await page.screenshot({
        path: path.join(outDir, `migration_ops_03_execution_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured migration_ops_03_execution_${res.name}.png`);

      // 4. Selected Migration - Performance & Flow Tab
      await navigateTo('/monitoring/migrations/mig-core-banking-01/performance');
      await page.screenshot({
        path: path.join(outDir, `migration_ops_04_performance_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured migration_ops_04_performance_${res.name}.png`);

      // 5. Selected Migration - Resources & Placement Tab
      await navigateTo('/monitoring/migrations/mig-core-banking-01/resources');
      await page.screenshot({
        path: path.join(outDir, `migration_ops_05_resources_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured migration_ops_05_resources_${res.name}.png`);

      // 6. Selected Migration - Health & Dependencies Tab
      await navigateTo('/monitoring/migrations/mig-core-banking-01/health');
      await page.screenshot({
        path: path.join(outDir, `migration_ops_06_health_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured migration_ops_06_health_${res.name}.png`);

      // 7. Selected Migration - Reliability & Recovery Tab
      await navigateTo('/monitoring/migrations/mig-core-banking-01/reliability');
      await page.screenshot({
        path: path.join(outDir, `migration_ops_07_reliability_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured migration_ops_07_reliability_${res.name}.png`);

      // 8. Selected Migration - Diagnostics Tab
      await navigateTo('/monitoring/migrations/mig-core-banking-01/diagnostics');
      await page.screenshot({
        path: path.join(outDir, `migration_ops_08_diagnostics_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured migration_ops_08_diagnostics_${res.name}.png`);

      await context.close();
    }

    await browser.close();
  } catch (err) {
    console.error('Error during capture:', err);
  } finally {
    server.close(() => {
      console.log('Server closed. All captures complete.');
      process.exit(0);
    });
  }
});
