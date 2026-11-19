/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'IBM Plex Sans Arabic',
          'Noto Sans Arabic',
          'Segoe UI',
          'system-ui',
          'sans-serif',
        ],
      },
      colors: {
        ink: '#111827',
        canvas: '#f8fafc',
        brand: {
          500: '#0f766e',
          600: '#0d5f59',
        },
      },
    },
  },
  plugins: [],
};
