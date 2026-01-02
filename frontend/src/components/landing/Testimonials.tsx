'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const testimonials = [
  {
    quote: "FAIM Lab transformed how we manage research. Finding connections between papers that would have taken days now happens instantly.",
    author: "Dr. Sarah Chen",
    role: "Head of Research, BioTech Innovations",
    avatar: "SC",
    accent: "cyan",
  },
  {
    quote: "The knowledge graph visualization alone is worth it. We can finally see how our entire knowledge base connects.",
    author: "Marcus Williams",
    role: "CTO, DataFlow Analytics",
    avatar: "MW",
    accent: "purple",
  },
  {
    quote: "We reduced time spent searching for information by 80%. FAIM remembers everything so we don't have to.",
    author: "Emily Rodriguez",
    role: "VP Engineering, CloudSync",
    avatar: "ER",
    accent: "emerald",
  },
];

export default function Testimonials() {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent((prev) => (prev + 1) % testimonials.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  const accentColors: Record<string, string> = {
    cyan: 'from-cyan-500 to-blue-500',
    purple: 'from-purple-500 to-pink-500',
    emerald: 'from-emerald-500 to-teal-500',
  };

  return (
    <section className="py-24 px-4 bg-gradient-to-b from-slate-900 to-slate-950">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <span className="text-emerald-400 text-sm font-medium tracking-wide uppercase">
            Testimonials
          </span>
          <h2 className="mt-4 text-3xl md:text-4xl font-bold text-white">
            Loved by Knowledge Workers
          </h2>
        </motion.div>

        {/* Testimonial Card */}
        <div className="relative min-h-[280px]">
          <AnimatePresence mode="wait">
            <motion.div
              key={current}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -30 }}
              transition={{ duration: 0.5 }}
              className="absolute inset-0"
            >
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-8 md:p-12">
                {/* Quote Mark */}
                <div className={`inline-flex w-12 h-12 rounded-xl bg-gradient-to-br ${accentColors[testimonials[current].accent] || accentColors.cyan} items-center justify-center mb-6`}>
                  <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151c-2.433.917-3.996 3.638-3.996 5.849h3.983v10h-9.983z" />
                  </svg>
                </div>

                <blockquote className="text-xl md:text-2xl text-white font-light leading-relaxed mb-8">
                  "{testimonials[current].quote}"
                </blockquote>

                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${accentColors[testimonials[current].accent] || accentColors.cyan} flex items-center justify-center text-white font-semibold`}>
                    {testimonials[current].avatar}
                  </div>
                  <div>
                    <p className="text-white font-semibold">{testimonials[current].author}</p>
                    <p className="text-slate-400 text-sm">{testimonials[current].role}</p>
                  </div>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Dots */}
        <div className="flex items-center justify-center gap-2 mt-8">
          {testimonials.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrent(index)}
              className={`w-2 h-2 rounded-full transition-all duration-300 ${
                index === current
                  ? 'w-6 bg-cyan-500'
                  : 'bg-slate-600 hover:bg-slate-500'
              }`}
              aria-label={`Go to testimonial ${index + 1}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
