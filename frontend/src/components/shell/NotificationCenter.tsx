"use client";

import React, { useRef, useState } from "react";
import { Dropdown } from "./topbar/Dropdown";
import { useOutsideClick } from "../ui/useOutsideClick";

function IconBell(props: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={props.className} fill="none">
      <path
        d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// Placeholder notifications
const MOCK_NOTIFS = [
  {
    id: "n1",
    title: "Analysis completed",
    msg: "Your graph analysis for 'Project Titan' is ready.",
    time: "2m ago",
    unread: true,
  },
  {
    id: "n2",
    title: "System update",
    msg: "FAIM Core updated to v2.1.0.",
    time: "1h ago",
    unread: true,
  },
  {
    id: "n3",
    title: "Memory limit warning",
    msg: "Graph size approaching 80% of allocated memory.",
    time: "3h ago",
    unread: false,
  },
];

export function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const anchorRef = useRef<HTMLButtonElement>(null);
  const [notifs, setNotifs] = useState(MOCK_NOTIFS);

  const unreadCount = notifs.filter((n) => n.unread).length;

  const markAllRead = () => {
    setNotifs((prev) => prev.map((n) => ({ ...n, unread: false })));
  };

  const removeNotif = (id: string) => {
    setNotifs((prev) => prev.filter((n) => n.id !== id));
  };

  return (
    <div className="relative">
      <button
        ref={anchorRef}
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 text-slate-400 hover:text-white transition-colors"
        title="Notifications"
      >
        <IconBell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute top-2 right-2.5 h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.8)]" />
        )}
      </button>

      <Dropdown
        open={open}
        anchorRef={anchorRef}
        onClose={() => setOpen(false)}
        className="w-[360px]"
      >
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
          <div className="text-[12px] font-semibold text-slate-200">
            Notifications
          </div>
          {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="text-[10px] text-cyan-400 hover:text-cyan-300"
              >
                Mark all read
              </button>
            )}
        </div>

        <div className="max-h-[320px] overflow-y-auto">
          {notifs.length === 0 ? (
            <div className="px-4 py-8 text-center text-[11px] text-slate-500">
              No new notifications.
            </div>
          ) : (
             <ul className="divide-y divide-white/5">
              {notifs.map((n) => (
                <li
                  key={n.id}
                  className={`group relative px-4 py-3 hover:bg-white/5 ${
                    n.unread ? "bg-white/[0.02]" : ""
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <div className="truncate text-[12px] font-medium text-slate-200">
                          {n.title}
                        </div>
                         <div className="text-[10px] text-slate-500">
                          {n.time}
                        </div>
                      </div>
                      <div className="mt-0.5 text-[11px] text-slate-400 line-clamp-2">
                        {n.msg}
                      </div>
                    </div>
                    {n.unread && (
                        <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-500" />
                    )}
                  </div>
                   <button
                    onClick={(e) => {
                         e.stopPropagation();
                         removeNotif(n.id);
                    }}
                     className="absolute top-2 right-2 hidden p-1 text-slate-500 hover:text-white group-hover:block"
                     title="Dismiss"
                   >
                     <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                       <path d="M18 6L6 18M6 6l12 12" />
                     </svg>
                   </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        
        <div className="border-t border-white/10 px-4 py-2 text-center">
             <button className="text-[10px] text-slate-500 hover:text-slate-300">
                 View all
             </button>
        </div>
      </Dropdown>
    </div>
  );
}
