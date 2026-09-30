import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../../core/synchronization.js';

export class Step5MappingPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get mappingReadinessIndicator(): Locator {
    return this.page.locator('text="Mapping readiness:", [data-testid="step5-readiness"]').first();
  }

  public get continueButton(): Locator {
    return this.page.locator('button[title="Continue to next step"], button:has-text("Continue to Configuration"), button:has-text("Continue to")').first();
  }

  public async verifyReadiness(timeoutMs: number = 10000): Promise<boolean> {
    await SynchronizationHelper.waitForVisible(this.mappingReadinessIndicator, timeoutMs, 'Step 5 Mapping Readiness');
    const text = (await this.mappingReadinessIndicator.textContent().catch(() => '')) || '';
    return !text.includes('blocker');
  }

  public async continueToStep6(): Promise<void> {
    await SynchronizationHelper.waitForEnabled(this.continueButton, 8000, 'Continue to Step 6');
    await this.continueButton.click();
  }
}
