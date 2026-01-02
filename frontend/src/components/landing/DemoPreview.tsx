'use client';

import { motion } from 'framer-motion';
import { useEffect, useState, useRef } from 'react';

// Simulated nodes for the demo
const demoNodes = [
  { id: 1, x: 50, y: 40, label: 'AI Research', color: 'cyan' },
  { id: 2, x: 30, y: 60, label: 'Machine Learning', color: 'purple' },
  { id: 3, x: 70, y: 55, label: 'Neural Networks', color: 'cyan' },
  { id: 4, x: 45, y: 75, label: 'Deep Learning', color: 'emerald' },
  { id: 5, x: 60, y: 30, label: 'NLP', color: 'purple' },
  { id: 6, x: 25, y: 35, label: 'Computer Vision', color: 'emerald' },
  { id: 7, x: 80, y: 40, label: 'Transformers', color: 'cyan' },
  { id: 8, x: 40, y: 20, label: 'GPT Models', color: 'purple' },
];

const demoEdges = [
  [1, 2], [1, 3], [2, 4], [3, 4], [1, 5], [5, 7], [5, 8], [6, 2], [7, 3], [8, 7],
];

export default function DemoPreview() {
  const [activeNode, setActiveNode] = useState<number | null>(null);
  const [pulsingEdge, setPulsingEdge] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setPulsingEdge((prev) => (prev + 1) % demoEdges.length);
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  const colorMap: Record<string, string> = {
    cyan: '#22d3ee',
    purple: '#a855f7',
    emerald: '#10b981',
  };

  return (
    <section className="py-24 px-4 bg-slate-950 overflow-hidden">
      <div className="max-w-6xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left: Description */}
          <motion.div
            initial={{ opacity: 0, x: -40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
          >
            <span className="text-cyan-400 text-sm font-medium tracking-wide uppercase">
              Live Preview
            </span>
            <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white leading-tight">
              See Your Knowledge
              <br />
              <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                Come Alive
              </span>
            </h2>
            <p className="mt-6 text-slate-400 leading-relaxed">
              Watch as FAIM automatically discovers connections between your documents,
              notes, and ideas. The knowledge graph grows and evolves in real-time,
              revealing insights you never knew existed.
            </p>
            <ul className="mt-6 space-y-3">
              {['Auto-clustering of related concepts', 'Real-time graph evolution', 'Interactive exploration'].map((item) => (
                <li key={item} className="flex items-center gap-3 text-slate-300">
                  <div className="w-2 h-2 rounded-full bg-cyan-500" />
                  {item}
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Right: Interactive Graph Demo */}
          <motion.div
            ref={containerRef}
            initial={{ opacity: 0, x: 40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="relative h-[400px] rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden"
          >
            {/* Grid Background */}
            <div 
              className="absolute inset-0 opacity-20"
              style={{
                backgroundImage: `radial-gradient(circle at 1px 1px, rgba(255,255,255,0.1) 1px, transparent 0)`,
                backgroundSize: '30px 30px'
              }}
            />

            {/* SVG for edges */}
            <svg className="absolute inset-0 w-full h-full">
              {demoEdges.map(([from, to], index) => {
                const fromNode = demoNodes.find(n => n.id === from)!;
                const toNode = demoNodes.find(n => n.id === to)!;
                const isPulsing = index === pulsingEdge;
                
                return (
                  <motion.line
                    key={`${from}-${to}`}
                    x1={`${fromNode.x}%`}
                    y1={`${fromNode.y}%`}
                    x2={`${toNode.x}%`}
                    y2={`${toNode.y}%`}
                    stroke={isPulsing ? '#22d3ee' : '#334155'}
                    strokeWidth={isPulsing ? 2 : 1}
                    initial={{ pathLength: 0 }}
                    animate={{ 
                      pathLength: 1,
                      opacity: isPulsing ? 1 : 0.5
                    }}
                    transition={{ duration: 0.5 }}
                  />
                );
              })}
            </svg>

            {/* Nodes */}
            {demoNodes.map((node) => (
              <motion.div
                key={node.id}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: node.id * 0.1, type: 'spring' }}
                onMouseEnter={() => setActiveNode(node.id)}
                onMouseLeave={() => setActiveNode(null)}
                className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer"
                style={{ left: `${node.x}%`, top: `${node.y}%` }}
              >
                <motion.div
                  animate={{
                    scale: activeNode === node.id ? 1.2 : 1,
                    boxShadow: activeNode === node.id 
                      ? `0 0 30px ${colorMap[node.color]}40`
                      : '0 0 0px transparent'
                  }}
                  className={`w-4 h-4 rounded-full bg-gradient-to-br ${
                    node.color === 'cyan' ? 'from-cyan-400 to-cyan-500' :
                    node.color === 'purple' ? 'from-purple-400 to-purple-500' :
                    'from-emerald-400 to-emerald-500'
                  }`}
                />
                
                {/* Label on hover */}
                <AnimatePresence>
                  {activeNode === node.id && (
                    <motion.div
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 5 }}
                      className="absolute top-6 left-1/2 -translate-x-1/2 px-3 py-1 bg-slate-800 rounded-lg text-xs text-white whitespace-nowrap"
                    >
                      {node.label}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}

            {/* Floating particles */}
            {[...Array(5)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-1 h-1 bg-cyan-400/30 rounded-full"
                animate={{
                  x: [0, Math.random() * 100 - 50],
                  y: [0, Math.random() * 100 - 50],
                  opacity: [0.3, 0.8, 0.3],
                }}
                transition={{
                  duration: 3 + Math.random() * 2,
                  repeat: Infinity,
                  repeatType: 'reverse',
                }}
                style={{
                  left: `${20 + Math.random() * 60}%`,
                  top: `${20 + Math.random() * 60}%`,
                }}
              />
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}

// Need to import AnimatePresence
import { AnimatePresence } from 'framer-motion';
