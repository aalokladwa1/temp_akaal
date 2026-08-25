import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'splash',
  },
  {
    path: 'splash',
    loadComponent: () =>
      import('./modules/splash/splash.component').then((m) => m.SplashComponent),
  },
  {
    path: 'setup',
    loadComponent: () =>
      import('./modules/setup-wizard/setup-wizard.component').then((m) => m.SetupWizardComponent),
  },
  {
    path: 'first-admin',
    loadComponent: () =>
      import('./modules/first-admin/first-admin.component').then((m) => m.FirstAdminComponent),
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./modules/auth/auth.component').then((m) => m.AuthComponent),
  },
  {
    path: 'app',
    loadComponent: () =>
      import('./modules/shell/shell.component').then((m) => m.ShellComponent),
  },
  {
    path: '**',
    redirectTo: 'splash',
  },
];
