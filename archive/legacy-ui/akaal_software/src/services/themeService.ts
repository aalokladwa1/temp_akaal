/**
 * AKAAL Theme Service
 * 
 * Manages light/dark theme switching with localStorage persistence.
 * Applies theme class to document.documentElement for global CSS variable switching.
 */

export type AppTheme = 'light' | 'dark';

const STORAGE_KEY = 'akaal_app_theme';
const LIGHT_CLASS = 'app-theme-light';
const DARK_CLASS = 'app-theme-dark';

type ThemeListener = (theme: AppTheme) => void;

class ThemeService {
  private current: AppTheme;
  private listeners: Set<ThemeListener> = new Set();

  constructor() {
    const stored = localStorage.getItem(STORAGE_KEY) as AppTheme | null;
    this.current = stored === 'light' ? 'light' : 'dark';
    this.apply(this.current);
  }

  getTheme(): AppTheme {
    return this.current;
  }

  toggle(): void {
    this.setTheme(this.current === 'dark' ? 'light' : 'dark');
  }

  setTheme(theme: AppTheme): void {
    if (this.current === theme) return;
    this.current = theme;
    localStorage.setItem(STORAGE_KEY, theme);
    this.apply(theme);
    this.listeners.forEach((l) => l(theme));
  }

  subscribe(listener: ThemeListener): () => void {
    this.listeners.add(listener);
    listener(this.current);
    return () => this.listeners.delete(listener);
  }

  private apply(theme: AppTheme): void {
    const root = document.documentElement;
    root.classList.remove(LIGHT_CLASS, DARK_CLASS);
    root.classList.add(theme === 'light' ? LIGHT_CLASS : DARK_CLASS);
  }
}

export const themeService = new ThemeService();
