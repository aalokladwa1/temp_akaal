/**
 * AKAAL Enterprise Design System - Design Tokens
 * 
 * Strict theme design tokens defining colors, typography, spacing, radius, and motion.
 * Avoid arbitrary values inside components.
 */

export const tokens = {
  colors: {
    // Enterprise Blue Light Theme (Dedicated Onboarding / Welcome Screen)
    light: {
      bg: {
        canvas: '#F8FAFC',
        surface: '#FFFFFF',
        surfaceHover: '#F8FAFC',
        primaryBtn: '#2563EB',
        primaryBtnHover: '#1D4ED8',
        secondaryBtn: '#F1F5F9',
        secondaryBtnHover: '#E2E8F0',
        secondaryBtnActive: '#CBD5E1',
      },
      text: {
        primary: '#0F172A',
        secondary: '#64748B',
        footer: '#94A3B8',
        brandEmphasis: '#1E3A8A',
      },
      border: {
        neutral: 'rgba(15, 23, 42, 0.08)',
        neutralHover: 'rgba(15, 23, 42, 0.14)',
      },
      shadow: {
        cardElevation: '0 20px 40px -15px rgba(15, 23, 42, 0.07), 0 1px 3px rgba(15, 23, 42, 0.04)',
      },
    },
    // Global Dark Theme (Future Workspace)
    dark: {
      bg: {
        canvas: '#0B0D11',
        surface: '#14171F',
        surfaceHover: '#1B1F2A',
        primaryBtn: '#2563EB',
        primaryBtnHover: '#3B82F6',
        secondaryBtn: 'rgba(255, 255, 255, 0.06)',
        secondaryBtnHover: 'rgba(255, 255, 255, 0.10)',
        secondaryBtnActive: 'rgba(255, 255, 255, 0.14)',
      },
      text: {
        primary: '#F9FAFB',
        secondary: '#9CA3AF',
        footer: 'rgba(255, 255, 255, 0.40)',
        brandEmphasis: '#FFFFFF',
      },
      border: {
        neutral: 'rgba(255, 255, 255, 0.08)',
        neutralHover: 'rgba(255, 255, 255, 0.12)',
      },
      shadow: {
        cardElevation: '0 20px 40px -15px rgba(0, 0, 0, 0.5), 0 0 1px rgba(255, 255, 255, 0.05)',
      },
    },
  },
  spacing: {
    cardPaddingVertical: '40px',
    cardPaddingHorizontal: '32px',
    buttonGap: '12px',
    contentGap: '28px',
    headerGap: '8px',
    cardToHeaderGap: '36px',
    titleGroupUpwardOffset: '-24px',
  },
  typography: {
    fontFamily: {
      sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      mono: "'JetBrains Mono', monospace",
    },
    fontSize: {
      welcomeSub: '24px',
      welcomeTitle: '40px',
      body: '14px',
      button: '14px',
      footer: '11px',
    },
    fontWeight: {
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.2,
      snug: 1.3,
      normal: 1.5,
    },
    letterSpacing: {
      tight: '-0.02em',
      normal: '0em',
      mono: '0.04em',
    },
  },
  radius: {
    card: '16px',
    button: '10px',
  },
  motion: {
    transitionControls: '180ms ease',
    transitionSurfaces: '220ms ease',
  },
  layout: {
    cardWidth: '580px',
    cardMinHeight: '240px',
    buttonHeight: '44px',
  },
} as const;

export type Tokens = typeof tokens;
