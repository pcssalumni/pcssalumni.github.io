// Shared by the browser and publication validator. External yearbook hosts are
// intentionally opt-in; add a host only after reviewing its preservation role.
export function safeBookUrl(value) {
  if (typeof value !== 'string' || !value || /[\s\\\x00-\x1f]/.test(value)) return false;
  if (/^yearbooks\/(?:[A-Za-z0-9_%-]+\/)*[A-Za-z0-9_.%+-]+\.pdf$/i.test(value)) {
    try { return !decodeURIComponent(value).split('/').some(part => part === '..' || /[\\\x00-\x1f]/.test(part)); }
    catch { return false; }
  }
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.port) return false;
    if (url.hostname === 'drive.google.com') return /^\/file\/d\/[A-Za-z0-9_-]+\/view$/.test(url.pathname);
    if (url.hostname === 'web.archive.org') return /^\/web\/\d{14}(?:id_)?\/https?:\/\/(?:www\.)?pcssalumni\.com(?::80)?\/PDF\/[^?#]+\.pdf$/i.test(url.pathname);
    return false;
  } catch { return false; }
}

export function validateBook(book) {
  if (!book || typeof book !== 'object' || !Number.isInteger(book.year) || book.year < 1900 || book.year > 2100) throw new Error('Invalid yearbook year');
  if (!['local', 'remote', 'wayback', 'preserved', 'missing'].includes(book.state)) throw new Error('Invalid yearbook state');
  for (const field of ['key', 'title', 'school', 'edition']) {
    if (book[field] !== undefined && typeof book[field] !== 'string') throw new Error(`Invalid yearbook ${field}`);
  }
  if (book.url !== undefined && !safeBookUrl(book.url)) throw new Error(`Unsafe yearbook URL: ${book.key}`);
  return book;
}
