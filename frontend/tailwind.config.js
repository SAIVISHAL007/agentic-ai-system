/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#0b1220',
          900: '#111827',
          800: '#1f2937',
          700: '#334155',
          600: '#475569',
          500: '#64748b',
          300: '#cbd5f5',
          200: '#e2e8f0',
          100: '#f1f5f9',
        },
        sand: {
          50: '#faf7f0',
          100: '#f4efe3',
          200: '#e8dfcc',
          300: '#d8c9ad',
        },
        paper: {
          50: '#fffdf7',
          100: '#fff9ee',
        },
        moss: {
          600: '#0f766e',
          500: '#14b8a6',
          200: '#a7f3d0',
        },
        sun: {
          600: '#d97706',
          400: '#f59e0b',
          200: '#fde68a',
        },
        ember: {
          600: '#dc2626',
          200: '#fecaca',
        },
      },
      fontFamily: {
        sans: ['"Space Grotesk"', 'ui-sans-serif', 'system-ui'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular'],
      },
      boxShadow: {
        soft: '0 18px 60px -45px rgba(15, 23, 42, 0.45)',
        card: '0 20px 50px -30px rgba(15, 23, 42, 0.25)',
      },
    },
  },
  plugins: [],
};
