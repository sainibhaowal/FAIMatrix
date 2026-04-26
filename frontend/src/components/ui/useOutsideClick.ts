"use client";

import { useEffect } from "react";

export function useOutsideClick(
  refs: React.RefObject<HTMLElement> | React.RefObject<HTMLElement>[],
  handler: (e: MouseEvent | TouchEvent) => void,
  active = true,
) {
  useEffect(() => {
    if (!active) return;

    const listener = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node;
      const refList = Array.isArray(refs) ? refs : [refs];

      // If clicking inside any of the refs, do nothing
      const isInside = refList.some(
        (r) => r.current && r.current.contains(target),
      );
      if (isInside) return;

      handler(event);
    };

    document.addEventListener("mousedown", listener);
    document.addEventListener("touchstart", listener);
    return () => {
      document.removeEventListener("mousedown", listener);
      document.removeEventListener("touchstart", listener);
    };
  }, [refs, handler, active]);
}
