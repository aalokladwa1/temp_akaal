import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve(process.cwd(), 'dist/akaal-software/browser');
const altDistDir = path.resolve(process.cwd(), 'dist/akaal-software');
const activeDistDir = fs.existsSync(distDir) ? distDir : altDistDir;

console.log('Serving SPA from:', activeDistDir);

const reportDir = path.resolve(process.cwd(), 'playwright-report/phase5');
if (!fs.existsSync(reportDir)) {
  fs.mkdirSync(reportDir, { recursive: true });
}

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

const PORT = 4398;
server.listen(PORT, async () => {
  console.log(`Phase 5 Hostile Playwright verification server running on http://localhost:${PORT}`);

  const results = {
    viewportsTested: [],
    routesAudited: [],
    titleStripTests: {},
    colorNeutralityAudits: [],
    themeSwitching: {},
    lightModeIntegrity: {},
    consoleErrors: []
  };

  try {
    const browser = await chromium.launch({ 
      headless: true,
      executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
    });

    const viewports = [
      { name: '1366x768', width: 1366, height: 768 },
      { name: '1440x900', width: 1440, height: 900 },
      { name: '1920x1080', width: 1920, height: 1080 }
    ];

    // Helper: parse rgb/rgba string
    function parseRgb(colorStr) {
      const match = colorStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      if (!match) return null;
      return { r: parseInt(match[1], 10), g: parseInt(match[2], 10), b: parseInt(match[3], 10) };
    }

    function isNeutral(rgb, maxDiff = 4) {
      if (!rgb) return true;
      const { r, g, b } = rgb;
      return Math.abs(r - g) <= maxDiff && Math.abs(g - b) <= maxDiff && Math.abs(r - b) <= maxDiff;
    }

    // ------------------------------------------------------------------------
    // VIEWPORT 1440x900 PRIMARY AUDIT & TITLE STRIP
    // ------------------------------------------------------------------------
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

    page.on('console', msg => {
      if (msg.type() === 'error') {
        results.consoleErrors.push(msg.text());
      }
    });

    // 1. Initial Load (Default Dark Mode from localStorage or system)
    console.log('--- 1. Testing Default Launch & Dark Mode ---');
    await page.goto(`http://localhost:${PORT}/dashboard`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Ensure dark mode is active
    await page.evaluate(() => {
      document.documentElement.classList.add('dark');
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('akaal_settings_appearance', JSON.stringify({
        theme: 'dark',
        palette: 'standard',
        contrast: 'standard',
        reduceMotion: false,
        enhancedFocus: false
      }));
    });
    await page.waitForTimeout(300);

    // ========================================================================
    // TITLE STRIP VERIFICATION (Owner Requirement 11)
    // ========================================================================
    console.log('--- 2. Verifying Desktop Title Strip Behavior ---');
    
    // Check elements exist
    const titleStrip = page.locator('#desktop-title-strip');
    const revealZone = page.locator('#desktop-top-edge-reveal-zone');
    const minBtn = page.locator('#window-minimize-btn');
    const maxBtn = page.locator('#window-maximize-btn');
    const closeBtn = page.locator('#window-close-btn');

    const stripExists = await titleStrip.count() > 0;
    const revealZoneExists = await revealZone.count() > 0;
    console.log(`Title strip DOM present: ${stripExists}, Reveal zone present: ${revealZoneExists}`);

    // A. Normal Use: Title Strip must be hidden
    const initialClass = await titleStrip.getAttribute('class');
    const isInitiallyHidden = initialClass.includes('-translate-y-full') && initialClass.includes('opacity-0');
    console.log(`Normal use: Title strip hidden: ${isInitiallyHidden}`);
    results.titleStripTests.hiddenNormally = isInitiallyHidden;

    await page.screenshot({ path: path.join(reportDir, '01_desktop_normal_strip_hidden.png') });

    // B. Cursor reaches top-edge reveal zone (hover over top edge)
    console.log('Hovering over top-edge reveal zone (y = 2px)...');
    await page.mouse.move(700, 2);
    await page.waitForTimeout(300);

    const revealedClass = await titleStrip.getAttribute('class');
    const isRevealedOnTopHover = revealedClass.includes('translate-y-0') && revealedClass.includes('opacity-100');
    console.log(`Top-edge hover: Title strip revealed: ${isRevealedOnTopHover}`);
    results.titleStripTests.revealsOnTopEdgeHover = isRevealedOnTopHover;

    await page.screenshot({ path: path.join(reportDir, '02_desktop_strip_revealed.png') });

    // Inspect title strip color in dark mode
    const titleStripBg = await titleStrip.evaluate(el => window.getComputedStyle(el).backgroundColor);
    const titleStripBorder = await titleStrip.evaluate(el => window.getComputedStyle(el).borderBottomColor);
    const titleStripRgb = parseRgb(titleStripBg);
    console.log(`Title strip dark background: ${titleStripBg}, border: ${titleStripBorder}`);
    results.titleStripTests.darkNeutralBackground = isNeutral(titleStripRgb);

    // C. Hover inside title strip: remains visible
    console.log('Interacting inside title strip (y = 16px)...');
    await page.mouse.move(700, 16);
    await page.waitForTimeout(200);
    const stayingClass = await titleStrip.getAttribute('class');
    const remainsVisibleDuringInteraction = stayingClass.includes('translate-y-0');
    console.log(`Interacting: Title strip remains visible: ${remainsVisibleDuringInteraction}`);
    results.titleStripTests.remainsVisibleDuringInteraction = remainsVisibleDuringInteraction;

    // D. Cursor leaves title strip: hides after delay
    console.log('Cursor leaves title strip into main canvas (y = 300px)...');
    await page.mouse.move(700, 300);
    // At 100ms, should still be visible (delay is 450ms)
    await page.waitForTimeout(100);
    const stillVisibleClass = await titleStrip.getAttribute('class');
    const staysDuringDelay = stillVisibleClass.includes('translate-y-0');
    console.log(`Within 100ms delay: Title strip still visible (no flicker): ${staysDuringDelay}`);

    // Wait until delay expires (total > 500ms)
    await page.waitForTimeout(500);
    const postDelayClass = await titleStrip.getAttribute('class');
    const hidesAfterDelay = postDelayClass.includes('-translate-y-full');
    console.log(`After delay: Title strip automatically hides: ${hidesAfterDelay}`);
    results.titleStripTests.hidesAfterDelay = hidesAfterDelay;

    // E. Re-enter before delay expires cancels hide
    console.log('Testing cancellation: hover top, leave, and quickly re-enter...');
    await page.mouse.move(700, 2);
    await page.waitForTimeout(250);
    await page.mouse.move(700, 300);
    await page.waitForTimeout(150); // only 150ms of 450ms delay
    await page.mouse.move(700, 16); // return before 450ms
    await page.waitForTimeout(450); // wait past the original timeout
    const cancelledHideClass = await titleStrip.getAttribute('class');
    const cancelWorked = cancelledHideClass.includes('translate-y-0');
    console.log(`Re-enter cancels hide timer: ${cancelWorked}`);
    results.titleStripTests.cancelPendingHideOnReturn = cancelWorked;

    // F. Keyboard focus within title strip preserves visibility
    console.log('Testing keyboard focus inside title strip...');
    await minBtn.focus();
    await page.waitForTimeout(200);
    const focusedClass = await titleStrip.getAttribute('class');
    const focusedVisible = focusedClass.includes('translate-y-0');
    console.log(`Keyboard focus keeps title strip visible: ${focusedVisible}`);
    results.titleStripTests.keyboardFocusPreservesVisibility = focusedVisible;

    // Move mouse away while focus is active
    await page.mouse.move(700, 500);
    await page.waitForTimeout(600);
    const stillFocusedClass = await titleStrip.getAttribute('class');
    const focusPreventsHide = stillFocusedClass.includes('translate-y-0');
    console.log(`Mouse leaving while control focused does not hide strip: ${focusPreventsHide}`);
    results.titleStripTests.focusPreventsUnwantedHide = focusPreventsHide;

    // Blur to restore normal hidden state
    await page.evaluate(() => document.activeElement?.blur());
    await page.waitForTimeout(600);

    // ========================================================================
    // MAJOR PRODUCT ROUTE COLOR AUDIT (Owner Requirement 12)
    // ========================================================================
    console.log('--- 3. Traversing Major Routes for Dark Mode Neutrality ---');

    const routes = [
      { path: '/dashboard', name: 'Dashboard' },
      { path: '/migration', name: 'Migration Portfolio' },
      { path: '/migration/projects', name: 'Projects & Initiatives' },
      { path: '/migration/create', name: 'New Migration Wizard' },
      { path: '/validation', name: 'Validation Studio' },
      { path: '/validation/create', name: 'New Validation Wizard' },
      { path: '/monitoring', name: 'Monitoring' },
      { path: '/reports', name: 'Reports' },
      { path: '/settings', name: 'Settings' },
      { path: '/administration', name: 'Administration' }
    ];

    for (const route of routes) {
      console.log(`Auditing route: ${route.name} (${route.path})`);
      await page.goto(`http://localhost:${PORT}${route.path}`, { waitUntil: 'networkidle' });
      await page.evaluate(() => {
        document.documentElement.classList.add('dark');
        document.documentElement.setAttribute('data-theme', 'dark');
      });
      await page.waitForTimeout(500);

      // Measure key structural surfaces
      const surfaceColors = await page.evaluate(() => {
        const bodyBg = window.getComputedStyle(document.body).backgroundColor;
        const mainEl = document.querySelector('main');
        const mainBg = mainEl ? window.getComputedStyle(mainEl).backgroundColor : null;
        const headerEl = document.querySelector('header');
        const headerBg = headerEl ? window.getComputedStyle(headerEl).backgroundColor : null;
        const asideEl = document.querySelector('aside:not(#desktop-title-strip)');
        const asideBg = asideEl ? window.getComputedStyle(asideEl).backgroundColor : null;

        // Sample cards
        const cards = Array.from(document.querySelectorAll('div.rounded-xl, div.rounded-2xl, div.rounded-lg, section'));
        const cardBgs = cards.slice(0, 5).map(c => window.getComputedStyle(c).backgroundColor);

        // Sample inputs
        const inputs = Array.from(document.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]), select, textarea'));
        const inputBgs = inputs.slice(0, 3).map(i => window.getComputedStyle(i).backgroundColor);

        return { bodyBg, mainBg, headerBg, asideBg, cardBgs, inputBgs };
      });

      // Analyze neutrality
      const bodyRgb = parseRgb(surfaceColors.bodyBg);
      const mainRgb = parseRgb(surfaceColors.mainBg);
      const headerRgb = parseRgb(surfaceColors.headerBg);
      const asideRgb = parseRgb(surfaceColors.asideBg);

      const isBodyNeutral = isNeutral(bodyRgb);
      const isMainNeutral = isNeutral(mainRgb);
      const isHeaderNeutral = isNeutral(headerRgb);
      const isAsideNeutral = isNeutral(asideRgb);

      const routeAudit = {
        route: route.path,
        name: route.name,
        bodyBg: surfaceColors.bodyBg,
        mainBg: surfaceColors.mainBg,
        headerBg: surfaceColors.headerBg,
        asideBg: surfaceColors.asideBg,
        allNeutral: isBodyNeutral && isMainNeutral && isHeaderNeutral && isAsideNeutral
      };
      results.colorNeutralityAudits.push(routeAudit);
      results.routesAudited.push(route.path);

      console.log(`  Body: ${surfaceColors.bodyBg} (Neutral: ${isBodyNeutral})`);
      console.log(`  Main Canvas: ${surfaceColors.mainBg} (Neutral: ${isMainNeutral})`);
      console.log(`  Header: ${surfaceColors.headerBg} (Neutral: ${isHeaderNeutral})`);
      console.log(`  Sidebar: ${surfaceColors.asideBg} (Neutral: ${isAsideNeutral})`);

      // Capture screenshot
      const safeName = route.name.toLowerCase().replace(/[^a-z0-9]/g, '_');
      await page.screenshot({ path: path.join(reportDir, `route_${safeName}_dark.png`), fullPage: false });
    }

    // ========================================================================
    // DIALOGS & OVERLAYS IN DARK MODE
    // ========================================================================
    console.log('--- 4. Auditing Overlays, Dialogs, Dropdowns ---');
    await page.goto(`http://localhost:${PORT}/dashboard`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);

    // A. Open Context dropdown
    const orgBtn = page.locator('header button:has-text("Organization"), header button[title*="Organization"]').first();
    if (await orgBtn.isVisible().catch(() => false)) {
      await orgBtn.click();
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(reportDir, 'overlay_org_dropdown_dark.png') });
      await page.click('body', { position: { x: 500, y: 500 } });
    }

    // B. Open Command Palette (Ctrl+K or Header Search Button)
    console.log('Opening Command Palette...');
    const searchBtn = page.locator('header button:has-text("Search or command")').first();
    if (await searchBtn.isVisible().catch(() => false)) {
      await searchBtn.click();
    } else {
      await page.keyboard.press('Control+k');
    }
    await page.waitForTimeout(400);
    const cmdInput = page.locator('input[placeholder*="Search navigation" i]').first();
    const cmdPaletteVisible = await cmdInput.isVisible().catch(() => false);
    console.log(`Command Palette visible: ${cmdPaletteVisible}`);
    await page.screenshot({ path: path.join(reportDir, 'overlay_command_palette_dark.png') });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    // C. Open User Menu
    const userMenuBtn = page.locator('header button:has(div:text("AL")), header button[title*="Ladwa" i]').first();
    if (await userMenuBtn.isVisible().catch(() => false)) {
      await userMenuBtn.click();
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(reportDir, 'overlay_user_menu_dark.png') });

      // Open Keyboard Shortcuts Dialog from user menu
      const shortcutsBtn = page.locator('button:has-text("Keyboard Shortcuts")').first();
      if (await shortcutsBtn.isVisible().catch(() => false)) {
        await shortcutsBtn.click();
        await page.waitForTimeout(300);
        await page.screenshot({ path: path.join(reportDir, 'overlay_shortcuts_dialog_dark.png') });
        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);
      }
    }

    // ========================================================================
    // THEME SWITCHING INTEGRITY (Dark -> Light -> Dark)
    // ========================================================================
    console.log('--- 5. Testing Theme Switching: Dark -> Light -> Dark ---');

    // Switch to Light Mode
    await page.evaluate(() => {
      document.documentElement.classList.remove('dark');
      document.documentElement.setAttribute('data-theme', 'enterprise-blue');
    });
    await page.waitForTimeout(400);

    const lightBodyBg = await page.evaluate(() => window.getComputedStyle(document.body).backgroundColor);
    const lightHeaderBg = await page.evaluate(() => {
      const h = document.querySelector('header');
      return h ? window.getComputedStyle(h).backgroundColor : null;
    });
    const lightCanvasBg = await page.evaluate(() => {
      const m = document.querySelector('main');
      return m ? window.getComputedStyle(m).backgroundColor : null;
    });

    console.log(`Light mode body: ${lightBodyBg}, header: ${lightHeaderBg}, canvas: ${lightCanvasBg}`);
    results.themeSwitching.lightModeBodyBg = lightBodyBg;
    results.themeSwitching.lightModeHeaderBg = lightHeaderBg;
    results.themeSwitching.lightModeClean = lightHeaderBg === 'rgb(255, 255, 255)' || lightHeaderBg === '#ffffff';

    await page.screenshot({ path: path.join(reportDir, 'theme_switch_01_dashboard_light.png') });

    // Switch back to Dark Mode
    await page.evaluate(() => {
      document.documentElement.classList.add('dark');
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await page.waitForTimeout(400);

    const returnDarkBodyBg = await page.evaluate(() => window.getComputedStyle(document.body).backgroundColor);
    const returnDarkHeaderBg = await page.evaluate(() => {
      const h = document.querySelector('header');
      return h ? window.getComputedStyle(h).backgroundColor : null;
    });

    console.log(`Return to Dark mode body: ${returnDarkBodyBg}, header: ${returnDarkHeaderBg}`);
    results.themeSwitching.returnDarkClean = isNeutral(parseRgb(returnDarkHeaderBg));

    await page.screenshot({ path: path.join(reportDir, 'theme_switch_02_dashboard_return_dark.png') });

    // ========================================================================
    // VIEWPORT AUDIT (1366x768, 1440x900, 1920x1080)
    // ========================================================================
    console.log('--- 6. Auditing Multiple Viewports ---');

    for (const vp of viewports) {
      console.log(`Testing viewport ${vp.name} (${vp.width}x${vp.height})...`);
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.waitForTimeout(400);

      // Verify title strip still works at this viewport
      await page.mouse.move(vp.width / 2, 2);
      await page.waitForTimeout(250);
      const vpRevealed = await titleStrip.getAttribute('class');
      const isVpRevealed = vpRevealed.includes('translate-y-0');

      await page.screenshot({ path: path.join(reportDir, `viewport_${vp.name}_revealed_dark.png`) });

      await page.mouse.move(vp.width / 2, 400);
      await page.waitForTimeout(600);

      results.viewportsTested.push({
        name: vp.name,
        width: vp.width,
        height: vp.height,
        titleStripWorks: isVpRevealed
      });
    }

    await browser.close();
    console.log('--- Phase 5 Playwright Verification Complete ---');
    console.log(JSON.stringify(results, null, 2));

    fs.writeFileSync(path.join(reportDir, 'phase5_results.json'), JSON.stringify(results, null, 2), 'utf-8');

  } catch (err) {
    console.error('Playwright verification encountered an error:', err);
    process.exitCode = 1;
  } finally {
    server.close();
  }
});
