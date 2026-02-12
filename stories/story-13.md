# Story 13: README, Examples, Test Polish

**Batch:** 8 | **Dependencies:** Story 12

## Description
Write comprehensive READMEs for both SDKs, add runnable examples, and fill test coverage gaps.

## Acceptance Criteria

1. Python README includes: badges, 5-line quickstart, full API reference, install instructions
2. TypeScript README includes: same structure as Python README
3. Python `examples/` folder with: `basic_usage.py`, `custom_embeddings.py`, `redaction_demo.py`
4. TypeScript `examples/` folder with: `basic-usage.ts`, `custom-embeddings.ts`
5. All examples are runnable (`python examples/basic_usage.py` works)
6. Test coverage > 80% for both SDKs (check with `pytest --cov` / vitest coverage)
7. Edge cases tested: empty DB, unicode text, very long text, special characters in lessons
8. Both READMEs include a "Why Lore?" section explaining the value prop

## Technical Notes
- README is the product for OSS. Spend real time on it.
- Quickstart must work with copy-paste — test it fresh
- API reference: document every public method with parameters and return types
