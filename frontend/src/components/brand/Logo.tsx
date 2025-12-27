'use client';

import React, { useEffect, useMemo, useRef } from 'react';

export type LogoSize = "sm" | "md" | "lg" | "small" | "medium" | "large";

export type LogoProps = {
  size?: LogoSize;
  className?: string;
  title?: string;
  px?: number;
};

/**
 * FAIM Interactive Logo (physics parallax + SVG)
 * - Single default export (no duplicate defaults)
 * - Safe to embed in Sidebar/Header
 * - Size-controlled wrapper
 */
export default function Logo({ size = 'small', className, title = 'FAIM', px }: LogoProps) {
  const s =
    size === "lg" ? "large" :
    size === "md" ? "medium" :
    size === "sm" ? "small" :
    size;

  const basePx = s === "large" ? 120 : s === "medium" ? 84 : 56;

  const finalPx = typeof px === 'number' ? px : basePx;

  return (
    <div
      className={className ?? ''}
      style={{ width: finalPx, height: finalPx }}

      aria-label={title}
      role="img"
    >
      <InteractiveLogo />
    </div>
  );
}

/* ---------------------------------------------
   INTERACTIVE LOGO (Physics & SVG Logic)
--------------------------------------------- */
function InteractiveLogo() {
  const containerRef = useRef<HTMLDivElement>(null);
  const target = useRef({ x: 0, y: 0 });
  const current = useRef({ x: 0, y: 0 });
  const rafId = useRef<number | null>(null);

  useEffect(() => {
    const updatePhysics = () => {
      const ease = 0.08;
      current.current.x += (target.current.x - current.current.x) * ease;
      current.current.y += (target.current.y - current.current.y) * ease;

      const el = containerRef.current;
      if (el) {
        el.style.setProperty('--mx', current.current.x.toFixed(4));
        el.style.setProperty('--my', current.current.y.toFixed(4));
      }
      rafId.current = requestAnimationFrame(updatePhysics);
    };

    updatePhysics();
    return () => {
      if (rafId.current) cancelAnimationFrame(rafId.current);
    };
  }, []);

  const handleMouseMove = (e: React.MouseEvent) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();

    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;

    target.current.x = x / (rect.width / 2);
    target.current.y = y / (rect.height / 2);
  };

  const handleMouseLeave = () => {
    target.current.x = 0;
    target.current.y = 0;
  };

  const pStrength = useMemo(() => ({ back: 3, mid: 8, front: 12, extras: 15 }), []);
  const pStyle = (depth: number): React.CSSProperties => ({
    transform: `translate(calc(var(--mx) * ${depth}px), calc(var(--my) * ${depth}px))`,
    willChange: 'transform',
  });

  const W = 1024;
  const cx = 512;
  const cy = 560;

  const arc = (r: number, a0: number, a1: number) => {
    const toRad = (d: number) => (d * Math.PI) / 180;
    const p0 = { x: cx + r * Math.cos(toRad(a0)), y: cy + r * Math.sin(toRad(a0)) };
    const p1 = { x: cx + r * Math.cos(toRad(a1)), y: cy + r * Math.sin(toRad(a1)) };
    const large = Math.abs(a1 - a0) > 180 ? 1 : 0;
    const sweep = a1 > a0 ? 1 : 0;
    return `M ${p0.x.toFixed(2)} ${p0.y.toFixed(2)} A ${r} ${r} 0 ${large} ${sweep} ${p1.x.toFixed(2)} ${p1.y.toFixed(2)}`;
  };

  const leftTraces = [
    {
      d: `M 410 480 L 290 480 L 250 440 L 150 440`,
      tone: 'cool',
      nodes: [
        { x: 150, y: 440, r: 10 },
        { x: 250, y: 440, r: 6, hollow: true },
      ],
    },
    {
      d: `M 410 520 L 310 520 L 250 560 L 170 560`,
      tone: 'cool',
      nodes: [
        { x: 170, y: 560, r: 8 },
        { x: 250, y: 560, r: 6, hollow: true },
      ],
    },
    { d: `M 410 560 L 300 560 L 260 610 L 190 610`, tone: 'neutral', nodes: [{ x: 190, y: 610, r: 8 }] },
    { d: `M 410 410 L 320 410 L 280 360 L 200 360`, tone: 'neutral', nodes: [{ x: 200, y: 360, r: 8, hollow: true }] },
    { d: `M 360 360 L 320 320 L 260 320`, tone: 'cool', nodes: [{ x: 260, y: 320, r: 7 }] },
    { d: `M 330 610 L 290 660 L 230 660`, tone: 'cool', nodes: [{ x: 230, y: 660, r: 7, hollow: true }] },
  ] as const;

  const spineTraces = [`M 490 780 L 490 860`, `M 512 780 L 512 900`, `M 534 780 L 534 860`, `M 470 820 L 470 890`, `M 554 820 L 554 890`] as const;

  const segsCool = [
    { r: 250, a0: 205, a1: 250, w: 18 },
    { r: 250, a0: 265, a1: 305, w: 18 },
    { r: 250, a0: 320, a1: 350, w: 18 },
    { r: 220, a0: 195, a1: 230, w: 12 },
    { r: 220, a0: 250, a1: 280, w: 12 },
    { r: 220, a0: 300, a1: 330, w: 12 },
  ] as const;

  const segsWarm = [
    { r: 250, a0: 20, a1: 60, w: 18 },
    { r: 250, a0: 75, a1: 115, w: 18 },
    { r: 250, a0: 130, a1: 165, w: 18 },
    { r: 220, a0: 35, a1: 70, w: 12 },
    { r: 220, a0: 90, a1: 120, w: 12 },
    { r: 220, a0: 140, a1: 165, w: 12 },
  ] as const;

  const ringN = 18;
  const ringR = 68;
  const pts = useMemo(
    () =>
      Array.from({ length: ringN }, (_, i) => {
        const t = (i / ringN) * Math.PI * 2;
        return { x: cx + ringR * Math.cos(t), y: cy + ringR * Math.sin(t) };
      }),
    [ringN, ringR]
  );

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="relative w-full h-full flex items-center justify-center cursor-pointer group"
      style={{ ['--mx' as any]: '0', ['--my' as any]: '0' }}
    >
      <style>{`
        @keyframes stream-flow { 0% { stroke-dashoffset: 1000; } 100% { stroke-dashoffset: 0; } }
        .anim-stream { stroke-dasharray: 100 900; animation: stream-flow 3s linear infinite; }

        @keyframes organic-pulse { 0%, 100% { opacity: 0.6; transform: scale(1); } 50% { opacity: 1; transform: scale(1.05); } }
        .anim-organic-pulse { transform-origin: 512px 560px; animation: organic-pulse 4s ease-in-out infinite; }

        @keyframes segment-scan { 0%, 100% { stroke-opacity: 0.3; } 50% { stroke-opacity: 1; } }
        .anim-scan-1 { animation: segment-scan 3s ease-in-out infinite; animation-delay: 0s; }
        .anim-scan-2 { animation: segment-scan 3s ease-in-out infinite; animation-delay: 0.5s; }
        .anim-scan-3 { animation: segment-scan 3s ease-in-out infinite; animation-delay: 1s; }
      `}</style>

      {/* hover glow (kept controlled, not “too much”) */}
      <div className="absolute inset-0 rounded-full blur-[14px] bg-cyan-500/10 group-hover:bg-cyan-500/18 transition-colors duration-500" />

      <svg viewBox="0 0 1024 1024" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
        <defs>
          <linearGradient id="coolGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#36e4ff" />
            <stop offset="60%" stopColor="#4c8dff" />
            <stop offset="100%" stopColor="#2b5cff" />
          </linearGradient>
          <linearGradient id="warmGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#f7b955" />
            <stop offset="45%" stopColor="#f0b2a6" />
            <stop offset="100%" stopColor="#d77cff" />
          </linearGradient>

          <linearGradient id="streamCool" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="transparent" />
            <stop offset="50%" stopColor="#a3f5ff" />
            <stop offset="100%" stopColor="transparent" />
          </linearGradient>
          <linearGradient id="streamWarm" x1="100%" y1="0%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="transparent" />
            <stop offset="50%" stopColor="#ffdab5" />
            <stop offset="100%" stopColor="transparent" />
          </linearGradient>

          <filter id="strongGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        <g style={pStyle(pStrength.mid)}>
          <g strokeLinecap="round" strokeLinejoin="round" fill="none">
            {leftTraces.map((t, i) => (
              <g key={`L-${i}`}>
                <path d={t.d} stroke={t.tone === 'cool' ? '#4c8dff' : '#b8c7ff'} strokeOpacity={0.15} strokeWidth={6} />
                <path
                  d={t.d}
                  stroke="url(#streamCool)"
                  strokeWidth={6}
                  className="anim-stream"
                  style={{ animationDuration: `${2 + i * 0.5}s` }}
                  filter="url(#strongGlow)"
                />
                {t.nodes.map((n, j) => (
                  <circle
                    key={`Ln-${i}-${j}`}
                    cx={n.x}
                    cy={n.y}
                    r={n.r}
                    fill={(n as any).hollow ? 'none' : '#bff8ff'}
                    stroke={(n as any).hollow ? '#bff8ff' : 'none'}
                    strokeWidth={(n as any).hollow ? 4 : 0}
                    opacity={0.8}
                  />
                ))}
              </g>
            ))}
          </g>

          <g transform={`translate(${W} 0) scale(-1 1)`} strokeLinecap="round" strokeLinejoin="round" fill="none">
            {leftTraces.map((t, i) => (
              <g key={`R-${i}`}>
                <path d={t.d} stroke={t.tone === 'cool' ? '#f7b955' : '#ffd9b3'} strokeOpacity={0.15} strokeWidth={6} />
                <path
                  d={t.d}
                  stroke="url(#streamWarm)"
                  strokeWidth={6}
                  className="anim-stream"
                  style={{ animationDuration: `${2.5 + i * 0.4}s` }}
                  filter="url(#strongGlow)"
                />
                {t.nodes.map((n, j) => (
                  <circle
                    key={`Rn-${i}-${j}`}
                    cx={n.x}
                    cy={n.y}
                    r={n.r}
                    fill={(n as any).hollow ? 'none' : '#ffe1b5'}
                    stroke={(n as any).hollow ? '#ffe1b5' : 'none'}
                    strokeWidth={(n as any).hollow ? 4 : 0}
                    opacity={0.8}
                  />
                ))}
              </g>
            ))}
          </g>

          <g stroke="#cfd8ff" strokeOpacity={0.35} strokeWidth={6} strokeLinecap="round">
            {spineTraces.map((d, i) => (
              <path key={`sp-${i}`} d={d} />
            ))}
          </g>
        </g>

        <g style={pStyle(pStrength.front)}>
          <circle cx={cx} cy={cy} r={292} fill="none" stroke="#9bb7ff" strokeOpacity={0.08} strokeWidth={36} />
          <circle cx={cx} cy={cy} r={270} fill="none" stroke="#1a2644" strokeWidth={34} />
          <circle cx={cx} cy={cy} r={270} fill="none" stroke="#ffffff" strokeOpacity={0.06} strokeWidth={2} />

          {segsCool.map((s, i) => (
            <path
              key={`c-${i}`}
              d={arc(s.r, s.a0, s.a1)}
              stroke="url(#coolGrad)"
              strokeWidth={s.w}
              strokeLinecap="round"
              fill="none"
              className={`anim-scan-${(i % 3) + 1}`}
            />
          ))}

          {segsWarm.map((s, i) => (
            <path
              key={`w-${i}`}
              d={arc(s.r, s.a0, s.a1)}
              stroke="url(#warmGrad)"
              strokeWidth={s.w}
              strokeLinecap="round"
              fill="none"
              className={`anim-scan-${(i % 3) + 1}`}
            />
          ))}

          <circle cx={cx} cy={cy} r={190} fill="none" stroke="#9bb7ff" strokeOpacity={0.18} strokeWidth={4} />
          <circle cx={cx} cy={cy} r={165} fill="none" stroke="#9bb7ff" strokeOpacity={0.1} strokeWidth={2} />
          <path d={arc(150, 210, 320)} stroke="url(#coolGrad)" strokeOpacity={0.55} strokeWidth={10} strokeLinecap="round" fill="none" />
          <path d={arc(150, 30, 150)} stroke="url(#warmGrad)" strokeOpacity={0.55} strokeWidth={10} strokeLinecap="round" fill="none" />
        </g>

        <g style={pStyle(pStrength.front)}>
          <circle cx={cx} cy={cy} r={120} fill="#070b12" stroke="#1d2b4a" strokeWidth={6} />
          <g className="anim-organic-pulse">
            <circle cx={cx} cy={cy} r={16} fill="#ffffff" opacity={0.98} filter="url(#strongGlow)" />
            {pts.map((p, i) => (
              <g key={`p-g-${i}`}>
                <circle cx={p.x} cy={p.y} r={5.2} fill="#ffffff" opacity={0.95} />
                <line x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#ffffff" strokeWidth={1.4} opacity={0.35} />
                <line x1={p.x} y1={p.y} x2={pts[(i + 1) % pts.length].x} y2={pts[(i + 1) % pts.length].y} stroke="#ffffff" strokeWidth={1.8} opacity={0.45} />
              </g>
            ))}
          </g>
        </g>

        <g style={pStyle(pStrength.extras)}>
          <path d={`M ${cx - 42} ${cy - 300} L ${cx - 20} ${cy - 330} H ${cx + 20} L ${cx + 42} ${cy - 300} Z`} fill="#0a1222" stroke="#2a3b66" strokeWidth={3} opacity={0.95} />
          <rect x={cx - 18} y={cy - 312} width={36} height={28} rx={6} fill="#0e1730" stroke="#2a3b66" strokeWidth={2} />
          <g transform={`translate(120 560)`}>
            <rect x={-18} y={-18} width={36} height={36} fill="none" stroke="#86f0ff" strokeWidth={4} opacity={0.75} transform="rotate(45)" />
          </g>
          <g transform={`translate(904 560)`}>
            <rect x={-18} y={-18} width={36} height={36} fill="none" stroke="#f7b955" strokeWidth={4} opacity={0.75} transform="rotate(45)" />
          </g>
          <g transform={`translate(${cx} 930) rotate(45)`}>
            <rect x={-22} y={-22} width={44} height={44} fill="none" stroke="#f0b2a6" strokeWidth={5} opacity={0.9} />
            <rect x={-10} y={-10} width={20} height={20} fill="none" stroke="#f7b955" strokeWidth={4} opacity={0.7} />
          </g>
        </g>
      </svg>
    </div>
  );
}
