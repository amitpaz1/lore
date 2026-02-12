# Story 12: TypeScript Redaction + Prompt Helper

**Batch:** 7 | **Dependencies:** Story 10

## Description
Port the redaction pipeline and prompt helper to TypeScript.

## Acceptance Criteria

1. Same 6 redaction layers as Python (API keys, emails, phones, IPs, credit cards, custom)
2. `[REDACTED:type]` format matches Python output exactly
3. Custom patterns work: `new Lore({ redactPatterns: [[/ACCT-\d+/, 'account_id']] })`
4. `new Lore({ redact: false })` disables redaction
5. `lore.asPrompt(lessons, { maxTokens: 500 })` returns formatted markdown string
6. Empty lessons returns empty string
7. Truncation includes only complete lessons
8. All redaction patterns tested with same test cases as Python SDK

## Technical Notes
- JavaScript regex is slightly different from Python — test edge cases
- Credit card Luhn check: reimplement in JS (simple algorithm)
- Phone regex: same patterns, may need adjustment for JS regex syntax
