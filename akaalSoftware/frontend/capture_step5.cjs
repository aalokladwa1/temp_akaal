const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

const DIST_DIR = path.join(__dirname, 'dist', 'akaal-software', 'browser');
const OUT_DIR = 'C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00';
const PORT = 4326;

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
  console.log(`Step 5 Capture Server listening on http://localhost:${PORT}`);

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
    console.log(`Capturing Step 5 for viewport: ${vp.name}...`);
    console.log(`========================================\n`);

    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height }
    });
    const page = await context.newPage();

    // 1. Navigate to Create Validation
    await page.goto(`http://localhost:${PORT}/migration/validation/new`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);

    // -------------------------------------------------------------------------
    // Shot 50: State A — Inherited Migration Baseline (Linked Project)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const wizardEl = document.querySelector('app-new-validation-wizard');
      // @ts-ignore
      const comp = window.ng?.getComponent(wizardEl);
      if (comp && comp.vs) {
        comp.vs.updateDraft({
          name: 'Core Financials Migration Audit',
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
          currentStep: 5,
          baselineIntent: 'INHERITED_MIGRATION'
        });
      }
    });
    await page.waitForTimeout(400);

    const shot50 = path.join(OUT_DIR, `validation_create_50_step5_inherited_baseline_${vp.name}.png`);
    await page.screenshot({ path: shot50, fullPage: false });
    console.log(`Captured: ${shot50}`);

    // -------------------------------------------------------------------------
    // Shot 51: State C — Independent Validation: Unresolved Baseline (Fail-closed)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const wizardEl = document.querySelector('app-new-validation-wizard');
      // @ts-ignore
      const comp = window.ng?.getComponent(wizardEl);
      if (comp && comp.vs) {
        comp.vs.updateDraft({
          name: 'Independent Cross-Engine Parity Check',
          validationContext: 'INDEPENDENT',
          projectId: undefined,
          projectName: undefined,
          sourceConnectionMode: 'SAVED',
          sourceConnectionId: 'conn-01',
          sourceProvider: 'Oracle',
          sourceHost: 'oracle-standalone.corp.internal',
          sourcePort: 1521,
          sourceDatabase: 'PROD_DB',
          sourceVerified: true,
          targetConnectionMode: 'SAVED',
          targetConnectionId: 'conn-02',
          targetProvider: 'PostgreSQL',
          targetHost: 'pg-replica-01.corp.internal',
          targetPort: 5432,
          targetDatabase: 'target_db',
          targetVerified: true,
          currentStep: 5,
          baselineIntent: undefined,
          maintenanceCondition: undefined
        });
      }
    });
    await page.waitForTimeout(400);

    const shot51 = path.join(OUT_DIR, `validation_create_51_step5_independent_unresolved_${vp.name}.png`);
    await page.screenshot({ path: shot51, fullPage: false });
    console.log(`Captured: ${shot51}`);

    // -------------------------------------------------------------------------
    // Shot 52: State C — Independent: Current Operational Baseline Selected
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const wizardEl = document.querySelector('app-new-validation-wizard');
      // @ts-ignore
      const comp = window.ng?.getComponent(wizardEl);
      if (comp && comp.vs) {
        comp.vs.updateDraft({
          baselineIntent: 'CURRENT_OPERATIONAL',
          maintenanceCondition: undefined
        });
      }
    });
    await page.waitForTimeout(400);

    const shot52 = path.join(OUT_DIR, `validation_create_52_step5_independent_operational_${vp.name}.png`);
    await page.screenshot({ path: shot52, fullPage: false });
    console.log(`Captured: ${shot52}`);

    // -------------------------------------------------------------------------
    // Shot 53: State C — Independent: Maintenance Baseline with "Writes stopped"
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const wizardEl = document.querySelector('app-new-validation-wizard');
      // @ts-ignore
      const comp = window.ng?.getComponent(wizardEl);
      if (comp && comp.vs) {
        comp.vs.updateDraft({
          baselineIntent: 'MAINTENANCE_COORDINATED',
          maintenanceCondition: 'WRITES_STOPPED_DECLARED'
        });
      }
    });
    await page.waitForTimeout(400);

    const shot53 = path.join(OUT_DIR, `validation_create_53_step5_independent_maintenance_${vp.name}.png`);
    await page.screenshot({ path: shot53, fullPage: false });
    console.log(`Captured: ${shot53}`);

    // -------------------------------------------------------------------------
    // Shot 54: State C — Independent: Static / Immutable Data Selected
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const wizardEl = document.querySelector('app-new-validation-wizard');
      // @ts-ignore
      const comp = window.ng?.getComponent(wizardEl);
      if (comp && comp.vs) {
        comp.vs.updateDraft({
          baselineIntent: 'STATIC_IMMUTABLE',
          maintenanceCondition: undefined
        });
      }
    });
    await page.waitForTimeout(400);

    const shot54 = path.join(OUT_DIR, `validation_create_54_step5_independent_static_${vp.name}.png`);
    await page.screenshot({ path: shot54, fullPage: false });
    console.log(`Captured: ${shot54}`);

    // -------------------------------------------------------------------------
    // Shot 55: State D — Insufficient / Unsupported: External Replication
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const wizardEl = document.querySelector('app-new-validation-wizard');
      // @ts-ignore
      const comp = window.ng?.getComponent(wizardEl);
      if (comp && comp.vs) {
        comp.vs.updateDraft({
          baselineIntent: 'EXTERNAL_REPLICATION',
          maintenanceCondition: undefined
        });
      }
    });
    await page.waitForTimeout(400);

    const shot55 = path.join(OUT_DIR, `validation_create_55_step5_independent_external_unavailable_${vp.name}.png`);
    await page.screenshot({ path: shot55, fullPage: false });
    console.log(`Captured: ${shot55}`);

    // -------------------------------------------------------------------------
    // Shot 56: Technical Details Progressive Disclosure Expanded (Operational Mode)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      const wizardEl = document.querySelector('app-new-validation-wizard');
      // @ts-ignore
      const comp = window.ng?.getComponent(wizardEl);
      if (comp && comp.vs) {
        comp.vs.updateDraft({
          baselineIntent: 'CURRENT_OPERATIONAL',
          maintenanceCondition: undefined
        });
      }
      const step5El = document.querySelector('app-step5-boundary');
      // @ts-ignore
      const step5Comp = window.ng?.getComponent(step5El);
      if (step5Comp) {
        step5Comp.isTechnicalDetailsOpen.set(true);
      }
    });
    await page.waitForTimeout(300);
    await page.evaluate(() => {
      const scrollableCanvas = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (scrollableCanvas) {
        scrollableCanvas.scrollTo({ top: scrollableCanvas.scrollHeight, behavior: 'instant' });
      }
    });
    await page.waitForTimeout(400);

    const shot56 = path.join(OUT_DIR, `validation_create_56_step5_technical_details_expanded_${vp.name}.png`);
    await page.screenshot({ path: shot56, fullPage: false });
    console.log(`Captured: ${shot56}`);

    await context.close();
  }

  await browser.close();
  server.close(() => {
    console.log('Capture server closed. All screenshots generated successfully.');
    process.exit(0);
  });
});
