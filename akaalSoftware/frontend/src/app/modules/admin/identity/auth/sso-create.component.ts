/**
 * AKAAL Administration — Create Single Sign-On Identity Provider
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { IdentityService } from '../../services/identity.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-sso-create',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-3xl mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Back Link -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-4">
          <a routerLink="/administration/identity/auth/sso" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all w-fit cursor-pointer">
            <app-lucide-icon name="arrow-left" [size]="14" class="text-slate-500"></app-lucide-icon>
            Back to SSO Providers
          </a>
        </div>

        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200">
          <div class="flex flex-col gap-1">
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Add Identity Provider</h1>
            <p class="text-sm font-medium text-slate-600">
              Configure SAML 2.0 or OpenID Connect (OIDC) federation with your enterprise IdP.
            </p>
          </div>
        </div>
      </div>

      <!-- Form Body -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-2xs p-6 flex flex-col gap-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          <div class="flex flex-col gap-1.5 md:col-span-2">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Identity Provider Display Name</label>
            <input
              type="text"
              [(ngModel)]="name"
              placeholder="e.g. Corporate Azure AD"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Federation Protocol</label>
            <app-custom-select
              [options]="protocolOptions"
              [(ngModel)]="protocol">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Provider Type</label>
            <app-custom-select
              [options]="providerTypeOptions"
              [(ngModel)]="providerType">
            </app-custom-select>
          </div>

          <div class="flex flex-col gap-1.5 md:col-span-2">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Entity ID / Issuer URL</label>
            <input
              type="text"
              [(ngModel)]="entityIdOrIssuer"
              placeholder="https://login.microsoftonline.com/tenant-id/v2.0 or http://www.okta.com/exk..."
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5 md:col-span-2">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Single Sign-On Endpoint URL</label>
            <input
              type="text"
              [(ngModel)]="singleSignOnUrl"
              placeholder="https://idp.corp.com/app/sso/saml or /oauth2/v2.0/authorize"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Client ID / SP Entity</label>
            <input
              type="text"
              [(ngModel)]="clientId"
              placeholder="e.g. akaal-sp-client"
              class="h-9 px-3 text-xs font-mono rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">Default Role Assignment</label>
            <input
              type="text"
              [(ngModel)]="defaultRoleAssign"
              placeholder="e.g. Standard Analyst"
              class="h-9 px-3 text-xs rounded border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
            />
          </div>

          <div class="flex items-center gap-3 pt-2 md:col-span-2">
            <input
              type="checkbox"
              id="jitToggle"
              [(ngModel)]="jitProvisioningEnabled"
              class="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <label for="jitToggle" class="text-xs font-bold text-slate-700">Enable Just-In-Time (JIT) Automatic User Account Provisioning</label>
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <a
            routerLink="/administration/identity/auth/sso"
            class="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors shadow-2xs">
            Cancel
          </a>
          <button
            (click)="save()"
            [disabled]="!name || !entityIdOrIssuer"
            class="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors shadow-2xs cursor-pointer">
            Save Provider
          </button>
        </div>
      </div>
    </div>
  `
})
export class SsoCreateComponent {
  private router = inject(Router);
  public identity = inject(IdentityService);

  public name = '';
  public protocol: any = 'OIDC';
  public providerType: any = 'AZURE_AD';
  public entityIdOrIssuer = '';
  public singleSignOnUrl = '';
  public clientId = '';
  public defaultRoleAssign = 'Data Engineer Standard';
  public jitProvisioningEnabled = true;

  public protocolOptions: CustomSelectOption[] = [
    { label: 'OpenID Connect (OIDC)', value: 'OIDC' },
    { label: 'SAML 2.0', value: 'SAML_2_0' }
  ];

  public providerTypeOptions: CustomSelectOption[] = [
    { label: 'Microsoft Entra ID (Azure AD)', value: 'AZURE_AD' },
    { label: 'Okta Workforce', value: 'OKTA' },
    { label: 'Google Workspace', value: 'GOOGLE_WORKSPACE' },
    { label: 'Ping Identity', value: 'PING_IDENTITY' },
    { label: 'Keycloak', value: 'KEYCLOAK' }
  ];

  public save(): void {
    if (!this.name || !this.entityIdOrIssuer) return;
    this.identity.createSsoProvider({
      name: this.name,
      protocol: this.protocol,
      providerType: this.providerType,
      entityIdOrIssuer: this.entityIdOrIssuer,
      singleSignOnUrl: this.singleSignOnUrl,
      clientId: this.clientId,
      defaultRoleAssign: this.defaultRoleAssign,
      jitProvisioningEnabled: this.jitProvisioningEnabled
    });
    this.router.navigate(['/administration/identity/auth/sso']);
  }
}
