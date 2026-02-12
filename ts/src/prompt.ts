/**
 * Prompt helper — formats lessons for system prompt injection.
 * Port of Python lore.prompt.as_prompt().
 */

import type { QueryResult } from './types.js';

const HEADER = '## Relevant Lessons\n';

/**
 * Format query results into a markdown string for system prompt injection.
 *
 * @param lessons - Query results from lore.query()
 * @param maxTokens - Approximate token budget (1 token ≈ 4 chars)
 * @returns Formatted markdown string, or empty string if no lessons
 */
export function asPrompt(lessons: QueryResult[], maxTokens = 1000): string {
  if (lessons.length === 0) return '';

  const maxChars = maxTokens * 4;

  // Sort by score descending (should already be sorted, but be safe)
  const sorted = [...lessons].sort((a, b) => b.score - a.score);

  const parts: string[] = [HEADER];
  let currentLen = HEADER.length;

  for (const result of sorted) {
    const lesson = result.lesson;
    const block =
      `**Problem:** ${lesson.problem}\n` +
      `**Resolution:** ${lesson.resolution}\n` +
      `**Confidence:** ${lesson.confidence}\n`;
    const blockLen = block.length + 1; // +1 for separator newline

    if (currentLen + blockLen > maxChars) break;

    parts.push(block);
    currentLen += blockLen;
  }

  // If no lessons fit, return empty
  if (parts.length === 1) return '';

  return parts.join('\n');
}
