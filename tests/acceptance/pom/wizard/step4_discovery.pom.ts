import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../../core/synchronization.js';

export class Step4DiscoveryPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get runDiscoveryButton(): Locator {
    return this.page.locator('button:has-text("Run Discovery"), button:has-text("Discover Schema"), button:has-text("Discover Metadata"), [data-testid="run-discovery-btn"]').first();
  }

  public get lockScopeButton(): Locator {
    return this.page.locator('button:has-text("Lock Scope"), button[title="Lock scope to proceed to Mapping"]').first();
  }

  public get selectAllCheckbox(): Locator {
    return this.page.locator('input[type="checkbox"][aria-label*="Select all"], input[type="checkbox"]').first();
  }

  public get discoveredTableRows(): Locator {
    return this.page.locator('tr:has(input[type="checkbox"]), .table-tree-item, [role="row"]:has(input[type="checkbox"])');
  }

  public get continueButton(): Locator {
    return this.page.locator('button[title="Continue to next step"], button:has-text("Continue to Mapping"), button:has-text("Continue to")').first();
  }

  public async triggerDiscovery(): Promise<void> {
    const btn = this.runDiscoveryButton;
    const isVisible = await btn.isVisible().catch(() => false);
    if (isVisible) {
      await btn.click();
    }
  }

  /**
   * Blindly observes what DevKros discovers without hardcoded database answers.
   */
  public async observeAndSelectDiscoveredTables(timeoutMs: number = 30000): Promise<string[]> {
    // Wait for at least one table row to appear
    await SynchronizationHelper.waitForCondition(
      async () => {
        const count = await this.discoveredTableRows.count();
        return count > 0 ? count : false;
      },
      timeoutMs,
      500,
      'Discovered Table Rows'
    );

    const count = await this.discoveredTableRows.count();
    const discoveredNames: string[] = [];

    for (let i = 0; i < count; i++) {
      const row = this.discoveredTableRows.nth(i);
      const text = (await row.textContent().catch(() => '')) || '';
      discoveredNames.push(text.trim().split('\n')[0]);
      
      const checkbox = row.locator('input[type="checkbox"]').first();
      if (await checkbox.isVisible().catch(() => false)) {
        if (!(await checkbox.isChecked().catch(() => false))) {
          await checkbox.check().catch(() => {});
        }
      }
    }

    // If lock scope button is present, lock it
    const lockBtn = this.lockScopeButton;
    if (await lockBtn.isVisible().catch(() => false)) {
      await SynchronizationHelper.waitForEnabled(lockBtn, 8000, 'Lock Scope Button');
      await lockBtn.click();
    }

    return discoveredNames;
  }

  public async continueToStep5(): Promise<void> {
    await SynchronizationHelper.waitForEnabled(this.continueButton, 8000, 'Continue to Step 5');
    await this.continueButton.click();
  }
}
