import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0/settings_part2_captures');

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

const PORT = 4391;
server.listen(PORT, async () => {
  console.log(`Settings Part 2 Verification Server running on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    const viewports = [
      { width: 1920, height: 1080, suffix: '1920x1080' },
      { width: 1440, height: 900, suffix: '1440x900' }
    ];

    for (const vp of viewports) {
      console.log(`\n========================================`);
      console.log(`STARTING VIEWPORT: ${vp.suffix}`);
      console.log(`========================================`);

      const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });

      const setAppearance = async (opts) => {
        await page.evaluate((o) => {
          const raw = localStorage.getItem('akaal_settings_appearance');
          let current = raw ? JSON.parse(raw) : {
            theme: 'enterprise-blue',
            palette: 'standard',
            contrast: 'standard',
            reduceMotion: false,
            enhancedFocus: false
          };
          current = { ...current, ...o };
          localStorage.setItem('akaal_settings_appearance', JSON.stringify(current));

          const root = document.documentElement;
          if (current.theme === 'dark') {
            root.classList.add('dark');
            root.setAttribute('data-theme', 'dark');
          } else {
            root.classList.remove('dark');
            root.setAttribute('data-theme', 'enterprise-blue');
          }

          if (current.palette === 'color-vision-safe') {
            root.classList.add('color-vision-safe');
            root.setAttribute('data-palette', 'color-vision-safe');
          } else {
            root.classList.remove('color-vision-safe');
            root.setAttribute('data-palette', 'standard');
          }

          if (current.contrast === 'high-contrast') {
            root.classList.add('high-contrast');
            root.setAttribute('data-contrast', 'high-contrast');
          } else {
            root.classList.remove('high-contrast');
            root.setAttribute('data-contrast', 'standard');
          }

          if (current.reduceMotion) {
            root.classList.add('reduce-motion');
            root.setAttribute('data-motion', 'reduced');
          } else {
            root.classList.remove('reduce-motion');
            root.setAttribute('data-motion', 'normal');
          }

          if (current.enhancedFocus) {
            root.classList.add('enhanced-focus');
            root.setAttribute('data-focus', 'enhanced');
          } else {
            root.classList.remove('enhanced-focus');
            root.setAttribute('data-focus', 'standard');
          }
        }, opts);
        await page.waitForTimeout(300);
      };

      // 1. 6.3 Runtime & Migration Defaults (Light)
      console.log(`Capturing 6.3 Runtime & Migration (Light) - ${vp.suffix}`);
      await page.goto(`http://localhost:${PORT}/settings/runtime-migration`, { waitUntil: 'networkidle' });
      await setAppearance({ theme: 'enterprise-blue', palette: 'standard', contrast: 'standard', reduceMotion: false, enhancedFocus: false });
      await page.waitForTimeout(500);

      await page.screenshot({ path: path.join(outDir, `01_settings_runtime_migration_top_${vp.suffix}.png`) });

      // Scroll down to middle (Queues, Resources, Bulk, CDC)
      await page.evaluate(() => {
        const el = document.getElementById('section-queues');
        if (el) el.scrollIntoView();
      });
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `02_settings_runtime_migration_middle_${vp.suffix}.png`) });

      // Scroll down to bottom (Incremental, Sync, Validation, Recovery)
      await page.evaluate(() => {
        const el = document.getElementById('section-incremental');
        if (el) el.scrollIntoView();
      });
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `03_settings_runtime_migration_bottom_${vp.suffix}.png`) });

      // 2. 6.4 Connector Defaults (Light)
      console.log(`Capturing 6.4 Connector Defaults (Light) - ${vp.suffix}`);
      await page.goto(`http://localhost:${PORT}/settings/connectors`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `04_settings_connectors_top_${vp.suffix}.png`) });

      // Scroll to bottom of Connectors
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `05_settings_connectors_bottom_${vp.suffix}.png`) });

      // 3. 6.5 Storage & Retention (Light)
      console.log(`Capturing 6.5 Storage & Retention (Light) - ${vp.suffix}`);
      await page.goto(`http://localhost:${PORT}/settings/storage`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `06_settings_storage_top_${vp.suffix}.png`) });

      // Scroll to bottom of Storage
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `07_settings_storage_bottom_${vp.suffix}.png`) });

      // 4. Dark Mode Captures
      console.log(`Capturing Dark Mode Surfaces - ${vp.suffix}`);
      await setAppearance({ theme: 'dark' });

      // 6.3 Runtime in Dark
      await page.goto(`http://localhost:${PORT}/settings/runtime-migration`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `08_settings_runtime_dark_${vp.suffix}.png`) });

      // 6.4 Connectors in Dark
      await page.goto(`http://localhost:${PORT}/settings/connectors`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `09_settings_connectors_dark_${vp.suffix}.png`) });

      // 6.5 Storage in Dark
      await page.goto(`http://localhost:${PORT}/settings/storage`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `10_settings_storage_dark_${vp.suffix}.png`) });

      // 5. Accessibility Modes
      console.log(`Capturing Accessibility Modes - ${vp.suffix}`);
      // High Contrast Dark
      await setAppearance({ theme: 'dark', contrast: 'high-contrast' });
      await page.goto(`http://localhost:${PORT}/settings/runtime-migration`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `11_settings_runtime_highcontrast_dark_${vp.suffix}.png`) });

      // High Contrast Light
      await setAppearance({ theme: 'enterprise-blue', contrast: 'high-contrast' });
      await page.goto(`http://localhost:${PORT}/settings/connectors`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `12_settings_connectors_highcontrast_light_${vp.suffix}.png`) });

      // Color Vision Safe (Okabe-Ito)
      await setAppearance({ theme: 'enterprise-blue', contrast: 'standard', palette: 'color-vision-safe' });
      await page.goto(`http://localhost:${PORT}/settings/storage`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `13_settings_storage_colorvision_${vp.suffix}.png`) });

      // Enhanced Focus & Reduced Motion
      await setAppearance({ theme: 'enterprise-blue', palette: 'standard', contrast: 'standard', reduceMotion: true, enhancedFocus: true });
      await page.goto(`http://localhost:${PORT}/settings/runtime-migration`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `14_settings_runtime_motion_focus_${vp.suffix}.png`) });

      // 6. Future Category Check: 6.6 Notifications
      await setAppearance({ theme: 'enterprise-blue', reduceMotion: false, enhancedFocus: false });
      await page.goto(`http://localhost:${PORT}/settings/notifications`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `15_future_notifications_planned_${vp.suffix}.png`) });

      await page.close();
    }

    // 7. Narrow desktop review (1280x800)
    console.log(`\n========================================`);
    console.log(`STARTING NARROW DESKTOP VIEWPORT: 1280x800`);
    console.log(`========================================`);
    const narrowPage = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    await narrowPage.goto(`http://localhost:${PORT}/settings/runtime-migration`, { waitUntil: 'networkidle' });
    await narrowPage.waitForTimeout(500);
    await narrowPage.screenshot({ path: path.join(outDir, `16_settings_runtime_narrow_1280x800.png`) });
    await narrowPage.close();

    await browser.close();
    server.close();
    console.log('\n========================================');
    console.log('ALL PLAYWRIGHT CAPTURES COMPLETED SUCCESSFULLY!');
    console.log(`Screenshots saved to: ${outDir}`);
    console.log('========================================\n');
  } catch (err) {
    console.error('Playwright execution error:', err);
    server.close();
    process.exit(1);
  }
});
