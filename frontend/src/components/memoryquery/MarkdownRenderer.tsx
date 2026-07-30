"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Check, Copy } from "lucide-react";

// ---------------------------------------------------------------------------
// Copy Button — for code blocks
// ---------------------------------------------------------------------------
function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-2.5 right-2.5 flex items-center gap-1.5 px-2 py-1 rounded-md bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-slate-400 hover:text-white transition-all duration-150 text-[10px] font-mono"
      title="Copy code"
    >
      {copied ? (
        <>
          <Check size={10} className="text-emerald-400" />
          <span className="text-emerald-400">Copied</span>
        </>
      ) : (
        <>
          <Copy size={10} />
          <span>Copy</span>
        </>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// MarkdownRenderer
// ---------------------------------------------------------------------------
export function MarkdownRenderer({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // ── Headings ──────────────────────────────────────────────────────
        h1: ({ children }) => (
          <h1 className="text-2xl font-black text-white mt-6 mb-3 pb-2 border-b border-white/10 tracking-tight leading-tight">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-xl font-bold text-white mt-5 mb-2.5 tracking-tight leading-tight">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-base font-bold text-slate-100 mt-4 mb-2 tracking-tight">
            {children}
          </h3>
        ),
        h4: ({ children }) => (
          <h4 className="text-sm font-bold text-slate-200 mt-3 mb-1.5 uppercase tracking-widest">
            {children}
          </h4>
        ),
        h5: ({ children }) => (
          <h5 className="text-sm font-semibold text-slate-300 mt-2 mb-1">
            {children}
          </h5>
        ),
        h6: ({ children }) => (
          <h6 className="text-xs font-semibold text-slate-400 mt-2 mb-1 uppercase tracking-widest">
            {children}
          </h6>
        ),

        // ── Paragraph ─────────────────────────────────────────────────────
        p: ({ children }) => (
          <p className="text-[14px] leading-7 text-slate-300 mb-3 last:mb-0">
            {children}
          </p>
        ),

        // ── Lists ─────────────────────────────────────────────────────────
        ul: ({ children }) => (
          <ul className="space-y-1.5 mb-3 pl-1">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="space-y-1.5 mb-3 pl-1 list-decimal list-inside">
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li className="flex items-start gap-2.5 text-[14px] leading-6 text-slate-300">
            <span className="mt-[9px] w-1.5 h-1.5 rounded-full bg-primary-500/70 flex-shrink-0" />
            <span className="flex-1">{children}</span>
          </li>
        ),

        // ── Ordered list items need different treatment ───────────────────
        // (remark-gfm handles numbering via ol > li)

        // ── Blockquote ────────────────────────────────────────────────────
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-primary-500/50 pl-4 py-0.5 my-3 bg-primary-500/5 rounded-r-lg">
            <div className="text-[13px] text-slate-400 italic leading-relaxed">
              {children}
            </div>
          </blockquote>
        ),

        // ── Inline code ───────────────────────────────────────────────────
        code: ({ node, className, children, ...props }: any) => {
          const match = /language-(\w+)/.exec(className || "");
          const isBlock =
            match ||
            (typeof children === "string" &&
              (children as string).includes("\n"));

          if (isBlock) {
            const lang = match?.[1] ?? "text";
            const codeString = String(children).replace(/\n$/, "");

            return (
              <div className="relative my-4 rounded-xl overflow-hidden border border-white/[0.07] shadow-xl">
                {/* Language badge */}
                <div className="flex items-center justify-between px-4 py-2 bg-[#1a1d2e] border-b border-white/[0.06]">
                  <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">
                    {lang}
                  </span>
                  <CopyButton code={codeString} />
                </div>
                <SyntaxHighlighter
                  style={oneDark}
                  language={lang}
                  PreTag="div"
                  customStyle={{
                    margin: 0,
                    padding: "1rem 1.25rem",
                    background: "#0d0f1a",
                    fontSize: "13px",
                    lineHeight: "1.7",
                    borderRadius: 0,
                  }}
                  codeTagProps={{
                    style: {
                      fontFamily: "var(--font-mono, 'Fira Code', monospace)",
                    },
                  }}
                >
                  {codeString}
                </SyntaxHighlighter>
              </div>
            );
          }

          return (
            <code
              className="px-1.5 py-0.5 rounded-md bg-primary-500/10 border border-primary-500/20 text-primary-300 font-mono text-[12px]"
              {...props}
            >
              {children}
            </code>
          );
        },

        // ── Pre (wrapper for code blocks) — handled inside code above ─────
        pre: ({ children }) => <>{children}</>,

        // ── Horizontal Rule ───────────────────────────────────────────────
        hr: () => (
          <hr className="my-4 border-none h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        ),

        // ── Bold / Italic / Strikethrough ─────────────────────────────────
        strong: ({ children }) => (
          <strong className="font-bold text-white">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="italic text-slate-300">{children}</em>
        ),
        del: ({ children }) => (
          <del className="line-through text-slate-500">{children}</del>
        ),

        // ── Links ─────────────────────────────────────────────────────────
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-400 hover:text-primary-300 underline underline-offset-2 decoration-primary-500/40 hover:decoration-primary-400 transition-colors"
          >
            {children}
          </a>
        ),

        // ── Tables (GFM) ──────────────────────────────────────────────────
        table: ({ children }) => (
          <div className="overflow-x-auto my-4 rounded-xl border border-white/[0.07] shadow-lg">
            <table className="w-full text-[13px] border-collapse">
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-white/[0.05] border-b border-white/10">
            {children}
          </thead>
        ),
        tbody: ({ children }) => (
          <tbody className="divide-y divide-white/[0.04]">{children}</tbody>
        ),
        tr: ({ children }) => (
          <tr className="transition-colors hover:bg-white/[0.03]">
            {children}
          </tr>
        ),
        th: ({ children }) => (
          <th className="px-4 py-2.5 text-left text-[10px] font-black uppercase tracking-widest text-slate-400">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-4 py-2.5 text-slate-300 leading-relaxed">
            {children}
          </td>
        ),

        // ── Task list checkboxes (GFM) ────────────────────────────────────
        input: ({ type, checked, ...props }: any) => {
          if (type === "checkbox") {
            return (
              <span
                className={`inline-flex items-center justify-center w-3.5 h-3.5 rounded border mr-1.5 flex-shrink-0 ${
                  checked
                    ? "bg-primary-500/30 border-primary-500/60 text-primary-400"
                    : "border-slate-600 bg-white/5"
                }`}
              >
                {checked && <Check size={9} />}
              </span>
            );
          }
          return <input type={type} {...props} />;
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
