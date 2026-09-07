import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00');
const studyDir = path.join(outDir, 'study');

if (!fs.existsSync(studyDir)) {
  fs.mkdirSync(studyDir, { recursive: true });
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

server.listen(4299, async () => {
  console.log('Static server listening on http://localhost:4299');

  const browser = await chromium.launch({ headless: true, channel: 'msedge' });

  const resolutions = [
    { name: '1920x1080', width: 1920, height: 1080 },
    { name: '1440x900', width: 1440, height: 900 }
  ];

  for (const res of resolutions) {
    const page = await browser.newPage({ viewport: { width: res.width, height: res.height } });
    await page.goto('http://localhost:4299/migration/validation');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(600);

    const saveScreenshot = async (name) => {
      const fileName = `${name}_${res.name}.png`;
      const rootPath = path.join(outDir, fileName);
      const studyPath = path.join(studyDir, fileName);
      await page.screenshot({ path: rootPath });
      fs.copyFileSync(rootPath, studyPath);
      console.log(`Saved screenshot: ${fileName}`);
    };

    // 1. Full Home View (Top)
    await saveScreenshot('validation_home_01_overview');

    // 2. Scrolled Middle Zone (Validations Table)
    await page.evaluate(() => {
      const main = document.querySelector('main');
      if (main) main.scrollTop = 450;
    });
    await page.waitForTimeout(200);
    await saveScreenshot('validation_home_02_table_view');

    // 3. Scrolled Lower Zone (Upcoming + Recent Results + Activity)
    await page.evaluate(() => {
      const main = document.querySelector('main');
      if (main) main.scrollTop = main.scrollHeight;
    });
    await page.waitForTimeout(200);
    await saveScreenshot('validation_home_03_lower_dock');

    // Scroll back to top
    await page.evaluate(() => {
      const main = document.querySelector('main');
      if (main) main.scrollTop = 0;
    });
    await page.waitForTimeout(200);

    // 4. Click Needs Attention KPI Filter
    const kpiCards = await page.$$('.grid-cols-1 > div, .sm\\:grid-cols-2 > div, .lg\\:grid-cols-4 > div');
    if (kpiCards.length >= 2) {
      await kpiCards[1].click();
      await page.waitForTimeout(300);
      await saveScreenshot('validation_home_04_kpi_attention_filtered');
      // Reset filter
      await kpiCards[1].click();
      await page.waitForTimeout(200);
    }

    // 5. Open Status Dropdown
    const statusDropdownBtn = await page.$('button:has-text("All Statuses")');
    if (statusDropdownBtn) {
      await statusDropdownBtn.click();
      await page.waitForTimeout(300);
      await saveScreenshot('validation_home_05_status_dropdown_open');
      // Close dropdown
      await page.click('body', { position: { x: 10, y: 10 } });
      await page.waitForTimeout(200);
    }

    // 6. Open Table Row Action Menu
    const actionBtn = await page.$('table button[title="Actions"]');
    if (actionBtn) {
      await actionBtn.click();
      await page.waitForTimeout(300);
      await saveScreenshot('validation_home_06_action_menu_open');
    }

    await page.close();
  }

  await browser.close();
  server.close();
  console.log('Finished capturing all Validation Home scenarios.');
  process.exit(0);
});
