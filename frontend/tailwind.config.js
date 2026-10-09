/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        high: "#dc2626",
        medium: "#d97706",
        low: "#ca8a04",
        safe: "#16a34a",
      },
    },
  },
  plugins: [],
};
