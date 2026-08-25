import { Injectable, signal } from '@angular/core';

export enum AppLifecycleState {
  SPLASH = 'splash',
  SETUP_WIZARD = 'setup-wizard',
  FIRST_ADMIN = 'first-admin',
  LOGIN = 'login',
  MAIN_APP = 'main-app',
}

@Injectable({
  providedIn: 'root',
})
export class LifecycleService {
  public currentState = signal<AppLifecycleState>(AppLifecycleState.SPLASH);
  public isSystemInitialized = signal<boolean>(false);
  public isAuthenticated = signal<boolean>(false);

  public transitionTo(state: AppLifecycleState): void {
    console.log(`[Lifecycle Transition] -> ${state}`);
    this.currentState.set(state);
  }

  public completeSplash(hasExistingInstallation: boolean): void {
    this.isSystemInitialized.set(hasExistingInstallation);
    if (!hasExistingInstallation) {
      this.transitionTo(AppLifecycleState.SETUP_WIZARD);
    } else if (!this.isAuthenticated()) {
      this.transitionTo(AppLifecycleState.LOGIN);
    } else {
      this.transitionTo(AppLifecycleState.MAIN_APP);
    }
  }

  public completeSetup(): void {
    this.transitionTo(AppLifecycleState.FIRST_ADMIN);
  }

  public completeFirstAdmin(): void {
    this.isSystemInitialized.set(true);
    this.transitionTo(AppLifecycleState.LOGIN);
  }

  public completeLogin(): void {
    this.isAuthenticated.set(true);
    this.transitionTo(AppLifecycleState.MAIN_APP);
  }

  public logout(): void {
    this.isAuthenticated.set(false);
    this.transitionTo(AppLifecycleState.LOGIN);
  }
}
