# PCSS Alumni Digital Archive

A Quarto-powered, static and portable mirror for public material formerly hosted at
`pcssalumni.com`, published at `https://pcssalumni.github.io/`.

The first restoration pass includes:

- a responsive archive home page;
- the original 67-edition yearbook catalogue (1930, 1951–2015, with two 2002
  editions) plus separately recovered 2016 and 2017 yearbooks;
- recovered scholarship recipient lists;
- an edited school-history timeline;
- a recovery index for the former site's major sections;
- scripts to index saved PDFs and inventory/download Wayback captures;
- a GitHub Pages deployment workflow.

## Preview locally

Install [Quarto](https://quarto.org/), then preview the editable `.qmd` sources:

```powershell
quarto preview
```

Quarto rebuilds the relevant HTML page whenever a `.qmd` source changes.

Edit the matching source file for each public page (`index.qmd`,
`yearbooks.qmd`, `scholarships.qmd`, `history.qmd`, `archive.qmd`, or
`about.qmd`). Shared navigation and footer markup lives in `includes/`, while
`_quarto.yml` controls the build. Do not edit `_site/` directly; it is generated.

Build and validate the same artifact used by GitHub Pages:

Use Node 22, Python 3.13 and Quarto 1.10.19. The protected build applies the
publication Content Security Policy and rejects injected redirects and unsafe
active content. See [SECURITY.md](SECURITY.md) for the confirmed legacy-host
incident, repository protections and outstanding hosting cleanup.

```powershell
node scripts/build-site.mjs
node scripts/validate-site.mjs
```

## Add the saved yearbooks

Copy PDF files into `yearbooks/`, then regenerate the catalogue:

```powershell
node scripts/index-yearbooks.mjs
```

See `yearbooks/README.md` for naming rules. If the complete collection is larger
than GitHub Pages' 1 GB published-site limit, host the source PDFs as durable
release assets or in an archival object store and add their URLs to
`data/yearbook-sources.json`.

Example source override:

```json
{
  "1984": {
    "url": "https://example.org/pcss/YB-1984.pdf",
    "note": "Preservation master"
  }
}
```

## Recover archived web content

Create a Wayback inventory without downloading files:

```powershell
python scripts/recover-wayback.py
```

Download non-PDF public pages and assets after reviewing the inventory:

```powershell
python scripts/recover-wayback.py --download
```

PDFs require a separate explicit flag because the collection is large:

```powershell
python scripts/recover-wayback.py --download --include-pdfs --max-file-mb 60
```

For a full preservation pass, including very large files, increase the limit and
use bounded workers. Downloads stream to disk, retry failures and resume by
skipping completed targets:

```powershell
python scripts/recover-wayback.py --download --include-pdfs --max-file-mb 2048 --workers 6 --retries 3 --timeout 90
```

The Internet Archive may throttle requests or be temporarily unavailable; rerun
the script later and existing files will be skipped.

## Preservation notes

- The site is independent and is not an official school or board website.
- Historic contact forms and personal details are not restored as active data.
- The surviving live site is treated as untrusted: advertising, trackers, injected
  scripts, obsolete forms and PHP errors are not copied into the mirror.
- Keep original masters outside the repository; this mirror is a publication copy,
  not the only backup.

