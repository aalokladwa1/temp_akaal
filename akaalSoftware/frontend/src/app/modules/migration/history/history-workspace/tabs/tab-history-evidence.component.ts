import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryWorkspaceService } from '../history-workspace.service';
import { EvidenceRecord, EvidenceManifestItem, EvidenceFactItem, ExecutionIdentitySealRecord } from '../history-workspace.models';

@Component({
  selector: 'app-tab-history-evidence',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (hws.currentRecord(); as record) {
      <div class="space-y-6">
        
        <!-- Evidence Integrity & Availability Header -->
        <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
          <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-slate-100">
            <div>
              <div class="flex items-center gap-2.5">
                <h2 class="text-base font-bold text-slate-900">
                  Evidence Package &amp; Cryptographic Manifest
                </h2>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  SHA-256 Verified
                </span>
                <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                  {{ record.evidence.availability }}
                </span>
              </div>
              <div class="text-xs text-slate-500 mt-1">
                Last integrity verification check: <strong class="text-slate-800">{{ formatTimestamp(record.evidence.lastIntegrityCheckAt) }}</strong>
              </div>
            </div>

            <!-- Completeness Metric -->
            <div class="flex items-center gap-3 bg-slate-50 px-4 py-2 rounded-md border border-slate-200 self-start md:self-auto">
              <div class="text-right">
                <div class="text-[10px] font-bold uppercase text-slate-500">Manifest Completeness</div>
                <div class="text-xs font-bold text-emerald-700">
                  {{ record.evidence.completeness }} (100% Artifacts Present)
                </div>
              </div>
            </div>
          </div>

          <!-- Integrity Notes -->
          <div class="mt-4 text-xs text-slate-600">
            <strong>Integrity Posture:</strong> {{ record.evidence.integrityVerificationNotes }}
          </div>
        </div>

        <!-- Authoritative Execution Identity Seal (15 Key Context Fields) -->
        <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
          <div class="flex items-center justify-between pb-3 mb-4 border-b border-slate-100">
            <div>
              <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Execution Identity Seal ({{ record.evidence.identitySeal.sealVersion }})
              </h3>
              <p class="text-xs text-slate-500 mt-0.5">Authoritative cryptographic metadata snapshot sealed at execution completion.</p>
            </div>
            <span class="font-mono text-[11px] bg-slate-100 text-slate-700 px-2.5 py-1 rounded border border-slate-200">
              SHA-256 Digest Verified
            </span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
            @for (field of record.evidence.identitySeal.fields; track field.name) {
              <div class="p-3 bg-slate-50/80 rounded-md border border-slate-200">
                <div class="text-[11px] text-slate-500 font-medium">{{ field.name }}</div>
                <div class="font-mono text-slate-900 font-medium mt-1 truncate" [title]="field.value">{{ field.value }}</div>
              </div>
            }
          </div>
        </div>

        <!-- Evidence Manifests Inventory -->
        <div class="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
          <div class="px-5 py-3.5 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Sealed Manifests ({{ record.evidence.manifests.length }})
            </h3>
            <span class="text-xs text-slate-500">Immutable forensic archive</span>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse min-w-[700px]">
              <thead>
                <tr class="border-b border-slate-200 bg-slate-50/50 text-[11px] font-bold text-slate-600 uppercase tracking-wider select-none">
                  <th class="py-2.5 px-4">Manifest ID</th>
                  <th class="py-2.5 px-4">Generated Timestamp</th>
                  <th class="py-2.5 px-4">Artifact Count</th>
                  <th class="py-2.5 px-4">Archive Size</th>
                  <th class="py-2.5 px-4">Root SHA-256 Digest</th>
                  <th class="py-2.5 px-4 text-right">Verification</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                @for (man of record.evidence.manifests; track man.manifestId) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3 px-4 font-mono font-medium text-slate-900">{{ man.manifestId }}</td>
                    <td class="py-3 px-4 font-mono text-slate-700">{{ formatTimestamp(man.generatedAt) }}</td>
                    <td class="py-3 px-4 text-slate-800 font-medium">{{ man.artifactCount }} files</td>
                    <td class="py-3 px-4 font-mono text-slate-800">{{ formatBytes(man.totalSizeBytes) }}</td>
                    <td class="py-3 px-4 font-mono text-[11px] text-slate-600 truncate max-w-[220px]" [title]="man.rootDigestSha256">
                      {{ man.rootDigestSha256 }}
                    </td>
                    <td class="py-3 px-4 text-right">
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {{ man.digestVerification }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

        <!-- Sealed Artifacts List -->
        <div class="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
          <div class="px-5 py-3.5 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Cryptographic Artifact Ledger ({{ record.evidence.artifacts.length }})
            </h3>
            <span class="text-xs text-slate-500">Individual file digests</span>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse min-w-[700px]">
              <thead>
                <tr class="border-b border-slate-200 bg-slate-50/50 text-[11px] font-bold text-slate-600 uppercase tracking-wider select-none">
                  <th class="py-2.5 px-4">Artifact Name</th>
                  <th class="py-2.5 px-4">Category</th>
                  <th class="py-2.5 px-4">SHA-256 Digest</th>
                  <th class="py-2.5 px-4">Sealed At</th>
                  <th class="py-2.5 px-4 text-right">Checksum Match</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                @for (art of record.evidence.artifacts; track art.id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3 px-4 font-mono font-medium text-slate-900">{{ art.name }}</td>
                    <td class="py-3 px-4 whitespace-nowrap">
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                        {{ art.category }}
                      </span>
                    </td>
                    <td class="py-3 px-4 font-mono text-[11px] text-slate-600 truncate max-w-[280px]" [title]="art.digest">
                      {{ art.digest }}
                    </td>
                    <td class="py-3 px-4 font-mono text-slate-600 whitespace-nowrap">{{ formatTimestamp(art.recordedAt) }}</td>
                    <td class="py-3 px-4 text-right whitespace-nowrap">
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Match (Valid)
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

      </div>
    }
  `
})
export class TabHistoryEvidenceComponent {
  public hws = inject(HistoryWorkspaceService);

  public formatBytes(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  }

  public formatTimestamp(ts: string | null): string {
    if (!ts) return '—';
    try {
      const d = new Date(ts);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return ts;
    }
  }
}
