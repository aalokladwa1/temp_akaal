import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00');

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

// Static HTTP server for Angular SPA
const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  if (reqPath === '/' || reqPath === '') reqPath = '/index.html';
  
  let filePath = path.join(distDir, reqPath);
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(distDir, 'index.html');
  }

  const ext = path.extname(filePath).toLowerCase();
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

  const contentType = mimeTypes[ext] || 'application/octet-stream';
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

const PORT = 4295;
server.listen(PORT, async () => {
  console.log(`Static server listening on http://localhost:${PORT}`);

  const browser = await chromium.launch({ headless: true, channel: 'msedge' });

  const resolutions = [
    { name: '1920x1080', width: 1920, height: 1080 },
    { name: '1440x900', width: 1440, height: 900 }
  ];

  for (const res of resolutions) {
    console.log(`\nCapturing at resolution ${res.name}...`);
    const context = await browser.newContext({
      viewport: { width: res.width, height: res.height },
      deviceScaleFactor: 1
    });
    const page = await context.newPage();

    // Navigate to Connections page
    await page.goto(`http://localhost:${PORT}/connections`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // 1. Full Inventory (Clean columns: Name, Provider, Verification, Usage)
    await page.screenshot({
      path: path.join(outDir, `conn_01_inventory_${res.name}.png`),
      fullPage: false
    });
    console.log(`Captured conn_01_inventory_${res.name}.png`);

    // 2. Open Overflow Action Menu (⋯) on the first row
    const menuBtn = page.locator('button[title="Quick Actions"]').first();
    if (await menuBtn.isVisible()) {
      await menuBtn.click();
      await page.waitForTimeout(400);
      await page.screenshot({
        path: path.join(outDir, `conn_02_action_menu_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured conn_02_action_menu_${res.name}.png`);
      // Close menu
      await page.keyboard.press('Escape');
      await page.waitForTimeout(200);
    }

    // 3. Filter: Click summary strip "Needs Attention" card
    const attentionCard = page.locator('text=Needs Attention').first();
    if (await attentionCard.isVisible()) {
      await attentionCard.click();
      await page.waitForTimeout(400);
      await page.screenshot({
        path: path.join(outDir, `conn_03_filter_attention_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured conn_03_filter_attention_${res.name}.png`);
    }

    // Reset to All
    const allCard = page.locator('text=Total Inventory').first();
    if (await allCard.isVisible()) {
      await allCard.click();
      await page.waitForTimeout(300);
    }

    // 4. Open Slide-over Inspect Drawer (Click on first row)
    const firstRowName = page.locator('table tbody tr td span.font-semibold').first();
    if (await firstRowName.isVisible()) {
      await firstRowName.click();
      await page.waitForTimeout(600);
      await page.screenshot({
        path: path.join(outDir, `conn_04_inspect_drawer_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured conn_04_inspect_drawer_${res.name}.png`);

      // Close drawer
      const closeBtn = page.locator('button:has-text("Close Drawer")').first();
      if (await closeBtn.isVisible()) {
        await closeBtn.click();
        await page.waitForTimeout(400);
      }
    }

    await context.close();
  }

  await browser.close();
  server.close(() => {
    console.log('Server closed. All screenshot captures complete.');
    process.exit(0);
  });
});
