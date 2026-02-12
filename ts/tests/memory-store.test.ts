import { describe, it, expect, beforeEach } from 'vitest';
import { MemoryStore } from '../src/store/memory.js';
import type { Lesson } from '../src/types.js';

function makeLessonFixture(overrides: Partial<Lesson> = {}): Lesson {
  return {
    id: 'test-id-1',
    problem: 'test problem',
    resolution: 'test resolution',
    context: null,
    tags: [],
    confidence: 0.5,
    source: null,
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

describe('MemoryStore', () => {
  let store: MemoryStore;

  beforeEach(() => {
    store = new MemoryStore();
  });

  it('save and get', async () => {
    const lesson = makeLessonFixture();
    await store.save(lesson);
    const got = await store.get('test-id-1');
    expect(got).not.toBeNull();
    expect(got!.problem).toBe('test problem');
  });

  it('get returns null for missing', async () => {
    expect(await store.get('nope')).toBeNull();
  });

  it('list returns all lessons ordered by createdAt desc', async () => {
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
    const updated = await store.update(makeLessonFixture({ problem: 'updated' }));
    expect(updated).toBe(true);
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
});
