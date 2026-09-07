const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

const DIST_DIR = path.join(__dirname, 'dist', 'akaal-software', 'browser');
const OUT_DIR = 'C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00';
const PORT = 4325;

// MIME types
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

// Static file server with SPA routing fallback to index.html
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
  console.log(`Step 4 Capture Server listening on http://localhost:${PORT}`);

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
    console.log(`Capturing Step 4 for viewport: ${vp.name}...`);
    console.log(`========================================\n`);

    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height }
    });
    const page = await context.newPage();

    // 1. Navigate to Create Validation
    await page.goto(`http://localhost:${PORT}/migration/validation/new`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);

    // Seed state directly to Step 4 with Linked Migration Project (Pathway A)
    await page.evaluate(() => {
      const wizardEl = document.querySelector('app-new-validation-wizard');
      // @ts-ignore
      const comp = window.ng?.getComponent(wizardEl);
      if (comp && comp.vs) {
        comp.vs.updateDraft({
          name: 'Global Treasury & Core Banking Reconcile',
          validationContext: 'EXISTING_PROJECT',
          projectId: 'proj-01',
          projectName: 'Cloud Modernization 2026',
          sourceConnectionMode: 'SAVED',
          sourceConnectionId: 'conn-01',
          sourceProvider: 'Oracle',
          sourceHost: 'prod-oracle-rac.internal',
          sourcePort: 1521,
          sourceDatabase: 'FINANCE',
          sourceVerified: true,
          targetConnectionMode: 'SAVED',
          targetConnectionId: 'conn-02',
          targetProvider: 'PostgreSQL',
          targetHost: 'aurora-pg-cluster.aws.internal',
          targetPort: 5432,
          targetDatabase: 'public',
          targetVerified: true,
          currentStep: 4,
          step4Pathway: 'INHERIT'
        });
      }
    });
    await page.waitForTimeout(600);

    // -------------------------------------------------------------------------
    // Screenshot 1: validation_create_32_step4_inherit_summary (Pathway A)
    // -------------------------------------------------------------------------
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_32_step4_inherit_summary_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_32_step4_inherit_summary_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 6: validation_create_37_step4_inspect_scope (Inspect Scope Drawer)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const step4El = document.querySelector('app-step4-scope');
      // @ts-ignore
      const comp = window.ng?.getComponent(step4El);
      if (comp) {
        comp.openInspectDrawer();
      }
    });
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_37_step4_inspect_scope_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_37_step4_inspect_scope_${vp.name}.png`);

    // Close Inspect Drawer
    await page.evaluate(() => {
      const step4El = document.querySelector('app-step4-scope');
      // @ts-ignore
      const comp = window.ng?.getComponent(step4El);
      if (comp) {
        comp.closeInspectDrawer();
      }
    });
    await page.waitForTimeout(300);

    // -------------------------------------------------------------------------
    // Screenshot 7: validation_create_38_step4_customize_scope (Customize Scope Modal)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const step4El = document.querySelector('app-step4-scope');
      // @ts-ignore
      const comp = window.ng?.getComponent(step4El);
      if (comp) {
        comp.openCustomizeModal();
      }
    });
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_38_step4_customize_scope_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_38_step4_customize_scope_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 8: validation_create_39_step4_empty_error (Empty Scope State)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const step4El = document.querySelector('app-step4-scope');
      // @ts-ignore
      const comp = window.ng?.getComponent(step4El);
      if (comp) {
        comp.deselectAllCustomUnits();
        comp.closeCustomizeModal();
      }
    });
    await page.waitForTimeout(400);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_39_step4_empty_error_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_39_step4_empty_error_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 2: validation_create_33_step4_choice_opening (Pathway B Opening)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const wizardEl = document.querySelector('app-new-validation-wizard');
      // @ts-ignore
      const comp = window.ng?.getComponent(wizardEl);
      if (comp && comp.vs) {
        comp.vs.setValidationContext('INDEPENDENT');
        comp.vs.updateDraft({ step4Pathway: 'CHOICE' });
      }
    });
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_33_step4_choice_opening_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_33_step4_choice_opening_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 3: validation_create_34_step4_import_unavailable (Pathway B Import State)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const step4El = document.querySelector('app-step4-scope');
      // @ts-ignore
      const comp = window.ng?.getComponent(step4El);
      if (comp) {
        comp.setPathway('IMPORT');
      }
    });
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_34_step4_import_unavailable_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_34_step4_import_unavailable_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 4 & 5: Pathway C (Define Scope & Decisions Required Workbench)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const step4El = document.querySelector('app-step4-scope');
      // @ts-ignore
      const comp = window.ng?.getComponent(step4El);
      if (comp) {
        comp.setPathway('DEFINE');
      }
    });
    await page.waitForTimeout(500);

    // Screenshot 4: validation_create_35_step4_define_scope
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_35_step4_define_scope_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_35_step4_define_scope_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 9: validation_create_40_step4_column_inspection (Premium Column View)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const step4El = document.querySelector('app-step4-scope');
      // @ts-ignore
      const comp = window.ng?.getComponent(step4El);
      if (comp) {
        comp.openInspectDrawer();
        const u = comp.units()[0];
        if (u) {
          comp.openColumnDrawer(u);
        }
      }
    });
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_40_step4_column_inspection_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_40_step4_column_inspection_${vp.name}.png`);

    // Close Column and Inspect Drawers
    await page.evaluate(() => {
      const step4El = document.querySelector('app-step4-scope');
      // @ts-ignore
      const comp = window.ng?.getComponent(step4El);
      if (comp) {
        comp.closeColumnDrawer();
        comp.closeInspectDrawer();
      }
    });
    await page.waitForTimeout(300);

    // -------------------------------------------------------------------------
    // Screenshot 10: validation_create_41_step4_change_decision (Resolved with Change Decision)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const step4El = document.querySelector('app-step4-scope');
      // @ts-ignore
      const comp = window.ng?.getComponent(step4El);
      if (comp) {
        comp.resolveDecisionTarget('disc-03', 'customers_legacy');
      }
    });
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_41_step4_change_decision_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_41_step4_change_decision_${vp.name}.png`);

    await context.close();
  }

  await browser.close();
  server.close();
  console.log('\nAll 16 screenshots captured successfully!');
  process.exit(0);
});
