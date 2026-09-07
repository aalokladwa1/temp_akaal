const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

const DIST_DIR = path.join(__dirname, 'dist', 'akaal-software', 'browser');
const OUT_DIR = 'C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00';
const PORT = 4338;

const MIME = {
  '.html': 'text/html',
  '.js': 'text/javascript',
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
  let filePath = path.join(DIST_DIR, reqPath);

  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    const ext = path.extname(filePath);
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    fs.createReadStream(filePath).pipe(res);
  } else {
    const indexPath = path.join(DIST_DIR, 'index.html');
    res.writeHead(200, { 'Content-Type': 'text/html' });
    fs.createReadStream(indexPath).pipe(res);
  }
});

server.listen(PORT, async () => {
  console.log(`Workstation Capture Server listening on http://localhost:${PORT}`);

  let browser;
  try {
    browser = await chromium.launch({ headless: true, channel: 'chrome' });
  } catch (e) {
    try {
      browser = await chromium.launch({ headless: true, channel: 'msedge' });
    } catch (e2) {
      browser = await chromium.launch({ headless: true });
    }
  }

  const viewports = [
    { name: '1920x1080', width: 1920, height: 1080 },
    { name: '1440x900', width: 1440, height: 900 }
  ];

  for (const vp of viewports) {
    console.log(`\n========================================`);
    console.log(`Capturing Workstation for viewport: ${vp.name}...`);
    console.log(`========================================\n`);

    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height }
    });
    const page = await context.newPage();

    // Helper to capture both top and scrolled view
    async function captureState(stateName) {
      // Top view
      await page.$eval('main.overflow-y-auto', el => el.scrollTop = 0);
      await page.waitForTimeout(300);
      await page.screenshot({
        path: path.join(OUT_DIR, `workstation_${stateName}_top_${vp.name}.png`)
      });
      // Scrolled view
      await page.$eval('main.overflow-y-auto', el => el.scrollTop = 1000);
      await page.waitForTimeout(300);
      await page.screenshot({
        path: path.join(OUT_DIR, `workstation_${stateName}_bottom_${vp.name}.png`)
      });
      // Bottom-most view (Baseline & Remediation)
      await page.$eval('main.overflow-y-auto', el => el.scrollTop = 2200);
      await page.waitForTimeout(300);
      await page.screenshot({
        path: path.join(OUT_DIR, `workstation_${stateName}_remediation_${vp.name}.png`)
      });
      console.log(`Captured ${stateName} top, mid, and remediation for ${vp.name}`);
    }

    // 1. Navigate to Validation Workstation Overview
    await page.goto(`http://localhost:${PORT}/validation/VAL-2026-0089`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Shot 1: Default Truthful Production (NOT_CONNECTED)
    await captureState('01_default_not_connected');

    // Shot 2: Running Clean Parity
    const selectElem = await page.$('select');
    if (selectElem) {
      await selectElem.selectOption('RUNNING_CLEAN');
      await page.waitForTimeout(400);
      await captureState('02_running_clean');

      // Shot 3: Running Divergence Flagged
      await selectElem.selectOption('RUNNING_DIFFS');
      await page.waitForTimeout(400);
      await captureState('03_running_diffs');

      // Shot 4: Completed Passed (SYNC)
      await selectElem.selectOption('COMPLETED_PASSED_SYNC');
      await page.waitForTimeout(400);
      await captureState('04_completed_passed_sync');

      // Shot 5: Completed Failed (SYNC)
      await selectElem.selectOption('COMPLETED_FAILED_SYNC');
      await page.waitForTimeout(400);
      await captureState('05_completed_failed_sync');

      // Shot 6: Interrupted
      await selectElem.selectOption('INTERRUPTED');
      await page.waitForTimeout(400);
      await captureState('06_interrupted');

      // Shot 11: Hostile Completed Passed ASYNC
      await selectElem.selectOption('COMPLETED_PASSED_ASYNC');
      await page.waitForTimeout(400);
      await captureState('11_completed_passed_async');

      // Shot 12: Hostile Completed Failed ASYNC
      await selectElem.selectOption('COMPLETED_FAILED_ASYNC');
      await page.waitForTimeout(400);
      await captureState('12_completed_failed_async');

      // Shot 15: Hostile Completed Unknown Mode
      await selectElem.selectOption('COMPLETED_UNKNOWN_MODE');
      await page.waitForTimeout(400);
      await captureState('15_completed_unknown_mode');

      // Shot 16: Hostile Withheld Attestation
      await selectElem.selectOption('WITHHELD');
      await page.waitForTimeout(400);
      await captureState('16_withheld');

      // Shot 17: Hostile Stale Baseline
      await selectElem.selectOption('BASELINE_INVALID');
      await page.waitForTimeout(400);
      await captureState('17_baseline_invalid');

      // Shot 18: Large Enterprise Scale
      await selectElem.selectOption('LARGE_ENTERPRISE');
      await page.waitForTimeout(400);
      await captureState('18_large_enterprise');
    }

    // Reset scroll to top
    await page.$eval('main.overflow-y-auto', el => el.scrollTop = 0);

    // Shot 7: Slide-Over Technical Drawer Open
    const drawerBtn = await page.getByRole('button', { name: /Technical Details/i });
    if (await drawerBtn.count() > 0) {
      await drawerBtn.first().click();
      await page.waitForTimeout(500);
      await page.screenshot({
        path: path.join(OUT_DIR, `workstation_07_technical_drawer_open_${vp.name}.png`)
      });
      console.log(`Captured workstation_07_technical_drawer_open_${vp.name}.png`);

      // Close drawer
      const closeBtn = await page.getByRole('button', { name: /Dismiss/i });
      if (await closeBtn.count() > 0) {
        await closeBtn.first().click();
        await page.waitForTimeout(400);
      }
    }

    // Shot 8: Discrepancies Workspace Tab
    const discrepanciesTab = await page.getByRole('button', { name: /Discrepancies/i });
    if (await discrepanciesTab.count() > 0) {
      await discrepanciesTab.first().click();
      await page.waitForTimeout(500);
      await page.screenshot({
        path: path.join(OUT_DIR, `workstation_08_discrepancies_workspace_${vp.name}.png`),
        fullPage: true
      });
      console.log(`Captured workstation_08_discrepancies_workspace_${vp.name}.png`);
    }

    // Shot 9: Repair & Revalidation Workspace Tab
    const repairTab = await page.getByRole('button', { name: /Repair & Revalidation/i });
    if (await repairTab.count() > 0) {
      await repairTab.first().click();
      await page.waitForTimeout(500);
      await page.screenshot({
        path: path.join(OUT_DIR, `workstation_09_repair_workspace_${vp.name}.png`),
        fullPage: true
      });
      console.log(`Captured workstation_09_repair_workspace_${vp.name}.png`);
    }

    // Shot 10: Results & Evidence Workspace Tab
    const evidenceTab = await page.getByRole('button', { name: /Results & Evidence/i });
    if (await evidenceTab.count() > 0) {
      await evidenceTab.first().click();
      await page.waitForTimeout(500);
      await page.screenshot({
        path: path.join(OUT_DIR, `workstation_10_evidence_workspace_${vp.name}.png`),
        fullPage: true
      });
      console.log(`Captured workstation_10_evidence_workspace_${vp.name}.png`);
    }

    await context.close();
  }

  await browser.close();
  server.close(() => {
    console.log('Capture Server closed. All workstation screenshots successfully written.');
    process.exit(0);
  });
});
