import { Injectable, signal, effect } from '@angular/core';

export type AkaalTheme =
  | 'midnight-blue-gray'
  | 'enterprise-blue'
  | 'onyx-oled'
  | 'nord-slate'
  | 'warm-platinum'
  | 'cyber-matrix'
  | 'monokai-pro'
  | 'colorblind-deuteranopia'
  | 'colorblind-protanopia'
  | 'high-contrast-aaa';

export type AkaalAccent =
  | 'electric-blue'
  | 'emerald-green'
  | 'vivid-cyan'
  | 'amethyst-violet'
  | 'solar-amber'
  | 'crimson-rose';

export interface ThemeDescriptor {
  id: AkaalTheme;
  name: string;
  category: 'dark' | 'light' | 'developer' | 'accessibility';
  description: string;
}

export interface AccentDescriptor {
  id: AkaalAccent;
  name: string;
  colorHex: string;
}

@Injectable({
  providedIn: 'root',
})
export class ThemeService {
  private readonly THEME_KEY = 'akaal_active_theme';
  private readonly ACCENT_KEY = 'akaal_active_accent';

  public currentTheme = signal<AkaalTheme>(this.getSavedTheme());
  public currentAccent = signal<AkaalAccent>(this.getSavedAccent());

  public readonly availableThemes: ThemeDescriptor[] = [
    { id: 'enterprise-blue', name: 'Enterprise Blue', category: 'light', description: 'Clean arctic canvas with cobalt accents (Core Default Theme)' },
    { id: 'midnight-blue-gray', name: 'Midnight Blue-Gray', category: 'dark', description: 'Obsidian base with glass surfaces (Dark Theme)' },
    { id: 'onyx-oled', name: 'Onyx Pure Black', category: 'dark', description: 'Pitch-black for OLED displays and low emissions' },
    { id: 'nord-slate', name: 'Nord Slate', category: 'dark', description: 'Cool frosted arctic blue aesthetic' },
    { id: 'warm-platinum', name: 'Warm Platinum', category: 'light', description: 'Soft titanium light palette to reduce eye fatigue' },
    { id: 'cyber-matrix', name: 'Cyber Matrix', category: 'developer', description: 'Developer mode with emerald matrix terminal accents' },
    { id: 'monokai-pro', name: 'Monokai Pro', category: 'developer', description: 'Code editor colorway for SQL/DDL heavy workflows' },
    { id: 'colorblind-deuteranopia', name: 'Deuteranopia Safe', category: 'accessibility', description: 'Cyan/Amber/Magenta high-clarity spectrum' },
    { id: 'colorblind-protanopia', name: 'Protanopia Safe', category: 'accessibility', description: 'Blue/Yellow high-contrast spectrum' },
    { id: 'high-contrast-aaa', name: 'High-Contrast AAA', category: 'accessibility', description: 'Ultra-crisp monochrome with high-visibility borders' },
  ];

  public readonly availableAccents: AccentDescriptor[] = [
    { id: 'electric-blue', name: 'Electric Blue', colorHex: '#0F62FE' },
    { id: 'emerald-green', name: 'Emerald Green', colorHex: '#10B981' },
    { id: 'vivid-cyan', name: 'Vivid Cyan', colorHex: '#06B6D4' },
    { id: 'amethyst-violet', name: 'Amethyst Violet', colorHex: '#8B5CF6' },
    { id: 'solar-amber', name: 'Solar Amber', colorHex: '#F59E0B' },
    { id: 'crimson-rose', name: 'Crimson Rose', colorHex: '#F43F5E' },
  ];

  constructor() {
    effect(() => {
      const theme = this.currentTheme();
      const accent = this.currentAccent();
      this.applyThemeToDOM(theme, accent);
    });
  }

  public setTheme(theme: AkaalTheme): void {
    this.currentTheme.set(theme);
    localStorage.setItem(this.THEME_KEY, theme);
  }

  public setAccent(accent: AkaalAccent): void {
    this.currentAccent.set(accent);
    localStorage.setItem(this.ACCENT_KEY, accent);
  }

  private applyThemeToDOM(theme: AkaalTheme, accent: AkaalAccent): void {
    if (typeof document !== 'undefined') {
      const root = document.documentElement;
      root.setAttribute('data-theme', theme);
      root.setAttribute('data-accent', accent);
    }
  }

  private getSavedTheme(): AkaalTheme {
    if (typeof localStorage !== 'undefined') {
      return (localStorage.getItem(this.THEME_KEY) as AkaalTheme) || 'enterprise-blue';
    }
    return 'enterprise-blue';
  }

  private getSavedAccent(): AkaalAccent {
    if (typeof localStorage !== 'undefined') {
      return (localStorage.getItem(this.ACCENT_KEY) as AkaalAccent) || 'electric-blue';
    }
    return 'electric-blue';
  }
}
