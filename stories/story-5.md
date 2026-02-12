# Story 5: Redaction Pipeline

**Batch:** 3 | **Dependencies:** Story 2

## Description
Implement the 6-layer regex redaction pipeline. Runs automatically on `publish()` before storage. Supports custom patterns.

## Acceptance Criteria

1. `lore.publish(problem="Call sk-abc123 for help")` stores `"Call [REDACTED:api_key] for help"`
2. Detects and redacts: API keys (sk-*, AKIA*, ghp_*, xoxb-*), emails, phone numbers, IPv4/v6 addresses, credit card numbers (with Luhn validation)
3. Redacted tokens use format `[REDACTED:type]` where type is: api_key, email, phone, ip_address, credit_card
4. Custom patterns work: `Lore(redact_patterns=[(r'ACCT-\d+', 'account_id')])` → `[REDACTED:account_id]`
5. `Lore(redact=False)` disables redaction entirely
6. Redaction runs on both `problem` and `resolution` fields (and `context` if present)
7. Redaction of a typical lesson takes < 5ms
8. Multiple sensitive items in one text are all caught
9. All 6 layers tested with positive and negative cases

## Technical Notes
- Single `redact(text, patterns)` function — keep it simple
- Compile regexes once at `Lore.__init__` time
- Credit card: strip spaces/dashes, check Luhn, then redact original
- Phone: handle +1-xxx-xxx-xxxx, (xxx) xxx-xxxx, international +44 etc.
- API key patterns: prefix-based (sk-, AKIA, ghp_, xoxb-, xoxp-)
