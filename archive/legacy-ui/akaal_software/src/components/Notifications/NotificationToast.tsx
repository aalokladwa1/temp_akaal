import { useState, useEffect, useRef, useCallback, type FC } from 'react';
import type { AppNotification } from '../../services/notificationService';
import { notificationService } from '../../services/notificationService';
import styles from './NotificationToast.module.css';

const DISPLAY_MS = 5000;
const CLOSE_BTN_DELAY_MS = 1000;

interface ToastItemProps {
  notification: AppNotification;
}

const ToastItem: FC<ToastItemProps> = ({ notification }) => {
  const [showClose, setShowClose] = useState(false);
  const [dismissing, setDismissing] = useState(false);
  const [progress, setProgress] = useState(100);
  const timerRef = useRef<number | null>(null);
  const startRef = useRef<number>(Date.now());
  const remainingRef = useRef<number>(DISPLAY_MS);
  const animFrameRef = useRef<number | null>(null);

  const dismiss = useCallback(() => {
    setDismissing(true);
    setTimeout(() => notificationService.dismiss(notification.id), 180);
  }, [notification.id]);

  const startTimer = useCallback(() => {
    startRef.current = Date.now();
    timerRef.current = window.setTimeout(dismiss, remainingRef.current);

    const tick = () => {
      const elapsed = Date.now() - startRef.current;
      const pct = Math.max(0, ((remainingRef.current - elapsed) / DISPLAY_MS) * 100);
      setProgress(pct);
      if (pct > 0) {
        animFrameRef.current = requestAnimationFrame(tick);
      }
    };
    animFrameRef.current = requestAnimationFrame(tick);
  }, [dismiss]);

  const pauseTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    remainingRef.current -= Date.now() - startRef.current;
  }, []);

  useEffect(() => {
    startTimer();
    const closeBtnTimer = window.setTimeout(() => setShowClose(true), CLOSE_BTN_DELAY_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      clearTimeout(closeBtnTimer);
    };
  }, [startTimer]);

  const dotClass = {
    info: styles.dotInfo,
    success: styles.dotSuccess,
    warning: styles.dotWarning,
    error: styles.dotError,
  }[notification.severity];

  return (
    <div
      className={[styles.toast, dismissing ? styles.toastDismissing : ''].filter(Boolean).join(' ')}
      onMouseEnter={pauseTimer}
      onMouseLeave={startTimer}
      role="alert"
      aria-live="assertive"
    >
      <div className={[styles.dot, dotClass].join(' ')} />
      <div className={styles.body}>
        <div className={styles.title}>{notification.title}</div>
        {notification.message && (
          <div className={styles.message}>{notification.message}</div>
        )}
      </div>
      <button
        className={[styles.closeBtn, showClose ? styles.closeBtnVisible : ''].filter(Boolean).join(' ')}
        onClick={dismiss}
        aria-label="Dismiss notification"
      >
        ×
      </button>
      <div
        className={styles.progressBar}
        style={{ width: `${progress}%` }}
      />
    </div>
  );
};

export const NotificationToastContainer: FC = () => {
  const [active, setActive] = useState<AppNotification[]>([]);

  useEffect(() => {
    return notificationService.subscribe((notifications) => {
      setActive(notifications);
    });
  }, []);

  return (
    <div className={styles.container}>
      {active.map((n) => (
        <ToastItem key={n.id} notification={n} />
      ))}
    </div>
  );
};
