import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-space-grotesk)", "system-ui", "sans-serif"],
      },
      colors: {
        surface: {
          DEFAULT: "#09090b",
          raised: "rgba(255, 255, 255, 0.03)",
          overlay: "rgba(255, 255, 255, 0.06)",
        },
        accent: {
          violet: "#8b5cf6",
          indigo: "#6366f1",
          cyan: "#22d3ee",
          emerald: "#34d399",
        },
      },
    },
  },
  plugins: [],
};

export default config;
