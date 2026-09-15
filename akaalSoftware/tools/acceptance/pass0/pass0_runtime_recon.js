const http = require('http');
const fs = require('fs');
const path = require('path');

const playwrightPath = path.resolve(__dirname, '../../../frontend/node_modules/playwright');
const { chromium } = require(playwrightPath);

const distDir = path.resolve(__dirname, '../../../frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/a6fe4362-4151-46e9-9b5c-71c3081e3f44/pass0_captures');
const manifestsDir = path.resolve(__dirname, 'manifests');

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}
if (!fs.existsSync(manifestsDir)) {
  fs.mkdirSync(manifestsDir, { recursive: true });
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

const PORT = 4350;
server.listen(PORT, async () => {
  console.log(`Pass 0 Recon Server running on http://localhost:${PORT}`);

  const results = {
    timestamp: new Date().toISOString(),
    surfacesTested: [],
    consoleErrors: [],
    consoleWarnings: [],
    themesTested: [],
    viewportsTested: []
  };

  let browser;
  try {
    browser = await chromium.launch({ headless: true, channel: 'msedge' });
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 }
    });
    const page = await context.newPage();

    page.on('console', msg => {
      if (msg.type() === 'error') {
        results.consoleErrors.push({ text: msg.text(), location: msg.location() });
      } else if (msg.type() === 'warning') {
        results.consoleWarnings.push({ text: msg.text(), location: msg.location() });
      }
    });

    page.on('pageerror', err => {
      results.consoleErrors.push({ text: err.message, stack: err.stack });
    });

    const routesToTest = [
      { name: 'Dashboard', path: '/dashboard', capture: '01_dashboard.png' },
      { name: 'Migration Portfolio', path: '/migration', capture: '02_migration.png' },
      { name: 'Execution Cockpit', path: '/cockpit', capture: '03_cockpit.png' },
      { name: 'Connections Home', path: '/connections', capture: '04_connections.png' },
      { name: 'Validation Portfolio', path: '/validation', capture: '05_validation.png' },
      { name: 'Monitoring Overview', path: '/monitoring', capture: '06_monitoring.png' },
      { name: 'Reports Library', path: '/reports', capture: '07_reports.png' },
      { name: 'Administration Home', path: '/administration', capture: '08_administration.png' },
      { name: 'Settings General', path: '/settings/general', capture: '09_settings_general.png' },
      { name: 'Settings Appearance', path: '/settings/appearance', capture: '10_settings_appearance.png' }
    ];

    for (const r of routesToTest) {
      console.log(`Navigating to ${r.name} (${r.path})...`);
      await page.goto(`http://localhost:${PORT}#${r.path}`, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(500);

      const title = await page.title();
      const hasShell = (await page.locator('header').count()) > 0;
      const hasNav = (await page.locator('aside').count()) > 0;
      const hasBrand = (await page.locator('text=DEVKROS').count()) > 0;

      const capturePath = path.join(outDir, r.capture);
      await page.screenshot({ path: capturePath });

      results.surfacesTested.push({
        name: r.name,
        route: r.path,
        renderedTitle: title,
        shellDetected: hasShell,
        sidebarDetected: hasNav,
        brandDetected: hasBrand,
        screenshot: r.capture,
        status: 'RENDERED_OK'
      });
    }

    // Theme tests
    console.log('Testing Dark Theme...');
    await page.evaluate(() => document.documentElement.classList.add('dark'));
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, '11_theme_dark.png') });
    results.themesTested.push('dark');

    console.log('Testing Color Vision Safe...');
    await page.evaluate(() => {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('color-vision-safe');
    });
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, '12_theme_color_vision_safe.png') });
    results.themesTested.push('color-vision-safe');

    console.log('Testing High Contrast...');
    await page.evaluate(() => {
      document.documentElement.classList.remove('color-vision-safe');
      document.documentElement.classList.add('high-contrast');
    });
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, '13_theme_high_contrast.png') });
    results.themesTested.push('high-contrast');

    // Reset themes
    await page.evaluate(() => {
      document.documentElement.classList.remove('high-contrast', 'dark', 'color-vision-safe');
    });

    // Viewport tests
    console.log('Testing Viewports...');
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, '14_viewport_1920x1080.png') });
    results.viewportsTested.push('1920x1080');

    await page.setViewportSize({ width: 1280, height: 800 });
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, '15_viewport_1280x800.png') });
    results.viewportsTested.push('1280x800');

    fs.writeFileSync(path.join(manifestsDir, 'pass0_recon_results.json'), JSON.stringify(results, null, 2));
    console.log('Reconnaissance complete! Results saved to manifests/pass0_recon_results.json');
  } catch (err) {
    console.error('Reconnaissance failed:', err);
    results.error = err.message;
    fs.writeFileSync(path.join(manifestsDir, 'pass0_recon_results.json'), JSON.stringify(results, null, 2));
  } finally {
    if (browser) await browser.close();
    server.close();
  }
});
