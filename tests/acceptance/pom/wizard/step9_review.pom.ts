import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../../core/synchronization.js';

export class Step9ReviewPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get initializeAndLaunchButton(): Locator {
    return this.page.locator('button:has-text("Initialize & Launch"), button:has-text("Launch Migration"), button:has-text("Start Migration"), [data-testid="initialize-migration-btn"]').first();
  }

  public get initializingSpinner(): Locator {
    return this.page.locator('text="Initializing...", .animate-spin').first();
  }

  public async initializeAndLaunch(timeoutMs: number = 25000): Promise<void> {
    await SynchronizationHelper.waitForEnabled(this.initializeAndLaunchButton, 8000, 'Initialize & Launch Button');
    await this.initializeAndLaunchButton.click();

    // Wait for transition to Cockpit route
    await this.page.waitForURL(/.*\/migration\/cockpit\/.*/, { timeout: timeoutMs }).catch(() => {});
  }
}
