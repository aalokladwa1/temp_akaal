/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  darkMode: ['class', '[data-theme*="dark"], [data-theme="midnight-blue-gray"], [data-theme="onyx-oled"], [data-theme="nord-slate"], [data-theme="cyber-matrix"], [data-theme="monokai-pro"], [data-theme="high-contrast-aaa"]'],
  theme: {
    extend: {
      fontFamily: {
        heading: ['var(--font-heading)'],
        sans: ['var(--font-body)'],
        mono: ['var(--font-code)'],
      },
      colors: {
        app: 'var(--bg-app)',
        surface: 'var(--bg-surface)',
        'surface-elevated': 'var(--bg-surface-elevated)',
        'border-subtle': 'var(--border-subtle)',
        'border-strong': 'var(--border-strong)',
        'border-active': 'var(--border-active)',
        accent: {
          DEFAULT: 'var(--accent-primary)',
          hover: 'var(--accent-primary-hover)',
          subtle: 'var(--accent-primary-subtle)',
          glow: 'var(--accent-glow)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
          inverse: 'var(--text-inverse)',
        },
        status: {
          success: 'var(--status-success)',
          warning: 'var(--status-warning)',
          error: 'var(--status-error)',
          info: 'var(--status-info)',
        },
      },
    },
  },
  plugins: [],
}
