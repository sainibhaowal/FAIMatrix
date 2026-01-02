'use client';

import FeaturePageLayout from '@/components/landing/FeaturePageLayout';

const icon = (
  <svg viewBox="0 0 24 24" className="w-12 h-12" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10z" />
    <path d="M8 10h.01M12 10h.01M16 10h.01" />
  </svg>
);

const benefits = [
  'Natural language queries - ask like you would ask a person',
  'Answers grounded in YOUR knowledge, not generic web data',
  'Source citations for every answer',
  'Context-aware follow-up questions',
  'Multi-turn conversations that remember context',
  'Export conversations for documentation',
];

export default function AIChatPage() {
  return (
    <FeaturePageLayout
      title="AI-Powered Chat"
      subtitle="Query your entire knowledge base with natural language. Get instant, contextual answers."
      gradient="from-emerald-500 to-teal-500"
      icon={icon}
      benefits={benefits}
    >
      <h2 className="text-2xl font-bold text-white mb-4">Chat With Your Knowledge</h2>
      <p className="text-slate-400 mb-6">
        Stop searching through files. Just ask. FAIM's AI understands your question, searches your entire knowledge base, and synthesizes a comprehensive answer.
      </p>
      
      <h3 className="text-xl font-semibold text-white mb-3">Grounded Answers</h3>
      <p className="text-slate-400 mb-6">
        Every answer comes with citations to the original sources in your knowledge base. Click through to verify or explore deeper.
      </p>
      
      <h3 className="text-xl font-semibold text-white mb-3">Context Memory</h3>
      <p className="text-slate-400 mb-6">
        FAIM remembers your conversation context. Ask follow-up questions, dig deeper into topics, or change direction - the AI keeps up.
      </p>
      
      <h3 className="text-xl font-semibold text-white mb-3">Your Data, Your Answers</h3>
      <p className="text-slate-400">
        Unlike generic AI, FAIM only answers from your knowledge. No hallucinations from internet data - just your trusted information.
      </p>
    </FeaturePageLayout>
  );
}
