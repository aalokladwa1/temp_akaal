import { Page, Locator } from 'playwright';

export class CockpitHeaderPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get pauseButton(): Locator {
    return this.page.locator('button:has-text("Pause"), button[title*="Pause"]').first();
  }

  public get resumeButton(): Locator {
    return this.page.locator('button:has-text("Resume"), button[title*="Resume"]').first();
  }

  public get abortButton(): Locator {
    return this.page.locator('button:has-text("Abort"), button:has-text("Cancel"), button[title*="Abort"]').first();
  }

  public get migrationTitleHeader(): Locator {
    return this.page.locator('h1, h2, [data-testid="cockpit-title"]').first();
  }
}
