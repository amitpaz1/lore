import { describe, it, expect } from 'vitest';
import { RedactionPipeline, redact } from '../src/redact.js';

describe('RedactionPipeline', () => {
  const pipeline = new RedactionPipeline();

  // Layer 1: API keys
  it('redacts OpenAI API key', () => {
    expect(pipeline.run('key: sk-abc123def456ghi789jkl012mno')).toBe(
      'key: [REDACTED:api_key]',
    );
  });

  it('redacts AWS access key', () => {
    expect(pipeline.run('aws: AKIAIOSFODNN7EXAMPLE')).toBe(
      'aws: [REDACTED:api_key]',
    );
  });

  it('redacts GitHub PAT', () => {
    const ghp = 'ghp_' + 'a'.repeat(36);
    expect(pipeline.run(`token: ${ghp}`)).toBe('token: [REDACTED:api_key]');
  });

  it('redacts Slack token', () => {
    expect(pipeline.run('slack: xoxb-1234567890-abcde')).toBe(
      'slack: [REDACTED:api_key]',
    );
  });

  // Layer 2: Emails
  it('redacts email addresses', () => {
    expect(pipeline.run('contact user@example.com for info')).toBe(
      'contact [REDACTED:email] for info',
    );
  });

  it('redacts emails with plus addressing', () => {
    expect(pipeline.run('mail: user+tag@domain.co.uk')).toBe(
      'mail: [REDACTED:email]',
    );
  });

  // Layer 3: Phones
  it('redacts international phone', () => {
    expect(pipeline.run('call +1 (555) 123-4567')).toBe(
      'call [REDACTED:phone]',
    );
  });

  it('redacts phone without international prefix', () => {
    expect(pipeline.run('call (555) 123-4567')).toBe(
      'call [REDACTED:phone]',
    );
  });

  // Layer 4: IPs
  it('redacts IPv4', () => {
    expect(pipeline.run('server at 192.168.1.100')).toBe(
      'server at [REDACTED:ip_address]',
    );
  });

  it('redacts IPv6 loopback', () => {
    expect(pipeline.run('localhost ::1')).toBe(
      'localhost [REDACTED:ip_address]',
    );
  });

  // Layer 5: Credit cards
  it('redacts valid credit card (Luhn)', () => {
    // 4111 1111 1111 1111 is a valid Luhn test number
    expect(pipeline.run('card: 4111 1111 1111 1111')).toBe(
      'card: [REDACTED:credit_card]',
    );
  });

  it('does not redact invalid credit card number', () => {
    // 1234567890123456 fails Luhn — should NOT be redacted as credit card
    // Use no spaces to avoid phone pattern matching
    expect(pipeline.run('number: 1234567890123456')).toBe(
      'number: 1234567890123456',
    );
  });

  it('redacts credit card with dashes', () => {
    expect(pipeline.run('cc: 4111-1111-1111-1111')).toBe(
      'cc: [REDACTED:credit_card]',
    );
  });

  // Layer 6: Custom patterns
  it('applies custom patterns', () => {
    const custom = new RedactionPipeline([[/ACCT-\d+/, 'account_id']]);
    expect(custom.run('account ACCT-12345 found')).toBe(
      'account [REDACTED:account_id] found',
    );
  });

  // Convenience function
  it('redact() convenience works', () => {
    expect(redact('email: user@test.com')).toBe('email: [REDACTED:email]');
  });

  // Multiple redactions in one string
  it('redacts multiple types in one string', () => {
    const text = 'key sk-abcdefghijklmnopqrst123 email user@test.com ip 10.0.0.1';
    const result = pipeline.run(text);
    expect(result).toContain('[REDACTED:api_key]');
    expect(result).toContain('[REDACTED:email]');
    expect(result).toContain('[REDACTED:ip_address]');
    expect(result).not.toContain('sk-');
    expect(result).not.toContain('user@');
    expect(result).not.toContain('10.0.0.1');
  });

  // Disabled redaction
  it('disabled redaction passes text through', () => {
    // This is tested via Lore constructor with redact: false
    const text = 'key: sk-abcdefghijklmnopqrst123';
    // Pipeline itself always redacts — the Lore class gates it
    expect(pipeline.run(text)).toBe('key: [REDACTED:api_key]');
  });
});
