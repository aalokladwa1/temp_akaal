import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-lucide-icon',
  standalone: true,
  imports: [CommonModule],
  host: {
    class: 'inline-flex items-center justify-center shrink-0 leading-none align-middle'
  },
  template: `
    <svg
      xmlns="http://www.w3.org/2000/svg"
      [attr.width]="size"
      [attr.height]="size"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      [attr.stroke-width]="strokeWidth"
      stroke-linecap="round"
      stroke-linejoin="round"
      [class]="class"
      class="shrink-0 transition-colors block">
      
      @switch (name) {
        @case ('search') {
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.3-4.3"/>
        }
        @case ('bell') {
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>
        }
        @case ('user-round') {
          <circle cx="12" cy="8" r="5"/>
          <path d="M20 21a8 8 0 0 0-16 0"/>
        }
        @case ('chevron-down') {
          <path d="m6 9 6 6 6-6"/>
        }
        @case ('chevron-up') {
          <path d="m18 15-6-6-6 6"/>
        }
        @case ('chevron-right') {
          <path d="m9 18 6-6-6-6"/>
        }
        @case ('chevron-left') {
          <path d="m15 18-6-6 6-6"/>
        }
        @case ('building-2') {
          <path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/>
          <path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/>
          <path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/>
          <path d="M10 6h4"/>
          <path d="M10 10h4"/>
          <path d="M10 14h4"/>
          <path d="M10 18h4"/>
        }
        @case ('panels-top-left') {
          <rect width="18" height="18" x="3" y="3" rx="2"/>
          <path d="M3 9h18"/>
          <path d="M9 21V9"/>
        }
        @case ('layout-dashboard') {
          <rect width="7" height="9" x="3" y="3" rx="1"/>
          <rect width="7" height="5" x="14" y="3" rx="1"/>
          <rect width="7" height="9" x="14" y="12" rx="1"/>
          <rect width="7" height="5" x="3" y="16" rx="1"/>
        }
        @case ('arrow-left-right') {
          <path d="M8 3 4 7l4 4"/>
          <path d="M4 7h16"/>
          <path d="m16 21 4-4-4-4"/>
          <path d="M20 17H4"/>
        }
        @case ('arrow-right') {
          <path d="M5 12h14"/>
          <path d="m12 5 7 7-7 7"/>
        }
        @case ('arrow-left') {
          <path d="m12 19-7-7 7-7"/>
          <path d="M19 12H5"/>
        }
        @case ('activity') {
          <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
        }
        @case ('file-text') {
          <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
          <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
          <path d="M10 9H8"/>
          <path d="M16 13H8"/>
          <path d="M16 17H8"/>
        }
        @case ('shield') {
          <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>
        }
        @case ('shield-check') {
          <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>
          <path d="m9 12 2 2 4-4"/>
        }
        @case ('shield-alert') {
          <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>
          <path d="M12 8v4"/>
          <path d="M12 16h.01"/>
        }
        @case ('settings') {
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
          <circle cx="12" cy="12" r="3"/>
        }
        @case ('panel-left-close') {
          <rect width="18" height="18" x="3" y="3" rx="2"/>
          <path d="M9 3v18"/>
          <path d="m16 15-3-3 3-3"/>
        }
        @case ('panel-left-open') {
          <rect width="18" height="18" x="3" y="3" rx="2"/>
          <path d="M9 3v18"/>
          <path d="m14 9 3 3-3 3"/>
        }
        @case ('circle-check') {
          <circle cx="12" cy="12" r="10"/>
          <path d="m9 12 2 2 4-4"/>
        }
        @case ('check-circle') {
          <circle cx="12" cy="12" r="10"/>
          <path d="m9 12 2 2 4-4"/>
        }
        @case ('check-circle-2') {
          <circle cx="12" cy="12" r="10"/>
          <path d="m9 12 2 2 4-4"/>
        }
        @case ('check') {
          <path d="M20 6 9 17l-5-5"/>
        }
        @case ('circle-x') {
          <circle cx="12" cy="12" r="10"/>
          <path d="m15 9-6 6"/>
          <path d="m9 9 6 6"/>
        }
        @case ('circle-alert') {
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" x2="12" y1="8" y2="12"/>
          <line x1="12" x2="12.01" y1="16" y2="16"/>
        }
        @case ('alert-circle') {
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" x2="12" y1="8" y2="12"/>
          <line x1="12" x2="12.01" y1="16" y2="16"/>
        }
        @case ('info') {
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 16v-4"/>
          <path d="M12 8h.01"/>
        }
        @case ('edit-3') {
          <path d="M12 20h9"/>
          <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
        }
        @case ('triangle-alert') {
          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
          <line x1="12" x2="12" y1="9" y2="13"/>
          <line x1="12" x2="12.01" y1="17" y2="17"/>
        }
        @case ('alert-triangle') {
          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
          <line x1="12" x2="12" y1="9" y2="13"/>
          <line x1="12" x2="12.01" y1="17" y2="17"/>
        }
        @case ('plus-circle') {
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 12h8"/>
          <path d="M12 8v8"/>
        }
        @case ('folder') {
          <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>
        }
        @case ('folder-git-2') {
          <path d="M9 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v2"/>
          <circle cx="13" cy="12" r="2"/>
          <circle cx="13" cy="18" r="2"/>
          <circle cx="19" cy="15" r="2"/>
          <path d="M13 14v2"/>
          <path d="m14.5 13.5 3 1"/>
        }
        @case ('file-code') {
          <path d="M10 12.5 8 15l2 2.5"/>
          <path d="m14 12.5 2 2.5-2 2.5"/>
          <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
          <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
        }
        @case ('file-code-2') {
          <path d="M4 22h14a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v4"/>
          <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
          <path d="m5 12-3 3 3 3"/>
          <path d="m9 18 3-3-3-3"/>
        }
        @case ('history') {
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
          <path d="M3 3v5h5"/>
          <path d="M12 7v5l4 2"/>
        }
        @case ('database') {
          <ellipse cx="12" cy="5" rx="9" ry="3"/>
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
          <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>
        }
        @case ('server') {
          <rect width="20" height="8" x="2" y="2" rx="2" ry="2"/>
          <rect width="20" height="8" x="2" y="14" rx="2" ry="2"/>
          <line x1="6" x2="6.01" y1="6" y2="6"/>
          <line x1="6" x2="6.01" y1="18" y2="18"/>
        }
        @case ('cpu') {
          <rect width="16" height="16" x="4" y="4" rx="2"/>
          <rect width="6" height="6" x="9" y="9" rx="1"/>
          <path d="M15 2v2"/>
          <path d="M15 20v2"/>
          <path d="M2 15h2"/>
          <path d="M2 9h2"/>
          <path d="M20 15h2"/>
          <path d="M20 9h2"/>
          <path d="M9 2v2"/>
          <path d="M9 20v2"/>
        }
        @case ('refresh-cw') {
          <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
          <path d="M21 3v5h-5"/>
          <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
          <path d="M8 16H3v5"/>
        }
        @case ('sliders') {
          <line x1="4" x2="4" y1="21" y2="14"/>
          <line x1="4" x2="4" y1="10" y2="3"/>
          <line x1="12" x2="12" y1="21" y2="12"/>
          <line x1="12" x2="12" y1="8" y2="3"/>
          <line x1="20" x2="20" y1="21" y2="16"/>
          <line x1="20" x2="20" y1="12" y2="3"/>
          <line x1="1" x2="7" y1="14" y2="14"/>
          <line x1="9" x2="15" y1="8" y2="8"/>
          <line x1="17" x2="23" y1="16" y2="16"/>
        }
        @case ('sliders-horizontal') {
          <line x1="21" x2="14" y1="4" y2="4"/>
          <line x1="10" x2="3" y1="4" y2="4"/>
          <line x1="21" x2="12" y1="12" y2="12"/>
          <line x1="8" x2="3" y1="12" y2="12"/>
          <line x1="21" x2="16" y1="20" y2="20"/>
          <line x1="12" x2="3" y1="20" y2="20"/>
          <line x1="14" x2="14" y1="2" y2="6"/>
          <line x1="8" x2="8" y1="10" y2="14"/>
          <line x1="16" x2="16" y1="18" y2="22"/>
        }
        @case ('settings-2') {
          <path d="M20 7h-9"/>
          <path d="M14 17H5"/>
          <circle cx="17" cy="17" r="3"/>
          <circle cx="7" cy="7" r="3"/>
        }
        @case ('gauge') {
          <path d="m12 14 4-4"/>
          <path d="M3.34 19a10 10 0 1 1 17.32 0"/>
        }
        @case ('x') {
          <path d="M18 6 6 18"/>
          <path d="m6 6 12 12"/>
        }
        @case ('check') {
          <path d="M20 6 9 17l-5-5"/>
        }
        @case ('plus') {
          <path d="M5 12h14"/>
          <path d="M12 5v14"/>
        }
        @case ('play') {
          <polygon points="6 3 20 12 6 21 6 3"/>
        }
        @case ('save') {
          <path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/>
          <path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/>
          <path d="M7 3v4a1 1 0 0 0 1 1h7"/>
        }
        @case ('pause') {
          <rect width="4" height="16" x="6" y="4"/>
          <rect width="4" height="16" x="14" y="4"/>
        }
        @case ('square') {
          <rect width="18" height="18" x="3" y="3" rx="2"/>
        }
        @case ('rotate-ccw') {
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
          <path d="M3 3v5h5"/>
        }
        @case ('lock') {
          <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        }
        @case ('unlock') {
          <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 9.9-1"/>
        }
        @case ('loader-2') {
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        }
        @case ('circle') {
          <circle cx="12" cy="12" r="10"/>
        }
        @case ('workflow') {
          <rect width="8" height="8" x="3" y="3" rx="2"/>
          <path d="M7 11v4a2 2 0 0 0 2 2h4"/>
          <rect width="8" height="8" x="13" y="13" rx="2"/>
        }
        @case ('git-branch') {
          <line x1="6" x2="6" y1="3" y2="15"/>
          <circle cx="18" cy="6" r="3"/>
          <circle cx="6" cy="18" r="3"/>
          <path d="M18 9a9 9 0 0 1-9 9"/>
        }
        @case ('columns-3') {
          <rect width="18" height="18" x="3" y="3" rx="2"/>
          <path d="M9 3v18"/>
          <path d="M15 3v18"/>
        }
        @case ('layers') {
          <path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/>
          <path d="m22 12.5-8.58 3.91a2 2 0 0 1-1.66 0L2 12.5"/>
          <path d="m22 17.5-8.58 3.91a2 2 0 0 1-1.66 0L2 17.5"/>
        }
        @case ('microscope') {
          <path d="M6 18h8"/>
          <path d="M3 22h18"/>
          <path d="M14 22a7 7 0 1 0 0-14h-1"/>
          <path d="M9 14h2"/>
          <path d="M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z"/>
          <path d="M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3"/>
        }
        @case ('radar') {
          <path d="M19.07 4.93A10 10 0 0 0 6.99 3.34"/>
          <path d="M4 6h.01"/>
          <path d="M2.29 9.62A10 10 0 1 0 21.31 8.35"/>
          <path d="M16.24 7.76A6 6 0 1 0 8.23 16.24"/>
          <path d="M12 18h.01"/>
          <path d="M17.99 11.66A6 6 0 0 1 15.77 14.24"/>
          <circle cx="12" cy="12" r="2"/>
          <path d="m13.41 10.59 5.66-5.66"/>
        }
        @case ('compass') {
          <circle cx="12" cy="12" r="10"/>
          <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>
        }
        @case ('folder-open') {
          <path d="m6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5c0-1.1.9-2 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2"/>
        }
        @case ('table-2') {
          <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18"/>
        }
        @case ('box') {
          <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>
          <path d="m3.3 7 8.7 5 8.7-5"/>
          <path d="M12 22V12"/>
        }
        @case ('code-2') {
          <path d="m18 16 4-4-4-4"/>
          <path d="m6 8-4 4 4 4"/>
          <path d="m14.5 4-5 16"/>
        }
        @case ('scan') {
          <path d="M3 7V5a2 2 0 0 1 2-2h2"/>
          <path d="M17 3h2a2 2 0 0 1 2 2v2"/>
          <path d="M21 17v2a2 2 0 0 1-2 2h-2"/>
          <path d="M7 21H5a2 2 0 0 1-2-2v-2"/>
        }
        @case ('refresh-cw') {
          <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
          <path d="M21 3v5h-5"/>
          <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
          <path d="M8 16H3v5"/>
        }
        @case ('lock') {
          <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        }
        @case ('unlock') {
          <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 9.9-1"/>
        }
        @case ('shield-alert') {
          <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>
          <path d="M12 8v4"/>
          <path d="M12 16h.01"/>
        }
        @case ('grid-2x2') {
          <rect width="18" height="18" x="3" y="3" rx="2"/>
          <path d="M3 12h18"/>
          <path d="M12 3v18"/>
        }
        @case ('table-properties') {
          <path d="M15 3v18"/>
          <rect width="18" height="18" x="3" y="3" rx="2"/>
          <path d="M21 9H3"/>
          <path d="M21 15H3"/>
        }
        @case ('file-diff') {
          <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
          <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
          <path d="M9 10h6"/>
          <path d="M12 13V7"/>
          <path d="M9 17h6"/>
        }
        @case ('trash-2') {
          <path d="M3 6h18"/>
          <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>
          <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
          <line x1="10" x2="10" y1="11" y2="17"/>
          <line x1="14" x2="14" y1="11" y2="17"/>
        }
        @case ('archive') {
          <rect width="20" height="5" x="2" y="3" rx="1"/>
          <path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/>
          <path d="M10 12h4"/>
        }
        @case ('clock') {
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        }
        @case ('calendar') {
          <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
          <line x1="16" x2="16" y1="2" y2="6"/>
          <line x1="8" x2="8" y1="2" y2="6"/>
          <line x1="3" x2="21" y1="10" y2="10"/>
        }
        @case ('sparkles') {
          <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275Z"/>
        }
        @case ('key') {
          <path d="m15.5 7.5 2.3 2.3a1 1 0 0 0 1.4 0l2.1-2.1a1 1 0 0 0 0-1.4L19 4"/>
          <path d="m21 2-9.6 9.6"/>
          <circle cx="7.5" cy="16.5" r="5.5"/>
        }
        @case ('eye') {
          <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
          <circle cx="12" cy="12" r="3"/>
        }
        @case ('eye-off') {
          <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/>
          <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/>
          <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/>
          <line x1="2" x2="22" y1="2" y2="22"/>
        }
        @case ('copy') {
          <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
          <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
        }
        @case ('hard-drive') {
          <line x1="12" x2="12.01" y1="18" y2="18"/>
          <rect width="20" height="8" x="2" y="14" rx="2"/>
          <path d="M6 14v-4a6 6 0 0 1 12 0v4"/>
        }
        @case ('arrow-up-right') {
          <path d="M7 7h10v10"/>
          <path d="M7 17 17 7"/>
        }
        @case ('alert-octagon') {
          <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/>
          <line x1="12" x2="12" y1="8" y2="12"/>
          <line x1="12" x2="12.01" y1="16" y2="16"/>
        }
        @case ('minimize-2') {
          <polyline points="5 15 3 15 3 21 9 21 9 19"/>
          <polyline points="19 9 21 9 21 3 15 3 15 5"/>
          <line x1="3" x2="9" y1="21" y2="15"/>
          <line x1="21" x2="15" y1="3" y2="9"/>
        }
        @case ('maximize-2') {
          <polyline points="15 3 21 3 21 9"/>
          <polyline points="9 21 3 21 3 15"/>
          <line x1="21" x2="14" y1="3" y2="10"/>
          <line x1="3" x2="10" y1="21" y2="14"/>
        }
        @case ('pen-tool') {
          <path d="m12 19 7-7 3 3-7 7-3-3z"/>
          <path d="m18 13-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/>
          <path d="m2 2 7.586 7.586"/>
          <circle cx="11" cy="11" r="2"/>
        }
        @case ('pencil') {
          <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
          <path d="m15 5 4 4"/>
        }
        @case ('external-link') {
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
          <polyline points="15 3 21 3 21 9"/>
          <line x1="10" x2="21" y1="14" y2="3"/>
        }
        @case ('zap') {
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
        }
        @case ('plug') {
          <path d="M12 22v-5"/>
          <path d="M9 8V2"/>
          <path d="M15 8V2"/>
          <path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>
        }
        @case ('table') {
          <path d="M12 3v18"/>
          <rect width="18" height="18" x="3" y="3" rx="2"/>
          <path d="M3 9h18"/>
          <path d="M3 15h18"/>
        }
        @case ('package') {
          <path d="m7.5 4.27 9 5.15"/>
          <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>
          <path d="m3.3 7 8.7 5 8.7-5"/>
          <path d="M12 22V12"/>
        }
        @case ('filter') {
          <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
        }
        @case ('hash') {
          <line x1="4" x2="20" y1="9" y2="9"/>
          <line x1="4" x2="20" y1="15" y2="15"/>
          <line x1="10" x2="8" y1="3" y2="21"/>
          <line x1="16" x2="14" y1="3" y2="21"/>
        }
        @case ('sliders-horizontal') {
          <line x1="21" x2="14" y1="4" y2="4"/>
          <line x1="10" x2="3" y1="4" y2="4"/>
          <line x1="21" x2="12" y1="12" y2="12"/>
          <line x1="8" x2="3" y1="12" y2="12"/>
          <line x1="21" x2="16" y1="20" y2="20"/>
          <line x1="12" x2="3" y1="20" y2="20"/>
          <line x1="14" x2="14" y1="2" y2="6"/>
          <line x1="8" x2="8" y1="10" y2="14"/>
          <line x1="16" x2="16" y1="18" y2="22"/>
        }
        @case ('code') {
          <polyline points="16 18 22 12 16 6"/>
          <polyline points="8 6 2 12 8 18"/>
        }
        @case ('check-square') {
          <polyline points="9 11 12 14 22 4"/>
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
        }
        @case ('minus-square') {
          <rect width="18" height="18" x="3" y="3" rx="2"/>
          <line x1="8" x2="16" y1="12" y2="12"/>
        }
        @case ('list') {
          <line x1="8" x2="21" y1="6" y2="6"/>
          <line x1="8" x2="21" y1="12" y2="12"/>
          <line x1="8" x2="21" y1="18" y2="18"/>
          <line x1="3" x2="3.01" y1="6" y2="6"/>
          <line x1="3" x2="3.01" y1="12" y2="12"/>
          <line x1="3" x2="3.01" y1="18" y2="18"/>
        }
        @case ('list-ordered') {
          <line x1="10" x2="21" y1="6" y2="6"/>
          <line x1="10" x2="21" y1="12" y2="12"/>
          <line x1="10" x2="21" y1="18" y2="18"/>
          <path d="M4 6h1v4"/>
          <path d="M4 10h2"/>
          <path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/>
        }
        @case ('list-tree') {
          <path d="M21 12h-8"/>
          <path d="M21 6H8"/>
          <path d="M21 18h-8"/>
          <path d="M3 6v4c0 1.1.9 2 2 2h3"/>
          <path d="M3 10v6c0 1.1.9 2 2 2h3"/>
        }
        @case ('bar-chart-2') {
          <line x1="18" x2="18" y1="20" y2="10"/>
          <line x1="12" x2="12" y1="20" y2="4"/>
          <line x1="6" x2="6" y1="20" y2="14"/>
        }
        @case ('bar-chart-3') {
          <path d="M3 3v18h18"/>
          <path d="M18 17V9"/>
          <path d="M13 17V5"/>
          <path d="M8 17v-3"/>
        }
        @case ('palette') {
          <circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/>
          <circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/>
          <circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/>
          <circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/>
          <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>
        }
        @case ('folder-kanban') {
          <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>
          <path d="M8 10v4"/>
          <path d="M12 10v2"/>
          <path d="M16 10v6"/>
        }
        @case ('folder-plus') {
          <path d="M12 10v6"/>
          <path d="M9 13h6"/>
          <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>
        }
        @case ('more-horizontal') {
          <circle cx="12" cy="12" r="1"/>
          <circle cx="19" cy="12" r="1"/>
          <circle cx="5" cy="12" r="1"/>
        }
        @case ('ellipsis') {
          <circle cx="12" cy="12" r="1"/>
          <circle cx="19" cy="12" r="1"/>
          <circle cx="5" cy="12" r="1"/>
        }
        @case ('more-vertical') {
          <circle cx="12" cy="12" r="1"/>
          <circle cx="12" cy="5" r="1"/>
          <circle cx="12" cy="19" r="1"/>
        }
        @case ('file-down') {
          <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
          <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
          <path d="M12 18v-6"/>
          <path d="m9 15 3 3 3-3"/>
        }
        @case ('file-spreadsheet') {
          <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
          <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
          <path d="M8 13h2"/>
          <path d="M14 13h2"/>
          <path d="M8 17h2"/>
          <path d="M14 17h2"/>
        }
        @case ('boxes') {
          <path d="M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 .97 1.71l3 1.8a2 2 0 0 0 2.06 0L12 19v-5.5l-5-3-4.03 2.42Z"/>
          <path d="m7 16.5-4.74-2.85"/>
          <path d="m7 16.5 5-3"/>
          <path d="M7 16.5v5.17"/>
          <path d="M12 13.5V19l3.97 2.38a2 2 0 0 0 2.06 0l3-1.8a2 2 0 0 0 .97-1.71v-3.24a2 2 0 0 0-.97-1.71L17 10.5l-5 3Z"/>
          <path d="m17 16.5-5-3"/>
          <path d="m17 16.5 4.74-2.85"/>
          <path d="M17 16.5v5.17"/>
          <path d="M7.97 4.42A2 2 0 0 0 7 6.13v4.37l5 3 5-3V6.13a2 2 0 0 0-.97-1.71l-3-1.8a2 2 0 0 0-2.06 0l-3 1.8Z"/>
          <path d="M12 8 7.26 5.15"/>
          <path d="m12 8 4.74-2.85"/>
          <path d="M12 13.5V8"/>
        }
        @case ('radio') {
          <path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/>
          <path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/>
          <circle cx="12" cy="12" r="2"/>
          <path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/>
          <path d="M19.1 4.9C23 8.8 23 15.1 19.1 19"/>
        }
        @case ('network') {
          <rect x="16" y="16" width="6" height="6" rx="1"/>
          <rect x="2" y="16" width="6" height="6" rx="1"/>
          <rect x="9" y="2" width="6" height="6" rx="1"/>
          <path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/>
          <path d="M12 12V8"/>
        }
        @case ('cloud') {
          <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
        }
        @case ('server') {
          <rect width="20" height="8" x="2" y="2" rx="2" ry="2"/>
          <rect width="20" height="8" x="2" y="14" rx="2" ry="2"/>
          <line x1="6" x2="6.01" y1="6" y2="6"/>
          <line x1="6" x2="6.01" y1="18" y2="18"/>
        }
        @case ('check-circle-2') {
          <circle cx="12" cy="12" r="10"/>
          <path d="m9 12 2 2 4-4"/>
        }
        @case ('x-circle') {
          <circle cx="12" cy="12" r="10"/>
          <path d="m15 9-6 6"/>
          <path d="m9 9 6 6"/>
        }
        @case ('alert-triangle') {
          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
          <line x1="12" x2="12" y1="9" y2="13"/>
          <line x1="12" x2="12.01" y1="17" y2="17"/>
        }
        @case ('alert-circle') {
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" x2="12" y1="8" y2="12"/>
          <line x1="12" x2="12.01" y1="16" y2="16"/>
        }
        @case ('key') {
          <circle cx="7.5" cy="15.5" r="5.5"/>
          <path d="m21 2-9.6 9.6"/>
          <path d="m15.5 7.5 3 3L22 7l-3-3"/>
        }
        @case ('link-2') {
          <path d="M9 17H7A5 5 0 0 1 7 7h2"/>
          <path d="M15 7h2a5 5 0 1 1 0 10h-2"/>
          <line x1="8" x2="16" y1="12" y2="12"/>
        }
        @case ('zoom-in') {
          <circle cx="11" cy="11" r="8"/>
          <line x1="21" x2="16.65" y1="21" y2="16.65"/>
          <line x1="11" x2="11" y1="8" y2="14"/>
          <line x1="8" x2="14" y1="11" y2="11"/>
        }
        @case ('zoom-out') {
          <circle cx="11" cy="11" r="8"/>
          <line x1="21" x2="16.65" y1="21" y2="16.65"/>
          <line x1="8" x2="14" y1="11" y2="11"/>
        }
        @case ('users') {
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
          <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        }
        @case ('git-commit') {
          <circle cx="12" cy="12" r="3"/>
          <line x1="3" x2="9" y1="12" y2="12"/>
          <line x1="15" x2="21" y1="12" y2="12"/>
        }
        @case ('shield-x') {
          <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>
          <path d="m14.5 9.5-5 5"/>
          <path d="m9.5 9.5 5 5"/>
        }
        @case ('shield-plus') {
          <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>
          <path d="M9 12h6"/>
          <path d="M12 9v6"/>
        }
        @case ('git-compare') {
          <circle cx="18" cy="18" r="3"/>
          <circle cx="6" cy="6" r="3"/>
          <path d="M13 6h3a2 2 0 0 1 2 2v7"/>
          <path d="M11 18H8a2 2 0 0 1-2-2V9"/>
        }
        @case ('git-fork') {
          <circle cx="12" cy="18" r="3"/>
          <circle cx="6" cy="6" r="3"/>
          <circle cx="18" cy="6" r="3"/>
          <path d="M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9"/>
          <path d="M12 12v3"/>
        }
        @case ('fingerprint') {
          <path d="M12 10a2 2 0 0 0-2 2c0 1.02-.1 2.51-.26 4"/>
          <path d="M14 13.12c0 2.38 0 6.38-1 8.88"/>
          <path d="M17.29 21.02c.12-.6.43-2.3.5-3.02"/>
          <path d="M2 12a10 10 0 0 1 18-6"/>
          <path d="M2 16h.01"/>
          <path d="M21.8 16c.2-2 .131-5.354 0-6"/>
          <path d="M5 19.5C5.5 18 6 15 6 12a6 6 0 0 1 .34-2"/>
          <path d="M8.65 22c.21-.66.45-1.32.57-2"/>
          <path d="M9 6.8a6 6 0 0 1 9 5.2v2"/>
        }
        @case ('wrench') {
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
        }
        @case ('upload') {
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" x2="12" y1="3" y2="15"/>
        }
        @case ('flag') {
          <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
          <line x1="4" x2="4" y1="22" y2="15"/>
        }
        @case ('split') {
          <path d="M16 3h5v5"/>
          <path d="M8 3H3v5"/>
          <path d="M12 22v-8.3a4 4 0 0 0-1.172-2.872L3 3"/>
          <path d="m15 9 6-6"/>
        }
        @case ('file') {
          <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
          <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
        }
        @case ('folder-tree') {
          <path d="M20 10a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-2.5a1 1 0 0 1-.8-.4l-.9-1.2A1 1 0 0 0 15 3h-2a1 1 0 0 0-1 1v6"/>
          <path d="M4 13a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1H2.5a1 1 0 0 1-.8-.4l-.9-1.2A1 1 0 0 0 0 3H-2"/>
          <path d="M3 21h18"/>
          <path d="M5 21v-7"/>
          <path d="M19 21v-7"/>
        }
        @case ('bookmark') {
          <path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>
        }
        @case ('layout-template') {
          <rect width="18" height="7" x="3" y="3" rx="1"/>
          <rect width="9" height="7" x="3" y="14" rx="1"/>
          <rect width="5" height="7" x="16" y="14" rx="1"/>
        }
        @case ('help-circle') {
          <circle cx="12" cy="12" r="10"/>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
          <path d="M12 17h.01"/>
        }
        @case ('circle-help') {
          <circle cx="12" cy="12" r="10"/>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
          <path d="M12 17h.01"/>
        }
        @case ('download') {
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" x2="12" y1="15" y2="3"/>
        }
        @default {
          <circle cx="12" cy="12" r="9"/>
        }
      }
    </svg>
  `
})
export class LucideIconComponent {
  @Input() public name: string = 'circle';
  @Input() public size: number = 16;
  @Input() public strokeWidth: number = 2;
  @Input() public class: string = '';
}
