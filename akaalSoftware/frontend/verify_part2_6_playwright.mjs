import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/7bb13979-7a02-48e3-9d1b-7626fcc38ff8/screenshots');

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
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

  const contentType = mimeTypes[ext] || 'text/html';
  res.writeHead(200, { 'Content-Type': contentType });
  fs.createReadStream(filePath).pipe(res);
});

server.listen(4200, async () => {
  console.log('Static server started at http://localhost:4200');

  const viewports = [
    { width: 1920, height: 1080, name: '1920x1080' },
    { width: 1440, height: 900, name: '1440x900' },
    { width: 1280, height: 800, name: '1280x800' },
    { width: 1024, height: 768, name: '1024x768' }
  ];

  const routes = [
    { path: '/migration/templates', name: 'templates_home' },
    { path: '/migration/templates/tmpl-ora-pg-m2', name: 'template_workspace' },
    { path: '/migration/history', name: 'history_list' },
    { path: '/migration/history/mig-fin-core-01', name: 'history_workspace' },
    { path: '/reports/evidence', name: 'evidence_explorer' }
  ];

  const browser = await chromium.launch({ channel: 'msedge', headless: true });

  for (const vp of viewports) {
    const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
    const page = await context.newPage();

    for (const r of routes) {
      const targetUrl = `http://localhost:4200${r.path}`;
      console.log(`Capturing ${r.name} at ${vp.name}...`);
      try {
        await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 10000 });
        await page.waitForTimeout(800);
        const shotFile = path.join(outDir, `${r.name}_${vp.name}.png`);
        await page.screenshot({ path: shotFile });
        console.log(`Saved: ${shotFile}`);
      } catch (err) {
        console.error(`Error capturing ${r.name} at ${vp.name}:`, err.message);
      }
    }

    await context.close();
  }

  await browser.close();
  server.close();
  console.log('Visual campaign complete!');
  process.exit(0);
});
