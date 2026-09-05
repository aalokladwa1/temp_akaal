import { DashboardSummary } from '../models/dashboard.models';
import { ConnectionState } from '../models/ipc.models';

export interface GreetingContext {
  greeting: string;
  statePhrase: string;
  formattedDate: string;
}

export function generateGreetingContext(
  userName: string | null,
  summary: DashboardSummary | null,
  connectionState: ConnectionState
): GreetingContext {
  const now = new Date();
  const hour = now.getHours();
  
  // 1. Time-aware greeting derived from local time
  let greetingPrefix = 'Good morning';
  if (hour >= 12 && hour < 17) {
    greetingPrefix = 'Good afternoon';
  } else if (hour >= 17 || hour < 5) {
    greetingPrefix = 'Good evening';
  }
  
  const displayName = userName?.trim() ? userName.trim() : 'Operator';
  const greeting = `${greetingPrefix}, ${displayName}.`;

  // 2. Formatted local date (e.g. Tuesday, 1 September 2026)
  const options: Intl.DateTimeFormatOptions = { 
    weekday: 'long', 
    day: 'numeric', 
    month: 'long',
    year: 'numeric'
  };
  // Format with explicit comma: "Tuesday, 1 September 2026"
  const weekday = now.toLocaleDateString('en-GB', { weekday: 'long' });
  const dayMonthYear = now.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  const formattedDate = `${weekday}, ${dayMonthYear}`;

  // 3. Small curated deterministic state phrase system (Strict priority)
  let statePhrase = 'All quiet where it matters.';

  if (connectionState === 'disconnected') {
    statePhrase = 'Engine connection offline. Reconnecting to local socket...';
  } else if (connectionState === 'connecting') {
    statePhrase = 'Connecting to DevKros motherboard IPC...';
  } else if (!summary) {
    statePhrase = 'Connecting to local engine IPC...';
  } else if (summary.incidents && summary.incidents.some(i => i.severity === 'critical')) {
    statePhrase = 'A few things need a closer look today.';
  } else if (summary.pendingApprovals && summary.pendingApprovals.length > 0) {
    statePhrase = 'A few decisions are waiting on you.';
  } else if (summary.attentionCount !== null && summary.attentionCount > 0) {
    statePhrase = 'A few things need a closer look today.';
  } else if (summary.runningCount !== null && summary.runningCount > 3) {
    statePhrase = 'The fleet is busy. The important bits are below.';
  } else if (summary.runningCount !== null && summary.runningCount > 0) {
    statePhrase = 'A lot is moving. Nothing important is hiding.';
  } else {
    // Quiet / Healthy morning fallback
    if (hour >= 5 && hour < 12) {
      statePhrase = 'Quiet systems make productive mornings.';
    } else {
      statePhrase = 'All quiet where it matters.';
    }
  }

  return {
    greeting,
    statePhrase,
    formattedDate
  };
}
