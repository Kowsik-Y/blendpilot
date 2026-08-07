export interface DocumentChunk {
  id: string;
  source: string; // e.g. "blender_docs/objects.md", "project_context/sci_fi_crate"
  category: "blender_docs" | "project_context" | "mcp_tools" | "prompts" | "custom";
  title: string;
  content: string;
  metadata?: Record<string, unknown>;
  tokenCount: number;
  createdAt: string;
}

export interface VectorRecord extends DocumentChunk {
  embedding?: number[];
}

export interface RAGQueryResult {
  chunk: DocumentChunk;
  score: number;
}

export interface RAGContext {
  formattedContext: string;
  totalTokens: number;
  sources: Array<{ title: string; source: string; score: number }>;
}

export interface IngestDocumentPayload {
  source: string;
  category: DocumentChunk["category"];
  title: string;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface IngestionStats {
  totalChunks: number;
  categoryCounts: Record<string, number>;
  lastIngestedAt?: string;
}
