import type { Lesson, ListOptions } from '../types.js';

/**
 * Abstract store interface for lesson persistence.
 */
export interface Store {
  save(lesson: Lesson): Promise<void>;
  get(lessonId: string): Promise<Lesson | null>;
  list(options?: ListOptions): Promise<Lesson[]>;
  update(lesson: Lesson): Promise<boolean>;
  delete(lessonId: string): Promise<boolean>;
  close(): Promise<void>;
}
