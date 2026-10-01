import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../../core/synchronization.js';

export class Step3TargetPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get continueButton(): Locator {
    return this.page.locator('button[title="Continue to next step"], button:has-text("Continue to Discovery"), button:has-text("Continue to")').first();
  }

  public async selectTargetConnection(nameOrProvider: string): Promise<void> {
    const target = this.page.locator(`text="${nameOrProvider}", option:has-text("${nameOrProvider}")`).first();
    await SynchronizationHelper.waitForVisible(target, 8000, `Target Connection: ${nameOrProvider}`);
    await target.click();
  }

  public async continueToStep4(): Promise<void> {
    await SynchronizationHelper.waitForEnabled(this.continueButton, 8000, 'Continue to Step 4');
    await this.continueButton.click();
  }
}
