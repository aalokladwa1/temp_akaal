import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../core/synchronization.js';

export class ConnectionsVaultPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get createConnectionButton(): Locator {
    return this.page.locator('button:has-text("Create Connection"), button:has-text("New Connection"), [data-testid="new-connection-btn"]').first();
  }

  public get testConnectionButton(): Locator {
    return this.page.locator('button:has-text("Test Connection"), button:has-text("Verify Connection"), button:has-text("Run Test")').first();
  }

  public get testSuccessBanner(): Locator {
    return this.page.locator('text="Connection verified successfully", text="Test succeeded", text="Reachable", .bg-emerald-50').first();
  }

  public get testFailureBanner(): Locator {
    return this.page.locator('text="Connection failed", text="Unreachable", text="Connection refused", text="ERROR", .bg-rose-50').first();
  }

  public async clickCreateConnection(): Promise<void> {
    await SynchronizationHelper.waitForVisible(this.createConnectionButton, 8000, 'Create Connection Button');
    await this.createConnectionButton.click();
  }

  public async runTestConnection(): Promise<void> {
    await SynchronizationHelper.waitForEnabled(this.testConnectionButton, 8000, 'Test Connection Button');
    await this.testConnectionButton.click();
  }

  public async expectTestSuccess(timeoutMs: number = 15000): Promise<boolean> {
    try {
      await SynchronizationHelper.waitForVisible(this.testSuccessBanner, timeoutMs, 'Connection Test Success');
      return true;
    } catch {
      return false;
    }
  }

  public async expectTestFailure(timeoutMs: number = 15000): Promise<boolean> {
    try {
      await SynchronizationHelper.waitForVisible(this.testFailureBanner, timeoutMs, 'Connection Test Failure');
      return true;
    } catch {
      return false;
    }
  }
}
