"use client";

import { motion } from "framer-motion";

interface FaimLogoProps {
  size?: number;
  showText?: boolean;
  className?: string;
}

export default function FaimLogo({
  size = 40,
  showText = true,
  className = "",
}: FaimLogoProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Logo Icon - Fractal Pattern */}
      <motion.svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        whileHover={{ scale: 1.05 }}
        className="shrink-0"
      >
        <defs>
          <linearGradient id="faimGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="50%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#8b5cf6" />
          </linearGradient>
          <linearGradient
            id="faimGradientDark"
            x1="0%"
            y1="0%"
            x2="100%"
            y2="100%"
          >
            <stop offset="0%" stopColor="#0891b2" />
            <stop offset="100%" stopColor="#6366f1" />
          </linearGradient>
        </defs>

        {/* Background Circle */}
        <circle
          cx="24"
          cy="24"
          r="22"
          fill="url(#faimGradient)"
          opacity="0.15"
        />
        <circle
          cx="24"
          cy="24"
          r="22"
          stroke="url(#faimGradient)"
          strokeWidth="1.5"
          fill="none"
          opacity="0.5"
        />

        {/* Central Node */}
        <circle cx="24" cy="24" r="4" fill="url(#faimGradient)" />

        {/* Orbital Nodes */}
        <circle cx="24" cy="12" r="2.5" fill="#22d3ee" />
        <circle cx="24" cy="36" r="2.5" fill="#8b5cf6" />
        <circle cx="12" cy="24" r="2.5" fill="#3b82f6" />
        <circle cx="36" cy="24" r="2.5" fill="#3b82f6" />

        {/* Diagonal Nodes */}
        <circle cx="15" cy="15" r="2" fill="#22d3ee" opacity="0.8" />
        <circle cx="33" cy="15" r="2" fill="#3b82f6" opacity="0.8" />
        <circle cx="15" cy="33" r="2" fill="#3b82f6" opacity="0.8" />
        <circle cx="33" cy="33" r="2" fill="#8b5cf6" opacity="0.8" />

        {/* Connection Lines */}
        <g stroke="url(#faimGradient)" strokeWidth="1" opacity="0.6">
          <line x1="24" y1="20" x2="24" y2="12" />
          <line x1="24" y1="28" x2="24" y2="36" />
          <line x1="20" y1="24" x2="12" y2="24" />
          <line x1="28" y1="24" x2="36" y2="24" />

          <line x1="21" y1="21" x2="17" y2="17" />
          <line x1="27" y1="21" x2="31" y2="17" />
          <line x1="21" y1="27" x2="17" y2="31" />
          <line x1="27" y1="27" x2="31" y2="31" />
        </g>

        {/* Outer Ring Dots */}
        <circle cx="24" cy="6" r="1" fill="#22d3ee" opacity="0.5" />
        <circle cx="24" cy="42" r="1" fill="#8b5cf6" opacity="0.5" />
        <circle cx="6" cy="24" r="1" fill="#3b82f6" opacity="0.5" />
        <circle cx="42" cy="24" r="1" fill="#3b82f6" opacity="0.5" />
      </motion.svg>

      {/* Text */}
      {showText && (
        <div>
          <p className="text-white font-bold text-lg tracking-tight">
            FAIM<span className="text-cyan-400 ml-1">Lab</span>
          </p>
          <p className="text-slate-500 text-[10px] tracking-wider -mt-0.5">
            FRACTAL AI MEMORY
          </p>
        </div>
      )}
    </div>
  );
}
