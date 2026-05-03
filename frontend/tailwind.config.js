/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "surface-tint": "#a6c8ff",
        "primary-fixed-dim": "#a6c8ff",
        "secondary-container": "#4816cb",
        "surface-container-low": "#181c22",
        "on-primary-fixed": "#001c3b",
        "surface-container-high": "#272a30",
        "on-secondary": "#31009a",
        "surface": "#101319",
        "surface-container": "#1c2026",
        "secondary-fixed": "#e6deff",
        "on-background": "#e0e2eb",
        "tertiary-container": "#dc8900",
        "tertiary": "#ffb866",
        "on-tertiary": "#482900",
        "inverse-on-surface": "#2d3037",
        "surface-container-lowest": "#0b0e14",
        "on-primary-container": "#003364",
        "secondary-fixed-dim": "#cabeff",
        "on-primary": "#00315f",
        "inverse-primary": "#005fb0",
        "primary": "#a6c8ff",
        "on-secondary-fixed-variant": "#4816cb",
        "inverse-surface": "#e0e2eb",
        "on-surface": "#e0e2eb",
        "on-error-container": "#ffdad6",
        "on-error": "#690005",
        "tertiary-fixed": "#ffddba",
        "tertiary-fixed-dim": "#ffb866",
        "secondary": "#cabeff",
        "error-container": "#93000a",
        "on-secondary-container": "#b9aaff",
        "primary-container": "#4f9dff",
        "error": "#ffb4ab",
        "on-secondary-fixed": "#1c0062",
        "outline": "#8b919e",
        "on-surface-variant": "#c1c6d4",
        "on-tertiary-fixed-variant": "#673d00",
        "background": "#101319",
        "on-primary-fixed-variant": "#004787",
        "on-tertiary-container": "#4c2c00",
        "outline-variant": "#414752",
        "surface-dim": "#101319",
        "surface-container-highest": "#32353b",
        "primary-fixed": "#d5e3ff",
        "surface-variant": "#32353b",
        "surface-bright": "#363940",
        "on-tertiary-fixed": "#2b1700"
      },
      borderRadius: {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px"
      },
      spacing: {
        "md": "1.5rem",
        "unit": "4px",
        "lg": "2rem",
        "xl": "3rem",
        "xs": "0.5rem",
        "container-max": "1280px",
        "sm": "1rem",
        "gutter": "24px"
      },
      fontFamily: {
        "inter": ["Inter", "sans-serif"],
        "space-grotesk": ["Space Grotesk", "sans-serif"],
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
