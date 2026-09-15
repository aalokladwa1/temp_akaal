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

const PORT = 4306;
server.listen(PORT, async () => {
  console.log(`Static server listening on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    const resolutions = [
      { name: '1920x1080', width: 1920, height: 1080 },
      { name: '1440x900', width: 1440, height: 900 }
    ];

    for (const res of resolutions) {
      console.log(`\n--- Capturing Platform Operations at resolution ${res.name} ---`);
      const context = await browser.newContext({
        viewport: { width: res.width, height: res.height },
        deviceScaleFactor: 1
      });
      const page = await context.newPage();

      // Helper to navigate client-side via router or pushState
      const navigateTo = async (url) => {
        await page.evaluate((target) => {
          window.history.pushState({}, '', target);
          window.dispatchEvent(new Event('popstate'));
        }, url);
        await page.waitForTimeout(800);
      };

      // Navigate to base
      await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(600);

      // 1. Overview Tab
      await navigateTo('/monitoring/platform');
      await page.screenshot({
        path: path.join(outDir, `platform_ops_01_overview_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured platform_ops_01_overview_${res.name}.png`);

      // 2. Runtime & Services Tab
      await navigateTo('/monitoring/platform/runtime');
      await page.screenshot({
        path: path.join(outDir, `platform_ops_02_runtime_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured platform_ops_02_runtime_${res.name}.png`);

      // 3. Connectivity & Endpoints Tab
      await navigateTo('/monitoring/platform/connectivity');
      await page.screenshot({
        path: path.join(outDir, `platform_ops_03_connectivity_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured platform_ops_03_connectivity_${res.name}.png`);

      // 4. Infrastructure & Fleet Tab
      await navigateTo('/monitoring/platform/infrastructure');
      await page.screenshot({
        path: path.join(outDir, `platform_ops_04_infrastructure_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured platform_ops_04_infrastructure_${res.name}.png`);

      // 5. Capacity & Utilization Tab
      await navigateTo('/monitoring/platform/capacity');
      await page.screenshot({
        path: path.join(outDir, `platform_ops_05_capacity_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured platform_ops_05_capacity_${res.name}.png`);

      // 6. Platform Performance Tab
      await navigateTo('/monitoring/platform/performance');
      await page.screenshot({
        path: path.join(outDir, `platform_ops_06_performance_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured platform_ops_06_performance_${res.name}.png`);

      // 7. Platform Reliability Tab
      await navigateTo('/monitoring/platform/reliability');
      await page.screenshot({
        path: path.join(outDir, `platform_ops_07_reliability_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured platform_ops_07_reliability_${res.name}.png`);

      // 8. Diagnostics Tab
      await navigateTo('/monitoring/platform/diagnostics');
      await page.screenshot({
        path: path.join(outDir, `platform_ops_08_diagnostics_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured platform_ops_08_diagnostics_${res.name}.png`);

      await context.close();
    }

    await browser.close();
    console.log('\nAll Platform Operations screenshots captured successfully!');
  } catch (err) {
    console.error('Error during screenshot capture:', err);
  } finally {
    server.close();
    process.exit(0);
  }
});
