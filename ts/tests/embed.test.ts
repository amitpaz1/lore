import { describe, it, expect } from 'vitest';
import {
  serializeEmbedding,
  deserializeEmbedding,
  cosineSimilarity,
  decayFactor,
  voteFactor,
} from '../src/embed.js';

describe('serializeEmbedding / deserializeEmbedding', () => {
  it('round-trips a vector', () => {
    const vec = [0.1, 0.2, 0.3, -0.5, 1.0];
    const buf = serializeEmbedding(vec);
    expect(buf.length).toBe(vec.length * 4);
    const result = deserializeEmbedding(buf);
    for (let i = 0; i < vec.length; i++) {
      expect(result[i]).toBeCloseTo(vec[i], 5);
    }
  });

  it('handles empty vector', () => {
    const buf = serializeEmbedding([]);
    expect(buf.length).toBe(0);
    expect(deserializeEmbedding(buf)).toEqual([]);
  });
});

describe('cosineSimilarity', () => {
  it('identical vectors return 1', () => {
    const v = [1, 0, 0];
    expect(cosineSimilarity(v, v)).toBeCloseTo(1.0);
  });

  it('orthogonal vectors return 0', () => {
    expect(cosineSimilarity([1, 0], [0, 1])).toBeCloseTo(0.0);
  });

  it('opposite vectors return -1', () => {
    expect(cosineSimilarity([1, 0], [-1, 0])).toBeCloseTo(-1.0);
  });

  it('zero vector returns 0', () => {
    expect(cosineSimilarity([0, 0], [1, 1])).toBe(0);
  });
});

describe('decayFactor', () => {
  it('zero age returns 1', () => {
    expect(decayFactor(0, 30)).toBe(1.0);
  });

  it('one half-life returns 0.5', () => {
    expect(decayFactor(30, 30)).toBeCloseTo(0.5);
  });

  it('two half-lives returns 0.25', () => {
    expect(decayFactor(60, 30)).toBeCloseTo(0.25);
  });
});

describe('voteFactor', () => {
  it('no votes returns 1.0', () => {
    expect(voteFactor(0, 0)).toBe(1.0);
  });

  it('upvotes increase factor', () => {
    expect(voteFactor(5, 0)).toBe(1.5);
  });

  it('downvotes decrease factor', () => {
    expect(voteFactor(0, 5)).toBe(0.5);
  });

  it('clamps to 0.1', () => {
    expect(voteFactor(0, 100)).toBe(0.1);
  });
});
