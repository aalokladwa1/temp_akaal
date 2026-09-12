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

const PORT = 4308;
server.listen(PORT, async () => {
  console.log(`Static server listening on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    const resolutions = [
      { name: '1920x1080', width: 1920, height: 1080 },
      { name: '1440x900', width: 1440, height: 900 }
    ];

    for (const res of resolutions) {
      console.log(`\n--- Capturing Alerts Operations at resolution ${res.name} ---`);
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

      // 1. Active Alerts Tab
      await navigateTo('/monitoring/alerts');
      await page.screenshot({ path: path.join(outDir, `alerts_ops_01_active_${res.name}.png`), fullPage: false });
      console.log(`Captured alerts_ops_01_active_${res.name}.png`);

      // 2. Alert Evaluation Tab
      await navigateTo('/monitoring/alerts/evaluation');
      await page.screenshot({ path: path.join(outDir, `alerts_ops_02_evaluation_${res.name}.png`), fullPage: false });
      console.log(`Captured alerts_ops_02_evaluation_${res.name}.png`);

      // 3. Incidents Tab
      await navigateTo('/monitoring/alerts/incidents');
      await page.screenshot({ path: path.join(outDir, `alerts_ops_03_incidents_${res.name}.png`), fullPage: false });
      console.log(`Captured alerts_ops_03_incidents_${res.name}.png`);

      // 4. Correlation Tab
      await navigateTo('/monitoring/alerts/correlation');
      await page.screenshot({ path: path.join(outDir, `alerts_ops_04_correlation_${res.name}.png`), fullPage: false });
      console.log(`Captured alerts_ops_04_correlation_${res.name}.png`);

      // 5. Notifications Tab
      await navigateTo('/monitoring/alerts/notifications');
      await page.screenshot({ path: path.join(outDir, `alerts_ops_05_notifications_${res.name}.png`), fullPage: false });
      console.log(`Captured alerts_ops_05_notifications_${res.name}.png`);

      // 6. Timeline Tab
      await navigateTo('/monitoring/alerts/timeline');
      await page.screenshot({ path: path.join(outDir, `alerts_ops_06_timeline_${res.name}.png`), fullPage: false });
      console.log(`Captured alerts_ops_06_timeline_${res.name}.png`);

      // Whole Monitoring Integration Proofs at 1920x1080
      if (res.name === '1920x1080') {
        console.log('\nCapturing Whole Monitoring Integration Proofs...');
        
        // Monitoring Home (Part 1)
        await navigateTo('/monitoring');
        await page.screenshot({ path: path.join(outDir, `monitoring_integration_01_home_${res.name}.png`), fullPage: false });
        console.log(`Captured monitoring_integration_01_home_${res.name}.png`);

        // Migration Operations (Part 2)
        await navigateTo('/monitoring/migrations');
        await page.screenshot({ path: path.join(outDir, `monitoring_integration_02_migrations_${res.name}.png`), fullPage: false });
        console.log(`Captured monitoring_integration_02_migrations_${res.name}.png`);

        // Platform Operations (Part 3)
        await navigateTo('/monitoring/platform');
        await page.screenshot({ path: path.join(outDir, `monitoring_integration_03_platform_${res.name}.png`), fullPage: false });
        console.log(`Captured monitoring_integration_03_platform_${res.name}.png`);

        // Incidents Direct Alias
        await navigateTo('/monitoring/incidents');
        await page.screenshot({ path: path.join(outDir, `monitoring_integration_04_incident_drilldown_${res.name}.png`), fullPage: false });
        console.log(`Captured monitoring_integration_04_incident_drilldown_${res.name}.png`);
      }

      await context.close();
    }

    await browser.close();
    console.log('\nAll Alerts and Whole-Monitoring screenshots captured successfully!');
  } catch (err) {
    console.error('Error during Playwright capture:', err);
  } finally {
    server.close();
    process.exit(0);
  }
});
