import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../../core/synchronization.js';

export class Step6ConfigPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get configReadinessIndicator(): Locator {
    return this.page.locator('text="Configuration readiness:", [data-testid="step6-readiness"]').first();
  }

  public get continueButton(): Locator {
    return this.page.locator('button[title="Continue to next step"], button:has-text("Continue to Execution Plan"), button:has-text("Continue to")').first();
  }

  public async verifyReadiness(timeoutMs: number = 10000): Promise<boolean> {
    await SynchronizationHelper.waitForVisible(this.configReadinessIndicator, timeoutMs, 'Step 6 Config Readiness');
    const text = (await this.configReadinessIndicator.textContent().catch(() => '')) || '';
    return text.includes('Ready');
  }

  public async continueToStep7(): Promise<void> {
    await SynchronizationHelper.waitForEnabled(this.continueButton, 8000, 'Continue to Step 7');
    await this.continueButton.click();
  }
}
