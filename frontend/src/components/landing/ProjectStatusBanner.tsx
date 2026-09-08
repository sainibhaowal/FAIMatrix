export default function ProjectStatusBanner() {
  return (
    <aside
      aria-label="FAIMATRIX project status"
      data-testid="project-status-banner"
      role="note"
      className="mx-auto flex w-fit max-w-[calc(100%-2rem)] flex-wrap items-center justify-center gap-x-3 gap-y-1 rounded-full border border-cyan-400/25 bg-cyan-400/[0.07] px-4 py-2 text-center text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-200 shadow-[0_0_30px_rgba(34,211,238,0.08)] sm:text-[11px]"
    >
      <span>FAIMATRIX</span>
      <span aria-hidden="true" className="text-cyan-400/60">
        ·
      </span>
      <span>Project experiment</span>
      <span aria-hidden="true" className="text-cyan-400/60">
        ·
      </span>
      <span>Alpha version</span>
      <span className="basis-full normal-case tracking-normal text-cyan-100/60 sm:basis-auto">
        Research preview — capabilities and performance are still being validated.
      </span>
    </aside>
  );
}
