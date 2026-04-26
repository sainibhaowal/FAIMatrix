/**
 * FAIM-Native Mock Data
 *
 * Demo graph data with full FAIM properties for UI testing without backend.
 */

export interface MockNode {
  id: string;
  label?: string;
  level: number;
  vector_hash: string;
  parents: string[];
  fractions?: number[];
  residual?: number;
  opp_signature?: Record<string, number>;
  novelty?: number;
  importance?: number;
  evolution_flags?: string[];
  merged?: boolean;
  pruned?: boolean;
  preview?: string;
}

export interface MockLink {
  source: string;
  target: string;
  rel?: string;
  weight?: number;
}

export interface MockGraphData {
  nodes: MockNode[];
  links: MockLink[];
}

// Generate deterministic hash-like string
function mockHash(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash << 5) - hash + seed.charCodeAt(i);
    hash = hash & hash;
  }
  return `sha256:${Math.abs(hash).toString(16).padStart(16, "0")}`;
}

export const MOCK_GRAPH_DATA: MockGraphData = {
  nodes: [
    // Level 0 - Raw Atoms (Cyan)
    {
      id: "atom-001",
      label: "Machine Learning Basics",
      level: 0,
      vector_hash: mockHash("atom-001"),
      parents: [],
      novelty: 0.3,
      importance: 0.5,
      preview:
        "Introduction to supervised and unsupervised learning algorithms.",
    },
    {
      id: "atom-002",
      label: "Neural Network Architecture",
      level: 0,
      vector_hash: mockHash("atom-002"),
      parents: [],
      novelty: 0.4,
      importance: 0.6,
      preview: "Deep dive into layers, activations, and backpropagation.",
    },
    {
      id: "atom-003",
      label: "Transformer Models",
      level: 0,
      vector_hash: mockHash("atom-003"),
      parents: [],
      novelty: 0.5,
      importance: 0.7,
      preview: "Self-attention mechanisms and positional encoding.",
    },
    {
      id: "atom-004",
      label: "Graph Neural Networks",
      level: 0,
      vector_hash: mockHash("atom-004"),
      parents: [],
      novelty: 0.6,
      importance: 0.5,
      preview: "Message passing and node embeddings in graph structures.",
    },
    {
      id: "atom-005",
      label: "Vector Databases",
      level: 0,
      vector_hash: mockHash("atom-005"),
      parents: [],
      novelty: 0.35,
      importance: 0.4,
      preview: "Efficient similarity search with HNSW and IVF indexes.",
    },

    // Level 1 - Synthesized Concepts (Teal)
    {
      id: "concept-001",
      label: "Deep Learning Foundations",
      level: 1,
      vector_hash: mockHash("concept-001"),
      parents: ["atom-001", "atom-002"],
      fractions: [0.4, 0.6],
      residual: 0.15,
      novelty: 0.55,
      importance: 0.7,
      evolution_flags: ["merged"],
      merged: true,
      preview:
        "Unified understanding of ML fundamentals and neural architectures.",
    },
    {
      id: "concept-002",
      label: "Modern NLP Stack",
      level: 1,
      vector_hash: mockHash("concept-002"),
      parents: ["atom-003", "atom-002"],
      fractions: [0.7, 0.3],
      residual: 0.1,
      novelty: 0.65,
      importance: 0.8,
      preview: "Transformers applied to language understanding and generation.",
    },
    {
      id: "concept-003",
      label: "Semantic Memory Systems",
      level: 1,
      vector_hash: mockHash("concept-003"),
      parents: ["atom-004", "atom-005"],
      fractions: [0.5, 0.5],
      residual: 0.08,
      novelty: 0.7,
      importance: 0.75,
      opp_signature: { forgetting: -0.3, compression: 0.5 },
      preview: "Graph + vector hybrid for knowledge representation.",
    },

    // Level 2 - Higher Abstractions (Purple)
    {
      id: "abstract-001",
      label: "FAIM Architecture",
      level: 2,
      vector_hash: mockHash("abstract-001"),
      parents: ["concept-001", "concept-002", "concept-003"],
      fractions: [0.3, 0.35, 0.35],
      residual: 0.05,
      novelty: 0.85,
      importance: 0.95,
      evolution_flags: ["synthesized", "emergent"],
      opp_signature: { static: -0.8, dynamic: 0.9 },
      preview: "Self-evolving fractal memory with antisymmetric opposition.",
    },
    {
      id: "abstract-002",
      label: "Fractal Inheritance Model",
      level: 2,
      vector_hash: mockHash("abstract-002"),
      parents: ["concept-001", "concept-003"],
      fractions: [0.45, 0.55],
      residual: 0.12,
      novelty: 0.78,
      importance: 0.85,
      preview: "Σf=1 constraint with parent vectors and residual novelty.",
    },

    // Level 3 - Deep Invention (Deep Violet)
    {
      id: "invention-001",
      label: "Self-Inventing Memory",
      level: 3,
      vector_hash: mockHash("invention-001"),
      parents: ["abstract-001", "abstract-002"],
      fractions: [0.6, 0.4],
      residual: 0.02,
      novelty: 0.95,
      importance: 1.0,
      evolution_flags: ["emergent", "invention"],
      opp_signature: { entropy: -0.9, order: 0.95 },
      preview:
        "The engine that invents new concepts from compressed knowledge.",
    },

    // Pruned node example
    {
      id: "pruned-001",
      label: "Deprecated Approach",
      level: 1,
      vector_hash: mockHash("pruned-001"),
      parents: ["atom-001"],
      fractions: [1.0],
      novelty: 0.1,
      importance: 0.1,
      evolution_flags: ["pruned"],
      pruned: true,
      preview: "Redundant concept removed during evolution cycle.",
    },
  ],
  links: [
    // Inheritance edges
    { source: "atom-001", target: "concept-001", rel: "inherits", weight: 0.4 },
    { source: "atom-002", target: "concept-001", rel: "inherits", weight: 0.6 },
    { source: "atom-003", target: "concept-002", rel: "inherits", weight: 0.7 },
    { source: "atom-002", target: "concept-002", rel: "inherits", weight: 0.3 },
    { source: "atom-004", target: "concept-003", rel: "inherits", weight: 0.5 },
    { source: "atom-005", target: "concept-003", rel: "inherits", weight: 0.5 },
    {
      source: "concept-001",
      target: "abstract-001",
      rel: "inherits",
      weight: 0.3,
    },
    {
      source: "concept-002",
      target: "abstract-001",
      rel: "inherits",
      weight: 0.35,
    },
    {
      source: "concept-003",
      target: "abstract-001",
      rel: "inherits",
      weight: 0.35,
    },
    {
      source: "concept-001",
      target: "abstract-002",
      rel: "inherits",
      weight: 0.45,
    },
    {
      source: "concept-003",
      target: "abstract-002",
      rel: "inherits",
      weight: 0.55,
    },
    {
      source: "abstract-001",
      target: "invention-001",
      rel: "inherits",
      weight: 0.6,
    },
    {
      source: "abstract-002",
      target: "invention-001",
      rel: "inherits",
      weight: 0.4,
    },

    // Cross-links (semantic relationships)
    { source: "atom-001", target: "atom-002", rel: "related", weight: 0.3 },
    { source: "atom-003", target: "atom-004", rel: "related", weight: 0.25 },
    {
      source: "concept-002",
      target: "concept-003",
      rel: "related",
      weight: 0.4,
    },

    // Pruned tether
    { source: "atom-001", target: "pruned-001", rel: "tether", weight: 0.05 },
  ],
};

export default MOCK_GRAPH_DATA;
