import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute, RouterLink } from '@angular/router';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';

interface CategoryInfo {
  title: string;
  scope: string;
  icon: string;
  description: string;
  plannedFeatures: string[];
}

const CATEGORY_MAP: Record<string, CategoryInfo> = {
  'runtime-migration': {
    title: 'Runtime & Migration Defaults',
    scope: 'Pipeline Execution & Resource Allocations',
    icon: 'workflow',
    description: 'Workstation and agent runtime execution thresholds, concurrent worker threads, and memory buffer allocations for migration workloads.',
    plannedFeatures: [
      'Default concurrent thread multiplier per migration pipeline',
      'Batch commit cadence and transaction checkpoint intervals',
      'Automatic failure backoff retry thresholds and timeouts',
      'CDC stream buffer memory allocation bounds'
    ]
  },
  'connectors': {
    title: 'Connector Defaults',
    scope: 'Network Topology & Connection Pools',
    icon: 'plug',
    description: 'Workstation baseline connection pooling, TLS cipher suite enforcement, and socket keep-alive defaults for database connectors.',
    plannedFeatures: [
      'Standard pool minimum and maximum socket allocations',
      'Default probe timeout and heartbeat check frequencies',
      'Mutual TLS client certificate selection preferences',
      'Corporate egress proxy routing overrides'
    ]
  },
  'storage': {
    title: 'Storage & Retention',
    scope: 'Local Cache & Temporary File Lifecycles',
    icon: 'hard-drive',
    description: 'Workstation scratch space allocation, local staging disk retention periods, and artifact compression parameters.',
    plannedFeatures: [
      'Maximum local scratch disk allocation before auto-pruning',
      'Temporary artifact retention lifecycle epoch (days)',
      'Zstandard vs Gzip default compression level for dumps',
      'Encrypted local cache storage volume path'
    ]
  },
  'notifications': {
    title: 'Notifications',
    scope: 'Local Desktop & Audio Alerts',
    icon: 'bell',
    description: 'Operating system notification toast permissions, sound cue preferences for barrier blocks, and cutover chime triggers.',
    plannedFeatures: [
      'Desktop native notification banner triggers',
      'Auditory chimes on critical approval barrier pauses',
      'Quiet hours suppression for non-critical alerts',
      'System tray status icon animation preferences'
    ]
  },
  'integrations': {
    title: 'Integrations',
    scope: 'External CLI & Third-Party Workstation Tools',
    icon: 'layers',
    description: 'Local development environment integrations with kubectl, AWS CLI, Azure CLI, gcloud, and local container runtimes.',
    plannedFeatures: [
      'Auto-discovery of local cloud provider CLI credentials',
      'Local Docker and Podman daemon socket path detection',
      'Default external diff and merge tool executable binding',
      'Custom webhook testing payload generator'
    ]
  },
  'ai-intelligence': {
    title: 'AI & Intelligence',
    scope: 'Model Routing & Data Scrubbing Policy',
    icon: 'bot',
    description: 'Workstation generative assistance policies, automated migration schema recommendations, and query optimization guidance.',
    plannedFeatures: [
      'Local vs Enterprise Gateway model endpoint selection',
      'Mandatory client-side schema PII anonymization prior to inference',
      'SQL dialect conversion suggestion confidence threshold',
      'Offline heuristic fallback mode'
    ]
  },
  'logging': {
    title: 'Logging & Diagnostics',
    scope: 'Telemetry Verbosity & Local Log Files',
    icon: 'file-text',
    description: 'Engine log level verbosity, rotation policies for local audit logs, and anonymized diagnostic package export.',
    plannedFeatures: [
      'Workstation log verbosity level (DEBUG, INFO, WARN, ERROR)',
      'Local log file size limits and rotation generation count',
      'Redaction masks for passwords and connection strings in logs',
      'One-click diagnostic support bundle packaging'
    ]
  },
  'advanced': {
    title: 'Advanced',
    scope: 'Developer Flags & Experimental Features',
    icon: 'terminal',
    description: 'Underlying Wails IPC protocol parameters, memory profiling hooks, and feature preview flags.',
    plannedFeatures: [
      'V8 JavaScript engine heap limit overrides',
      'IPC socket connection timeout tuning',
      'Experimental high-throughput pipeline driver enablement',
      'Factory reset of workstation configuration state'
    ]
  }
};

@Component({
  selector: 'app-settings-placeholder',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150 max-w-3xl">
      
      <!-- Category Header -->
      <div class="flex flex-col gap-1 pb-4 border-b border-slate-200">
        <div class="flex items-center gap-2">
          <span class="text-[11px] font-bold text-blue-600 tracking-wider uppercase font-mono">
            {{ info.scope }}
          </span>
          <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
            Future Scope
          </span>
        </div>
        <h2 class="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
          <app-lucide-icon [name]="info.icon" [size]="20" class="text-slate-600"></app-lucide-icon>
          <span>{{ info.title }}</span>
        </h2>
        <p class="text-xs text-slate-500 max-w-2xl leading-relaxed">
          {{ info.description }}
        </p>
      </div>

      <!-- Scope Card -->
      <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-5">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
            <app-lucide-icon name="sparkles" [size]="18"></app-lucide-icon>
          </div>
          <div>
            <h3 class="text-sm font-semibold text-slate-900">Planned Configuration Capabilities</h3>
            <p class="text-xs text-slate-500">This section is preserved structurally and will become active in future releases.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          @for (item of info.plannedFeatures; track item) {
            <div class="p-3 rounded-lg bg-slate-50 border border-slate-200/80 flex items-start gap-2.5">
              <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
              <span class="text-xs text-slate-700 font-medium leading-tight">{{ item }}</span>
            </div>
          }
        </div>
      </div>

      <!-- Return Navigation -->
      <div class="flex items-center gap-3 pt-2">
        <a 
          routerLink="/settings/general"
          class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer shadow-xs">
          <app-lucide-icon name="sliders" [size]="14"></app-lucide-icon>
          <span>Go to General Settings</span>
        </a>

        <a 
          routerLink="/settings/appearance"
          class="h-9 px-4 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer shadow-2xs">
          <app-lucide-icon name="palette" [size]="14"></app-lucide-icon>
          <span>Go to Appearance</span>
        </a>
      </div>

    </div>
  `
})
export class SettingsPlaceholderComponent {
  private route = inject(ActivatedRoute);

  public get categoryKey(): string {
    const url = this.route.snapshot.url;
    return url.length > 0 ? url[0].path : 'runtime-migration';
  }

  public get info(): CategoryInfo {
    return CATEGORY_MAP[this.categoryKey] || {
      title: 'Operational Defaults',
      scope: 'Enterprise Configuration',
      icon: 'workflow',
      description: 'Configuration module scheduled for Part 2 scope.',
      plannedFeatures: ['Custom parameter configuration', 'Workstation tuning']
    };
  }
}
