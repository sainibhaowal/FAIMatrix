// src/app/layout.tsx
import type { Metadata } from 'next';
import './globals.css';

import { FaimShell } from '../components/shell/FaimShell';

export const metadata: Metadata = {
  title: 'FAIM Lab',
  description: 'Fractal Antisymmetric Inheritance Memory Lab',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased overflow-x-hidden">
        <FaimShell>{children}</FaimShell>
      </body>
    </html>
  );
}
