import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../../core/synchronization.js';

export class Step8GovernancePOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get governanceReadinessIndicator(): Locator {
    return this.page.locator('text="Governance Readiness", text="Ready", [data-testid="step8-readiness"]').first();
  }

  public get continueButton(): Locator {
    return this.page.locator('button[title="Continue to next step"], button:has-text("Continue to Review"), button:has-text("Continue to")').first();
  }

  public async verifyReadiness(timeoutMs: number = 10000): Promise<boolean> {
    await SynchronizationHelper.waitForVisible(this.governanceReadinessIndicator, timeoutMs, 'Step 8 Governance Readiness');
    return true;
  }

  public async continueToStep9(): Promise<void> {
    await SynchronizationHelper.waitForEnabled(this.continueButton, 8000, 'Continue to Step 9');
    await this.continueButton.click();
  }
}
