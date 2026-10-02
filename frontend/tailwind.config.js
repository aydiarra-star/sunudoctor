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
          50: "#F2F8FF",
          100: "#EAF4FF",
          200: "#CFE5FF",
          300: "#A9CEFB",
          400: "#5C9BE8",
          500: "#0B63CE",
          600: "#0A57B4",
          700: "#08458F",
          800: "#063B7A",
          900: "#052E5E",
        },
        accent: {
          DEFAULT: "#12B8E8",
          light: "#E3F7FD",
        },
        ink: "#102A43",
        muted: "#64748B",
        surface: "#F7FAFC",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16,42,67,0.04), 0 1px 3px rgba(16,42,67,0.06)",
        card: "0 4px 12px rgba(16,42,67,0.06), 0 1px 3px rgba(16,42,67,0.04)",
        elevated: "0 12px 32px rgba(6,59,122,0.12), 0 2px 8px rgba(16,42,67,0.06)",
        glow: "0 0 0 4px rgba(18,184,232,0.18)",
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      keyframes: {
        wave: {
          "0%, 100%": { transform: "scaleY(0.35)" },
          "50%": { transform: "scaleY(1)" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.9)", opacity: "0.55" },
          "70%": { transform: "scale(1.5)", opacity: "0" },
          "100%": { transform: "scale(1.5)", opacity: "0" },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "check-pop": {
          "0%": { transform: "scale(0.6)", opacity: "0" },
          "60%": { transform: "scale(1.15)", opacity: "1" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
      },
      animation: {
        wave: "wave 1s infinite ease-in-out",
        "pulse-ring": "pulse-ring 2s cubic-bezier(0.4,0,0.6,1) infinite",
        "fade-in-up": "fade-in-up 0.35s ease-out both",
        shimmer: "shimmer 1.6s infinite",
        "check-pop": "check-pop 0.35s ease-out both",
      },
    },
  },
  plugins: [],
};
