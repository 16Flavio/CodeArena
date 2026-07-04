/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Familjen Grotesk', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['IBM Plex Mono', 'JetBrains Mono', 'monospace'],
      },
      colors: {
        // "Jour de concours" palette. Both scales are defined here so
        // the whole app retints from one place.
        //
        // The neutral scale deliberately shadows Tailwind's `zinc`:
        // every existing zinc-* class in the codebase picks up these
        // teal-tinted inks instead of the stock gray.
        zinc: {
          50: '#eff3f1',
          100: '#e4ebe8',
          200: '#d3ded9',
          300: '#b7c8c3',
          400: '#8ba39d',
          500: '#64807b',
          600: '#4d6560',
          700: '#3b504c',
          800: '#243735',
          900: '#142124',
          950: '#0c1517',
        },
        // Single accent: deep teal. 600 is the light-mode primary,
        // 500 the dark-mode primary.
        accent: {
          50: '#ecf5f3',
          100: '#d9ece8',
          200: '#b3d9d1',
          300: '#85c1b6',
          400: '#55b3a5',
          500: '#2f9a8d',
          600: '#0e6b63',
          700: '#10574f',
          800: '#12463f',
          900: '#123a35',
          950: '#0a2622',
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'score-flash': 'scoreFlash 0.6s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        scoreFlash: {
          '0%': { backgroundColor: 'rgba(34, 197, 94, 0.3)' },
          '100%': { backgroundColor: 'transparent' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
