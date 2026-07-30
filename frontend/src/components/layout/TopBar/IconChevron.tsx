"use client";

import React from "react";

export function IconChevron(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="none">
      <path
        d="M7 10l5 5 5-5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
