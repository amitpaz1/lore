import { homedir } from 'os';
import { join } from 'path';
import { ulid } from 'ulid';
import type { Store } from './store/base.js';
import { SqliteStore } from './store/sqlite.js';
import type { Lesson, PublishOptions, ListOptions } from './types.js';

/** Options for constructing a Lore instance. */
export interface LoreOptions {
  project?: string;
  dbPath?: string;
  store?: Store;
}

function utcNowIso(): string {
  return new Date().toISOString();
}

/**
 * Main entry point for the Lore SDK.
 *
 * Usage:
 * ```ts
 * const lore = new Lore();
 * const id = await lore.publish({ problem: "...", resolution: "..." });
 * const lesson = await lore.get(id);
 * ```
 */
export class Lore {
  private store: Store;
  private project: string | undefined;

  constructor(options?: LoreOptions) {
    this.project = options?.project;

    if (options?.store) {
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

    const now = utcNowIso();
    const lesson: Lesson = {
      id: ulid(),
      problem: opts.problem,
      resolution: opts.resolution,
      context: opts.context ?? null,
      tags: opts.tags ?? [],
      confidence,
      source: opts.source ?? null,
      project: opts.project ?? this.project ?? null,
      embedding: null,
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
