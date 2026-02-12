/**
 * 6-layer redaction pipeline — port of Python lore.redact.
 *
 * Layers: API keys, emails, phones, IPs (v4+v6), credit cards (Luhn), custom.
 */

// ── Patterns ────────────────────────────────────────────────────────────

/** Layer 1: API keys — prefix-based */
const API_KEY = new RegExp(
  '\\b(?:' +
    'sk-[A-Za-z0-9]{20,}' +        // OpenAI
    '|AKIA[A-Z0-9]{16}' +           // AWS
    '|ghp_[A-Za-z0-9]{36,}' +       // GitHub PAT
    '|gh[sor]_[A-Za-z0-9]{36,}' +   // GitHub other
    '|xox[bp]-[A-Za-z0-9\\-]{10,}' + // Slack
  ')\\b',
  'g',
);

/** Layer 2: Email addresses */
const EMAIL = /\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b/g;

/** Layer 3: Phone numbers (international formats) */
const PHONE = new RegExp(
  '(?<!\\d)' +
  '(?:' +
    '\\+\\d{1,3}[\\s\\-]?' +
  ')?' +
  '(?:' +
    '\\(\\d{2,4}\\)[\\s\\-]?' +
    '|\\d{2,4}[\\s\\-]' +
  ')' +
  '\\d{3,4}[\\s\\-]?\\d{3,4}' +
  '(?!\\d)',
  'g',
);

/** Layer 4a: IPv4 */
const IPV4 = new RegExp(
  '\\b(?:(?:25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}' +
  '(?:25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\b',
  'g',
);

/** Layer 4b: IPv6 */
const IPV6 = new RegExp(
  '(?:' +
    '\\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\\b' +
    '|\\b(?:[0-9a-fA-F]{1,4}:){1,7}:' +
    '|::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}\\b' +
    '|\\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\\b' +
    '|::1\\b' +
  ')',
  'g',
);

/** Layer 5: Credit card (broad match, validated with Luhn) */
const CREDIT_CARD = /\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{1,7}\b/g;

// ── Luhn ────────────────────────────────────────────────────────────────

function luhnCheck(number: string): boolean {
  const digits = number.split('').map(Number);
  let checksum = 0;
  for (let i = digits.length - 1, alt = false; i >= 0; i--, alt = !alt) {
    let d = digits[i];
    if (alt) {
      d *= 2;
      if (d > 9) d -= 9;
    }
    checksum += d;
  }
  return checksum % 10 === 0;
}

// ── Pipeline ────────────────────────────────────────────────────────────

export type PatternDef = [RegExp | string, string];

export class RedactionPipeline {
  private readonly ccPattern: RegExp;
  private readonly simpleLayers: Array<[RegExp, string]>;
  private readonly customLayers: Array<[RegExp, string]>;

  constructor(customPatterns?: PatternDef[]) {
    // We clone global regexes so lastIndex resets per call
    this.ccPattern = new RegExp(CREDIT_CARD.source, CREDIT_CARD.flags);
    this.simpleLayers = [
      [new RegExp(API_KEY.source, API_KEY.flags), '[REDACTED:api_key]'],
      [new RegExp(EMAIL.source, EMAIL.flags), '[REDACTED:email]'],
      [new RegExp(PHONE.source, PHONE.flags), '[REDACTED:phone]'],
      [new RegExp(IPV4.source, IPV4.flags), '[REDACTED:ip_address]'],
      [new RegExp(IPV6.source, IPV6.flags), '[REDACTED:ip_address]'],
    ];
    this.customLayers = [];
    if (customPatterns) {
      for (const [pat, label] of customPatterns) {
        const re = typeof pat === 'string' ? new RegExp(pat, 'g') : new RegExp(pat.source, pat.flags.includes('g') ? pat.flags : pat.flags + 'g');
        this.customLayers.push([re, `[REDACTED:${label}]`]);
      }
    }
  }

  run(text: string): string {
    // Credit cards first (before phone to avoid conflicts)
    text = text.replace(new RegExp(this.ccPattern.source, this.ccPattern.flags), (match) => {
      const digitsOnly = match.replace(/[\s\-]/g, '');
      if (digitsOnly.length < 13 || digitsOnly.length > 19) return match;
      return luhnCheck(digitsOnly) ? '[REDACTED:credit_card]' : match;
    });

    for (const [pattern, replacement] of this.simpleLayers) {
      text = text.replace(new RegExp(pattern.source, pattern.flags), replacement);
    }

    for (const [pattern, replacement] of this.customLayers) {
      text = text.replace(new RegExp(pattern.source, pattern.flags), replacement);
    }

    return text;
  }
}

/** Convenience function: redact sensitive data from text. */
export function redact(text: string, pipeline?: RedactionPipeline): string {
  const p = pipeline ?? new RedactionPipeline();
  return p.run(text);
}
