/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // AKAAL theme tokens (CSS variable references)
        'akaal-primary':    'var(--akaal-primary)',
        'akaal-secondary':  'var(--akaal-secondary)',
        'akaal-accent':     'var(--akaal-accent)',
        'akaal-bg':         'var(--akaal-bg)',
        'akaal-surface':    'var(--akaal-surface)',
        'akaal-elevated':   'var(--akaal-surface-elevated)',
        'akaal-text':       'var(--akaal-text)',
        'akaal-text-sec':   'var(--akaal-text-secondary)',
        'akaal-text-muted': 'var(--akaal-text-muted)',
        'akaal-border':     'var(--akaal-border)',
        'akaal-success':    'var(--akaal-success)',
        'akaal-warning':    'var(--akaal-warning)',
        'akaal-error':      'var(--akaal-error)',
        'akaal-info':       'var(--akaal-info)',
        // Legacy tokens
        void: '#0B0D0F',
        surface: '#1A1D23',
        'surface-2': '#22262F',
        phosphor: '#39FF14',
        'phosphor-dim': 'rgba(57,255,20,0.15)',
        plasma: '#FFE600',
        'plasma-dim': 'rgba(255,230,0,0.15)',
        signal: '#FF3562',
        'signal-dim': 'rgba(255,53,98,0.15)',
        fg: '#E4E8EF',
        'fg-muted': '#7A8394',
        'fg-dim': '#3D4350',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['Manrope', 'sans-serif'],
      },
      boxShadow: {
        phosphor: '0 0 20px rgba(57,255,20,0.4), 0 0 60px rgba(57,255,20,0.1)',
        'phosphor-sm': '0 0 10px rgba(57,255,20,0.3)',
        plasma: '0 0 15px rgba(255,230,0,0.3)',
        signal: '0 0 15px rgba(255,53,98,0.3)',
      },
      animation: {
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
        'blink': 'blink-cursor 1s step-end infinite',
        'scroll-log': 'scroll-log 20s linear infinite',
        'slide-up': 'slide-up-fade 0.8s cubic-bezier(0.16,1,0.3,1) forwards',
        'check-pop': 'check-pop 0.4s cubic-bezier(0.34,1.56,0.64,1) forwards',
        'float': 'float-y 4s ease-in-out infinite',
        'shimmer': 'shimmer 6s linear infinite',
        'flow-right': 'flow-right 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};