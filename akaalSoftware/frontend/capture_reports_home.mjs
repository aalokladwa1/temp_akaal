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

const PORT = 4325;
server.listen(PORT, async () => {
  console.log(`Rebuild verification server listening on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    const resolutions = [
      { name: '1920x1080', width: 1920, height: 1080 },
      { name: '1440x900', width: 1440, height: 900 },
      { name: '1024x768', width: 1024, height: 768 }
    ];

    for (const res of resolutions) {
      console.log(`\n--- Capturing Rebuilt Reports Home at ${res.name} ---`);
      const context = await browser.newContext({
        viewport: { width: res.width, height: res.height },
        deviceScaleFactor: 1
      });
      const page = await context.newPage();

      const navigateTo = async (url) => {
        await page.evaluate((target) => {
          window.history.pushState({}, '', target);
          window.dispatchEvent(new Event('popstate'));
        }, url);
        await page.waitForTimeout(800);
      };

      await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(600);

      // 1. Top Section
      await navigateTo('/reports');
      await page.screenshot({ path: path.join(outDir, `rebuilt_reports_01_top_${res.name}.png`), fullPage: false });
      console.log(`Captured rebuilt_reports_01_top_${res.name}.png`);

      // 2. Scrolled Section (Recent Reports Table & Evidence Activity)
      await page.evaluate(() => {
        const m = document.querySelector('main');
        if (m) m.scrollTo({ top: 400, behavior: 'instant' });
      });
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `rebuilt_reports_02_scrolled_${res.name}.png`), fullPage: false });
      console.log(`Captured rebuilt_reports_02_scrolled_${res.name}.png`);

      await context.close();
    }

    await browser.close();
    console.log('\nAll post-rebuild verification captures completed successfully!');
  } catch (err) {
    console.error('Error during Playwright capture:', err);
  } finally {
    server.close();
    process.exit(0);
  }
});
