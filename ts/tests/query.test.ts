import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { Lore } from '../src/lore.js';
import { MemoryStore } from '../src/store/memory.js';
import type { EmbeddingFn } from '../src/types.js';

/**
 * Fake embedding function for deterministic testing.
 * Maps known words to different dimensions of a 4-dim vector.
 */
function fakeEmbedder(): EmbeddingFn {
  return (text: string) => {
    const lower = text.toLowerCase();
    const vec = [0, 0, 0, 0];
    if (lower.includes('rate') || lower.includes('limit') || lower.includes('throttle')) vec[0] = 1;
    if (lower.includes('timeout') || lower.includes('slow')) vec[1] = 1;
    if (lower.includes('auth') || lower.includes('token') || lower.includes('permission')) vec[2] = 1;
    if (lower.includes('database') || lower.includes('sql') || lower.includes('query')) vec[3] = 1;
    // Normalize
    const norm = Math.sqrt(vec.reduce((s, v) => s + v * v, 0));
    return norm > 0 ? vec.map((v) => v / norm) : [0.25, 0.25, 0.25, 0.25];
    };
}

describe('Lore.query()', () => {
  let lore: Lore;

  beforeEach(async () => {
    lore = new Lore({
      store: new MemoryStore(),
      embeddingFn: fakeEmbedder(),
      redact: false,
    });

    await lore.publish({ problem: 'rate limit errors', resolution: 'add exponential backoff', tags: ['api'], confidence: 0.9 });
    await lore.publish({ problem: 'timeout on large queries', resolution: 'increase timeout to 120s', tags: ['api', 'database'], confidence: 0.8 });
    await lore.publish({ problem: 'auth token expired', resolution: 'refresh token before expiry', tags: ['auth'], confidence: 0.7 });
  });

  afterEach(async () => {
    await lore.close();
  });

  it('returns results ranked by similarity', async () => {
    const results = await lore.query('rate limiting');
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].lesson.problem).toContain('rate limit');
    expect(results[0].score).toBeGreaterThan(0);
  });

  it('filters by tags', async () => {
    const results = await lore.query('timeout', { tags: ['auth'] });
    expect(results.every((r) => r.lesson.tags.includes('auth'))).toBe(true);
  });

  it('respects limit', async () => {
    const results = await lore.query('api issues', { limit: 1 });
    expect(results.length).toBeLessThanOrEqual(1);
  });

  it('respects minConfidence', async () => {
    const results = await lore.query('auth', { minConfidence: 0.8 });
    expect(results.every((r) => r.lesson.confidence >= 0.8)).toBe(true);
  });

  it('throws without embeddingFn', async () => {
    const noEmbedLore = new Lore({ store: new MemoryStore(), redact: false });
    await expect(noEmbedLore.query('test')).rejects.toThrow('embeddingFn');
    await noEmbedLore.close();
  });

  it('returns empty for no matches', async () => {
    const emptyLore = new Lore({
      store: new MemoryStore(),
      embeddingFn: fakeEmbedder(),
      redact: false,
    });
    const results = await emptyLore.query('anything');
    expect(results).toEqual([]);
    await emptyLore.close();
  });
});

describe('Lore.upvote() / downvote()', () => {
  let lore: Lore;

  beforeEach(() => {
    lore = new Lore({ store: new MemoryStore(), redact: false });
  });

  afterEach(async () => {
    await lore.close();
  });

  it('upvote increments', async () => {
    const id = await lore.publish({ problem: 'p', resolution: 'r' });
    await lore.upvote(id);
    await lore.upvote(id);
    const lesson = await lore.get(id);
    expect(lesson!.upvotes).toBe(2);
  });

  it('downvote increments', async () => {
    const id = await lore.publish({ problem: 'p', resolution: 'r' });
    await lore.downvote(id);
    const lesson = await lore.get(id);
    expect(lesson!.downvotes).toBe(1);
  });

  it('upvote throws for missing lesson', async () => {
    await expect(lore.upvote('nonexistent')).rejects.toThrow('not found');
  });
});

describe('Lore with redaction', () => {
  let lore: Lore;

  beforeEach(() => {
    lore = new Lore({ store: new MemoryStore() });
  });

  afterEach(async () => {
    await lore.close();
  });

  it('redacts on publish', async () => {
    const id = await lore.publish({
      problem: 'API key sk-abcdefghijklmnopqrst123 leaked',
      resolution: 'rotate key',
    });
    const lesson = await lore.get(id);
    expect(lesson!.problem).toContain('[REDACTED:api_key]');
    expect(lesson!.problem).not.toContain('sk-');
  });

  it('redact: false disables redaction', async () => {
    const noRedactLore = new Lore({ store: new MemoryStore(), redact: false });
    const id = await noRedactLore.publish({
      problem: 'API key sk-abcdefghijklmnopqrst123 is here',
      resolution: 'ok',
    });
    const lesson = await noRedactLore.get(id);
    expect(lesson!.problem).toContain('sk-');
    await noRedactLore.close();
  });

  it('custom redaction patterns work', async () => {
    const customLore = new Lore({
      store: new MemoryStore(),
      redactPatterns: [[/ACCT-\d+/, 'account_id']],
    });
    const id = await customLore.publish({
      problem: 'account ACCT-12345 has error',
      resolution: 'fix it',
    });
    const lesson = await customLore.get(id);
    expect(lesson!.problem).toContain('[REDACTED:account_id]');
    await customLore.close();
  });
});

describe('Lore.asPrompt()', () => {
  it('delegates to prompt helper', () => {
    const lore = new Lore({ store: new MemoryStore(), redact: false });
    const result = lore.asPrompt([]);
    expect(result).toBe('');
  });
});
