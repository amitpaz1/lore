import Database from 'better-sqlite3';
import type { Store } from './base.js';
import type { Lesson, ListOptions } from '../types.js';
import { mkdirSync } from 'fs';
import { dirname } from 'path';

const SCHEMA = `
CREATE TABLE IF NOT EXISTS lessons (
    id          TEXT PRIMARY KEY,
    problem     TEXT NOT NULL,
    resolution  TEXT NOT NULL,
    context     TEXT,
    tags        TEXT,
    confidence  REAL DEFAULT 0.5,
    source      TEXT,
    project     TEXT,
    embedding   BLOB,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    expires_at  TEXT,
    upvotes     INTEGER DEFAULT 0,
    downvotes   INTEGER DEFAULT 0,
    meta        TEXT
);
CREATE INDEX IF NOT EXISTS idx_lessons_project ON lessons(project);
CREATE INDEX IF NOT EXISTS idx_lessons_tags ON lessons(tags);
CREATE INDEX IF NOT EXISTS idx_lessons_created ON lessons(created_at);
`;

function lessonToRow(lesson: Lesson): Record<string, unknown> {
  return {
    id: lesson.id,
    problem: lesson.problem,
    resolution: lesson.resolution,
    context: lesson.context,
    tags: JSON.stringify(lesson.tags),
    confidence: lesson.confidence,
    source: lesson.source,
    project: lesson.project,
    embedding: lesson.embedding,
    created_at: lesson.createdAt,
    updated_at: lesson.updatedAt,
    expires_at: lesson.expiresAt,
    upvotes: lesson.upvotes,
    downvotes: lesson.downvotes,
    meta: lesson.meta != null ? JSON.stringify(lesson.meta) : null,
  };
}

function rowToLesson(row: Record<string, unknown>): Lesson {
  const tagsRaw = row['tags'] as string | null;
  const metaRaw = row['meta'] as string | null;

  return {
    id: row['id'] as string,
    problem: row['problem'] as string,
    resolution: row['resolution'] as string,
    context: (row['context'] as string) ?? null,
    tags: tagsRaw ? (JSON.parse(tagsRaw) as string[]) : [],
    confidence: row['confidence'] as number,
    source: (row['source'] as string) ?? null,
    project: (row['project'] as string) ?? null,
    embedding: (row['embedding'] as Buffer) ?? null,
    createdAt: row['created_at'] as string,
    updatedAt: row['updated_at'] as string,
    expiresAt: (row['expires_at'] as string) ?? null,
    upvotes: row['upvotes'] as number,
    downvotes: row['downvotes'] as number,
    meta: metaRaw ? (JSON.parse(metaRaw) as Record<string, unknown>) : null,
  };
}

/**
 * SQLite-backed lesson store. Cross-compatible with the Python SDK's SqliteStore.
 */
export class SqliteStore implements Store {
  private db: Database.Database;

  constructor(dbPath: string) {
    mkdirSync(dirname(dbPath), { recursive: true });
    this.db = new Database(dbPath);
    this.db.pragma('journal_mode = WAL');
    this.db.exec(SCHEMA);
  }

  async save(lesson: Lesson): Promise<void> {
    const row = lessonToRow(lesson);
    this.db.prepare(`
      INSERT OR REPLACE INTO lessons
        (id, problem, resolution, context, tags, confidence, source,
         project, embedding, created_at, updated_at, expires_at,
         upvotes, downvotes, meta)
      VALUES
        (@id, @problem, @resolution, @context, @tags, @confidence, @source,
         @project, @embedding, @created_at, @updated_at, @expires_at,
         @upvotes, @downvotes, @meta)
    `).run(row);
  }

  async get(lessonId: string): Promise<Lesson | null> {
    const row = this.db.prepare('SELECT * FROM lessons WHERE id = ?').get(lessonId) as Record<string, unknown> | undefined;
    return row ? rowToLesson(row) : null;
  }

  async list(options?: ListOptions): Promise<Lesson[]> {
    let query = 'SELECT * FROM lessons';
    const params: unknown[] = [];

    if (options?.project != null) {
      query += ' WHERE project = ?';
      params.push(options.project);
    }

    query += ' ORDER BY created_at DESC';

    if (options?.limit != null) {
      query += ' LIMIT ?';
      params.push(options.limit);
    }

    const rows = this.db.prepare(query).all(...params) as Record<string, unknown>[];
    return rows.map(rowToLesson);
  }

  async update(lesson: Lesson): Promise<boolean> {
    const row = lessonToRow(lesson);
    const result = this.db.prepare(`
      UPDATE lessons SET
        problem=@problem, resolution=@resolution, context=@context,
        tags=@tags, confidence=@confidence, source=@source,
        project=@project, embedding=@embedding, updated_at=@updated_at,
        expires_at=@expires_at, upvotes=@upvotes, downvotes=@downvotes,
        meta=@meta
      WHERE id=@id
    `).run(row);
    return result.changes > 0;
  }

  async delete(lessonId: string): Promise<boolean> {
    const result = this.db.prepare('DELETE FROM lessons WHERE id = ?').run(lessonId);
    return result.changes > 0;
  }

  async close(): Promise<void> {
    this.db.close();
  }
}
