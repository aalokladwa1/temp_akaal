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
    await page.waitForFunction(() => typeof window.__wizardMs !== 'undefined', { timeout: 10000 });

    // Helper to set draft state and jump to step 9
    const setupStep9 = async (mode = 'M2_BULK_CDC', environment = 'Production', overrides = {}) => {
      await page.evaluate(({ m, env, ovr }) => {
        const ms = window.__wizardMs;
        const s9 = window.__step9Store;
        if (s9) {
          s9.submitPhase.set('IDLE');
          s9.operationError.set(null);
          s9.setTimingChoice('RUN_NOW');
        }
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
            collisionPolicy: 'FAIL_ON_COLLISION',
            currentStep: 9,
            ...ovr
          });
        }
        const section = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
        if (section) section.scrollTop = 0;
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

    // 00. Step 1 Visual Benchmark
    await page.evaluate(() => {
      window.__wizardMs.updateDraft({ currentStep: 1, name: 'Core Banking Ledger Migration', environment: 'Production', mode: 'M2_BULK_CDC' });
    });
    await page.waitForTimeout(300);
    await saveShot('step1_benchmark');

    // 01. Run Now - Ready State
    await setupStep9('M2_BULK_CDC', 'Production');
    await saveShot('step9_01_run_now_ready_state');

    // 02. Scrolled state of Run Now (to inspect lower sections & footer)
    await page.evaluate(() => {
      const section = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (section) section.scrollTop = 1100;
    });
    await page.waitForTimeout(300);
    await saveShot('step9_02_run_now_scrolled_footer');

    // Reset scroll
    await page.evaluate(() => {
      const section = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (section) section.scrollTop = 0;
    });

    // 03. Schedule for Later Selected (revealing date/time/timezone)
    await page.evaluate(() => {
      window.__step9Store.setTimingChoice('SCHEDULE_LATER');
    });
    await page.waitForTimeout(300);
    await saveShot('step9_03_schedule_for_later');

    // 04. Schedule for Later Scrolled
    await page.evaluate(() => {
      const section = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (section) section.scrollTop = 1100;
    });
    await page.waitForTimeout(300);
    await saveShot('step9_04_schedule_for_later_scrolled');

    // 05. Production Environment with Destructive Policy Notice
    await setupStep9('M2_BULK_CDC', 'Production', { collisionPolicy: 'DROP_AND_RECREATE' });
    await saveShot('step9_05_production_destructive_notice');

    // 06. Technical Details Modal Open
    await setupStep9('M2_BULK_CDC', 'Production');
    await page.evaluate(() => {
      window.__step9Store.openTechnicalModal();
    });
    await page.waitForTimeout(300);
    await saveShot('step9_06_technical_details_modal');

    // Close modal
    await page.evaluate(() => {
      window.__step9Store.closeTechnicalModal();
    });
    await page.waitForTimeout(200);

    // 07. Mode M1 (Bulk Offline)
    await setupStep9('M1_BULK', 'Non-Production');
    await saveShot('step9_07_mode_m1_bulk');

    // 08. Mode M1 with Advanced Recurring Schedule
    await page.evaluate(() => {
      window.__step9Store.setTimingChoice('SCHEDULE_LATER');
      if (!window.__step9Store.isAdvancedRecurring()) {
        window.__step9Store.toggleAdvancedRecurring();
      }
    });
    await page.waitForTimeout(300);
    await saveShot('step9_08_mode_m1_advanced_recurring');

    // 09. Mode M3 (CDC Stream Only)
    await setupStep9('M3_CDC', 'Production');
    await saveShot('step9_09_mode_m3_cdc');

    // 10. Mode M6 (Schema Only)
    await setupStep9('M6_SCHEMA_ONLY', 'Development');
    await saveShot('step9_10_mode_m6_schema_only');

    // 11. Mode M7 (Data Only)
    await setupStep9('M7_DATA_ONLY', 'Staging');
    await saveShot('step9_11_mode_m7_data_only');

    // 12. Error State
    await setupStep9('M2_BULK_CDC', 'Production');
    await page.evaluate(() => {
      window.__step9Store.submitPhase.set('ERROR');
      window.__step9Store.operationError.set({
        phase: 'INITIALIZATION',
        title: 'Backend Verification Failed',
        message: 'The target PostgreSQL database instance rejected the batch worker transaction pool.',
        isRetryable: true,
        recoveryGuidance: 'Ensure target database connection pool size is at least 20 and retry initialization.'
      });
    });
    await page.waitForTimeout(300);
    await saveShot('step9_12_error_state');

    await page.close();
  }

  await browser.close();
  server.close();
  console.log('Step 9 screenshot capture complete!');
  process.exit(0);
});
