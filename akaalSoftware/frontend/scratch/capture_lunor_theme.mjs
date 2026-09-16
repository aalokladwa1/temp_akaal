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

const PORT = 4399;
server.listen(PORT, async () => {
  try {
    const browser = await chromium.launch({ 
      headless: true,
      executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
    });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    
    await context.addInitScript(() => {
      try {
        localStorage.setItem('akaal_settings_appearance', JSON.stringify({
          theme: 'dark',
          palette: 'standard',
          contrast: 'standard',
          reduceMotion: false,
          enhancedFocus: false
        }));
      } catch (e) {}
    });

    const page = await context.newPage();

    console.log('Navigating to root...');
    await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);

    // 1. Capture Dashboard
    const outDir = 'c:/Users/LENOVO/.gemini/antigravity-ide/brain/11ed0572-67f4-46e9-a2a8-72859c78ddcb';
    await page.screenshot({ path: path.join(outDir, 'lunor_dark_dashboard.png') });
    console.log('Saved lunor_dark_dashboard.png');

    // 2. Click on Settings in the sidebar
    console.log('Clicking Settings in sidebar...');
    await page.click('a[routerlink="/settings"]');
    await page.waitForTimeout(600);

    // 3. Click on Appearance in the settings sidebar
    console.log('Clicking Appearance tab...');
    await page.click('a[href*="appearance"], a:has-text("Appearance")');
    await page.waitForTimeout(600);

    // 4. Click Dark Mode card to trigger the notification banner
    console.log('Clicking Dark Mode radio card to test banner...');
    await page.click('div[role="radio"]:has-text("Dark Mode")');
    await page.waitForTimeout(600);

    await page.screenshot({ path: path.join(outDir, 'lunor_dark_appearance.png') });
    console.log('Saved lunor_dark_appearance.png with banner and active theme');

    // 5. Click Migration in sidebar
    console.log('Clicking Migration...');
    await page.click('a[routerlink="/migration"]');
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, 'lunor_dark_migration.png') });
    console.log('Saved lunor_dark_migration.png');

    await browser.close();
  } catch (err) {
    console.error(err);
  } finally {
    server.close();
  }
});
