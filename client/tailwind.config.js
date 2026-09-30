/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#0F1216',
          900: '#14171C',
          800: '#1B1F26',
          700: '#232833',
          600: '#2A2F38',
          500: '#3A4048',
        },
        paper: {
          100: '#F5F3EC',
          200: '#EDEAE1',
          300: '#D8D4C7',
        },
        muted: {
          400: '#8B909A',
          500: '#6E737C',
        },
        scanner: {
          400: '#5BAAB9',
          500: '#3F8FA0',
          600: '#317684',
        },
        flag: {
          400: '#D46459',
          500: '#C1443C',
          600: '#A6362F',
        },
        verified: {
          400: '#6BA97C',
          500: '#4C8B5D',
          600: '#3B6E49',
        },
      },
      fontFamily: {
        display: ['"Fraunces"', 'serif'],
        sans: ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        none_: 'none',
      },
      keyframes: {
        sweep: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        rise: {
          '0%': { opacity: 0, transform: 'translateY(6px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
      },
      animation: {
        sweep: 'sweep 2.4s ease-in-out 1',
        rise: 'rise 0.5s ease-out both',
      },
    },
  },
  plugins: [],
};
