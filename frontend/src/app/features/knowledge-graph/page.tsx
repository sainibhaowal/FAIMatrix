'use client';

import FeaturePageLayout from '@/components/landing/FeaturePageLayout';

const icon = (
  <svg viewBox="0 0 24 24" className="w-12 h-12" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="12" cy="12" r="2" />
    <circle cx="6" cy="6" r="2" />
    <circle cx="18" cy="6" r="2" />
    <circle cx="6" cy="18" r="2" />
    <circle cx="18" cy="18" r="2" />
    <path d="M12 10V8M8 8l2-2M14 8l2-2M12 14v2M8 16l2 2M14 16l2 2" />
  </svg>
);

const benefits = [
  'Interactive 3D visualization of your knowledge',
  'Real-time updates as connections form',
  'Zoom from overview to individual nodes',
  'Filter by topic, date, or relationship type',
  'Export graph for presentations',
  'Discover hidden patterns in your data',
];

export default function KnowledgeGraphPage() {
  return (
    <FeaturePageLayout
      title="Knowledge Graph"
      subtitle="Visualize connections between your ideas in stunning 3D. See how knowledge connects and evolves."
      gradient="from-purple-500 to-pink-500"
      icon={icon}
      benefits={benefits}
    >
      <h2 className="text-2xl font-bold text-white mb-4">See Your Knowledge Come Alive</h2>
      <p className="text-slate-400 mb-6">
        The Knowledge Graph transforms your documents, notes, and ideas into an interactive visualization. Watch as concepts connect, clusters form, and insights emerge.
      </p>
      
      <h3 className="text-xl font-semibold text-white mb-3">Interactive Exploration</h3>
      <p className="text-slate-400 mb-6">
        Click on any node to explore its connections. Drag to reorganize. Double-click to zoom into a concept cluster. The graph responds to your curiosity.
      </p>
      
      <h3 className="text-xl font-semibold text-white mb-3">Real-Time Updates</h3>
      <p className="text-slate-400 mb-6">
        As you add new documents or chat with FAIM, watch the graph evolve in real-time. New nodes appear, connections form, and clusters reorganize themselves.
      </p>
      
      <h3 className="text-xl font-semibold text-white mb-3">Pattern Discovery</h3>
      <p className="text-slate-400">
        The visual layout reveals patterns you might miss in text. See which topics dominate your knowledge, find orphaned ideas, and discover unexpected connections.
      </p>
    </FeaturePageLayout>
  );
}
