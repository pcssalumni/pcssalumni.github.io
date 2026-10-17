#!/usr/bin/env node
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateBook } from '../assets/catalogue-policy.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const yearbookDir = path.join(root, 'yearbooks');
const dataDir = path.join(root, 'data');
const sourcesPath = path.join(dataDir, 'yearbook-sources.json');
const driveLinksPath = path.join(dataDir, 'yearbook-drive-links.json');
const preservationPath = path.join(dataDir, 'preservation-status.json');
const outputPath = path.join(dataDir, 'yearbooks.json');

const expected = [
  { key: '1930', year: 1930 },
  ...Array.from({ length: 51 }, (_, index) => ({ key: String(1951 + index), year: 1951 + index })),
  { key: '2002-junior', year: 2002, edition: 'Junior yearbook' },
  { key: '2002-senior', year: 2002, edition: 'Senior yearbook' },
  ...Array.from({ length: 13 }, (_, index) => ({ key: String(2003 + index), year: 2003 + index })),
  { key: '2016', year: 2016, edition: 'Recovered edition' },
  { key: '2017', year: 2017, edition: 'Recovered edition' },
];

const defaultFilename = (book) => book.year === 2002
  ? `YB-2002-${book.edition.startsWith('Junior') ? 'Junior' : 'Senior'}.pdf`
  : `YB-${book.year}.pdf`;

async function walk(directory) {
  let entries = [];
  try { entries = await fs.readdir(directory, { withFileTypes: true }); }
  catch (error) { if (error.code === 'ENOENT') return []; throw error; }
  const files = [];
  for (const entry of entries) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await walk(absolute));
    else if (entry.isFile() && entry.name.toLowerCase().endsWith('.pdf')) files.push(absolute);
  }
  return files;
}

function identify(file) {
  const name = path.basename(file, path.extname(file));
  const match = name.match(/(?:19|20)\d{2}/);
  if (!match) return null;
  const year = Number(match[0]);
  if (year === 2002) {
    if (/junior|jr\b/i.test(name)) return '2002-junior';
    if (/senior|sr\b/i.test(name)) return '2002-senior';
  }
  return String(year);
}

async function main() {
  await fs.mkdir(dataDir, { recursive: true });
  await fs.mkdir(yearbookDir, { recursive: true });
  const sources = JSON.parse(await fs.readFile(sourcesPath, 'utf8').catch(() => '{}'));
  const driveLinks = JSON.parse(await fs.readFile(driveLinksPath, 'utf8').catch(() => '{}'));
  const preservation = JSON.parse(await fs.readFile(preservationPath, 'utf8').catch(() => '{}'));
  const localFiles = new Map();
  for (const file of await walk(yearbookDir)) {
    const key = identify(file);
    if (!key) continue;
    const stats = await fs.stat(file);
    const relative = path.relative(root, file).split(path.sep).join('/');
    localFiles.set(key, { url: relative, bytes: stats.size });
  }

  const books = expected.map((book) => {
    const local = localFiles.get(book.key);
    const source = sources[book.key] || {};
    const filename = source.originalFilename || defaultFilename(book);
    const school = book.year < 1956 ? 'PCHS' : 'PCSS';
    if (local) return { ...book, title: `${book.year} yearbook`, school, state: 'local', ...local };
    if (driveLinks[book.key]) return { ...book, title: `${book.year} yearbook`, school, state: 'remote', url: driveLinks[book.key], note: 'Public Google Drive preservation copy.' };
    if (source.url) return { ...book, title: `${book.year} yearbook`, school, state: source.state || 'remote', url: source.url, note: source.note || undefined };
    if (preservation.yearbooks?.complete) return { ...book, title: `${book.year} yearbook`, school, state: 'preserved', note: source.note || 'Preservation master verified locally; public hosting is pending.' };
    return { ...book, title: `${book.year} yearbook`, school, state: 'missing', note: 'The catalogue entry survives, but no public copy is currently linked.' };
  });

  const manifest = {
    generated: new Date().toISOString(),
    description: 'Port Credit High School / Port Credit Secondary School yearbook catalogue recovered from pcssalumni.com.',
    books,
  };
  books.forEach(validateBook);
  await fs.writeFile(outputPath, `${JSON.stringify(manifest, null, 2)}\n`);
  const localCount = books.filter((book) => book.state === 'local').length;
  const onlineCount = books.filter((book) => book.url).length;
  const preservedCount = books.filter((book) => book.state === 'preserved').length;
  console.log(`Indexed ${books.length} editions (${onlineCount + localCount} available, ${preservedCount} preserved pending hosting).`);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });

