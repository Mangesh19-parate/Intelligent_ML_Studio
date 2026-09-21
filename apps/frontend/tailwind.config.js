/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        'surface-hover': 'var(--color-surface-hover)',
        'surface-card': 'var(--color-surface-card)',
        border: 'var(--color-border)',
        text: 'var(--color-text)',
        'text-muted': 'var(--color-text-muted)',
        accent: 'var(--color-accent)',
        'accent-hover': 'var(--color-accent-hover)',
        mc: {
          red: '#EB001B',
          yellow: '#F79E1B',
          orange: '#CF4500',
          'orange-light': '#F37338',
          ink: '#141413',
          charcoal: '#262627',
          cream: '#F3F0EE',
          'cream-lifted': '#FCFBFA',
          slate: '#696969',
          border: '#E3DFDC',
          'dark-bg': '#141413',
          'dark-surface': '#1E1E1C',
          'dark-border': '#333230',
        },
      },
      fontFamily: {
        sans: ['"Sofia Sans"', '"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        'stadium': '9999px',
        'card': '24px',
        'hero': '40px',
      },
    },
  },
  plugins: [],
}
