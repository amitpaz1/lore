/**
 * Remote HTTP store implementation.
 * Mirrors Python RemoteStore — delegates to a Lore Cloud server via REST API.
 */

import type { Store } from './base.js';
import type { Lesson, ListOptions } from '../types.js';
import { LoreConnectionError, LoreAuthError, LessonNotFoundError } from '../errors.js';
import { deserializeEmbedding } from '../embed.js';

/** Options for constructing a RemoteStore. */
export interface RemoteStoreOptions {
  apiUrl: string;
  apiKey: string;
  timeoutMs?: number;
}

interface RequestOptions {
  method: string;
  path: string;
  body?: unknown;
  params?: Record<string, string>;
}

function lessonToDict(lesson: Lesson): Record<string, unknown> {
  const d: Record<string, unknown> = {
    problem: lesson.problem,
    resolution: lesson.resolution,
    context: lesson.context,
    tags: lesson.tags,
    confidence: lesson.confidence,
    source: lesson.source,
    project: lesson.project,
    created_at: lesson.createdAt,
    updated_at: lesson.updatedAt,
    expires_at: lesson.expiresAt,
    upvotes: lesson.upvotes,
    downvotes: lesson.downvotes,
    meta: lesson.meta ?? {},
  };
  if (lesson.embedding !== null && lesson.embedding.length > 0) {
    d.embedding = deserializeEmbedding(lesson.embedding);
  } else {
    d.embedding = [];
  }
  return d;
}

function responseToLesson(data: Record<string, unknown>): Lesson {
  const createdAt = String(data.created_at ?? '');
  const updatedAt = String(data.updated_at ?? '');
  const expiresAt = data.expires_at != null ? String(data.expires_at) : null;

  return {
    id: data.id as string,
    problem: data.problem as string,
    resolution: data.resolution as string,
    context: (data.context as string | null) ?? null,
    tags: (data.tags as string[]) ?? [],
    confidence: (data.confidence as number) ?? 0.5,
    source: (data.source as string | null) ?? null,
    project: (data.project as string | null) ?? null,
    embedding: null, // Server doesn't return embeddings in normal responses
    createdAt,
    updatedAt,
    expiresAt,
    upvotes: (data.upvotes as number) ?? 0,
    downvotes: (data.downvotes as number) ?? 0,
    meta: (data.meta as Record<string, unknown> | null) ?? null,
  };
}

/** HTTP-backed lesson store that delegates to a Lore Cloud server. */
export class RemoteStore implements Store {
  private readonly apiUrl: string;
  private readonly apiKey: string;
  private readonly timeoutMs: number;

  constructor(options: RemoteStoreOptions) {
    this.apiUrl = options.apiUrl.replace(/\/+$/, '');
    this.apiKey = options.apiKey;
    this.timeoutMs = options.timeoutMs ?? 30000;
  }

  private async request(opts: RequestOptions): Promise<Response> {
    let url = `${this.apiUrl}${opts.path}`;
    if (opts.params) {
      const qs = new URLSearchParams(opts.params).toString();
      if (qs) url += `?${qs}`;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    let resp: Response;
    try {
      resp = await fetch(url, {
        method: opts.method,
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
        signal: controller.signal,
      });
    } catch (err: unknown) {
      const error = err as Error;
      if (error.name === 'AbortError') {
        throw new LoreConnectionError(`Request timed out: ${url}`);
      }
      throw new LoreConnectionError(`Cannot connect to ${this.apiUrl}: ${error.message}`);
    } finally {
      clearTimeout(timer);
    }

    if (resp.status === 401 || resp.status === 403) {
      const text = await resp.text();
      throw new LoreAuthError(`Authentication failed (${resp.status}): ${text}`);
    }

    return resp;
  }

  async save(lesson: Lesson): Promise<void> {
    const payload = lessonToDict(lesson);
    const resp = await this.request({ method: 'POST', path: '/v1/lessons', body: payload });
    if (!resp.ok) {
      throw new Error(`Save failed (${resp.status}): ${await resp.text()}`);
    }
  }

  async get(lessonId: string): Promise<Lesson | null> {
    const resp = await this.request({ method: 'GET', path: `/v1/lessons/${lessonId}` });
    if (resp.status === 404) return null;
    if (!resp.ok) throw new Error(`Get failed (${resp.status}): ${await resp.text()}`);
    return responseToLesson(await resp.json() as Record<string, unknown>);
  }

  async list(options?: ListOptions): Promise<Lesson[]> {
    const params: Record<string, string> = {};
    if (options?.project != null) params.project = options.project;
    if (options?.limit != null) params.limit = String(options.limit);

    const resp = await this.request({ method: 'GET', path: '/v1/lessons', params });
    if (!resp.ok) throw new Error(`List failed (${resp.status}): ${await resp.text()}`);
    const data = await resp.json() as { lessons: Record<string, unknown>[] };
    return data.lessons.map(responseToLesson);
  }

  async update(lesson: Lesson): Promise<boolean> {
    const payload: Record<string, unknown> = {
      confidence: lesson.confidence,
      tags: lesson.tags,
      upvotes: lesson.upvotes,
      downvotes: lesson.downvotes,
      meta: lesson.meta ?? {},
    };
    const resp = await this.request({
      method: 'PATCH',
      path: `/v1/lessons/${lesson.id}`,
      body: payload,
    });
    if (resp.status === 404) return false;
    if (!resp.ok) throw new Error(`Update failed (${resp.status}): ${await resp.text()}`);
    return true;
  }

  async delete(lessonId: string): Promise<boolean> {
    const resp = await this.request({ method: 'DELETE', path: `/v1/lessons/${lessonId}` });
    if (resp.status === 404) return false;
    if (!resp.ok) throw new Error(`Delete failed (${resp.status}): ${await resp.text()}`);
    return true;
  }

  async search(
    embedding: number[],
    options?: { tags?: string[]; project?: string; limit?: number; minConfidence?: number },
  ): Promise<Array<Record<string, unknown>>> {
    const payload: Record<string, unknown> = {
      embedding,
      limit: options?.limit ?? 5,
      min_confidence: options?.minConfidence ?? 0.0,
    };
    if (options?.tags) payload.tags = options.tags;
    if (options?.project) payload.project = options.project;

    const resp = await this.request({ method: 'POST', path: '/v1/lessons/search', body: payload });
    if (!resp.ok) throw new Error(`Search failed (${resp.status}): ${await resp.text()}`);
    const data = await resp.json() as { lessons: Array<Record<string, unknown>> };
    return data.lessons;
  }

  async upvote(lessonId: string): Promise<void> {
    const resp = await this.request({
      method: 'PATCH',
      path: `/v1/lessons/${lessonId}`,
      body: { upvotes: '+1' },
    });
    if (resp.status === 404) throw new LessonNotFoundError(lessonId);
    if (!resp.ok) throw new Error(`Upvote failed (${resp.status}): ${await resp.text()}`);
  }

  async downvote(lessonId: string): Promise<void> {
    const resp = await this.request({
      method: 'PATCH',
      path: `/v1/lessons/${lessonId}`,
      body: { downvotes: '+1' },
    });
    if (resp.status === 404) throw new LessonNotFoundError(lessonId);
    if (!resp.ok) throw new Error(`Downvote failed (${resp.status}): ${await resp.text()}`);
  }

  async exportLessons(): Promise<Array<Record<string, unknown>>> {
    const resp = await this.request({ method: 'POST', path: '/v1/lessons/export' });
    if (!resp.ok) throw new Error(`Export failed (${resp.status}): ${await resp.text()}`);
    const data = await resp.json() as { lessons: Array<Record<string, unknown>> };
    return data.lessons;
  }

  async importLessons(lessons: Array<Record<string, unknown>>): Promise<number> {
    const resp = await this.request({
      method: 'POST',
      path: '/v1/lessons/import',
      body: { lessons },
    });
    if (!resp.ok) throw new Error(`Import failed (${resp.status}): ${await resp.text()}`);
    const data = await resp.json() as { imported: number };
    return data.imported;
  }

  async close(): Promise<void> {
    // No persistent connection to close with fetch
  }
}
