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

// Static HTTP server for Angular SPA
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

server.listen(4298, async () => {
  console.log('Static server listening on http://localhost:4298');

  const browser = await chromium.launch({ headless: true, channel: 'msedge' });

  const resolutions = [
    { name: '1920x1080', width: 1920, height: 1080 },
    { name: '1440x900', width: 1440, height: 900 }
  ];

  for (const res of resolutions) {
    const page = await browser.newPage({ viewport: { width: res.width, height: res.height } });
    await page.goto('http://localhost:4298/migration/create');
    await page.waitForLoadState('networkidle');

    // Helper to set draft state and jump to step 8
    const setupStep8 = async (mode = 'M2_BULK_CDC', environment = 'Production', overrides = {}) => {
      await page.evaluate(({ m, env, ovr }) => {
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
            sourceVerified: true,
            targetProvider: 'PostgreSQL',
            targetHost: 'pg-aurora.internal',
            targetPort: 5432,
            targetDatabase: 'finance',
            targetVerified: true,
            collisionPolicy: 'RENAME_AND_BACKUP',
            currentStep: 8,
            ...ovr
          });
        }
      }, { m: mode, env: environment, ovr: overrides });
      await page.waitForTimeout(400);
    };

    const saveShot = async (name) => {
      const fileName = `${name}_${res.name}.png`;
      const p1 = path.join(outDir, fileName);
      const p2 = path.join(studyDir, fileName);
      await page.screenshot({ path: p1, fullPage: false });
      fs.copyFileSync(p1, p2);
      console.log(`Saved screenshot: ${fileName}`);
    };

    // 1. Step 8 Awaiting Approvals (Default Production M2 State)
    await setupStep8('M2_BULK_CDC', 'Production');
    await saveShot('step8_01_awaiting_approvals_default');

    // 2. Step 8 Zero-Approval Ready State (Development / M1 with approved gates)
    await setupStep8('M1_BULK', 'Development');
    await saveShot('step8_02_overall_ready_state');

    // 3. Step 8 Action Required State (Source connection blocker)
    await setupStep8('M2_BULK_CDC', 'Production', { sourceVerified: false });
    await saveShot('step8_03_action_required_blockers');

    // 4. Step 8 Governance Gates & SoD Card
    await setupStep8('M2_BULK_CDC', 'Production');
    await page.evaluate(() => {
      const section = document.querySelector('section:nth-of-type(3)');
      if (section) section.scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await page.waitForTimeout(300);
    await saveShot('step8_04_governance_gates_section');

    // 5. Step 8 Readiness Checks (6 Categorized Accordion Groups)
    await page.evaluate(() => {
      const section = document.querySelector('section:nth-of-type(4)');
      if (section) section.scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await page.waitForTimeout(300);
    await saveShot('step8_05_readiness_categories_section');

    // 6. Step 8 Policy Acknowledgements (High concurrency in Prod)
    await setupStep8('M2_BULK_CDC', 'Production', {
      basicView: {
        performancePreset: 'HIGH_THROUGHPUT',
        derivedMinWorkers: 4,
        derivedMaxWorkers: 16,
        derivedBatchMb: 64,
        durabilityLevel: 'STANDARD',
        spillHeadroomGb: 32,
        cdcLagObjectiveMs: 250,
        watermarkFreshnessSec: 30,
        validationDepth: 'STANDARD'
      }
    });
    await page.evaluate(() => {
      const section = document.querySelector('section:nth-of-type(5)');
      if (section) section.scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await page.waitForTimeout(300);
    await saveShot('step8_06_policy_acknowledgements');

    // 7. Step 8 Governed Plan Snapshot
    await page.evaluate(() => {
      const section = document.querySelector('section:last-of-type');
      if (section) section.scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await page.waitForTimeout(300);
    await saveShot('step8_07_governed_plan_snapshot');

    // 8. Step 8 Approval Drawer Open
    await setupStep8('M2_BULK_CDC', 'Production');
    await page.evaluate(() => {
      const store = window.__step8Store;
      if (store && store.governanceGates().length > 0) {
        store.openApprovalDrawer(store.governanceGates()[0]);
      }
    });
    await page.waitForTimeout(400);
    await saveShot('step8_08_approval_drawer_open');

    // Close approval drawer
    await page.evaluate(() => {
      const store = window.__step8Store;
      if (store) store.closeApprovalDrawer();
    });
    await page.waitForTimeout(200);

    // 9. Step 8 Readiness Check Inspector Drawer Open
    await page.evaluate(() => {
      const store = window.__step8Store;
      if (store) {
        const firstCat = store.readinessCategories()[0];
        if (firstCat && firstCat.checks.length > 0) {
          store.openReadinessDrawer(firstCat.checks[0]);
        }
      }
    });
    await page.waitForTimeout(400);
    await saveShot('step8_09_readiness_drawer_open');

    // Close readiness drawer
    await page.evaluate(() => {
      const store = window.__step8Store;
      if (store) store.closeReadinessDrawer();
    });
    await page.waitForTimeout(200);

    // 10. Step 8 Technical Details Modal Open
    await page.evaluate(() => {
      const store = window.__step8Store;
      if (store) store.openTechnicalModal();
    });
    await page.waitForTimeout(400);
    await saveShot('step8_10_technical_details_modal');

    // Close modal
    await page.evaluate(() => {
      const store = window.__step8Store;
      if (store) store.closeTechnicalModal();
    });
    await page.waitForTimeout(200);

    // 11. Step 8 Governance Activity Timeline Drawer Open
    await page.evaluate(() => {
      const store = window.__step8Store;
      if (store) store.openActivityDrawer();
    });
    await page.waitForTimeout(400);
    await saveShot('step8_11_governance_activity_drawer');

    // Close activity drawer
    await page.evaluate(() => {
      const store = window.__step8Store;
      if (store) store.closeActivityDrawer();
    });
    await page.waitForTimeout(200);

    // 12. Mode M1 (Bulk) Full Presentation
    await setupStep8('M1_BULK', 'Production');
    await saveShot('step8_12_mode_m1_bulk_flow');

    // 13. Mode M4 (Incremental) Full Presentation
    await setupStep8('M4_INCREMENTAL', 'Production');
    await saveShot('step8_13_mode_m4_incremental_flow');

    // 14. Mode M6 (Schema Only) Full Presentation
    await setupStep8('M6_SCHEMA_ONLY', 'Production');
    await saveShot('step8_14_mode_m6_schema_only_flow');

    // 15. Mode M7 (Data Only) Full Presentation
    await setupStep8('M7_DATA_ONLY', 'Production');
    await saveShot('step8_15_mode_m7_data_only_flow');

    await page.close();
  }

  await browser.close();
  server.close(() => {
    console.log('Capture suite complete. Static server stopped.');
    process.exit(0);
  });
});
