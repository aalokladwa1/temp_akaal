/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Roboto"', 'sans-serif'],
        heading: ['"Roboto"', 'sans-serif'],
        mono: ['"Roboto"', 'sans-serif'],
      },
      colors: {
        background: 'var(--color-bg-canvas)',
        surface: 'var(--color-bg-surface)',
        'surface-elevated': 'var(--color-bg-elevated)',
        'surface-subtle': 'var(--color-bg-subtle)',
        'border-default': 'var(--color-border-default)',
        'border-strong': 'var(--color-border-strong)',
        'border-subtle': 'var(--color-border-subtle)',
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-muted': 'var(--color-text-muted)',
        accent: {
          DEFAULT: 'var(--color-accent)',
          hover: 'var(--color-accent-hover)',
          muted: 'var(--color-accent-muted)',
        },
        status: {
          success: 'var(--color-status-success)',
          warning: 'var(--color-status-warning)',
          error: 'var(--color-status-error)',
          info: 'var(--color-status-info)',
        }
      }
    },
  },
  plugins: [],
}
