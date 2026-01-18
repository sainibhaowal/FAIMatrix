import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/app/**/*.{ts,tsx}", "./src/components/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
        "3xl": "1.5rem",
      },
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",

        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },

        // OmniSync quick refs
        os: {
          bg: "var(--os-bg)",
          s1: "var(--os-surface-1)",
          s2: "var(--os-surface-2)",
          s3: "var(--os-surface-3)",
          text1: "var(--os-text-1)",
          text2: "var(--os-text-2)",
          text3: "var(--os-text-3)",
        },
      },
      boxShadow: {
        "os-deep": "var(--os-shadow-deep)",
        "os-line": "var(--os-shadow-line)",
      },
      animation: {
        shimmer: "shimmer 2s linear infinite",
        slideIn: "slideIn 0.3s ease-out forwards",
        fadeIn: "fadeIn 0.5s ease-out forwards",
        "pulse-glow": "pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "spin-slow": "spin 3s linear infinite",
        "progress-stripe": "progress-stripe 1s linear infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
