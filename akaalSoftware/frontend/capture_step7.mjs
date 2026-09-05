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

// Simple static HTTP server for Angular SPA
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
    await page.goto('http://localhost:4299/migration/create');
    await page.waitForLoadState('networkidle');

    // Helper to set draft state and jump to step 7
    const setupStep7 = async (mode = 'M2_BULK_CDC', environment = 'Production') => {
      await page.evaluate(({ m, env }) => {
        const ms = window.__wizardMs;
        if (ms) {
          ms.updateDraft({
            name: 'Core Banking Ledger Migration',
            description: 'Mission-critical database migration to cloud PostgreSQL',
            mode: m,
            environment: env,
            sourceProvider: 'Oracle',
            sourceHost: 'orcl-prod.corp.internal',
            sourcePort: 1521,
            sourceDatabase: 'ORCLPDB',
            targetProvider: 'PostgreSQL',
            targetHost: 'pg-aurora.internal',
            targetPort: 5432,
            targetDatabase: 'finance',
            collisionPolicy: 'RENAME_AND_BACKUP',
            currentStep: 7
          });
        }
      }, { m: mode, env: environment });
      await page.waitForTimeout(500);
    };

    const saveShot = async (name) => {
      const fileName = `${name}_${res.name}.png`;
      const p1 = path.join(outDir, fileName);
      const p2 = path.join(studyDir, fileName);
      await page.screenshot({ path: p1, fullPage: false });
      fs.copyFileSync(p1, p2);
      console.log(`Saved screenshot: ${fileName}`);
    };

    // 1. Step 7 Overview (Top View: Section 1 Migration Plan)
    await setupStep7('M2_BULK_CDC', 'Production');
    await page.evaluate(() => {
      const el = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (el) el.scrollTop = 0;
    });
    await page.waitForTimeout(400);
    await saveShot('step7_01_section1_migration_plan');

    // 2. Scrolled View: Section 2 Plan Review
    await page.evaluate(() => {
      const el = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (el) el.scrollTop = 480;
    });
    await page.waitForTimeout(400);
    await saveShot('step7_02_section2_plan_review');

    // 3. Scrolled View: Section 3 Governance Boundaries & Section 4 Plan Summary
    await page.evaluate(() => {
      const el = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (el) el.scrollTop = 1050;
    });
    await page.waitForTimeout(400);
    await saveShot('step7_03_section3_and_4_governance_summary');

    // 4. Stage Drawer Opened: Work & Provenance Metrics + Work Objects
    await page.evaluate(() => {
      const store = window.__step7Store;
      if (store) {
        const stage = store.nodes().find(n => n.stageType === 'BULK_EXTRACT' || n.stageType === 'BULK_LOAD');
        if (stage) store.openStageDrawer(stage);
      }
    });
    await page.waitForTimeout(500);
    await saveShot('step7_04_stage_drawer_work_metrics');

    // 5. Stage Drawer Scrolled: Resolved Configuration (Step 6 link) & Dependencies
    await page.evaluate(() => {
      const drawerBody = document.querySelector('aside .overflow-y-auto');
      if (drawerBody) drawerBody.scrollTop = 380;
    });
    await page.waitForTimeout(400);
    await saveShot('step7_05_stage_drawer_resolved_config');

    // 6. Approval Barrier Drawer Opened: Mandatory SOX-404 Gate
    await page.evaluate(() => {
      const store = window.__step7Store;
      if (store) {
        store.closeStageDrawer();
        const gate = store.approvalGates()[0];
        if (gate) store.openGateDrawer(gate);
      }
    });
    await page.waitForTimeout(500);
    await saveShot('step7_06_approval_drawer_mandatory_policy');

    // 7. Add Approval Gate Modal Dialog
    await page.evaluate(() => {
      const store = window.__step7Store;
      if (store) {
        store.closeGateDrawer();
        store.openAddGateModal();
      }
    });
    await page.waitForTimeout(500);
    await saveShot('step7_07_add_approval_gate_modal');

    // 8. Technical Plan Details Modal Dialog (SHA-256 Fingerprint & JSON)
    await page.evaluate(() => {
      const store = window.__step7Store;
      if (store) {
        store.closeAddGateModal();
        store.openTechnicalModal();
      }
    });
    await page.waitForTimeout(500);
    await saveShot('step7_08_technical_details_modal');

    // 9. Close Modal and Switch Mode to M1_BULK
    await page.evaluate(() => {
      const store = window.__step7Store;
      if (store) store.closeTechnicalModal();
    });
    await setupStep7('M1_BULK', 'Staging');
    await page.evaluate(() => {
      const el = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (el) el.scrollTop = 0;
    });
    await page.waitForTimeout(400);
    await saveShot('step7_09_mode_m1_bulk_flow');

    // 10. Switch Mode to M4_INCREMENTAL
    await setupStep7('M4_INCREMENTAL', 'Production');
    await page.evaluate(() => {
      const el = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (el) el.scrollTop = 0;
    });
    await page.waitForTimeout(400);
    await saveShot('step7_10_mode_m4_incremental_flow');

    // 11. Switch Mode to M6_SCHEMA_ONLY
    await setupStep7('M6_SCHEMA_ONLY', 'Development');
    await page.evaluate(() => {
      const el = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (el) el.scrollTop = 0;
    });
    await page.waitForTimeout(400);
    await saveShot('step7_11_mode_m6_schema_only_flow');

    await page.close();
  }

  await browser.close();
  server.close();
  console.log('All Step 7 screenshots captured successfully!');
  process.exit(0);
});
