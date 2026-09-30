/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0F1524",
          900: "#161D2E",
          800: "#1E2740",
          700: "#2A3350",
        },
        surface: {
          50: "#F7F8FA",
          100: "#EEF0F4",
          200: "#E2E5EA",
        },
        line: "#E2E5EA",
        accent: {
          DEFAULT: "#3452E1",
          dim: "#2A3EBF",
          tint: "#EBEFFD",
        },
        status: {
          healthy: "#16A34A",
          healthyBg: "#EAF7EF",
          warning: "#B45309",
          warningBg: "#FEF3E2",
          critical: "#DC2626",
          criticalBg: "#FDECEC",
          info: "#2563EB",
          infoBg: "#EAF1FE",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      borderRadius: {
        sm: "4px",
        DEFAULT: "6px",
        md: "6px",
      },
      fontSize: {
        xs: ["11px", { lineHeight: "16px" }],
        sm: ["12.5px", { lineHeight: "18px" }],
        base: ["13.5px", { lineHeight: "20px" }],
      },
    },
  },
  plugins: [],
};
