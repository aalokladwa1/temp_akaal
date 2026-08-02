/**
 * AKAAL Notification Service
 * 
 * Manages application toast notifications with queue, history,
 * and observer pattern for React components.
 */

export type NotificationSeverity = 'info' | 'success' | 'warning' | 'error';

export interface AppNotification {
  id: string;
  title: string;
  message?: string;
  severity: NotificationSeverity;
  createdAt: number;
  dismissedAt?: number;
}

type NotificationListener = (notifications: AppNotification[], history: AppNotification[]) => void;

const MAX_VISIBLE = 3;

class NotificationService {
  private active: AppNotification[] = [];
  private history: AppNotification[] = [];
  private listeners: Set<NotificationListener> = new Set();
  private counter = 0;

  subscribe(listener: NotificationListener): () => void {
    this.listeners.add(listener);
    listener([...this.active], [...this.history]);
    return () => this.listeners.delete(listener);
  }

  push(title: string, severity: NotificationSeverity = 'info', message?: string): string {
    const id = `notif_${Date.now()}_${++this.counter}`;
    const notif: AppNotification = { id, title, message, severity, createdAt: Date.now() };

    if (this.active.length >= MAX_VISIBLE) {
      // Dismiss oldest to make room
      const oldest = this.active[0];
      this.dismiss(oldest.id, false);
    }

    this.active = [...this.active, notif];
    this.notify();
    return id;
  }

  dismiss(id: string, addToHistory = true): void {
    const notif = this.active.find((n) => n.id === id);
    if (!notif) return;

    this.active = this.active.filter((n) => n.id !== id);
    if (addToHistory) {
      const dismissed = { ...notif, dismissedAt: Date.now() };
      this.history = [dismissed, ...this.history].slice(0, 100);
    }
    this.notify();
  }

  clearHistory(): void {
    this.history = [];
    this.notify();
  }

  private notify(): void {
    const snapshot = [...this.active];
    const histSnap = [...this.history];
    this.listeners.forEach((l) => l(snapshot, histSnap));
  }
}

export const notificationService = new NotificationService();
