import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { Lore } from '../src/lore.js';
import { MemoryStore } from '../src/store/memory.js';
import { SqliteStore } from '../src/store/sqlite.js';
import { mkdtempSync, rmSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';

describe('Lore with MemoryStore', () => {
  let lore: Lore;

  beforeEach(() => {
    lore = new Lore({ store: new MemoryStore() });
  });

  afterEach(async () => {
    await lore.close();
  });

  it('publish returns a ULID', async () => {
    const id = await lore.publish({ problem: 'p', resolution: 'r' });
    expect(id).toMatch(/^[0-9A-Z]{26}$/);
  });

  it('publish and get round-trip', async () => {
    const id = await lore.publish({
      problem: 'rate limit',
      resolution: 'backoff',
      tags: ['api'],
      confidence: 0.9,
    });
    const lesson = await lore.get(id);
    expect(lesson).not.toBeNull();
    expect(lesson!.problem).toBe('rate limit');
    expect(lesson!.tags).toEqual(['api']);
    expect(lesson!.confidence).toBe(0.9);
  });

  it('get returns null for missing', async () => {
    expect(await lore.get('nope')).toBeNull();
  });

  it('list returns lessons', async () => {
    await lore.publish({ problem: 'p1', resolution: 'r1' });
    await lore.publish({ problem: 'p2', resolution: 'r2' });
    const all = await lore.list();
    expect(all).toHaveLength(2);
  });

  it('list filters by project', async () => {
    await lore.publish({ problem: 'p1', resolution: 'r1', project: 'a' });
    await lore.publish({ problem: 'p2', resolution: 'r2', project: 'b' });
    const filtered = await lore.list({ project: 'a' });
    expect(filtered).toHaveLength(1);
    expect(filtered[0].project).toBe('a');
  });

  it('delete removes lesson', async () => {
    const id = await lore.publish({ problem: 'p', resolution: 'r' });
    expect(await lore.delete(id)).toBe(true);
    expect(await lore.get(id)).toBeNull();
  });

  it('delete returns false for missing', async () => {
    expect(await lore.delete('nope')).toBe(false);
  });

  it('publish rejects invalid confidence', async () => {
    await expect(lore.publish({ problem: 'p', resolution: 'r', confidence: 1.5 }))
      .rejects.toThrow(RangeError);
    await expect(lore.publish({ problem: 'p', resolution: 'r', confidence: -0.1 }))
      .rejects.toThrow(RangeError);
  });

  it('publish uses project from constructor', async () => {
    const projLore = new Lore({ store: new MemoryStore(), project: 'my-proj' });
    const id = await projLore.publish({ problem: 'p', resolution: 'r' });
    const lesson = await projLore.get(id);
    expect(lesson!.project).toBe('my-proj');
    await projLore.close();
  });

  it('publish option project overrides constructor project', async () => {
    const projLore = new Lore({ store: new MemoryStore(), project: 'default' });
    const id = await projLore.publish({ problem: 'p', resolution: 'r', project: 'override' });
    const lesson = await projLore.get(id);
    expect(lesson!.project).toBe('override');
    await projLore.close();
  });
});

describe('Lore with SqliteStore', () => {
  let lore: Lore;
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'lore-test-'));
    lore = new Lore({ dbPath: join(tmpDir, 'test.db') });
  });

  afterEach(async () => {
    await lore?.close();
    rmSync(tmpDir, { recursive: true, force: true });
  });

  it('full CRUD cycle', async () => {
    const id = await lore.publish({
      problem: 'timeout',
      resolution: 'increase to 120s',
      tags: ['api'],
      confidence: 0.85,
    });

    // Read
    const lesson = await lore.get(id);
    expect(lesson!.problem).toBe('timeout');

    // List
    const all = await lore.list();
    expect(all).toHaveLength(1);

    // Delete
    expect(await lore.delete(id)).toBe(true);
    expect(await lore.list()).toHaveLength(0);
  });

  it('default db path creates ~/.lore/default.db', async () => {
    // Just test that constructor doesn't throw with defaults
    const defaultLore = new Lore();
    const id = await defaultLore.publish({ problem: 'p', resolution: 'r' });
    expect(id).toBeTruthy();
    await defaultLore.close();
  });
});
