import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0/pre_part4_refs');

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

const PORT = 4350;
server.listen(PORT, async () => {
  console.log(`Pre-implementation Part 4 Reference Server running on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });

    const viewports = [
      { width: 1920, height: 1080, suffix: '1920x1080' },
      { width: 1440, height: 900, suffix: '1440x900' },
      { width: 1280, height: 800, suffix: '1280x800' }
    ];

    for (const vp of viewports) {
      const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });

      // 1. Reports Home
      await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      await page.locator('aside a[href*="reports"], a:has-text("Reports")').first().click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `ref_1_reports_home_${vp.suffix}.png`) });

      // 2. Report Library
      await page.locator('a[routerLink="/reports/library"], a[href*="reports/library"], a:has-text("Report Library")').first().click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `ref_2_reports_library_${vp.suffix}.png`) });

      // 3. Selected Report (REP-2026-0101)
      const invBtn = page.getByRole('button', { name: 'All Generated Reports' });
      if (await invBtn.isVisible()) {
        await invBtn.click();
        await page.waitForTimeout(300);
        await page.locator('tbody tr').first().click();
        await page.waitForTimeout(400);
        await page.screenshot({ path: path.join(outDir, `ref_3_selected_report_${vp.suffix}.png`) });
      }

      // 4. Trust & Certification Overview
      await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      await page.locator('aside a[href*="reports"], a:has-text("Reports")').first().click();
      await page.waitForTimeout(500);
      await page.locator('a[routerLink="/reports/certification"], a[href*="reports/certification"], a:has-text("Trust & Certification")').first().click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `ref_4_trust_certification_overview_${vp.suffix}.png`) });

      // 5. Certification Detail
      await page.getByRole('button', { name: 'Migration Certification' }).first().click();
      await page.waitForTimeout(300);
      await page.locator('tbody tr').first().click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `ref_5_certification_detail_${vp.suffix}.png`) });

      // 6. Verification Console
      await page.getByRole('button', { name: 'Back' }).first().click();
      await page.waitForTimeout(300);
      await page.getByRole('button', { name: 'Verification Console' }).first().click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `ref_6_verification_console_${vp.suffix}.png`) });

      // 7. Monitoring Home
      await page.locator('aside a[href*="monitoring"], a:has-text("Monitoring")').first().click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `ref_7_monitoring_home_${vp.suffix}.png`) });

      // 8. History Home
      await page.locator('aside a[href*="migration"], a:has-text("Migration")').first().click();
      await page.waitForTimeout(500);
      const histLink = page.locator('a[href*="history"], a:has-text("History")').first();
      if (await histLink.isVisible()) {
        await histLink.click();
        await page.waitForTimeout(500);
        await page.screenshot({ path: path.join(outDir, `ref_8_history_home_${vp.suffix}.png`) });
      }

      // 9. Existing Evidence Portal placeholder
      await page.locator('aside a[href*="reports"], a:has-text("Reports")').first().click();
      await page.waitForTimeout(500);
      await page.locator('a[routerLink="/reports/evidence"], a[href*="reports/evidence"], a:has-text("Evidence Portal")').first().click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `ref_9_evidence_portal_initial_${vp.suffix}.png`) });

      await page.close();
      console.log(`Captured all pre-Part 4 reference surfaces for ${vp.suffix}`);
    }

    await browser.close();
    console.log('ALL PRE-PART 4 PLAYWRIGHT REFERENCES CAPTURED SUCCESSFULLY!');
  } catch (err) {
    console.error('Pre-implementation capture error:', err);
  } finally {
    server.close();
  }
});
