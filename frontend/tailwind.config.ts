import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#000000",
        card: "#000000",
        "card-border": "#222222",
        muted: "#8b8b9e",
        win: "#00ff87",
        loss: "#ff4757",
        draw: "#ffa502",
      },
      fontFamily: {
        sans: [
          "var(--font-body)",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        display: ["var(--font-display)", "system-ui", "sans-serif"],
      },
      lineHeight: {
        display: "var(--leading-display)",
        title: "var(--leading-title)",
        copy: "var(--leading-body)",
        ui: "var(--leading-ui)",
      },
      letterSpacing: {
        display: "var(--tracking-display)",
        caps: "var(--tracking-caps)",
      },
      animation: {
        "bar-fill": "barFill 0.8s ease-out forwards",
      },
      keyframes: {
        barFill: {
          "0%": { width: "0%" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
