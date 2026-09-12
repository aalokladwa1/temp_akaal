import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0/settings_reference_captures');

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
      if (filePath.endsWith('index.html')) {
        let html = content.toString('utf-8');
        html = html.replace('<base href="./">', '<base href="/">');
        res.writeHead(200, { 'Content-Type': 'text/html' });
        return res.end(html, 'utf-8');
      }
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

const PORT = 4371;
server.listen(PORT, async () => {
  console.log(`Baseline verification server running on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    const viewports = [
      { width: 1920, height: 1080, suffix: '1920x1080' },
      { width: 1440, height: 900, suffix: '1440x900' }
    ];

    const routes = [
      { name: '01_admin_home', path: '/administration' },
      { name: '02_monitoring', path: '/monitoring' },
      { name: '03_connections', path: '/connections' },
      { name: '04_migration', path: '/migration' },
      { name: '05_reports', path: '/reports' }
    ];

    for (const vp of viewports) {
      console.log(`\n=== Capturing baseline for viewport: ${vp.suffix} ===`);
      const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });

      await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(400);

      const navTo = async (route) => {
        await page.evaluate((r) => {
          window.location.hash = '';
          window.history.pushState({}, '', r);
          window.dispatchEvent(new PopStateEvent('popstate'));
        }, route);
        await page.waitForTimeout(600);
      };

      for (const r of routes) {
        await navTo(r.path);
        const capturePath = path.join(outDir, `${r.name}_${vp.suffix}.png`);
        await page.screenshot({ path: capturePath });
        console.log(`Captured ${path.basename(capturePath)}`);
      }

      await page.close();
    }

    await browser.close();
    console.log('\nAll baseline captures saved to settings_reference_captures!');
  } catch (err) {
    console.error('Error during capture:', err);
  } finally {
    server.close();
    process.exit(0);
  }
});
