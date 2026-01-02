'use client';

import FeaturePageLayout from '@/components/landing/FeaturePageLayout';

const icon = (
  <svg viewBox="0 0 24 24" className="w-12 h-12" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="12" cy="12" r="3" />
    <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
  </svg>
);

const benefits = [
  'Infinite scalability - no limits on knowledge size',
  'Automatic relationship discovery between concepts',
  'Self-optimizing structure that improves over time',
  'Sub-millisecond retrieval at any scale',
  'Fractal compression reduces storage costs by 50x',
  'Real-time evolution as new knowledge is added',
];

export default function MemoryEnginePage() {
  return (
    <FeaturePageLayout
      title="Fractal Memory Engine"
      subtitle="Self-organizing knowledge structures that grow smarter with every piece of information you add."
      gradient="from-cyan-500 to-blue-500"
      icon={icon}
      benefits={benefits}
    >
      <h2 className="text-2xl font-bold text-white mb-4">How It Works</h2>
      <p className="text-slate-400 mb-6">
        The Fractal Memory Engine is the core of FAIM Lab. Unlike traditional databases that store information in rigid hierarchies, our engine uses fractal patterns to organize knowledge in a way that mirrors human memory.
      </p>
      
      <h3 className="text-xl font-semibold text-white mb-3">Automatic Organization</h3>
      <p className="text-slate-400 mb-6">
        When you add new information, the engine automatically finds the best place to store it, creating connections to related concepts. No manual tagging or categorization required.
      </p>
      
      <h3 className="text-xl font-semibold text-white mb-3">Continuous Evolution</h3>
      <p className="text-slate-400 mb-6">
        The memory structure isn't static. As you interact with your knowledge, the engine learns which connections are most valuable and strengthens them, while gradually forgetting unused paths.
      </p>
      
      <h3 className="text-xl font-semibold text-white mb-3">Fractal Compression</h3>
      <p className="text-slate-400">
        Similar concepts share structure at multiple scales, dramatically reducing storage requirements while maintaining full fidelity of information.
      </p>
    </FeaturePageLayout>
  );
}
