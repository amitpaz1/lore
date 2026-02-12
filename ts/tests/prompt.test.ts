import { describe, it, expect } from 'vitest';
import { asPrompt } from '../src/prompt.js';
import type { QueryResult, Lesson } from '../src/types.js';

function makeResult(problem: string, resolution: string, confidence: number, score: number): QueryResult {
  const lesson: Lesson = {
    id: 'test-id',
    problem,
    resolution,
    context: null,
    tags: [],
    confidence,
    source: null,
    project: null,
    embedding: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    expiresAt: null,
    upvotes: 0,
    downvotes: 0,
    meta: null,
  };
  return { lesson, score };
}

describe('asPrompt', () => {
  it('returns empty string for empty array', () => {
    expect(asPrompt([])).toBe('');
  });

  it('formats a single lesson', () => {
    const results = [makeResult('rate limit', 'backoff', 0.9, 0.8)];
    const prompt = asPrompt(results);
    expect(prompt).toContain('## Relevant Lessons');
    expect(prompt).toContain('**Problem:** rate limit');
    expect(prompt).toContain('**Resolution:** backoff');
    expect(prompt).toContain('**Confidence:** 0.9');
  });

  it('sorts by score descending', () => {
    const results = [
      makeResult('low', 'low-r', 0.5, 0.3),
      makeResult('high', 'high-r', 0.9, 0.9),
    ];
    const prompt = asPrompt(results);
    const highIdx = prompt.indexOf('high');
    const lowIdx = prompt.indexOf('low');
    expect(highIdx).toBeLessThan(lowIdx);
  });

  it('truncates to maxTokens', () => {
    const results = Array.from({ length: 100 }, (_, i) =>
      makeResult(`problem ${i} ${'x'.repeat(50)}`, `resolution ${i}`, 0.5, 1 - i * 0.01),
    );
    const prompt = asPrompt(results, 100); // ~400 chars
    // Should have header + only a few lessons
    expect(prompt.length).toBeLessThan(500);
    expect(prompt).toContain('## Relevant Lessons');
  });

  it('returns empty if no lessons fit', () => {
    const results = [makeResult('x'.repeat(1000), 'y'.repeat(1000), 0.5, 0.8)];
    const prompt = asPrompt(results, 10); // ~40 chars budget
    expect(prompt).toBe('');
  });
});
