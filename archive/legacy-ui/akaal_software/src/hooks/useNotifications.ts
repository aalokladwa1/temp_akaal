import { useState, useEffect } from 'react';
import { notificationService, type AppNotification } from '../services/notificationService';

export function useNotifications() {
  const [active, setActive] = useState<AppNotification[]>([]);
  const [history, setHistory] = useState<AppNotification[]>([]);

  useEffect(() => {
    return notificationService.subscribe((a, h) => {
      setActive(a);
      setHistory(h);
    });
  }, []);

  return { active, history };
}
