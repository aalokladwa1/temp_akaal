import { Page, Locator } from 'playwright';

export class CockpitDagPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get dagContainer(): Locator {
    return this.page.locator('app-cockpit-dag-view, [data-testid="cockpit-dag"]').first();
  }

  public get activeDagNodes(): Locator {
    return this.page.locator('.dag-node, [role="treeitem"], .cytoscape-node');
  }
}
