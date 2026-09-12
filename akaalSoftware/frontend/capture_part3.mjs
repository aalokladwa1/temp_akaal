import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('./dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0/settings_part3_captures');

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

const PORT = 4395;
server.listen(PORT, async () => {
  console.log(`Settings Part 3 Capture Server running on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    async function setPreferences(page, appearance) {
      await page.addInitScript((app) => {
        window.localStorage.setItem('akaal_settings_appearance', JSON.stringify(app));
      }, appearance);
    }

    // 1. Standard Light Theme (1920x1080)
    console.log('Capturing Light Theme 1920x1080...');
    let page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    await setPreferences(page, { theme: 'enterprise-blue', palette: 'standard', contrast: 'standard', reduceMotion: false, enhancedFocus: false });

    // 1.1 Notifications
    await page.goto(`http://localhost:${PORT}/settings/notifications`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '01_settings_notifications_1920x1080.png'), fullPage: true });

    // 1.2 Integrations
    await page.goto(`http://localhost:${PORT}/settings/integrations`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '02_settings_integrations_1920x1080.png'), fullPage: true });

    // 1.3 AI & Intelligence
    await page.goto(`http://localhost:${PORT}/settings/ai-intelligence`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '03_settings_ai_intelligence_1920x1080.png'), fullPage: true });

    // 1.4 Left Nav Shell Overview
    await page.screenshot({ path: path.join(outDir, '04_settings_nav_shell_1920x1080.png') });
    await page.close();

    // 2. Responsive 1440x900
    console.log('Capturing Light Theme 1440x900...');
    page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await setPreferences(page, { theme: 'enterprise-blue', palette: 'standard', contrast: 'standard', reduceMotion: false, enhancedFocus: false });

    await page.goto(`http://localhost:${PORT}/settings/notifications`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '05_settings_notifications_1440x900.png'), fullPage: true });

    await page.goto(`http://localhost:${PORT}/settings/integrations`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '06_settings_integrations_1440x900.png'), fullPage: true });

    await page.goto(`http://localhost:${PORT}/settings/ai-intelligence`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '07_settings_ai_intelligence_1440x900.png'), fullPage: true });
    await page.close();

    // 3. Compact 1280x800
    console.log('Capturing Compact 1280x800...');
    page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    await setPreferences(page, { theme: 'enterprise-blue', palette: 'standard', contrast: 'standard', reduceMotion: false, enhancedFocus: false });

    await page.goto(`http://localhost:${PORT}/settings/notifications`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '08_settings_notifications_1280x800.png'), fullPage: true });

    await page.goto(`http://localhost:${PORT}/settings/integrations`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '09_settings_integrations_1280x800.png'), fullPage: true });

    await page.goto(`http://localhost:${PORT}/settings/ai-intelligence`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '10_settings_ai_intelligence_1280x800.png'), fullPage: true });
    await page.close();

    // 4. Dark Theme (1920x1080)
    console.log('Capturing Dark Theme 1920x1080...');
    page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    await setPreferences(page, { theme: 'dark', palette: 'standard', contrast: 'standard', reduceMotion: false, enhancedFocus: false });

    await page.goto(`http://localhost:${PORT}/settings/notifications`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '11_settings_notifications_dark_1920x1080.png'), fullPage: true });

    await page.goto(`http://localhost:${PORT}/settings/integrations`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '12_settings_integrations_dark_1920x1080.png'), fullPage: true });

    await page.goto(`http://localhost:${PORT}/settings/ai-intelligence`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '13_settings_ai_intelligence_dark_1920x1080.png'), fullPage: true });
    await page.close();

    // 5. High Contrast Mode (1440x900)
    console.log('Capturing High Contrast 1440x900...');
    page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await setPreferences(page, { theme: 'enterprise-blue', palette: 'standard', contrast: 'high-contrast', reduceMotion: false, enhancedFocus: true });

    await page.goto(`http://localhost:${PORT}/settings/notifications`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '14_settings_notifications_highcontrast_1440x900.png'), fullPage: true });

    await page.goto(`http://localhost:${PORT}/settings/integrations`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '15_settings_integrations_highcontrast_1440x900.png'), fullPage: true });
    await page.close();

    // 6. Color Vision Safe Mode (1440x900)
    console.log('Capturing Color Vision Safe 1440x900...');
    page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await setPreferences(page, { theme: 'enterprise-blue', palette: 'color-vision-safe', contrast: 'standard', reduceMotion: false, enhancedFocus: false });

    await page.goto(`http://localhost:${PORT}/settings/ai-intelligence`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '16_settings_ai_intelligence_colorvision_1440x900.png'), fullPage: true });
    await page.close();

    // 7. Preserved Planned Categories
    console.log('Capturing Planned Categories...');
    page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto(`http://localhost:${PORT}/settings/logging`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, '17_future_logging_planned_1440x900.png'), fullPage: true });
    await page.close();

    await browser.close();
    server.close();
    console.log('All Settings Part 3 screenshots captured successfully!');
  } catch (err) {
    console.error('Error during capture:', err);
    server.close();
    process.exit(1);
  }
});
