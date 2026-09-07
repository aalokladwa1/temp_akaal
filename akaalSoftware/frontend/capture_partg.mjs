import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00');

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
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

const PORT = 4292;
server.listen(PORT, async () => {
  console.log(`Static server listening on http://localhost:${PORT}`);

  const browser = await chromium.launch({ headless: true, channel: 'msedge' });

  const resolutions = [
    { name: '1920x1080', width: 1920, height: 1080 },
    { name: '1440x900', width: 1440, height: 900 }
  ];

  for (const res of resolutions) {
    console.log(`\n=== Capturing resolution: ${res.name} ===`);
    const page = await browser.newPage({
      viewport: { width: res.width, height: res.height }
    });

    // 1. Portfolio Home
    console.log('1. Portfolio Home');
    await page.goto(`http://localhost:${PORT}/migration/projects`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_01_portfolio_home_${res.name}.png`) });

    // 2. Projects Discovery
    console.log('2. Projects Discovery');
    const projectsTab = page.locator('button:has-text("Projects"), a:has-text("Projects")').first();
    if (await projectsTab.count() > 0) {
      await projectsTab.click();
      await page.waitForTimeout(500);
    }
    await page.screenshot({ path: path.join(outDir, `partg_02_projects_discovery_${res.name}.png`) });

    // 3. Initiatives Discovery
    console.log('3. Initiatives Discovery');
    const initiativesTab = page.locator('button:has-text("Initiatives"), a:has-text("Initiatives")').first();
    if (await initiativesTab.count() > 0) {
      await initiativesTab.click();
      await page.waitForTimeout(500);
    }
    await page.screenshot({ path: path.join(outDir, `partg_03_initiatives_discovery_${res.name}.png`) });

    // 4. Create Initiative - Step 1
    console.log('4. Create Initiative - Step 1');
    await page.goto(`http://localhost:${PORT}/migration/initiatives/new`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_04_create_initiative_step1_${res.name}.png`) });

    // 5. Create Initiative - Step 2
    console.log('5. Create Initiative - Step 2');
    const initName = page.locator('input[placeholder*="Data Center Exit"]');
    if (await initName.count() > 0) {
      await initName.fill('Enterprise Migration Modernization 2028');
      const initObj = page.locator('textarea');
      if (await initObj.count() > 0) {
        await initObj.fill('Core transactional database and event streaming migration program.');
      }
      await page.waitForTimeout(200);
      const continueBtn = page.locator('footer button:has-text("Continue")');
      if (await continueBtn.count() > 0) {
        await continueBtn.click();
        await page.waitForTimeout(500);
        await page.screenshot({ path: path.join(outDir, `partg_05_create_initiative_step2_${res.name}.png`) });

        // Select a project
        const projectItem = page.locator('.divide-y > div').first();
        if (await projectItem.count() > 0) {
          await projectItem.click();
          await page.waitForTimeout(200);
        }

        // 6. Create Initiative - Step 3
        console.log('6. Create Initiative - Step 3');
        const continueBtn2 = page.locator('footer button:has-text("Continue")');
        if (await continueBtn2.count() > 0) {
          await continueBtn2.click();
          await page.waitForTimeout(500);
          await page.screenshot({ path: path.join(outDir, `partg_06_create_initiative_step3_${res.name}.png`) });
        }
      }
    }

    // 7. Initiative Workspace - Overview
    console.log('7. Initiative Workspace - Overview');
    await page.goto(`http://localhost:${PORT}/migration/initiatives/init-dc-exit-2027/overview`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_07_initiative_workspace_overview_${res.name}.png`) });

    // 8. Initiative Workspace - Projects
    console.log('8. Initiative Workspace - Projects');
    await page.goto(`http://localhost:${PORT}/migration/initiatives/init-dc-exit-2027/projects`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_08_initiative_workspace_projects_${res.name}.png`) });

    // 9. Initiative Workspace - Activity
    console.log('9. Initiative Workspace - Activity');
    await page.goto(`http://localhost:${PORT}/migration/initiatives/init-dc-exit-2027/activity`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_09_initiative_workspace_activity_${res.name}.png`) });

    // 10. Initiative Workspace - Settings
    console.log('10. Initiative Workspace - Settings');
    await page.goto(`http://localhost:${PORT}/migration/initiatives/init-dc-exit-2027/settings`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_10_initiative_workspace_settings_${res.name}.png`) });

    // 11. Create Project - Step 1
    console.log('11. Create Project - Step 1');
    await page.goto(`http://localhost:${PORT}/migration/projects/new`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_11_create_project_step1_${res.name}.png`) });

    // 12. Create Project - Step 2
    console.log('12. Create Project - Step 2');
    const prjName = page.locator('input[placeholder*="Core Banking"]');
    if (await prjName.count() > 0) {
      await prjName.fill('Treasury Ledger Modernization');
      const prjDesc = page.locator('textarea');
      if (await prjDesc.count() > 0) {
        await prjDesc.fill('Enterprise scale migration of treasury accounting and reporting streams.');
      }
      await page.waitForTimeout(200);
      const continuePrjBtn = page.locator('footer button:has-text("Continue")');
      if (await continuePrjBtn.count() > 0) {
        await continuePrjBtn.click();
        await page.waitForTimeout(500);
        await page.screenshot({ path: path.join(outDir, `partg_12_create_project_step2_${res.name}.png`) });

        // Select an initiative
        const initItem = page.locator('button:has-text("Data Center Exit 2027")').first();
        if (await initItem.count() > 0) {
          await initItem.click();
          await page.waitForTimeout(200);
        }

        // 13. Create Project - Step 3
        console.log('13. Create Project - Step 3');
        const continuePrjBtn2 = page.locator('footer button:has-text("Continue")');
        if (await continuePrjBtn2.count() > 0) {
          await continuePrjBtn2.click();
          await page.waitForTimeout(500);
          await page.screenshot({ path: path.join(outDir, `partg_13_create_project_step3_${res.name}.png`) });
        }
      }
    }

    // 14. Project Workspace - Overview
    console.log('14. Project Workspace - Overview');
    await page.goto(`http://localhost:${PORT}/migration/projects/proj-core-banking/overview`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_14_project_workspace_overview_${res.name}.png`) });

    // 15. Project Workspace - Migrations
    console.log('15. Project Workspace - Migrations');
    await page.goto(`http://localhost:${PORT}/migration/projects/proj-core-banking/migrations`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_15_project_workspace_migrations_${res.name}.png`) });

    // 16. Project Workspace - Validations
    console.log('16. Project Workspace - Validations');
    await page.goto(`http://localhost:${PORT}/migration/projects/proj-core-banking/validations`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_16_project_workspace_validations_${res.name}.png`) });

    // 17. Project Workspace - Resources
    console.log('17. Project Workspace - Resources');
    await page.goto(`http://localhost:${PORT}/migration/projects/proj-core-banking/resources`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_17_project_workspace_resources_${res.name}.png`) });

    // 18. Project Workspace - Activity
    console.log('18. Project Workspace - Activity');
    await page.goto(`http://localhost:${PORT}/migration/projects/proj-core-banking/activity`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_18_project_workspace_activity_${res.name}.png`) });

    // 19. Project Workspace - Access
    console.log('19. Project Workspace - Access');
    await page.goto(`http://localhost:${PORT}/migration/projects/proj-core-banking/access`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_19_project_workspace_access_${res.name}.png`) });

    // 20. Project Workspace - Governance
    console.log('20. Project Workspace - Governance');
    await page.goto(`http://localhost:${PORT}/migration/projects/proj-core-banking/governance`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_20_project_workspace_governance_${res.name}.png`) });

    // 21. Project Workspace - Settings
    console.log('21. Project Workspace - Settings');
    await page.goto(`http://localhost:${PORT}/migration/projects/proj-core-banking/settings`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(outDir, `partg_21_project_workspace_settings_${res.name}.png`) });

    // 22. Move Migration Modal
    console.log('22. Move Migration Modal');
    await page.goto(`http://localhost:${PORT}/migration/projects/proj-core-banking/migrations`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    const moveBtn = page.locator('button:has-text("Move")').first();
    if (await moveBtn.count() > 0) {
      await moveBtn.click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(outDir, `partg_22_move_migration_modal_${res.name}.png`) });
    }

    await page.close();
  }

  await browser.close();
  server.close();
  console.log('All Part G screenshots captured successfully with correct project IDs!');
  process.exit(0);
});
