import { ApplicationConfig, ErrorHandler, Injectable, provideZoneChangeDetection } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { providePrimeNG } from 'primeng/config';
import Aura from '@primeng/themes/aura';
import { routes } from './app.routes';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  handleError(error: any): void {
    console.error('=== [ANGULAR GLOBAL ERROR CAUGHT] ===', error);
    const msg = error?.message || (typeof error === 'string' ? error : JSON.stringify(error));
    const stack = error?.stack || '';

    if (typeof document !== 'undefined') {
      let banner = document.getElementById('akaal-runtime-error-banner');
      if (!banner) {
        banner = document.createElement('div');
        banner.id = 'akaal-runtime-error-banner';
        banner.style.cssText = 'position:fixed;bottom:10px;left:10px;right:10px;max-height:220px;overflow:auto;background:#fee2e2;color:#991b1b;border:2px solid #ef4444;padding:12px;border-radius:8px;font-family:monospace;font-size:12px;z-index:99999;box-shadow:0 10px 25px rgba(0,0,0,0.3);';
        document.body.appendChild(banner);
      }
      banner.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;"><strong>⚠️ Application Error Detected:</strong><button onclick="this.parentElement.parentElement.remove()" style="background:#ef4444;color:white;border:none;padding:2px 8px;border-radius:4px;cursor:pointer;font-weight:bold;">&times; Dismiss</button></div><div>${msg}</div><pre style="margin-top:6px;font-size:10px;white-space:pre-wrap;opacity:0.8;">${stack}</pre>`;
    }
  }
}

export const appConfig: ApplicationConfig = {
  providers: [
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes, withComponentInputBinding()),
    provideAnimationsAsync(),
    providePrimeNG({
      theme: {
        preset: Aura,
        options: {
          darkModeSelector: false,
          cssLayer: false
        }
      },
      ripple: true
    })
  ]
};
