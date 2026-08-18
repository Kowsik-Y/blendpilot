/**
 * BlendPilot — Unified RAG Service
 *
 * Orchestrates document ingestion, vector indexing, and context retrieval
 * for Blender documentation and project history.
 */

import { BlenderDocsService } from "./blender-docs-service";
import { EmbeddingsService } from "./embeddings";
import { ProjectContextService } from "./project-context-service";
import {
  type DocumentChunk,
  type IngestDocumentPayload,
  type IngestionStats,
  type RAGContext,
  type RAGQueryResult,
  type VectorRecord,
} from "./types";
import { getGlobalVectorStore, VectorStore } from "./vector-store";

export interface RAGServiceOptions {
  apiKey?: string;
  baseUrl?: string;
  embeddingModel?: string;
}

export class RAGService {
  private vectorStore: VectorStore;
  private embeddings: EmbeddingsService;
  private initialized: boolean = false;

  constructor(options: RAGServiceOptions = {}) {
    this.vectorStore = getGlobalVectorStore();
    this.embeddings = new EmbeddingsService({
      apiKey: options.apiKey,
      baseUrl: options.baseUrl,
      model: options.embeddingModel,
    });
  }

  /**
   * Ensure standard Blender documentation and base guides are indexed.
   */
  async initializeBaseline(): Promise<IngestionStats> {
    if (this.initialized && this.vectorStore.getStats().total > 0) {
      return this.getStats();
    }

    const baselineDocs = BlenderDocsService.getBaselineBlenderDocuments();
    await this.ingestDocuments(baselineDocs);
    this.initialized = true;

    return this.getStats();
  }

  /**
   * Ingest raw documents into the vector store.
   */
  async ingestDocuments(docs: IngestDocumentPayload[]): Promise<number> {
    const recordsToEmbed: VectorRecord[] = [];
    const textsToEmbed: string[] = [];

    for (const doc of docs) {
      // Chunk document if lengthy
      const chunks = BlenderDocsService.splitMarkdownIntoChunks(doc.content, doc.title);

      for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i];
        const recordId = `${doc.source}_${i}`;
        const record: VectorRecord = {
          id: recordId,
          source: doc.source,
          category: doc.category,
          title: chunk.title,
          content: chunk.content,
          metadata: doc.metadata,
          tokenCount: chunk.tokenCount,
          createdAt: new Date().toISOString(),
        };

        recordsToEmbed.push(record);
        textsToEmbed.push(`${chunk.title}\n${chunk.content}`);
      }
    }

    if (recordsToEmbed.length === 0) return 0;

    // Generate embeddings
    const embeddings = await this.embeddings.embedDocuments(textsToEmbed);
    for (let i = 0; i < recordsToEmbed.length; i++) {
      recordsToEmbed[i].embedding = embeddings[i];
    }

    this.vectorStore.addRecords(recordsToEmbed);
    return recordsToEmbed.length;
  }

  /**
   * Ingest active project context for a specific user.
   */
  async syncProjectContext(userId: string, projectId?: string): Promise<number> {
    const projectDocs = await ProjectContextService.getProjectContextDocuments(
      userId,
      projectId
    );
    return this.ingestDocuments(projectDocs);
  }

  /**
   * Query the knowledge base and return formatted context for LLM prompts.
   */
  async retrieveContext(
    query: string,
    options: {
      topK?: number;
      maxTokens?: number;
      category?: DocumentChunk["category"] | DocumentChunk["category"][];
      minScore?: number;
    } = {}
  ): Promise<RAGContext> {
    await this.initializeBaseline();

    const { topK = 4, maxTokens = 1500, category, minScore = 0.05 } = options;

    const queryEmbedding = await this.embeddings.embedQuery(query);
    const results: RAGQueryResult[] = this.vectorStore.search(queryEmbedding, {
      topK,
      category,
      minScore,
    });

    let currentTokens = 0;
    const selectedChunks: RAGQueryResult[] = [];
    const formattedBlocks: string[] = [];

    for (const res of results) {
      if (currentTokens + res.chunk.tokenCount > maxTokens && selectedChunks.length > 0) {
        break;
      }

      selectedChunks.push(res);
      currentTokens += res.chunk.tokenCount;

      formattedBlocks.push(
        `### [${res.chunk.category.toUpperCase()}] ${res.chunk.title} (Source: ${res.chunk.source})\n${res.chunk.content}`
      );
    }

    return {
      formattedContext: formattedBlocks.join("\n\n---\n\n"),
      totalTokens: currentTokens,
      sources: selectedChunks.map((c) => ({
        title: c.chunk.title,
        source: c.chunk.source,
        score: Math.round(c.score * 100) / 100,
      })),
    };
  }

  /**
   * Return store statistics.
   */
  getStats(): IngestionStats {
    const stats = this.vectorStore.getStats();
    return {
      totalChunks: stats.total,
      categoryCounts: stats.byCategory,
      lastIngestedAt: new Date().toISOString(),
    };
  }
}
