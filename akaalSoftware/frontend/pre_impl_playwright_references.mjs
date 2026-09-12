import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0/part4_playwright_captures');

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

const PORT = 4355;
server.listen(PORT, async () => {
  console.log(`Part 4 Verification Server running on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    const viewports = [
      { width: 1920, height: 1080, suffix: '1920x1080' },
      { width: 1440, height: 900, suffix: '1440x900' },
      { width: 1280, height: 800, suffix: '1280x800' }
    ];

    for (const vp of viewports) {
      console.log(`Starting viewport: ${vp.suffix}`);
      const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
      
      // Load base app
      await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(400);

      // Helper for navigation
      const navTo = async (route) => {
        await page.evaluate((r) => {
          window.location.hash = '';
          window.history.pushState({}, '', r);
          window.dispatchEvent(new PopStateEvent('popstate'));
        }, route);
        await page.waitForTimeout(400);
      };

      // 1. Evidence Explorer Tab
      await navTo('/reports/evidence');
      await page.screenshot({ path: path.join(outDir, `part4_01_evidence_explorer_${vp.suffix}.png`) });
      console.log(`Captured part4_01_evidence_explorer_${vp.suffix}.png`);

      // 2. Evidence Detail - Overview
      await navTo('/reports/evidence?evidenceId=EV-2026-MIG-01');
      await page.screenshot({ path: path.join(outDir, `part4_02_evidence_detail_overview_${vp.suffix}.png`) });
      console.log(`Captured part4_02_evidence_detail_overview_${vp.suffix}.png`);

      // 3. Evidence Detail - Scope & Context
      const scopeTab = page.getByRole('button', { name: /Scope/i });
      if (await scopeTab.count() > 0) {
        await scopeTab.first().click();
        await page.waitForTimeout(300);
        await page.screenshot({ path: path.join(outDir, `part4_03_evidence_detail_scope_${vp.suffix}.png`) });
        console.log(`Captured part4_03_evidence_detail_scope_${vp.suffix}.png`);
      }

      // 4. Evidence Detail - Provenance
      const provTab = page.getByRole('button', { name: /Provenance/i });
      if (await provTab.count() > 0) {
        await provTab.first().click();
        await page.waitForTimeout(300);
        await page.screenshot({ path: path.join(outDir, `part4_04_evidence_detail_provenance_${vp.suffix}.png`) });
        console.log(`Captured part4_04_evidence_detail_provenance_${vp.suffix}.png`);
      }

      // 5. Evidence Detail - Trust & Integrity
      const intTab = page.getByRole('button', { name: /Trust & Integrity/i });
      if (await intTab.count() > 0) {
        await intTab.first().click();
        await page.waitForTimeout(300);
        await page.screenshot({ path: path.join(outDir, `part4_05_evidence_detail_integrity_${vp.suffix}.png`) });
        console.log(`Captured part4_05_evidence_detail_integrity_${vp.suffix}.png`);
      }

      // 6. Evidence Detail - Related Artifacts
      const relTab = page.getByRole('button', { name: /Related Artifacts/i });
      if (await relTab.count() > 0) {
        await relTab.first().click();
        await page.waitForTimeout(300);
        await page.screenshot({ path: path.join(outDir, `part4_06_evidence_detail_related_${vp.suffix}.png`) });
        console.log(`Captured part4_06_evidence_detail_related_${vp.suffix}.png`);
      }

      // 7. Dossiers Inventory
      await navTo('/reports/evidence?tab=DOSSIERS');
      await page.screenshot({ path: path.join(outDir, `part4_07_dossiers_inventory_${vp.suffix}.png`) });
      console.log(`Captured part4_07_dossiers_inventory_${vp.suffix}.png`);

      // 8. Dossier Detail Inspection
      await navTo('/reports/evidence?dossierId=DOS-2026-001');
      await page.screenshot({ path: path.join(outDir, `part4_08_dossier_detail_${vp.suffix}.png`) });
      console.log(`Captured part4_08_dossier_detail_${vp.suffix}.png`);

      // 9. Certificates Inventory
      await navTo('/reports/evidence?tab=CERTIFICATES');
      await page.screenshot({ path: path.join(outDir, `part4_09_certificates_inventory_${vp.suffix}.png`) });
      console.log(`Captured part4_09_certificates_inventory_${vp.suffix}.png`);

      // 10. Certificate Detail
      await navTo('/reports/evidence?certId=CERT-MIG-2026-001');
      await page.screenshot({ path: path.join(outDir, `part4_10_certificate_detail_${vp.suffix}.png`) });
      console.log(`Captured part4_10_certificate_detail_${vp.suffix}.png`);

      // 11. Evidence Packages Inventory
      await navTo('/reports/evidence?tab=PACKAGES');
      await page.screenshot({ path: path.join(outDir, `part4_11_packages_inventory_${vp.suffix}.png`) });
      console.log(`Captured part4_11_packages_inventory_${vp.suffix}.png`);

      // 12. Package Detail & Manifest
      await navTo('/reports/evidence?packageId=PKG-2026-001');
      await page.screenshot({ path: path.join(outDir, `part4_12_package_detail_manifest_${vp.suffix}.png`) });
      console.log(`Captured part4_12_package_detail_manifest_${vp.suffix}.png`);

      // 13. Integrity Verification Workspace Default
      await navTo('/reports/evidence?tab=VERIFICATION');
      await page.screenshot({ path: path.join(outDir, `part4_13_verification_workspace_default_${vp.suffix}.png`) });
      console.log(`Captured part4_13_verification_workspace_default_${vp.suffix}.png`);

      // 14. Verification Success (EV-2026-MIG-01)
      const input = page.locator('input[placeholder*="EV-2026-MIG-01"]');
      if (await input.count() > 0) {
        await input.first().fill('EV-2026-MIG-01');
        await page.getByRole('button', { name: 'Verify Fingerprint' }).click();
        await page.waitForTimeout(300);
        await page.screenshot({ path: path.join(outDir, `part4_14_verification_success_${vp.suffix}.png`) });
        console.log(`Captured part4_14_verification_success_${vp.suffix}.png`);

        // 15. Verification Unavailable (UNKNOWN-CORRUPTED-999)
        await input.first().fill('UNKNOWN-CORRUPTED-999');
        await page.getByRole('button', { name: 'Verify Fingerprint' }).click();
        await page.waitForTimeout(300);
        await page.screenshot({ path: path.join(outDir, `part4_15_verification_unavailable_${vp.suffix}.png`) });
        console.log(`Captured part4_15_verification_unavailable_${vp.suffix}.png`);
      }

      // 16. Whole-Reports Regression Surfaces
      await navTo('/reports');
      await page.screenshot({ path: path.join(outDir, `part4_16_regression_reports_home_${vp.suffix}.png`) });
      console.log(`Captured part4_16_regression_reports_home_${vp.suffix}.png`);

      await navTo('/reports/library');
      await page.screenshot({ path: path.join(outDir, `part4_17_regression_reports_library_${vp.suffix}.png`) });
      console.log(`Captured part4_17_regression_reports_library_${vp.suffix}.png`);

      await navTo('/reports/library?reportId=REP-2026-0101');
      await page.screenshot({ path: path.join(outDir, `part4_18_regression_report_detail_migration_${vp.suffix}.png`) });
      console.log(`Captured part4_18_regression_report_detail_migration_${vp.suffix}.png`);

      await navTo('/reports/certification');
      await page.screenshot({ path: path.join(outDir, `part4_19_regression_trust_cert_overview_${vp.suffix}.png`) });
      console.log(`Captured part4_19_regression_trust_cert_overview_${vp.suffix}.png`);

      await page.close();
    }

    await browser.close();
    console.log('ALL PART 4 & REGRESSION PLAYWRIGHT SCREENSHOTS CAPTURED SUCCESSFULLY!');
  } catch (err) {
    console.error('Playwright error:', err);
  } finally {
    server.close();
  }
});


