#!/usr/bin/env node
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { validateBook } from '../assets/catalogue-policy.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const site = path.join(root, '_site');
execFileSync('python', [path.join(root, 'scripts/secure_site.py'), site], { stdio: 'inherit' });
const htmlFiles = (await fs.readdir(site)).filter((file) => file.endsWith('.html'));
const missing = [];

for (const file of htmlFiles) {
  const html = await fs.readFile(path.join(site, file), 'utf8');
  const references = [...html.matchAll(/(?:href|src)="([^"]+)"/g)].map((match) => match[1]);
  for (const reference of references) {
    if (/^https?:\/\/(?:www\.)?urshort\./i.test(reference)) {
      missing.push(`${file}: unsafe redirect host ${reference}`);
      continue;
    }
    if (/^https?:\/\/(?:www\.)?pcssalumni\.com(?:\/|$)/i.test(reference)) {
      missing.push(`${file}: direct link to compromised legacy host ${reference}`);
      continue;
    }
    if (/^(?:https?:|mailto:|tel:|#)/.test(reference)) continue;
    const clean = reference.split(/[?#]/)[0].replace(/^\/+/, '');
    if (!clean) continue;
    const target = path.resolve(site, clean);
    if (!target.startsWith(site) || !(await fs.stat(target).catch(() => null))) missing.push(`${file}: ${reference}`);
  }
}

const manifest = JSON.parse(await fs.readFile(path.join(site, 'data/yearbooks.json'), 'utf8'));
const keys = new Set(manifest.books.map((book) => book.key));
if (manifest.books.length !== 69) missing.push(`Expected 69 yearbook editions, found ${manifest.books.length}`);
if (keys.size !== manifest.books.length) missing.push('Duplicate yearbook keys found');
for (const book of manifest.books) {
  try { validateBook(book); } catch (error) { missing.push(`${book.key}: ${error.message}`); }
  if (/^https?:\/\/(?:www\.)?(?:pcssalumni\.com|urshort\.)/i.test(book.url || '')) {
    missing.push(`${book.key}: unsafe yearbook host ${book.url}`);
  }
}

if (missing.length) {
  console.error('Validation failed:\n' + missing.map((item) => `- ${item}`).join('\n'));
  process.exitCode = 1;
} else {
  console.log(`Validated ${htmlFiles.length} HTML pages and ${manifest.books.length} yearbook editions.`);
}

