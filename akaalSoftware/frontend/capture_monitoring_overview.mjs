import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0');

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

const PORT = 4299;
server.listen(PORT, async () => {
  console.log(`Static server listening on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    const resolutions = [
      { name: '1920x1080', width: 1920, height: 1080 },
      { name: '1440x900', width: 1440, height: 900 }
    ];

    for (const res of resolutions) {
      console.log(`\nCapturing Monitoring Overview at resolution ${res.name}...`);
      const context = await browser.newContext({
        viewport: { width: res.width, height: res.height },
        deviceScaleFactor: 1
      });
      const page = await context.newPage();

      // Navigate to Monitoring page
      await page.goto(`http://localhost:${PORT}/monitoring`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(1000);

      // 1. Top Section Viewport
      await page.screenshot({
        path: path.join(outDir, `monitoring_01_top_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured monitoring_01_top_${res.name}.png`);

      // 2. Middle Section Viewport (scroll 600)
      await page.evaluate(() => {
        const main = document.querySelector('main');
        if (main) main.scrollTop = 550;
      });
      await page.waitForTimeout(500);

      await page.screenshot({
        path: path.join(outDir, `monitoring_02_middle_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured monitoring_02_middle_${res.name}.png`);

      // 3. Bottom Section Viewport (scroll 1200 for Alerts & Recent Events)
      await page.evaluate(() => {
        const main = document.querySelector('main');
        if (main) main.scrollTop = 1200;
      });
      await page.waitForTimeout(500);

      await page.screenshot({
        path: path.join(outDir, `monitoring_03_bottom_${res.name}.png`),
        fullPage: false
      });
      console.log(`Captured monitoring_03_bottom_${res.name}.png`);

      await context.close();
    }

    await browser.close();
  } catch (err) {
    console.error('Error during capture:', err);
  } finally {
    server.close(() => {
      console.log('Server closed. All screenshot captures complete.');
      process.exit(0);
    });
  }
});
