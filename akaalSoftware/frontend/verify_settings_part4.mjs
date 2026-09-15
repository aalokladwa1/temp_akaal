import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0/settings_part4_captures');

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
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

const PORT = 4349;
server.listen(PORT, async () => {
  console.log(`Part 4 Verification server running on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    // Helper to capture a page state
    async function capture(page, filename, description) {
      const fullPath = path.join(outDir, filename);
      await page.screenshot({ path: fullPath, fullPage: false });
      console.log(`[CAPTURED] ${filename} — ${description}`);
    }

    // Helper to navigate to a settings category via UI click and wait for component to be active
    async function goToSettingsCategory(page, categoryLabel, headingMatch = null) {
      const targetHeading = headingMatch || categoryLabel;
      if (!page.url().includes('/settings')) {
        const settingsNav = page.locator('aside a:has-text("Settings"), a[href*="settings"]').first();
        await settingsNav.click();
        await page.waitForTimeout(400);
      }
      const catLink = page.locator(`nav a:has-text("${categoryLabel}")`).first();
      await catLink.click();
      await page.locator(`h2:has-text("${targetHeading}")`).waitFor({ state: 'visible', timeout: 6000 });
      await page.waitForTimeout(300);
    }

    // ------------------------------------------------------------------------
    // 1. Desktop Standard 1920x1080 (Daylight Default)
    // ------------------------------------------------------------------------
    const page1080 = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    await page1080.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
    await page1080.waitForTimeout(500);

    // 01: Logging & Diagnostics (1920x1080)
    await goToSettingsCategory(page1080, 'Logging & Diagnostics');
    await capture(page1080, '01_settings_logging_1920x1080.png', 'Surface 9: Logging & Diagnostics');

    // 02: Advanced (1920x1080)
    await goToSettingsCategory(page1080, 'Advanced');
    await capture(page1080, '02_settings_advanced_1920x1080.png', 'Surface 10: Advanced');

    // 03: AI & Intelligence Defect Fix Check (1920x1080)
    await goToSettingsCategory(page1080, 'AI & Intelligence');
    await page1080.locator('text="CDC Buffer Saturation Warning"').scrollIntoViewIfNeeded();
    await page1080.waitForTimeout(300);
    await capture(page1080, '03_settings_ai_intelligence_defect_fixed_1920x1080.png', 'AI & Intelligence: CDC Buffer drain text on next line, icons rendered');
    await page1080.locator('main.overflow-y-auto').evaluate(el => el.scrollTop = 0);

    // 04: Notifications Icon Verification (1920x1080)
    await goToSettingsCategory(page1080, 'Notifications');
    await capture(page1080, '04_settings_notifications_icons_verified_1920x1080.png', 'Notifications: Mail, message-square, webhook icons verified');

    // 05: Integrations (1920x1080)
    await goToSettingsCategory(page1080, 'Integrations');
    await capture(page1080, '05_settings_integrations_1920x1080.png', 'Integrations: Observability, Lineage, Installed cards');

    // 06: General (1920x1080)
    await goToSettingsCategory(page1080, 'General');
    await capture(page1080, '06_settings_general_1920x1080.png', 'General: Workstation landing, localization, safety gates');

    // 07: Appearance (1920x1080)
    await goToSettingsCategory(page1080, 'Appearance');
    await capture(page1080, '07_settings_appearance_1920x1080.png', 'Appearance: Themes, high contrast, color vision safe');

    // 08: Runtime & Migration (1920x1080)
    await goToSettingsCategory(page1080, 'Runtime & Migration');
    await capture(page1080, '08_settings_runtime_migration_1920x1080.png', 'Runtime & Migration: Pipeline concurrency, batching');

    // 09: Connector Defaults (1920x1080)
    await goToSettingsCategory(page1080, 'Connector Defaults');
    await capture(page1080, '09_settings_connectors_1920x1080.png', 'Connector Defaults: Timeouts, keep-alives, security baselines');

    // 10: Storage & Retention (1920x1080)
    await goToSettingsCategory(page1080, 'Storage & Retention');
    await capture(page1080, '10_settings_storage_1920x1080.png', 'Storage & Retention: Checkpoints, CDC buffers, logs');

    await page1080.close();

    // ------------------------------------------------------------------------
    // 2. Laptop Standard 1440x900
    // ------------------------------------------------------------------------
    const page900 = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page900.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
    await page900.waitForTimeout(500);

    await goToSettingsCategory(page900, 'Logging & Diagnostics');
    await capture(page900, '11_settings_logging_1440x900.png', 'Logging & Diagnostics at 1440x900');

    await goToSettingsCategory(page900, 'Advanced');
    await capture(page900, '12_settings_advanced_1440x900.png', 'Advanced at 1440x900');

    await goToSettingsCategory(page900, 'AI & Intelligence');
    await page900.locator('text="CDC Buffer Saturation Warning"').scrollIntoViewIfNeeded();
    await page900.waitForTimeout(300);
    await capture(page900, '13_settings_ai_intelligence_1440x900.png', 'AI & Intelligence at 1440x900 with drain line wrap');

    await page900.close();

    // ------------------------------------------------------------------------
    // 3. Compact Laptop 1280x800
    // ------------------------------------------------------------------------
    const page800 = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    await page800.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
    await page800.waitForTimeout(500);

    await goToSettingsCategory(page800, 'Logging & Diagnostics');
    await capture(page800, '14_settings_logging_1280x800.png', 'Logging & Diagnostics at 1280x800');

    await goToSettingsCategory(page800, 'Advanced');
    await capture(page800, '15_settings_advanced_1280x800.png', 'Advanced at 1280x800');

    await goToSettingsCategory(page800, 'AI & Intelligence');
    await page800.locator('text="CDC Buffer Saturation Warning"').scrollIntoViewIfNeeded();
    await page800.waitForTimeout(300);
    await capture(page800, '16_settings_ai_intelligence_1280x800.png', 'AI & Intelligence at 1280x800 (checking switch spacing)');

    await page800.close();

    // ------------------------------------------------------------------------
    // 4. Dark Mode Verification (1440x900)
    // ------------------------------------------------------------------------
    const pageDark = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await pageDark.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
    await pageDark.waitForTimeout(500);

    await pageDark.evaluate(() => {
      document.documentElement.classList.add('dark');
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await pageDark.waitForTimeout(300);

    await goToSettingsCategory(pageDark, 'Logging & Diagnostics');
    await pageDark.evaluate(() => {
      document.documentElement.classList.add('dark');
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await pageDark.waitForTimeout(300);
    await capture(pageDark, '17_settings_logging_dark_1440x900.png', 'Logging & Diagnostics in Dark Mode');

    await goToSettingsCategory(pageDark, 'Advanced');
    await pageDark.evaluate(() => {
      document.documentElement.classList.add('dark');
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await pageDark.waitForTimeout(300);
    await capture(pageDark, '18_settings_advanced_dark_1440x900.png', 'Advanced in Dark Mode');

    await goToSettingsCategory(pageDark, 'AI & Intelligence');
    await pageDark.evaluate(() => {
      document.documentElement.classList.add('dark');
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await pageDark.locator('text="CDC Buffer Saturation Warning"').scrollIntoViewIfNeeded();
    await pageDark.waitForTimeout(300);
    await capture(pageDark, '19_settings_ai_intelligence_dark_1440x900.png', 'AI & Intelligence in Dark Mode');

    await pageDark.close();

    // ------------------------------------------------------------------------
    // 5. High Contrast Mode Verification (1440x900)
    // ------------------------------------------------------------------------
    const pageHC = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await pageHC.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
    await pageHC.waitForTimeout(500);

    await goToSettingsCategory(pageHC, 'Logging & Diagnostics');
    await pageHC.evaluate(() => {
      document.documentElement.classList.add('high-contrast');
      document.documentElement.setAttribute('data-contrast', 'high-contrast');
    });
    await pageHC.waitForTimeout(300);
    await capture(pageHC, '20_settings_logging_high_contrast_1440x900.png', 'Logging & Diagnostics in High Contrast Mode');

    await goToSettingsCategory(pageHC, 'Advanced');
    await pageHC.evaluate(() => {
      document.documentElement.classList.add('high-contrast');
      document.documentElement.setAttribute('data-contrast', 'high-contrast');
    });
    await pageHC.waitForTimeout(300);
    await capture(pageHC, '21_settings_advanced_high_contrast_1440x900.png', 'Advanced in High Contrast Mode');

    await pageHC.close();

    // ------------------------------------------------------------------------
    // 6. Color Vision Safe Mode Verification (1440x900)
    // ------------------------------------------------------------------------
    const pageCVS = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await pageCVS.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
    await pageCVS.waitForTimeout(500);

    await goToSettingsCategory(pageCVS, 'Logging & Diagnostics');
    await pageCVS.evaluate(() => {
      document.documentElement.classList.add('color-vision-safe');
      document.documentElement.setAttribute('data-palette', 'color-vision-safe');
    });
    await pageCVS.waitForTimeout(300);
    await capture(pageCVS, '22_settings_logging_color_vision_safe_1440x900.png', 'Logging & Diagnostics in Color Vision Safe Mode');

    await goToSettingsCategory(pageCVS, 'Advanced');
    await pageCVS.evaluate(() => {
      document.documentElement.classList.add('color-vision-safe');
      document.documentElement.setAttribute('data-palette', 'color-vision-safe');
    });
    await pageCVS.waitForTimeout(300);
    await capture(pageCVS, '23_settings_advanced_color_vision_safe_1440x900.png', 'Advanced in Color Vision Safe Mode');

    await pageCVS.close();

    // ------------------------------------------------------------------------
    // 7. Verification of Zero 6.x and Zero Missing Icons
    // ------------------------------------------------------------------------
    const verifyPage = await browser.newPage();
    await verifyPage.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
    await goToSettingsCategory(verifyPage, 'Logging & Diagnostics');

    const bodyText = await verifyPage.innerText('body');
    const has6x = /6\.[0-9]/.test(bodyText);
    console.log(`[VERIFICATION] Zero 6.x on Logging page: ${!has6x}`);

    await goToSettingsCategory(verifyPage, 'Advanced');
    const bodyTextAdv = await verifyPage.innerText('body');
    const has6xAdv = /6\.[0-9]/.test(bodyTextAdv);
    console.log(`[VERIFICATION] Zero 6.x on Advanced page: ${!has6xAdv}`);

    // Check SVG icons have children
    const emptySvgs = await verifyPage.evaluate(() => {
      const svgs = document.querySelectorAll('svg');
      let emptyCount = 0;
      svgs.forEach(s => {
        if (s.children.length === 0) emptyCount++;
      });
      return emptyCount;
    });
    console.log(`[VERIFICATION] Empty SVGs count on Advanced: ${emptySvgs} (expected 0)`);

    await verifyPage.close();
    await browser.close();

    console.log('\n Master Playwright Verification Complete: All 23 captures generated successfully!');
  } catch (err) {
    console.error('Playwright verification error:', err);
  } finally {
    server.close();
  }
});
