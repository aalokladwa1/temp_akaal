import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../../core/synchronization.js';

export class Step7PlanPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get planDagContainer(): Locator {
    return this.page.locator('.dag-container, [data-testid="plan-dag"], canvas, svg, [role="region"][aria-label*="Plan"]').first();
  }

  public get continueButton(): Locator {
    return this.page.locator('button[title="Continue to next step"], button:has-text("Continue to Governance"), button:has-text("Continue to")').first();
  }

  public async verifyPlanCompiled(timeoutMs: number = 20000): Promise<boolean> {
    await SynchronizationHelper.waitForVisible(this.planDagContainer, timeoutMs, 'Step 7 Plan DAG');
    return true;
  }

  public async continueToStep8(): Promise<void> {
    await SynchronizationHelper.waitForEnabled(this.continueButton, 8000, 'Continue to Step 8');
    await this.continueButton.click();
  }
}
