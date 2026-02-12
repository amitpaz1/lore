/**
 * A single lesson learned by an agent.
 * Field names use camelCase in TS but map to snake_case in SQLite for cross-compatibility.
 */
export interface Lesson {
  id: string;
  problem: string;
  resolution: string;
  context: string | null;
  tags: string[];
  confidence: number;
  source: string | null;
  project: string | null;
  embedding: Buffer | null;
  createdAt: string;
  updatedAt: string;
  expiresAt: string | null;
  upvotes: number;
  downvotes: number;
  meta: Record<string, unknown> | null;
}

/** Options for publishing a new lesson. */
export interface PublishOptions {
  problem: string;
  resolution: string;
  context?: string;
  tags?: string[];
  confidence?: number;
  source?: string;
  project?: string;
}

/** Options for listing lessons. */
export interface ListOptions {
  project?: string;
  limit?: number;
}
