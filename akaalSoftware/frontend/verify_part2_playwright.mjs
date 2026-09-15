import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0');

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

const PORT = 4340;
server.listen(PORT, async () => {
  console.log(`Verification server running on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

    // Navigate to base index and click through sidebar to Reports
    await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);

    // Click Reports in sidebar
    await page.locator('aside a[href*="reports"], a:has-text("Reports")').first().click();
    await page.waitForTimeout(500);

    // Click Report Library button/link on Reports Home
    await page.locator('a[routerLink="/reports/library"], a[href*="reports/library"], a:has-text("Report Library")').first().click();
    await page.waitForTimeout(500);

    // 1. Catalog View
    await page.screenshot({ path: path.join(outDir, 'part2_library_catalog_1920x1080.png'), fullPage: false });
    console.log('Captured part2_library_catalog_1920x1080.png');

    // 2. All Generated Reports Inventory Tab
    await page.getByRole('button', { name: 'All Generated Reports' }).click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, 'part2_library_inventory_1920x1080.png'), fullPage: false });
    console.log('Captured part2_library_inventory_1920x1080.png');

    const allReportsToCapture = [
      { id: 'REP-2026-0101', name: 'validation', title: 'Dual-Engine Reconciliation & Verification Report' },
      { id: 'REP-2026-0102', name: 'schema', title: 'Schema Translation & DDL Conformance Audit' },
      { id: 'REP-2026-0103', name: 'cdc', title: 'Continuous CDC LogMiner Replay Drift Analysis' },
      { id: 'REP-2026-0104', name: 'migration', title: 'Snowflake Lakehouse Batch Partition Snapshot Verification' },
      { id: 'REP-2026-0105', name: 'performance', title: 'Kafka Egress Throughput & Stage Latency Profile' },
      { id: 'REP-2026-0106', name: 'data_quality', title: 'Delta Sync Watermark Ingestion & Referential Integrity' },
      { id: 'REP-2026-0107', name: 'cutover', title: 'Production Cutover Rehearsal & Readiness Assessment' },
      { id: 'REP-2026-0108', name: 'recovery', title: 'Worker Failover & State Savepoint Reconstruction Audit' },
      { id: 'REP-2026-0109', name: 'security', title: 'Data-in-Transit mTLS & Secret Access Verification' },
      { id: 'REP-2026-0110', name: 'compliance', title: 'Technical Control Evaluation & Separation of Duties' },
      { id: 'REP-2026-0111', name: 'governance', title: 'Stage 4 Production Gate Dual-Control Quorum Ledger' },
      { id: 'REP-2026-0112', name: 'audit', title: 'Operator Mutation & Privileged Access Action Journal' },
      { id: 'REP-2026-0113', name: 'fleet', title: 'Worker Node Capacity & Lease Placement Inventory' },
      { id: 'REP-2026-0114', name: 'executive', title: 'Executive Program Rollup & Modernization Status' }
    ];

    for (const rep of allReportsToCapture) {
      // Switch to All Generated Reports if in catalog
      const invBtn = page.getByRole('button', { name: 'All Generated Reports' });
      if (await invBtn.isVisible()) {
        await invBtn.click();
        await page.waitForTimeout(200);
      }

      // Search for the report ID
      await page.locator('input[placeholder*="Search by title"]').fill(rep.id);
      await page.waitForTimeout(200);

      // Click the first row in tbody
      await page.locator('tbody tr').first().click();
      await page.waitForTimeout(400);

      // Click Findings & Results
      await page.getByRole('button', { name: 'Findings & Results' }).click();
      await page.waitForTimeout(300);

      // Capture screenshot
      const filename = `part2_detail_${rep.name}_findings_1920x1080.png`;
      await page.screenshot({ path: path.join(outDir, filename), fullPage: false });
      console.log(`Captured ${filename}`);

      // Go back to library
      await page.getByRole('button', { name: 'Back' }).first().click();
      await page.waitForTimeout(200);
    }

    // Capture 1440x900 screens
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.getByRole('button', { name: 'Catalog (14 Domains)' }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part2_library_catalog_1440x900.png'), fullPage: false });
    console.log('Captured part2_library_catalog_1440x900.png');

    await page.getByRole('button', { name: 'All Generated Reports' }).click();
    await page.waitForTimeout(300);
    await page.locator('input[placeholder*="Search by title"]').fill('');
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part2_library_inventory_1440x900.png'), fullPage: false });
    console.log('Captured part2_library_inventory_1440x900.png');

    await page.close();
    await browser.close();
    console.log('ALL 14 TYPE-SPECIFIC REPORTS SUCCESSFULLY CAPTURED ACROSS VIEWPORTS!');
  } catch (err) {
    console.error('Playwright verification error:', err);
  } finally {
    server.close();
  }
});
