/** Raised when the remote server cannot be reached or times out. */
export class LoreConnectionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'LoreConnectionError';
  }
}

/** Raised when authentication fails (401/403). */
export class LoreAuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'LoreAuthError';
  }
}

/** Raised when a lesson is not found. */
export class LessonNotFoundError extends Error {
  readonly lessonId: string;
  constructor(lessonId: string) {
    super(`Lesson not found: ${lessonId}`);
    this.name = 'LessonNotFoundError';
    this.lessonId = lessonId;
  }
}
