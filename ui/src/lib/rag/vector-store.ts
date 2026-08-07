/**
 * BlendPilot AI — In-Memory & Persisted Vector Store
 *
 * Fast vector similarity store supporting cosine similarity,
 * category filtering, and persistence.
 */

import { type DocumentChunk, type RAGQueryResult, type VectorRecord } from "./types";

export class VectorStore {
  private records: Map<string, VectorRecord> = new Map();

  constructor(initialRecords: VectorRecord[] = []) {
    for (const record of initialRecords) {
      this.records.set(record.id, record);
    }
  }

  /**
   * Add or update records in the vector store.
   */
  addRecords(records: VectorRecord[]): void {
    for (const record of records) {
      this.records.set(record.id, record);
    }
  }

  /**
   * Delete records matching a specific source.
   */
  deleteBySource(source: string): number {
    let count = 0;
    for (const [id, record] of this.records.entries()) {
      if (record.source === source) {
        this.records.delete(id);
        count++;
      }
    }
    return count;
  }

  /**
   * Clear all records in a category.
   */
  clearCategory(category: DocumentChunk["category"]): void {
    for (const [id, record] of this.records.entries()) {
      if (record.category === category) {
        this.records.delete(id);
      }
    }
  }

  /**
   * Search for top-K similar chunks using cosine similarity.
   */
  search(
    queryEmbedding: number[],
    options: {
      topK?: number;
      minScore?: number;
      category?: DocumentChunk["category"] | DocumentChunk["category"][];
    } = {}
  ): RAGQueryResult[] {
    const { topK = 5, minScore = 0.05, category } = options;
    const results: RAGQueryResult[] = [];

    const allowedCategories = category
      ? Array.isArray(category)
        ? category
        : [category]
      : null;

    for (const record of this.records.values()) {
      if (allowedCategories && !allowedCategories.includes(record.category)) {
        continue;
      }

      if (!record.embedding || record.embedding.length === 0) {
        continue;
      }

      const score = this.cosineSimilarity(queryEmbedding, record.embedding);
      if (score >= minScore) {
        const { embedding: _emb, ...chunk } = record;
        results.push({ chunk, score });
      }
    }

    // Sort descending by score
    results.sort((a, b) => b.score - a.score);
    return results.slice(0, topK);
  }

  /**
   * Return store statistics.
   */
  getStats(): { total: number; byCategory: Record<string, number> } {
    const byCategory: Record<string, number> = {};
    for (const record of this.records.values()) {
      byCategory[record.category] = (byCategory[record.category] || 0) + 1;
    }
    return {
      total: this.records.size,
      byCategory,
    };
  }

  getAllRecords(): VectorRecord[] {
    return Array.from(this.records.values());
  }

  private cosineSimilarity(vecA: number[], vecB: number[]): number {
    if (vecA.length !== vecB.length || vecA.length === 0) {
      return 0;
    }

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < vecA.length; i++) {
      dotProduct += vecA[i] * vecB[i];
      normA += vecA[i] * vecA[i];
      normB += vecB[i] * vecB[i];
    }

    if (normA === 0 || normB === 0) return 0;
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }
}

// Global Singleton for the Vector Store
const globalStore = globalThis as unknown as { __blendpilot_vector_store__?: VectorStore };

export function getGlobalVectorStore(): VectorStore {
  if (!globalStore.__blendpilot_vector_store__) {
    globalStore.__blendpilot_vector_store__ = new VectorStore();
  }
  return globalStore.__blendpilot_vector_store__;
}
