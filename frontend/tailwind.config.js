/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // SunuDoctor palette — "Bleu captivant"
        primary: {
          DEFAULT: "#0B63CE",
          dark: "#063B7A",
          light: "#EAF4FF",
        },
        accent: "#12B8E8",
        ink: "#102A43",
        muted: "#64748B",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      keyframes: {
        wave: {
          "0%, 100%": { transform: "scaleY(0.4)" },
          "50%": { transform: "scaleY(1)" },
        },
      },
      animation: { wave: "wave 1s infinite ease-in-out" },
    },
  },
  plugins: [],
};
