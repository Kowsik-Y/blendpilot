/**
 * BlendPilot AI — Embeddings Service
 *
 * Generates vector embeddings for text chunks using:
 * 1. OpenAI / OpenAI-compatible API (if API key provided)
 * 2. Deterministic semantic hashing fallback (zero-dependency, always works offline)
 */

interface EmbeddingConfig {
  apiKey?: string;
  baseUrl?: string;
  model?: string;
}

const FALLBACK_DIMENSIONS = 128;

export class EmbeddingsService {
  private config: EmbeddingConfig;

  constructor(config: EmbeddingConfig = {}) {
    this.config = {
      model: config.model || "text-embedding-3-small",
      baseUrl: config.baseUrl || "https://api.openai.com/v1",
      apiKey: config.apiKey,
    };
  }

  /**
   * Embed a single text string into a float vector.
   */
  async embedQuery(text: string): Promise<number[]> {
    const results = await this.embedDocuments([text]);
    return results[0] || new Array(FALLBACK_DIMENSIONS).fill(0);
  }

  /**
   * Embed multiple text chunks into float vectors.
   */
  async embedDocuments(texts: string[]): Promise<number[][]> {
    if (this.config.apiKey && this.config.apiKey.trim().length > 0) {
      try {
        return await this.fetchOpenAIEmbeddings(texts);
      } catch (err) {
        console.warn("External embeddings API failed, falling back to local vectorizer:", err);
      }
    }
    return texts.map((t) => this.generateLocalEmbedding(t));
  }

  private async fetchOpenAIEmbeddings(texts: string[]): Promise<number[][]> {
    const response = await fetch(`${this.config.baseUrl}/embeddings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.config.apiKey}`,
      },
      body: JSON.stringify({
        input: texts,
        model: this.config.model,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Embedding API error (${response.status}): ${errText}`);
    }

    const data = (await response.json()) as {
      data: Array<{ embedding: number[]; index: number }>;
    };

    return data.data
      .sort((a, b) => a.index - b.index)
      .map((item) => item.embedding);
  }

  /**
   * Deterministic local embedding generator.
   * Produces a normalized term-frequency + n-gram vector for high-accuracy local similarity search.
   */
  private generateLocalEmbedding(text: string): number[] {
    const vector = new Array(FALLBACK_DIMENSIONS).fill(0);
    const cleaned = text.toLowerCase().replace(/[^a-z0-9_\s]/g, " ");
    const words = cleaned.split(/\s+/).filter(Boolean);

    for (let i = 0; i < words.length; i++) {
      const word = words[i];
      // Word hash
      const hash = this.hashString(word);
      const index = Math.abs(hash) % FALLBACK_DIMENSIONS;
      vector[index] += 1.0;

      // Bigram hash
      if (i < words.length - 1) {
        const bigram = `${word}_${words[i + 1]}`;
        const biHash = this.hashString(bigram);
        const biIdx = Math.abs(biHash) % FALLBACK_DIMENSIONS;
        vector[biIdx] += 1.5;
      }
    }

    // Normalize vector (L2 norm)
    const norm = Math.sqrt(vector.reduce((sum, v) => sum + v * v, 0));
    if (norm > 0) {
      return vector.map((v) => v / norm);
    }
    return vector;
  }

  private hashString(str: string): number {
    let hash = 5381;
    for (let i = 0; i < str.length; i++) {
      hash = (hash * 33) ^ str.charCodeAt(i);
    }
    return hash;
  }
}
