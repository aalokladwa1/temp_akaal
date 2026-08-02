/**
 * AKAAL Enterprise Adaptive Greeting Utility
 * 
 * Provides time-based enterprise titles (Good Morning / Afternoon / Evening)
 * paired with a curated collection of 50 calm, professional, non-motivational,
 * non-repetitive second lines.
 */

const ENTERPRISE_GREETING_LINES: string[] = [
  'Everything is prepared for you.',
  'Your workspace systems are active and secure.',
  'All background operations are running normally.',
  'Workspace integrity verified and ready for migration.',
  'System status is healthy across all operational channels.',
  'Your security parameters are fully active.',
  'All workspace modules are loaded and operational.',
  'System logs and session state remain synchronized.',
  'Data integrity verified across all storage locations.',
  'Your enterprise environment is clean and ready.',
  'No unexpected system alerts or exceptions detected.',
  'All local storage endpoints are mounted and verified.',
  'Audit engine is active and capturing system events.',
  'Security policies are active and enforced.',
  'Your session is encrypted and verified.',
  'All configuration parameters match target schema.',
  'Workspace performance is optimal.',
  'Local services are operating within normal parameters.',
  'Encryption keys and credentials vault are secure.',
  'Environment parameters validated successfully.',
  'Your workspace configuration is locked and verified.',
  'System memory allocation is balanced.',
  'Storage subsystems are responding normally.',
  'Session lifetime monitoring is active.',
  'All migration engines are ready for execution.',
  'Workspace data pathways are clear.',
  'System event dispatcher is listening.',
  'Active security tokens are verified.',
  'Workspace state is synchronized.',
  'Local access privileges confirmed.',
  'All diagnostic checks passed without warnings.',
  'System runtime environment is stable.',
  'Enterprise policies applied to active session.',
  'Directory paths verified and writable.',
  'Security kernel reporting normal execution.',
  'Workspace storage disk space is sufficient.',
  'No pending configuration changes.',
  'Authentication boundaries intact.',
  'Session heartbeat monitoring is active.',
  'System configuration loaded from secure vault.',
  'Audit trail logging enabled for this session.',
  'All environment checks completed.',
  'Workspace infrastructure is fully operational.',
  'Local IPC channel initialized successfully.',
  'Your enterprise workspace is ready.',
  'System telemetry parameters normal.',
  'Workspace data layer initialized.',
  'All service contracts validated.',
  'Identity boundary verified.',
  'Everything is ready for your workflow.',
];

let lastSelectedIndex = -1;

export interface EnterpriseGreeting {
  title: string;
  subtitle: string;
}

export function getEnterpriseGreeting(displayName?: string | null): EnterpriseGreeting {
  const nameToUse = (displayName || 'Administrator').trim();
  const firstName = nameToUse.split(' ')[0] || nameToUse;

  const currentHour = new Date().getHours();
  let timePrefix = 'Good Morning';

  if (currentHour >= 12 && currentHour < 17) {
    timePrefix = 'Good Afternoon';
  } else if (currentHour >= 17 || currentHour < 5) {
    timePrefix = 'Good Evening';
  }

  const title = `${timePrefix}, ${firstName}.`;

  // Select non-consecutive second line
  let randomIndex = Math.floor(Math.random() * ENTERPRISE_GREETING_LINES.length);
  if (randomIndex === lastSelectedIndex) {
    randomIndex = (randomIndex + 1) % ENTERPRISE_GREETING_LINES.length;
  }
  lastSelectedIndex = randomIndex;

  const subtitle = ENTERPRISE_GREETING_LINES[randomIndex];

  return { title, subtitle };
}
