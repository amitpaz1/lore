import type { Store } from './base.js';
import type { Lesson, ListOptions } from '../types.js';

function cloneLesson(lesson: Lesson): Lesson {
  return {
    ...lesson,
    tags: [...lesson.tags],
    meta: lesson.meta ? { ...lesson.meta } : null,
  };
}

/**
 * In-memory store for testing. Uses a Map keyed by lesson ID.
 */
export class MemoryStore implements Store {
  private lessons = new Map<string, Lesson>();

  async save(lesson: Lesson): Promise<void> {
    this.lessons.set(lesson.id, cloneLesson(lesson));
  }

  async get(lessonId: string): Promise<Lesson | null> {
    const lesson = this.lessons.get(lessonId);
    return lesson ? cloneLesson(lesson) : null;
  }

  async list(options?: ListOptions): Promise<Lesson[]> {
    let results = Array.from(this.lessons.values());

    if (options?.project != null) {
      results = results.filter((l) => l.project === options.project);
    }

    // Sort by createdAt descending
    results.sort((a, b) => b.createdAt.localeCompare(a.createdAt));

    if (options?.limit != null) {
      results = results.slice(0, options.limit);
    }

    return results.map(cloneLesson);
  }

  async update(lesson: Lesson): Promise<boolean> {
    if (!this.lessons.has(lesson.id)) return false;
    this.lessons.set(lesson.id, cloneLesson(lesson));
    return true;
  }

  async delete(lessonId: string): Promise<boolean> {
    return this.lessons.delete(lessonId);
  }

  async close(): Promise<void> {
    this.lessons.clear();
  }
}
