import { test } from 'node:test';
import assert from 'node:assert/strict';
import { safeBookUrl, validateBook } from '../assets/catalogue-policy.js';

test('catalogue allows reviewed preservation URLs and local PDFs', () => {
  for (const url of ['yearbooks/YB-1984.pdf', 'https://drive.google.com/file/d/abc-123/view',
    'https://web.archive.org/web/20220505212957id_/http://pcssalumni.com/PDF/YB-1930.pdf']) {
    assert.equal(safeBookUrl(url), true, url);
  }
});

test('catalogue rejects ad redirects, scripts, credential tricks and traversal', () => {
  for (const url of ['javascript:alert(1)', 'data:text/html,ads', '//urshort.live/ads',
    'https://www.pcssalumni.com/PDF/YB-1984.pdf', 'https://urshort.live/ads',
    'https://drive.google.com.evil.example/file/d/abc/view', 'https://user@drive.google.com/file/d/abc/view',
    'https://drive.google.com/sydvgas.php', 'yearbooks/../x.pdf', 'yearbooks/%2e%2e/x.pdf',
    'https://web.archive.org/web/20220505212957id_/http://evil.example/ads.pdf']) {
    assert.equal(safeBookUrl(url), false, url);
  }
});

test('catalogue refuses HTML in year and state fields', () => {
  const book = { key: '1984', year: 1984, state: 'remote', url: 'https://drive.google.com/file/d/abc/view' };
  assert.equal(validateBook(book), book);
  assert.throws(() => validateBook({ ...book, year: '<img onerror=alert(1)>' }));
  assert.throws(() => validateBook({ ...book, state: 'remote" onmouseover="alert(1)' }));
  assert.throws(() => validateBook({ ...book, url: 'javascript:alert(1)' }));
});
