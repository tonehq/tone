/** @type {import('tailwindcss').Config} */
module.exports = {
    important: true,
    content: [
      "./pages/**/*.{js,ts,jsx,tsx,mdx}",
      "./components/**/*.{js,ts,jsx,tsx,mdx}",
      "./app/**/*.{js,ts,jsx,tsx,mdx}",
      "./src/**/*.{js,ts,jsx,tsx,mdx}",  // <— add this if everything is inside /src
    ],
    theme: {
      extend: {
        fontFamily: {
          inter: ['Inter', 'sans-serif'],
        },
        colors: {
          primary: "#1D4ED8",
          secondary: "#9333EA",
          background: "#eff1ff",
          border: "#e2e8f0",
          text: "#111827",
          textSecondary: "#6b7280",
          textTertiary: "#e5e7eb",
          backgroundSecondary: "#f9fafb",
        },
      },
    },
    plugins: [],
  }
  