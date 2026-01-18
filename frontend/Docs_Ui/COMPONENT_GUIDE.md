# Component Guide

This guide covers the primary functional components used in the FAIM UI.

## 1. TopBar Components

- **WorkspaceSelector**: Handles switching between Memory Graphs. Displays the user's secure identity (User ID, Graph ID, Tenant ID) and a visual "ISOLATED" badge for security confirmation.
- **SearchPanel**: Global search interface for querying the Memory Graph.

## 2. Navigation

- **AppShell**: Root layout component providing the responsive grid structure.
- **LeftNav**: Collapsible sidebar navigation for switching between Dashboard, Monitor, FIG, and Settings.

## 3. Visualization (The Engine)

- **Graph3DView**: High-performance Three.js graph renderer for Memory Graphs.
- **NodeInspector**: Detailed view for individual nodes, displaying vector hashes, touch counts, and level indicators.
- **FIG Blueprint (FIG.tsx)**: The "Master Workbench" view using physically nested hexagons to represent fractal memory structures.

## 4. Analysis

- **EventJournalPanel**: Real-time log of engine operations (Ingestion, Evolve, Prune).
- **DashboardActivity**: High-level overview of system usage and memory density.

## Reusable UI Elements

Located in `src/components/ui/`, these components use standard design tokens for a consistent look and feel:

- `Button`: Multiple variants (Primary, Secondary, Ghost, Cyan).
- `Card`: Gradient-bordered containers with glassmorphism backgrounds.
- `Tabs`: Animated tab switching using Framer Motion.
