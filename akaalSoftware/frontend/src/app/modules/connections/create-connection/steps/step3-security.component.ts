import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateConnectionService } from '../create-connection.service';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { AccordionComponent } from '../../../../shared/components/accordion.component';

@Component({
  selector: 'app-step3-security',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent, LucideIconComponent, AccordionComponent],
  template: `
    <div class="max-w-5xl mx-auto w-full space-y-6 select-none animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- Top Section Header -->
      <div class="flex flex-col gap-1 border-b border-slate-200 pb-3">
        <h2 class="text-base font-bold text-slate-900 tracking-tight">Security &amp; Network Routing</h2>
        <p class="text-xs text-slate-500 font-normal">
          Configure authentication credentials, TLS transport encryption, and secure network routing topology.
        </p>
      </div>

      <!-- ========================================================================= -->
      <!-- CARD 1: AUTHENTICATION & SECRETS                                          -->
      <!-- ========================================================================= -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
        <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
          <span class="text-xs font-bold text-slate-900">1. Authentication &amp; Credential References</span>
          <span class="text-[11px] text-slate-400 font-normal">Opaque SecretRef custody &middot; Never logged or persisted in plaintext</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Authentication Method (Tailored strictly to selected provider) -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Authentication Method <span class="text-rose-500">*</span>
            </label>
            <app-custom-select
              [options]="authMethodOptions"
              [value]="cs.draft().authMethod"
              (valueChange)="onAuthMethodChange($event)">
            </app-custom-select>
            <span class="text-[11px] text-slate-400">
              Supported protocols derived from canonical provider manifest.
            </span>
          </div>

          <!-- Username / Principal / Service Account Identifier -->
          @if (cs.draft().authMethod !== 'NONE' && cs.draft().authMethod !== 'AWS_CHAIN' && cs.draft().authMethod !== 'INSTANCE_PRINCIPAL' && cs.draft().authMethod !== 'RESOURCE_PRINCIPAL') {
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-slate-700">
                Username / Principal Identifier <span class="text-rose-500">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="cs.draft().authUsername"
                (ngModelChange)="cs.markConfigurationMutated()"
                placeholder="akaal_service_account or db_user"
                class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
            </div>
          }

        </div>

        <!-- IAM Role ARN (When AWS IAM is selected) -->
        @if (cs.draft().authMethod === 'IAM_ROLE' || cs.draft().authMethod === 'AWS_IAM') {
          <div class="p-3.5 bg-blue-50/40 border border-blue-200 rounded-xl flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-800">
              AWS IAM Role ARN (STS AssumeRole) <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="cs.draft().authRoleArn"
              (ngModelChange)="cs.markConfigurationMutated()"
              placeholder="arn:aws:iam::123456789012:role/AKAALMigrationExecutionRole"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 font-mono" />
          </div>
        }

        <!-- Secret Reference / Password Input (Strictly Masked) -->
        @if (cs.draft().authMethod !== 'NONE' && cs.draft().authMethod !== 'AWS_CHAIN' && cs.draft().authMethod !== 'INSTANCE_PRINCIPAL' && cs.draft().authMethod !== 'RESOURCE_PRINCIPAL' && cs.draft().authMethod !== 'ADC') {
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            
            <div class="flex flex-col gap-1.5 md:col-span-2">
              <label class="text-xs font-semibold text-slate-700 flex items-center justify-between">
                <span>Secret Reference or Password <span class="text-rose-500">*</span></span>
                <span class="text-[11px] text-slate-400 font-normal">Supports vault://, aws-secretsmanager:, azure-keyvault:</span>
              </label>

              <div class="relative">
                <input
                  [type]="isSecretVisible() ? 'text' : 'password'"
                  [(ngModel)]="cs.draft().authSecretRef"
                  (ngModelChange)="cs.markConfigurationMutated()"
                  placeholder="vault://secret/prod/database_password or Enter credential..."
                  class="w-full h-9 px-3 pr-10 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 font-mono" />
                <button
                  type="button"
                  (click)="isSecretVisible.set(!isSecretVisible())"
                  class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer p-0.5"
                  [title]="isSecretVisible() ? 'Hide secret' : 'Show secret'">
                  <app-lucide-icon [name]="isSecretVisible() ? 'eye-off' : 'eye'" [size]="14"></app-lucide-icon>
                </button>
              </div>

              <span class="text-[11px] text-slate-400">
                Production environments mandate opaque secret references managed by Enterprise Vault or Cloud KMS.
              </span>
            </div>

          </div>
        }

      </div>

      <!-- ========================================================================= -->
      <!-- CARD 2: TRANSPORT SECURITY (TLS) & mTLS                                    -->
      <!-- ========================================================================= -->
      @if (cs.selectedProvider()?.supportsTls) {
        <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
          <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
            <span class="text-xs font-bold text-slate-900">2. Transport Layer Security (TLS Binding)</span>
            <span class="text-[11px] text-slate-400 font-normal">Unified transport encryption &middot; Fail-closed verification</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            <!-- TLS Mode Selector -->
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-slate-700">
                TLS Verification Mode <span class="text-rose-500">*</span>
              </label>
              <app-custom-select
                [options]="tlsModeOptions"
                [value]="cs.draft().tlsMode"
                (valueChange)="onTlsModeChange($event)">
              </app-custom-select>
              <span class="text-[11px] text-slate-400">
                VERIFY_FULL enforces CA chain and Subject Alternative Name (SAN) hostname validation.
              </span>
            </div>

            <!-- Minimum TLS Version -->
            @if (cs.draft().tlsMode !== 'DISABLED') {
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">
                  Minimum TLS Version <span class="text-rose-500">*</span>
                </label>
                <app-custom-select
                  [options]="minTlsOptions"
                  [value]="cs.draft().minTlsVersion"
                  (valueChange)="onMinTlsChange($event)">
                </app-custom-select>
              </div>
            }

          </div>

          <!-- TLS Certificates & Hostname Override (When TLS is active) -->
          @if (cs.draft().tlsMode !== 'DISABLED') {
            <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl space-y-3.5">
              
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Custom CA Certificate Reference -->
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-semibold text-slate-700">
                    Custom CA Certificate Reference <span class="text-slate-400 font-normal">(Optional)</span>
                  </label>
                  <input
                    type="text"
                    [(ngModel)]="cs.draft().caCertificateRef"
                    (ngModelChange)="cs.markConfigurationMutated()"
                    placeholder="/etc/ssl/certs/internal-root-ca.pem or vault://secret/ca_cert"
                    class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600 font-mono" />
                </div>

                <!-- Server Name Override (SNI) -->
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-semibold text-slate-700">
                    Server Name Override (SNI) <span class="text-slate-400 font-normal">(Optional)</span>
                  </label>
                  <input
                    type="text"
                    [(ngModel)]="cs.draft().serverNameOverride"
                    (ngModelChange)="cs.markConfigurationMutated()"
                    placeholder="db.corp.internal"
                    class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                </div>
              </div>

              <!-- Allow Self-Signed (With Fail-Closed Warning) -->
              <div class="flex flex-col gap-1 pt-2 border-t border-slate-200/60">
                <label class="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    [(ngModel)]="cs.draft().allowSelfSigned"
                    (ngModelChange)="cs.markConfigurationMutated()"
                    class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                  <span class="text-xs font-semibold text-slate-800">
                    Allow Self-Signed / Unverified Server Certificate
                  </span>
                </label>
                @if (cs.draft().allowSelfSigned) {
                  <span class="text-[11px] text-amber-700 pl-6">
                    &bull; Warning: Bypasses strict CA chain validation. Prohibited on Production environments.
                  </span>
                }
              </div>

            </div>
          }

          <!-- ========================================================================= -->
          <!-- MUTUAL TLS (mTLS) - Exposed conditionally when provider supports mTLS    -->
          <!-- ========================================================================= -->
          @if (cs.selectedProvider()?.supportsMtls && cs.draft().tlsMode !== 'DISABLED') {
            <app-accordion
              title="Mutual TLS (mTLS Client Certificate)"
              subtitle="X.509 Client Certificate &amp; Private Key"
              icon="key"
              [isOpen]="false">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-semibold text-slate-700">Client Certificate Reference (.crt / .pem)</label>
                  <input
                    type="text"
                    [(ngModel)]="cs.draft().clientCertRef"
                    (ngModelChange)="cs.markConfigurationMutated()"
                    placeholder="/etc/akaal/certs/client.crt or vault://secret/client_cert"
                    class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600 font-mono" />
                </div>

                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-semibold text-slate-700">Client Private Key Reference (.key)</label>
                  <input
                    type="password"
                    [(ngModel)]="cs.draft().clientPrivateKeyRef"
                    (ngModelChange)="cs.markConfigurationMutated()"
                    placeholder="vault://secret/client_key"
                    class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600 font-mono" />
                </div>
              </div>
            </app-accordion>
          }

        </div>
      }

      <!-- ========================================================================= -->
      <!-- CARD 3: NETWORK ROUTE & TOPOLOGY                                          -->
      <!-- ========================================================================= -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
        <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
          <span class="text-xs font-bold text-slate-900">3. Network Routing Topology</span>
          <span class="text-[11px] text-slate-400 font-normal">Direct, SSH Bastion, PrivateLink, HTTP/SOCKS Proxy</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Route Type Selector -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Network Route <span class="text-rose-500">*</span>
            </label>
            <app-custom-select
              [options]="networkRouteOptions"
              [value]="cs.draft().networkRoute"
              (valueChange)="onRouteTypeChange($event)">
            </app-custom-select>
          </div>

          <!-- Direct Route Summary -->
          @if (cs.draft().networkRoute === 'DIRECT') {
            <div class="flex flex-col justify-center gap-1 p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 text-[11px]">
              <span class="font-semibold text-slate-800">Direct TCP Connection</span>
              <span>Standard routed IP connectivity over corporate VPC peering, private LAN, or container network.</span>
            </div>
          }

          <!-- DNS Happy Eyeballs Summary -->
          @if (cs.draft().networkRoute === 'DNS_HAPPY_EYEBALLS') {
            <div class="flex flex-col justify-center gap-1 p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 text-[11px]">
              <span class="font-semibold text-slate-800">DNS Dual-Stack (RFC 8305)</span>
              <span>Concurrent IPv6/IPv4 connection resolution with automated fast-fallback.</span>
            </div>
          }

        </div>

        <!-- Route 1: SSH Bastion Tunnel -->
        @if (cs.draft().networkRoute === 'SSH_BASTION') {
          <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl space-y-3.5 animate-in fade-in duration-100">
            <span class="text-xs font-bold text-slate-900">SSH Bastion Jump Host Parameters</span>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3.5">
              <div class="flex flex-col gap-1.5 md:col-span-2">
                <label class="text-xs font-semibold text-slate-700">SSH Bastion Host <span class="text-rose-500">*</span></label>
                <input
                  type="text"
                  [(ngModel)]="cs.draft().sshBastionHost"
                  (ngModelChange)="cs.markConfigurationMutated()"
                  placeholder="bastion.prod.company.com"
                  class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">SSH Port</label>
                <input
                  type="number"
                  [(ngModel)]="cs.draft().sshBastionPort"
                  (ngModelChange)="cs.markConfigurationMutated()"
                  placeholder="22"
                  class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-700">SSH Username <span class="text-rose-500">*</span></label>
                <input
                  type="text"
                  [(ngModel)]="cs.draft().sshBastionUsername"
                  (ngModelChange)="cs.markConfigurationMutated()"
                  placeholder="ec2-user or jump_admin"
                  class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
              </div>

              <div class="flex flex-col gap-1.5 md:col-span-2">
                <label class="text-xs font-semibold text-slate-700">SSH Private Key SecretRef</label>
                <input
                  type="password"
                  [(ngModel)]="cs.draft().sshBastionKeyRef"
                  (ngModelChange)="cs.markConfigurationMutated()"
                  placeholder="vault://secret/bastion_key"
                  class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600 font-mono" />
              </div>

              <div class="flex flex-col gap-1.5 md:col-span-3">
                <label class="text-xs font-semibold text-slate-700">SSH Host Key Fingerprint (Pinned SHA-256)</label>
                <input
                  type="text"
                  [(ngModel)]="cs.draft().sshHostKeyFingerprint"
                  (ngModelChange)="cs.markConfigurationMutated()"
                  placeholder="SHA256:4t7a1G8eM2u9... (Fail-closed host attestation)"
                  class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600 font-mono" />
              </div>
            </div>
          </div>
        }

        <!-- Route 2: HTTP / SOCKS5 Proxy -->
        @if (cs.draft().networkRoute === 'HTTP_PROXY' || cs.draft().networkRoute === 'SOCKS5_PROXY') {
          <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl grid grid-cols-1 md:grid-cols-3 gap-3.5 animate-in fade-in duration-100">
            <div class="flex flex-col gap-1.5 md:col-span-2">
              <label class="text-xs font-semibold text-slate-700">Proxy Host <span class="text-rose-500">*</span></label>
              <input
                type="text"
                [(ngModel)]="cs.draft().proxyHost"
                (ngModelChange)="cs.markConfigurationMutated()"
                placeholder="proxy.corp.internal"
                class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-slate-700">Proxy Port</label>
              <input
                type="number"
                [(ngModel)]="cs.draft().proxyPort"
                (ngModelChange)="cs.markConfigurationMutated()"
                [placeholder]="cs.draft().networkRoute === 'HTTP_PROXY' ? '8080' : '1080'"
                class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
            </div>
          </div>
        }

        <!-- Route 3: Private Endpoint -->
        @if (cs.draft().networkRoute === 'PRIVATE_ENDPOINT') {
          <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl flex flex-col gap-1.5 animate-in fade-in duration-100">
            <label class="text-xs font-semibold text-slate-700">AWS PrivateLink / Azure Private Endpoint Identifier <span class="text-rose-500">*</span></label>
            <input
              type="text"
              [(ngModel)]="cs.draft().privateEndpointUrl"
              (ngModelChange)="cs.markConfigurationMutated()"
              placeholder="vpce-0123456789abcdef0.vpce-svc-0123.us-east-1.vpce.amazonaws.com"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600 font-mono" />
          </div>
        }

      </div>

      <!-- ========================================================================= -->
      <!-- CARD 4: ADVANCED NETWORK SETTINGS ACCORDION                               -->
      <!-- ========================================================================= -->
      <app-accordion
        title="Advanced Socket &amp; TCP Keepalive Settings"
        subtitle="Timeouts, Keepalive probes, Idle intervals"
        icon="network"
        [isOpen]="false">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">DNS Resolution Timeout (ms)</label>
            <input
              type="number"
              [(ngModel)]="cs.draft().dnsTimeoutMs"
              placeholder="5000"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Socket Connect Timeout (ms)</label>
            <input
              type="number"
              [(ngModel)]="cs.draft().connectTimeoutMs"
              placeholder="15000"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Socket Read Timeout (ms)</label>
            <input
              type="number"
              [(ngModel)]="cs.draft().socketTimeoutMs"
              placeholder="30000"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
          </div>
        </div>
      </app-accordion>

    </div>
  `
})
export class Step3SecurityComponent {
  public cs = inject(CreateConnectionService);
  public isSecretVisible = signal<boolean>(false);

  public get authMethodOptions(): CustomSelectOption[] {
    const p = this.cs.selectedProvider();
    if (!p) return [{ label: 'Password', value: 'PASSWORD' }];
    return p.authMethods.map(m => ({
      label: m.label,
      value: m.value,
      desc: m.desc
    }));
  }

  public tlsModeOptions: CustomSelectOption[] = [
    { label: 'VERIFY_FULL (Verify CA Chain + SAN Hostname)', value: 'VERIFY_FULL' },
    { label: 'VERIFY_CA (Verify CA Chain Only)', value: 'VERIFY_CA' },
    { label: 'REQUIRED (Enforce TLS Encryption)', value: 'REQUIRED' },
    { label: 'PREFERRED (Allow Plaintext Downgrade Fallback)', value: 'PREFERRED' },
    { label: 'DISABLED (Unencrypted Plaintext Socket)', value: 'DISABLED' }
  ];

  public minTlsOptions: CustomSelectOption[] = [
    { label: 'TLS 1.2 (Standard Enterprise Minimum)', value: 'TLS_1_2' },
    { label: 'TLS 1.3 (Modern Maximum Cipher Security)', value: 'TLS_1_3' }
  ];

  public networkRouteOptions: CustomSelectOption[] = [
    { label: 'Direct TCP Connection (Default Routed IP)', value: 'DIRECT' },
    { label: 'DNS Happy Eyeballs (IPv6/IPv4 Dual-Stack)', value: 'DNS_HAPPY_EYEBALLS' },
    { label: 'SSH Bastion Tunnel (Encrypted Jump Host)', value: 'SSH_BASTION' },
    { label: 'HTTP CONNECT Forward Proxy', value: 'HTTP_PROXY' },
    { label: 'SOCKS5 Network Proxy', value: 'SOCKS5_PROXY' },
    { label: 'Private Endpoint / VPC Link', value: 'PRIVATE_ENDPOINT' }
  ];

  public onAuthMethodChange(val: string): void {
    this.cs.draft().authMethod = val;
    this.cs.markConfigurationMutated();
  }

  public onTlsModeChange(val: string): void {
    this.cs.draft().tlsMode = val as any;
    this.cs.markConfigurationMutated();
  }

  public onMinTlsChange(val: string): void {
    this.cs.draft().minTlsVersion = val as any;
    this.cs.markConfigurationMutated();
  }

  public onRouteTypeChange(val: string): void {
    this.cs.draft().networkRoute = val as any;
    this.cs.markConfigurationMutated();
  }
}
