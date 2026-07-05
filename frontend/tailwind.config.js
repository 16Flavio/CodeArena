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
        // Classic theme: stock zinc neutrals (no tint) + a single
        // desaturated steel-blue accent. 600 is the light-mode primary,
        // 500 the dark-mode primary. Swapping the brand color is a
        // one-place change.
        accent: {
          50: '#f2f6fa',
          100: '#e4ecf4',
          200: '#c6d7e8',
          300: '#9cbbd6',
          400: '#6d99bf',
          500: '#4b7ca8',
          600: '#3a6690',
          700: '#325575',
          800: '#2c4762',
          900: '#283c52',
          950: '#1a2836',
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
