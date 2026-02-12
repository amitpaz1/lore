import { homedir } from 'os';
import { join } from 'path';
import { ulid } from 'ulid';
import type { Store } from './store/base.js';
import { SqliteStore } from './store/sqlite.js';
import { RemoteStore } from './store/remote.js';
import type {
  Lesson,
  PublishOptions,
  ListOptions,
  QueryResult,
  QueryOptions,
  EmbeddingFn,
  RedactPattern,
} from './types.js';
import {
  serializeEmbedding,
  deserializeEmbedding,
  cosineSimilarity,
  decayFactor,
  voteFactor,
} from './embed.js';
import { RedactionPipeline } from './redact.js';
import { asPrompt as _asPrompt } from './prompt.js';

const DEFAULT_HALF_LIFE_DAYS = 30;

/** Options for constructing a Lore instance. */
export interface LoreOptions {
  project?: string;
  dbPath?: string;
  store?: Store | 'remote';
  apiUrl?: string;
  apiKey?: string;
  embeddingFn?: EmbeddingFn;
  redact?: boolean;
  redactPatterns?: RedactPattern[];
  decayHalfLifeDays?: number;
}

function utcNowIso(): string {
  return new Date().toISOString();
}

/**
 * Main entry point for the Lore SDK.
 */
export class Lore {
  private store: Store;
  private project: string | undefined;
  private embeddingFn: EmbeddingFn | undefined;
  private redactor: RedactionPipeline | null;
  private halfLifeDays: number;

  constructor(options?: LoreOptions) {
    this.project = options?.project;
    this.halfLifeDays = options?.decayHalfLifeDays ?? DEFAULT_HALF_LIFE_DAYS;

    // Embedding
    this.embeddingFn = options?.embeddingFn;

    // Redaction
    const redactEnabled = options?.redact !== false;
    if (redactEnabled) {
      const customPatterns = options?.redactPatterns?.map(
        ([pat, label]) => [pat, label] as [RegExp | string, string],
      );
      this.redactor = new RedactionPipeline(customPatterns);
    } else {
      this.redactor = null;
    }

    if (options?.store === 'remote') {
      if (!options.apiUrl || !options.apiKey) {
        throw new Error('apiUrl and apiKey are required when store is "remote"');
      }
      this.store = new RemoteStore({ apiUrl: options.apiUrl, apiKey: options.apiKey });
    } else if (options?.store && typeof options.store !== 'string') {
      this.store = options.store;
    } else {
      const dbPath = options?.dbPath ?? join(homedir(), '.lore', 'default.db');
      this.store = new SqliteStore(dbPath);
    }
  }

  /**
   * Publish a new lesson. Returns the lesson ID (ULID).
   */
  async publish(opts: PublishOptions): Promise<string> {
    const confidence = opts.confidence ?? 0.5;
    if (confidence < 0 || confidence > 1) {
      throw new RangeError(`confidence must be between 0.0 and 1.0, got ${confidence}`);
    }

    // Redact sensitive data before storage
    let problem = opts.problem;
    let resolution = opts.resolution;
    let context = opts.context ?? null;

    if (this.redactor) {
      problem = this.redactor.run(problem);
      resolution = this.redactor.run(resolution);
      if (context) {
        context = this.redactor.run(context);
      }
    }

    // Compute embedding if we have an embedding function
    let embeddingBuf: Buffer | null = null;
    if (this.embeddingFn) {
      const embedText = context
        ? `${problem} ${resolution} ${context}`
        : `${problem} ${resolution}`;
      const vec = await this.embeddingFn(embedText);
      embeddingBuf = serializeEmbedding(vec);
    }

    const now = utcNowIso();
    const lesson: Lesson = {
      id: ulid(),
      problem,
      resolution,
      context,
      tags: opts.tags ?? [],
      confidence,
      source: opts.source ?? null,
      project: opts.project ?? this.project ?? null,
      embedding: embeddingBuf,
      createdAt: now,
      updatedAt: now,
      expiresAt: null,
      upvotes: 0,
      downvotes: 0,
      meta: null,
    };

    await this.store.save(lesson);
    return lesson.id;
  }

  /**
   * Query lessons by semantic similarity, optionally filtered by tags.
   * Requires embeddingFn to be set.
   */
  async query(text: string, options?: QueryOptions): Promise<QueryResult[]> {
    if (!this.embeddingFn) {
      throw new Error('query() requires an embeddingFn to be configured');
    }

    const limit = options?.limit ?? 5;
    const minConfidence = options?.minConfidence ?? 0.0;
    const tags = options?.tags;
    const now = new Date();

    // Get all candidates
    let candidates = await this.store.list({ project: this.project ?? undefined });

    // Filter expired
    candidates = candidates.filter((l) => {
      if (!l.expiresAt) return true;
      return new Date(l.expiresAt) > now;
    });

    // Filter by tags
    if (tags && tags.length > 0) {
      const tagSet = new Set(tags);
      candidates = candidates.filter((l) =>
        [...tagSet].every((t) => l.tags.includes(t)),
      );
    }

    // Filter by min confidence
    if (minConfidence > 0) {
      candidates = candidates.filter((l) => l.confidence >= minConfidence);
    }

    // Filter to those with embeddings
    candidates = candidates.filter((l) => l.embedding !== null && l.embedding.length > 0);
    if (candidates.length === 0) return [];

    // Embed query
    const queryVec = await this.embeddingFn(text);

    // Score each candidate
    const results: QueryResult[] = [];
    for (const lesson of candidates) {
      const lessonVec = deserializeEmbedding(lesson.embedding!);
      const cosine = cosineSimilarity(queryVec, lessonVec);

      const ageDays =
        (now.getTime() - new Date(lesson.createdAt).getTime()) / (86400 * 1000);
      const timeFactor = decayFactor(ageDays, this.halfLifeDays);
      const vFactor = voteFactor(lesson.upvotes, lesson.downvotes);
      const decay = lesson.confidence * timeFactor * vFactor;
      const finalScore = cosine * decay;

      results.push({ lesson, score: finalScore });
    }

    results.sort((a, b) => b.score - a.score);
    return results.slice(0, limit);
  }

  /** Upvote a lesson. */
  async upvote(lessonId: string): Promise<void> {
    const lesson = await this.store.get(lessonId);
    if (!lesson) throw new Error(`Lesson not found: ${lessonId}`);
    lesson.upvotes += 1;
    lesson.updatedAt = utcNowIso();
    await this.store.update(lesson);
  }

  /** Downvote a lesson. */
  async downvote(lessonId: string): Promise<void> {
    const lesson = await this.store.get(lessonId);
    if (!lesson) throw new Error(`Lesson not found: ${lessonId}`);
    lesson.downvotes += 1;
    lesson.updatedAt = utcNowIso();
    await this.store.update(lesson);
  }

  /** Format query results for system prompt injection. */
  asPrompt(lessons: QueryResult[], maxTokens = 1000): string {
    return _asPrompt(lessons, maxTokens);
  }

  /** Get a lesson by ID. */
  async get(lessonId: string): Promise<Lesson | null> {
    return this.store.get(lessonId);
  }

  /** List lessons, optionally filtered by project. */
  async list(options?: ListOptions): Promise<Lesson[]> {
    return this.store.list(options);
  }

  /** Delete a lesson by ID. */
  async delete(lessonId: string): Promise<boolean> {
    return this.store.delete(lessonId);
  }

  /** Close underlying store. */
  async close(): Promise<void> {
    return this.store.close();
  }
}
