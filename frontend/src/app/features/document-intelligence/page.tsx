"use client";

import FeaturePageLayout from "@/components/landing/FeaturePageLayout";

const icon = (
  <svg
    viewBox="0 0 24 24"
    className="w-12 h-12"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
  >
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" />
    <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
  </svg>
);

const benefits = [
  "Support for PDF, DOCX, TXT, Markdown, and more",
  "Automatic text extraction and OCR for scanned docs",
  "Table and image extraction",
  "Code file parsing with syntax awareness",
  "Batch upload for large document sets",
  "Progress tracking for long uploads",
];

export default function DocumentIntelligencePage() {
  return (
    <FeaturePageLayout
      title="Document Intelligence"
      subtitle="Upload PDFs, docs, and text. FAIM automatically extracts and connects knowledge."
      gradient="from-orange-500 to-amber-500"
      icon={icon}
      benefits={benefits}
    >
      <h2 className="text-2xl font-bold text-white mb-4">
        Turn Documents Into Knowledge
      </h2>
      <p className="text-slate-400 mb-6">
        Drag and drop your files, and FAIM does the rest. We extract text,
        understand structure, identify key concepts, and integrate everything
        into your knowledge graph.
      </p>

      <h3 className="text-xl font-semibold text-white mb-3">
        Multi-Format Support
      </h3>
      <p className="text-slate-400 mb-6">
        PDF, Word, PowerPoint, plain text, Markdown, code files - FAIM handles
        them all. Even scanned documents get OCR processing.
      </p>

      <h3 className="text-xl font-semibold text-white mb-3">
        Smart Extraction
      </h3>
      <p className="text-slate-400 mb-6">
        We don't just extract text. FAIM understands document structure -
        headings, sections, tables, and lists are preserved and used to create
        meaningful connections.
      </p>

      <h3 className="text-xl font-semibold text-white mb-3">
        Automatic Linking
      </h3>
      <p className="text-slate-400">
        As documents are processed, FAIM automatically finds connections to
        existing knowledge. Your new document enriches everything you already
        know.
      </p>
    </FeaturePageLayout>
  );
}
