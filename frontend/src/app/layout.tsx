// src/app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";

import { Providers } from "../components/providers/Providers";

export const metadata: Metadata = {
  title: {
    default: "FAIM Lab - Fractal AI Memory",
    template: "%s | FAIM Lab",
  },
  description:
    "Transform your knowledge into intelligence with FAIM Lab. AI-powered knowledge management, fractal memory engine, and intelligent document processing. Built by Ravinder Singh.",
  keywords: [
    "AI",
    "knowledge management",
    "fractal memory",
    "knowledge graph",
    "document intelligence",
    "AI chat",
    "FAIM Lab",
  ],
  authors: [{ name: "Ravinder Singh", url: "https://faimlab.com" }],
  creator: "Ravinder Singh",
  publisher: "FAIM Lab",

  // Open Graph (Facebook, LinkedIn)
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://faimlab.com",
    siteName: "FAIM Lab",
    title: "FAIM Lab - Where Your Knowledge Becomes Intelligence",
    description:
      "AI-powered knowledge management with fractal memory engine. Transform documents, notes, and ideas into an intelligent, self-evolving knowledge graph.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "FAIM Lab - Fractal AI Memory",
      },
    ],
  },

  // Twitter Card
  twitter: {
    card: "summary_large_image",
    title: "FAIM Lab - Fractal AI Memory",
    description:
      "Transform your knowledge into intelligence with AI-powered knowledge management.",
    images: ["/og-image.png"],
    creator: "@ravinder_singh",
  },

  // Other
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: "/favicon.ico",
  },
};

// JSON-LD Structured Data
const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "FAIM Lab",
  description: "AI-powered knowledge management with fractal memory engine",
  url: "https://faimlab.com",
  applicationCategory: "ProductivityApplication",
  operatingSystem: "Web",
  author: {
    "@type": "Person",
    name: "Ravinder Singh",
    jobTitle: "Founder & CEO",
  },
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased overflow-x-hidden">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
