import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { SqliteStore } from '../src/store/sqlite.js';
import type { Lesson } from '../src/types.js';
import { mkdtempSync, rmSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';

function makeLessonFixture(overrides: Partial<Lesson> = {}): Lesson {
  return {
    id: 'test-id-1',
    problem: 'test problem',
    resolution: 'test resolution',
    context: null,
    tags: ['tag1'],
    confidence: 0.8,
    source: 'test-agent',
    project: null,
    embedding: null,
    createdAt: '2026-01-01T00:00:00.000Z',
    updatedAt: '2026-01-01T00:00:00.000Z',
    expiresAt: null,
    upvotes: 0,
    downvotes: 0,
    meta: null,
    ...overrides,
  };
}

describe('SqliteStore', () => {
  let store: SqliteStore;
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'lore-test-'));
    store = new SqliteStore(join(tmpDir, 'test.db'));
  });

  afterEach(async () => {
    await store?.close();
    rmSync(tmpDir, { recursive: true, force: true });
  });

  it('save and get', async () => {
    const lesson = makeLessonFixture();
    await store.save(lesson);
    const got = await store.get('test-id-1');
    expect(got).not.toBeNull();
    expect(got!.problem).toBe('test problem');
    expect(got!.tags).toEqual(['tag1']);
    expect(got!.confidence).toBe(0.8);
  });

  it('get returns null for missing', async () => {
    expect(await store.get('nope')).toBeNull();
  });

  it('save with meta round-trips JSON', async () => {
    await store.save(makeLessonFixture({ meta: { key: 'value' } }));
    const got = await store.get('test-id-1');
    expect(got!.meta).toEqual({ key: 'value' });
  });

  it('list returns ordered by created_at desc', async () => {
    await store.save(makeLessonFixture({ id: 'a', createdAt: '2026-01-01T00:00:00Z' }));
    await store.save(makeLessonFixture({ id: 'b', createdAt: '2026-01-02T00:00:00Z' }));
    const all = await store.list();
    expect(all).toHaveLength(2);
    expect(all[0].id).toBe('b');
  });

  it('list filters by project', async () => {
    await store.save(makeLessonFixture({ id: 'a', project: 'foo' }));
    await store.save(makeLessonFixture({ id: 'b', project: 'bar' }));
    const filtered = await store.list({ project: 'foo' });
    expect(filtered).toHaveLength(1);
    expect(filtered[0].id).toBe('a');
  });

  it('list respects limit', async () => {
    await store.save(makeLessonFixture({ id: 'a', createdAt: '2026-01-01T00:00:00Z' }));
    await store.save(makeLessonFixture({ id: 'b', createdAt: '2026-01-02T00:00:00Z' }));
    const limited = await store.list({ limit: 1 });
    expect(limited).toHaveLength(1);
  });

  it('update existing lesson', async () => {
    await store.save(makeLessonFixture());
    const ok = await store.update(makeLessonFixture({ problem: 'updated' }));
    expect(ok).toBe(true);
    const got = await store.get('test-id-1');
    expect(got!.problem).toBe('updated');
  });

  it('update returns false for missing', async () => {
    expect(await store.update(makeLessonFixture({ id: 'nope' }))).toBe(false);
  });

  it('delete existing lesson', async () => {
    await store.save(makeLessonFixture());
    expect(await store.delete('test-id-1')).toBe(true);
    expect(await store.get('test-id-1')).toBeNull();
  });

  it('delete returns false for missing', async () => {
    expect(await store.delete('nope')).toBe(false);
  });

  it('save is upsert (INSERT OR REPLACE)', async () => {
    await store.save(makeLessonFixture());
    await store.save(makeLessonFixture({ problem: 'replaced' }));
    const got = await store.get('test-id-1');
    expect(got!.problem).toBe('replaced');
    const all = await store.list();
    expect(all).toHaveLength(1);
  });
});
