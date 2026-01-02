'use client';

import { motion } from 'framer-motion';

const logos = [
  { name: 'TechCorp', icon: '◆' },
  { name: 'StartupAI', icon: '◇' },
  { name: 'DataFlow', icon: '○' },
  { name: 'CloudSync', icon: '□' },
  { name: 'NeuralNet', icon: '△' },
  { name: 'Quantix', icon: '◎' },
];

export default function TrustedBy() {
  return (
    <section className="py-16 px-4 bg-slate-950 border-y border-slate-800/50">
      <div className="max-w-6xl mx-auto">
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center text-sm text-slate-500 mb-8"
        >
          Trusted by innovative teams worldwide
        </motion.p>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="flex flex-wrap items-center justify-center gap-8 md:gap-16"
        >
          {logos.map((logo, index) => (
            <motion.div
              key={logo.name}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className="flex items-center gap-2 text-slate-600 hover:text-slate-400 transition-colors"
            >
              <span className="text-2xl">{logo.icon}</span>
              <span className="text-sm font-medium tracking-wide">{logo.name}</span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
