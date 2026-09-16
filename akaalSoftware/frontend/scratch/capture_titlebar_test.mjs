import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve(process.cwd(), 'akaalSoftware/frontend/dist/akaal-software/browser');
const altDistDir = path.resolve(process.cwd(), 'akaalSoftware/frontend/dist/akaal-software');
const activeDistDir = fs.existsSync(distDir) ? distDir : altDistDir;

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  const ext = path.extname(reqPath).toLowerCase();
  let filePath = path.join(activeDistDir, reqPath);

  if (ext) {
    if (!fs.existsSync(filePath)) {
      filePath = path.join(activeDistDir, path.basename(reqPath));
    }
  } else {
    filePath = path.join(activeDistDir, 'index.html');
  }

  if (!fs.existsSync(filePath)) {
    filePath = path.join(activeDistDir, 'index.html');
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

const PORT = 4397;
server.listen(PORT, async () => {
  try {
    const browser = await chromium.launch({ 
      headless: true,
      executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
    });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    const outDir = 'c:/Users/LENOVO/.gemini/antigravity-ide/brain/11ed0572-67f4-46e9-a2a8-72859c78ddcb';

    // 1. Dark Mode Titlebar Test
    console.log('Testing Dark Mode Titlebar...');
    await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
    await page.evaluate(() => {
      document.documentElement.classList.add('dark');
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await page.waitForTimeout(500);

    // Hover over top edge (y = 2) to reveal titlebar
    await page.mouse.move(700, 2);
    await page.waitForTimeout(400);

    // Capture full title strip area (crop top 120px)
    await page.screenshot({ 
      path: path.join(outDir, 'professional_titlebar_dark.png'),
      clip: { x: 0, y: 0, width: 1440, height: 100 }
    });
    console.log('Saved professional_titlebar_dark.png');

    // 2. Light Mode Titlebar Test
    console.log('Testing Light Mode Titlebar...');
    await page.evaluate(() => {
      document.documentElement.classList.remove('dark');
      document.documentElement.setAttribute('data-theme', 'light');
    });
    await page.waitForTimeout(500);

    // Hover top edge to reveal titlebar
    await page.mouse.move(700, 2);
    await page.waitForTimeout(400);

    await page.screenshot({ 
      path: path.join(outDir, 'professional_titlebar_light.png'),
      clip: { x: 0, y: 0, width: 1440, height: 100 }
    });
    console.log('Saved professional_titlebar_light.png');

    await browser.close();
  } catch (err) {
    console.error(err);
  } finally {
    server.close();
  }
});
