import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0');

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

const PORT = 4322;
server.listen(PORT, async () => {
  console.log(`Forensics server listening on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    const resolutions = [
      { name: '1920x1080', width: 1920, height: 1080 },
      { name: '1440x900', width: 1440, height: 900 },
      { name: '1024x768', width: 1024, height: 768 }
    ];

    const targets = [
      { name: 'monitoring', url: '/monitoring' },
      { name: 'migration', url: '/migration' },
      { name: 'validation', url: '/validation' },
      { name: 'connections', url: '/connections' }
    ];

    for (const res of resolutions) {
      console.log(`\n=== Capturing Reference Homes at ${res.name} ===`);
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

      for (const target of targets) {
        await navigateTo(target.url);
        const filename = `ref_${target.name}_${res.name}.png`;
        await page.screenshot({ path: path.join(outDir, filename), fullPage: false });
        console.log(`Captured ${filename}`);

        if (res.name === '1920x1080') {
          // Extract DOM metrics for this page
          const metrics = await page.evaluate(() => {
            const container = document.querySelector('main > div') || document.querySelector('main');
            const header = document.querySelector('header') || document.querySelector('main h1')?.parentElement;
            const buttons = Array.from(document.querySelectorAll('button, a.btn, a[class*="bg-blue-600"]')).map(b => ({
              text: b.innerText?.trim(),
              height: b.getBoundingClientRect().height,
              classes: b.className
            }));
            const cards = Array.from(document.querySelectorAll('div[class*="rounded-"], div[class*="border"]')).slice(0, 10).map(c => ({
              padding: window.getComputedStyle(c).padding,
              borderRadius: window.getComputedStyle(c).borderRadius,
              bg: window.getComputedStyle(c).backgroundColor
            }));
            return {
              containerWidth: container?.getBoundingClientRect().width,
              title: document.querySelector('h1')?.innerText?.trim(),
              subtitle: document.querySelector('h1 + p, h1 ~ p')?.innerText?.trim(),
              buttonSample: buttons.slice(0, 5),
              cardSample: cards.slice(0, 3)
            };
          });
          console.log(`Metrics for ${target.name}:`, JSON.stringify(metrics, null, 2));
        }
      }

      await context.close();
    }

    await browser.close();
    console.log('\nAll reference home forensics captured successfully!');
  } catch (err) {
    console.error('Forensics error:', err);
  } finally {
    server.close();
    process.exit(0);
  }
});
