import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../core/synchronization.js';

export class AppShellPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get navMigrationsLink(): Locator {
    return this.page.locator('a[href="/migration"], a[routerlink="/migration"], button:has-text("Migrations"), nav a:has-text("Migration")').first();
  }

  public get navConnectionsLink(): Locator {
    return this.page.locator('a[href="/connections"], a[routerlink="/connections"], button:has-text("Connections"), nav a:has-text("Connection")').first();
  }

  public get createMigrationButton(): Locator {
    return this.page.locator('button:has-text("Create Migration"), a:has-text("Create Migration"), [data-testid="create-migration-btn"]').first();
  }

  public async navigateToMigrations(): Promise<void> {
    await SynchronizationHelper.waitForVisible(this.navMigrationsLink, 8000, 'Nav Migrations Link');
    await this.navMigrationsLink.click();
  }

  public async navigateToConnections(): Promise<void> {
    await SynchronizationHelper.waitForVisible(this.navConnectionsLink, 8000, 'Nav Connections Link');
    await this.navConnectionsLink.click();
  }

  public async openCreateMigrationWizard(): Promise<void> {
    await SynchronizationHelper.waitForVisible(this.createMigrationButton, 8000, 'Create Migration Button');
    await this.createMigrationButton.click();
  }
}
