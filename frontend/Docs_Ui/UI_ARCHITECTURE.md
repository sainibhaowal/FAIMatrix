# UI Architecture

The FAIM UI is built with **Next.js 14** using the App Router and a modern, high-performance tech stack.

## Tech Stack

- **Framework**: Next.js 14 (React)
- **Styling**: Vanilla CSS with Design Tokens (`lib/tokens.ts`)
- **Icons**: Lucide React
- **Animations**: Framer Motion
- **Auth**: NextAuth.js (Custom Credentials Provider)
- **Communication**: SSE (Server-Sent Events) for live data

## Directory Structure

```text
frontend/
├── src/
│   ├── app/            # Next.js App Router (Routes & Layouts)
│   ├── components/     # Reusable UI Components
│   │   ├── layout/     # Shell, TopBar, Sidebar
│   │   ├── ui/         # Base UI components (Buttons, Cards, etc.)
│   │   └── dashboard/  # Page-specific components
│   ├── lib/            # Utilities (Tokens, API client, Auth options)
│   └── types/          # TypeScript Definitions
├── Docs_Ui/            # Documentation Suite (You are here)
└── public/             # Static Assets
```

## Route Groups

- `(landing)`: Public marketing pages.
- `(auth)`: Login and registration flows.
- `(app)`: Protected dashboard and engine controls.

## Design Philosophy: "Reference-Accurate Master Workbench"

The UI is modeled after the FIG (Fractal Intelligence Graph) master workbench. It prioritizes:

1.  **High Visual Fidelity**: SVG-based circuitry and physically nested hexagonal layouts.
2.  **GPU Acceleration**: Smooth panning and zooming for large memory graphs.
3.  **Real-time Feedback**: Continuous monitoring via SSE streams.
