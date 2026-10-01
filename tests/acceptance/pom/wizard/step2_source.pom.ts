import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../../core/synchronization.js';

export class Step2SourcePOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get connectionCardOrSelect(): Locator {
    return this.page.locator('select, [data-testid="source-connection-select"], div[role="radio"], button:has-text("Oracle"), div:has-text("Oracle")').first();
  }

  public get continueButton(): Locator {
    return this.page.locator('button[title="Continue to next step"], button:has-text("Continue to Select Target"), button:has-text("Continue to")').first();
  }

  public async selectSourceConnection(nameOrProvider: string): Promise<void> {
    const target = this.page.locator(`text="${nameOrProvider}", option:has-text("${nameOrProvider}")`).first();
    await SynchronizationHelper.waitForVisible(target, 8000, `Source Connection: ${nameOrProvider}`);
    await target.click();
  }

  public async continueToStep3(): Promise<void> {
    await SynchronizationHelper.waitForEnabled(this.continueButton, 8000, 'Continue to Step 3');
    await this.continueButton.click();
  }
}
