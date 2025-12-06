/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: "#0f83bd",
        "background-light": "#F5F5DC",
        "background-dark": "#1d1d1b",
        "card-light": "#F8F8F8",
        "card-dark": "#2a2a2a",
        "text-light": "#36454F",
        "text-dark": "#e0e0e0",
        "text-muted-light": "#617c89",
        "text-muted-dark": "#9e9e9e",
        accent: "#c9a97d",
      },
      fontFamily: {
        display: ["Manrope", "sans-serif"],
        serif: ["Playfair Display", "serif"],
      },
      borderRadius: {
        DEFAULT: "1rem",
        lg: "2rem",
        xl: "3rem",
        full: "9999px",
      },
      // 👇 NEW: animations for card fade-in
      animation: {
        fadeIn: "fadeIn 0.35s ease-in-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: 0, transform: "translateY(8px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"), // 👈 for .prose styling in bot replies
  ],
};
