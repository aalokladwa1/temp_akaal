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

const PORT = 4342;
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

    // Click Trust & Certification navigation link on Reports Home
    const trustCertLink = page.locator('a[routerLink="/reports/certification"], a[href*="reports/certification"], a:has-text("Trust & Certification")').first();
    await trustCertLink.click();
    await page.waitForTimeout(500);

    // 1. Overview Screen (1920x1080)
    await page.screenshot({ path: path.join(outDir, 'part3_certification_overview_1920x1080.png'), fullPage: false });
    console.log('Captured part3_certification_overview_1920x1080.png');

    // 2. Migration Inventory Screen
    await page.getByRole('button', { name: 'Migration Certification' }).first().click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, 'part3_migration_inventory_1920x1080.png'), fullPage: false });
    console.log('Captured part3_migration_inventory_1920x1080.png');

    // Open first migration certification detail
    await page.locator('tbody tr').first().click();
    await page.waitForTimeout(400);

    // Migration Detail Tabs
    await page.screenshot({ path: path.join(outDir, 'part3_migration_detail_overview_1920x1080.png'), fullPage: false });
    console.log('Captured part3_migration_detail_overview_1920x1080.png');

    await page.getByRole('button', { name: 'Criteria & Assertions' }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_migration_detail_criteria_1920x1080.png'), fullPage: false });
    console.log('Captured part3_migration_detail_criteria_1920x1080.png');

    await page.getByRole('button', { name: 'Evidence Basis' }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_migration_detail_evidence_1920x1080.png'), fullPage: false });
    console.log('Captured part3_migration_detail_evidence_1920x1080.png');

    await page.getByRole('button', { name: 'Governance & Decision' }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_migration_detail_governance_1920x1080.png'), fullPage: false });
    console.log('Captured part3_migration_detail_governance_1920x1080.png');

    await page.getByRole('button', { name: 'Trust & Integrity' }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_migration_detail_integrity_1920x1080.png'), fullPage: false });
    console.log('Captured part3_migration_detail_integrity_1920x1080.png');

    await page.getByRole('button', { name: 'Related Reports' }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_migration_detail_related_1920x1080.png'), fullPage: false });
    console.log('Captured part3_migration_detail_related_1920x1080.png');

    // Go back to certification root
    await page.getByRole('button', { name: 'Back' }).first().click();
    await page.waitForTimeout(300);

    // 3. Validation Inventory Screen
    await page.getByRole('button', { name: 'Validation Certification' }).first().click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, 'part3_validation_inventory_1920x1080.png'), fullPage: false });
    console.log('Captured part3_validation_inventory_1920x1080.png');

    // Open first validation certification detail
    await page.locator('tbody tr').first().click();
    await page.waitForTimeout(400);

    // Validation Detail Tabs
    await page.screenshot({ path: path.join(outDir, 'part3_validation_detail_overview_1920x1080.png'), fullPage: false });
    console.log('Captured part3_validation_detail_overview_1920x1080.png');

    await page.getByRole('button', { name: 'Criteria & Assertions' }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_validation_detail_criteria_1920x1080.png'), fullPage: false });
    console.log('Captured part3_validation_detail_criteria_1920x1080.png');

    await page.getByRole('button', { name: 'Evidence Basis' }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_validation_detail_evidence_1920x1080.png'), fullPage: false });
    console.log('Captured part3_validation_detail_evidence_1920x1080.png');

    const govTab = page.getByRole('button', { name: 'Governance & Decision' });
    if (await govTab.isVisible()) {
      await govTab.click();
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(outDir, 'part3_validation_detail_governance_1920x1080.png'), fullPage: false });
      console.log('Captured part3_validation_detail_governance_1920x1080.png');
    }

    await page.getByRole('button', { name: 'Trust & Integrity' }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_validation_detail_integrity_1920x1080.png'), fullPage: false });
    console.log('Captured part3_validation_detail_integrity_1920x1080.png');

    await page.getByRole('button', { name: 'Related Reports' }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_validation_detail_related_1920x1080.png'), fullPage: false });
    console.log('Captured part3_validation_detail_related_1920x1080.png');

    // Go back
    await page.getByRole('button', { name: 'Back' }).first().click();
    await page.waitForTimeout(300);

    // 4. Verification Console Screen
    await page.getByRole('button', { name: 'Verification Console' }).first().click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, 'part3_verification_workspace_default_1920x1080.png'), fullPage: false });
    console.log('Captured part3_verification_workspace_default_1920x1080.png');

    // Fill target identifier and click Verify Fingerprint
    await page.locator('input[placeholder*="CERT-MIG-2026-001"]').fill('CERT-MIG-2026-001');
    await page.getByRole('button', { name: 'Verify Fingerprint' }).click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, 'part3_verification_workspace_success_1920x1080.png'), fullPage: false });
    console.log('Captured part3_verification_workspace_success_1920x1080.png');

    // Test a non-existent / mismatch / invalid ID
    await page.locator('input[placeholder*="CERT-MIG-2026-001"]').fill('UNKNOWN-CORRUPTED-HASH-ARTIFACT');
    await page.getByRole('button', { name: 'Verify Fingerprint' }).click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, 'part3_verification_workspace_mismatch_1920x1080.png'), fullPage: false });
    console.log('Captured part3_verification_workspace_mismatch_1920x1080.png');

    // 5. 1440x900 responsive captures
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.getByRole('button', { name: 'Overview' }).first().click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_certification_overview_1440x900.png'), fullPage: false });
    console.log('Captured part3_certification_overview_1440x900.png');

    await page.getByRole('button', { name: 'Migration Certification' }).first().click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_migration_inventory_1440x900.png'), fullPage: false });
    console.log('Captured part3_migration_inventory_1440x900.png');

    await page.getByRole('button', { name: 'Validation Certification' }).first().click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_validation_inventory_1440x900.png'), fullPage: false });
    console.log('Captured part3_validation_inventory_1440x900.png');

    // 6. 1280x800 responsive capture
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.getByRole('button', { name: 'Overview' }).first().click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'part3_certification_overview_1280x800.png'), fullPage: false });
    console.log('Captured part3_certification_overview_1280x800.png');

    await page.close();
    await browser.close();
    console.log('ALL PART 3 PLAYWRIGHT SCREENSHOTS SUCCESSFULLY CAPTURED ACROSS VIEWPORTS!');
  } catch (err) {
    console.error('Playwright verification error:', err);
  } finally {
    server.close();
  }
});
