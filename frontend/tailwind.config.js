/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Hand-Drawn design system palette
        paper: '#fdfbf7',   // Background
        pencil: '#2d2d2d',  // Foreground, Borders, Shadows
        marker: '#ff4d4d',   // Accent, Error, Fake
        ink: '#2d5da1',     // Secondary Accent, Primary Action, Real
      },
      fontFamily: {
        sans: ['"Patrick Hand"', 'cursive'],
        heading: ['Kalam', 'cursive'],
      },
      boxShadow: {
        hard: '4px 4px 0px 0px #2d2d2d',
      },
      keyframes: {
        'fade-in': {
          '0%':   { opacity: 0, transform: 'translateY(4px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 200ms ease-out',
      },
    },
  },
  plugins: [],
};
