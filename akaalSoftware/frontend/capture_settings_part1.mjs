import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0/settings_captures');

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

const PORT = 4389;
server.listen(PORT, async () => {
  console.log(`Settings Interactive Verification Server running on http://localhost:${PORT}`);

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

      // Navigate to base index
      await page.goto(`http://localhost:${PORT}/settings`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(600);

      const clickNav = async (selector) => {
        await page.locator(selector).first().click();
        await page.waitForTimeout(400);
      };

      // Helper to set and apply appearance options directly via SettingsService
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
          // Theme
          if (current.theme === 'dark') {
            root.classList.add('dark');
            root.setAttribute('data-theme', 'dark');
          } else {
            root.classList.remove('dark');
            root.setAttribute('data-theme', 'enterprise-blue');
          }

          // Palette
          if (current.palette === 'color-vision-safe') {
            root.classList.add('color-vision-safe');
            root.setAttribute('data-palette', 'color-vision-safe');
          } else {
            root.classList.remove('color-vision-safe');
            root.setAttribute('data-palette', 'standard');
          }

          // Contrast
          if (current.contrast === 'high-contrast') {
            root.classList.add('high-contrast');
            root.setAttribute('data-contrast', 'high-contrast');
          } else {
            root.classList.remove('high-contrast');
            root.setAttribute('data-contrast', 'standard');
          }

          // Motion
          if (current.reduceMotion) {
            root.classList.add('reduce-motion');
            root.setAttribute('data-motion', 'reduced');
          } else {
            root.classList.remove('reduce-motion');
            root.setAttribute('data-motion', 'normal');
          }

          // Focus
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

      // Reset to default
      await setAppearance({ theme: 'enterprise-blue', palette: 'standard', contrast: 'standard', reduceMotion: false, enhancedFocus: false });

      // 1. General Settings (Default Light)
      await clickNav('a[href="/settings/general"]');
      await page.screenshot({ path: path.join(outDir, `01_settings_general_light_${vp.suffix}.png`) });
      console.log(`Captured 01_settings_general_light_${vp.suffix}.png`);

      // 2. Appearance Settings (Default Light)
      await clickNav('a[href="/settings/appearance"]');
      await page.screenshot({ path: path.join(outDir, `02_settings_appearance_light_${vp.suffix}.png`) });
      console.log(`Captured 02_settings_appearance_light_${vp.suffix}.png`);

      // 3. Appearance Settings -> Click Dark Mode Tile interactively!
      const darkTile = page.locator('div[role="radio"]').filter({ hasText: 'Dark Mode' });
      if (await darkTile.count() > 0) {
        await darkTile.first().click();
        await page.waitForTimeout(400);
      } else {
        await setAppearance({ theme: 'dark' });
      }
      await page.screenshot({ path: path.join(outDir, `04_settings_appearance_dark_${vp.suffix}.png`) });
      console.log(`Captured 04_settings_appearance_dark_${vp.suffix}.png`);

      // 4. General Settings (Dark Mode)
      await clickNav('a[href="/settings/general"]');
      await page.screenshot({ path: path.join(outDir, `03_settings_general_dark_${vp.suffix}.png`) });
      console.log(`Captured 03_settings_general_dark_${vp.suffix}.png`);

      // 5. Back to Appearance -> Color Vision Safe in Dark Mode
      await clickNav('a[href="/settings/appearance"]');
      const cvsTile = page.locator('div[role="radio"]').filter({ hasText: 'Color Vision Safe' });
      if (await cvsTile.count() > 0) {
        await cvsTile.first().click();
        await page.waitForTimeout(400);
      } else {
        await setAppearance({ palette: 'color-vision-safe' });
      }
      await page.screenshot({ path: path.join(outDir, `06_settings_appearance_colorvision_dark_${vp.suffix}.png`) });
      console.log(`Captured 06_settings_appearance_colorvision_dark_${vp.suffix}.png`);

      // 6. Color Vision Safe in Light Mode
      const lightTile = page.locator('div[role="radio"]').filter({ hasText: 'Enterprise Blue' });
      if (await lightTile.count() > 0) {
        await lightTile.first().click();
        await page.waitForTimeout(400);
      } else {
        await setAppearance({ theme: 'enterprise-blue' });
      }
      await page.screenshot({ path: path.join(outDir, `05_settings_appearance_colorvision_light_${vp.suffix}.png`) });
      console.log(`Captured 05_settings_appearance_colorvision_light_${vp.suffix}.png`);

      // 7. High Contrast in Light Mode
      const stdPaletteTile = page.locator('div[role="radio"]').filter({ hasText: 'Standard Enterprise' });
      if (await stdPaletteTile.count() > 0) {
        await stdPaletteTile.first().click();
      }
      const hcTile = page.locator('div[role="radio"]').filter({ hasText: 'High Contrast' });
      if (await hcTile.count() > 0) {
        await hcTile.first().click();
        await page.waitForTimeout(400);
      }
      await page.screenshot({ path: path.join(outDir, `07_settings_appearance_highcontrast_light_${vp.suffix}.png`) });
      console.log(`Captured 07_settings_appearance_highcontrast_light_${vp.suffix}.png`);

      // 8. High Contrast in Dark Mode
      if (await darkTile.count() > 0) {
        await darkTile.first().click();
        await page.waitForTimeout(400);
      }
      await page.screenshot({ path: path.join(outDir, `08_settings_appearance_highcontrast_dark_${vp.suffix}.png`) });
      console.log(`Captured 08_settings_appearance_highcontrast_dark_${vp.suffix}.png`);

      // 9. Motion & Focus Toggles
      await setAppearance({ theme: 'enterprise-blue', contrast: 'standard', reduceMotion: true, enhancedFocus: true });
      await page.screenshot({ path: path.join(outDir, `09_settings_appearance_motion_focus_${vp.suffix}.png`) });
      console.log(`Captured 09_settings_appearance_motion_focus_${vp.suffix}.png`);

      // 10. Future Category: 6.3 Runtime & Migration
      await setAppearance({ theme: 'enterprise-blue', contrast: 'standard', reduceMotion: false, enhancedFocus: false });
      await clickNav('a[href="/settings/runtime-migration"]');
      await page.screenshot({ path: path.join(outDir, `10_future_runtime_migration_${vp.suffix}.png`) });
      console.log(`Captured 10_future_runtime_migration_${vp.suffix}.png`);

      // 11. Future Category: 6.4 Connector Defaults
      await clickNav('a[href="/settings/connectors"]');
      await page.screenshot({ path: path.join(outDir, `11_future_connectors_${vp.suffix}.png`) });
      console.log(`Captured 11_future_connectors_${vp.suffix}.png`);

      // 12. Future Category: 6.6 Notifications
      await clickNav('a[href="/settings/notifications"]');
      await page.screenshot({ path: path.join(outDir, `12_future_notifications_${vp.suffix}.png`) });
      console.log(`Captured 12_future_notifications_${vp.suffix}.png`);

      // 13. Administration Home in Dark Mode
      await setAppearance({ theme: 'dark' });
      await clickNav('a[href="/administration"]');
      await page.screenshot({ path: path.join(outDir, `13_admin_home_dark_mode_${vp.suffix}.png`) });
      console.log(`Captured 13_admin_home_dark_mode_${vp.suffix}.png`);

      // 14. Monitoring in Dark Mode
      await clickNav('a[href="/monitoring"]');
      await page.screenshot({ path: path.join(outDir, `14_monitoring_dark_mode_${vp.suffix}.png`) });
      console.log(`Captured 14_monitoring_dark_mode_${vp.suffix}.png`);

      // 15. Reports in Dark Mode
      await clickNav('a[href="/reports"]');
      await page.screenshot({ path: path.join(outDir, `15_reports_dark_mode_${vp.suffix}.png`) });
      console.log(`Captured 15_reports_dark_mode_${vp.suffix}.png`);

      await page.close();
    }

    await browser.close();
    console.log('\nAll 30 Playwright captures completed successfully!');
  } catch (err) {
    console.error('Capture error:', err);
  } finally {
    server.close();
    process.exit(0);
  }
});
