# Redirect incident and archive security

## Confirmed findings — 2026-10-16

A non-executing HTTP inspection of `https://www.pcssalumni.com/`, using a mobile user agent, returned HTTP 200 with:

- a PHP warning identifying `public_html/sydvgas.php`, line 14;
- repeated meta-refresh and JavaScript `location.replace()` redirects to the advertising host `urshort.live`;
- canonical, navigation and API links rewritten to `urshort.com`.

The suspicious PHP endpoint also returned HTTP 200. These observations support the reported compromise and show that the legacy response is unsafe. They do not reveal the PHP source, initial entry point or full extent of persistence. No advertising destination was followed and no returned JavaScript was executed.

There is no `sydvgas.php`, PHP application, WordPress installation, hosting configuration or database in this repository. Its GitHub Pages publication is a separate static site. Repository fixes cannot remove a file or backdoor from the legacy web host. The legacy-host remediation below remains outstanding until its administrator performs and verifies it. Do not describe the legacy site as cleaned based on the archive changes.

## Protections implemented here

- Recovery HTTP requests validate the initial URL and every HTTP redirect. WordPress recovery is limited to the legacy API/upload paths, yearbook recovery to `/PDF/`, and Wayback recovery to `web.archive.org` capture/CDX paths. HTTPS is mandatory; an advertising redirect fails before its target is requested. Recovered bytes remain untrusted even when obtained from an allowed host.
- The build starts from a fresh `_site` directory. It rejects PHP/server-executable files, raw recovery directories, known injection indicators, external or unexpected script references, inline event handlers, meta-refresh redirects, frames, forms and base elements in published HTML. New executable features require deliberate policy review.
- Generated pages receive a Content Security Policy before any scripts. It blocks unapproved inline code, remote scripts, objects, frames, forms and external fetches. Quarto initialization scripts receive content hashes. The policy allows local scripts and inline styling needed by the current rendering. It does not make a malicious change to an allowed local script safe.
- The Quarto initializer must also match a reviewed hash for the pinned renderer, so spoofing its script element ID does not authorize new inline code. Renderer upgrades or configuration changes that alter this initializer require review and a deliberate baseline update.
- Catalogue data is checked both before generation and in the browser. Years and states are constrained, and yearbook links are restricted to local PDF paths, Google Drive file views and timestamped Wayback yearbook captures. A new storage provider requires an explicit reviewed policy change.
- Security fixtures run before deployment and in a read-only pull-request validation workflow. Publication validation independently checks that the expected CSP is present and matches the generated inline code.

Raw HTML, SVG, documents and PDFs recovered from the old host are not automatically sanitized. Keep them outside `_site`; review and transform content before publishing it. The gate is defense in depth and rejects known dangerous structures; it is not a general proof that arbitrary JavaScript or media is harmless.

GitHub Pages does not acquire server header configuration from an `.htaccess` or `_headers` file committed here. The CSP is therefore embedded in generated HTML. If a reverse proxy is added, also set an HTTP CSP and `X-Content-Type-Options: nosniff`, and use HTTP `frame-ancestors 'none'` for anti-framing protection. That directive cannot be enforced through a CSP meta tag.

## Legacy hosting cleanup — requires hosting access

Follow the [WordPress hacked-site recovery guide](https://wordpress.org/documentation/article/faq-my-site-was-hacked/) and [WordPress hardening guidance](https://developer.wordpress.org/advanced-administration/security/hardening/). Merely deleting the named file or hiding PHP warnings does not establish that the host is clean.

1. **Contain and preserve evidence.** Have the host stop serving the infected application or put a clean static maintenance page in front of it. Preserve a restricted, non-public snapshot of the filesystem, database, access/error logs and relevant scheduled jobs before cleanup. Record file hashes, owners and modification times. Blocking the public URL alone does not stop another PHP file from including it internally.
2. **Find the loading and persistence paths.** Inspect the actual `sydvgas.php` contents offline. Search the web root and relevant parent configuration for references to it, `urshort`, unexpected PHP includes and `auto_prepend_file`/`auto_append_file`. Review `index.php`, `wp-config.php`, `.htaccess`, `.user.ini`, PHP configuration, active and must-use plugins, themes, upload directories and scheduled tasks. Inspect WordPress database site/home URLs, options, injected page content and unauthorized administrators. The rewritten links warrant checking database configuration as well as files; a specific cause is not proven yet.
3. **Rebuild from trusted sources.** Replace WordPress core, plugins and themes with clean supported packages and restore reviewed content from a known-good source. Remove unknown files and unused extensions. Patch the entry point identified from logs and file review. Check other sites sharing the hosting account; a reinfecting sibling site or account-level task can undo an application-only cleanup. For migration to a static site, retire the old PHP application and writable upload execution rather than retaining an abandoned installation.
4. **Invalidate compromised access.** From a trusted device, rotate hosting, SFTP/SSH, WordPress administrator and database credentials, review authorized keys/users and regenerate WordPress salts to invalidate sessions. Remove unauthorized accounts and scheduled jobs. Do not store credentials or forensic dumps in this repository.
5. **Harden the retained host.** Apply least-privilege ownership and permissions, prevent PHP execution in upload directories using the actual web server configuration, disable unused services/extensions and the WordPress dashboard file editor where appropriate, and maintain tested backups. Turn off public error display while retaining private logs after preserving evidence. Confirm both PHP and WordPress are supported and updated.
6. **Verify before reopening.** Purge host/CDN/application caches. Check root and representative legacy pages with desktop and mobile user agents, referrers and fresh sessions; inspect HTTP headers and response bodies for redirects and rewritten links. Confirm the removed endpoint is absent, no configuration includes it, logs show no recreation, and file integrity/administrators/scheduled jobs remain clean. Continue watching for reinfection. If moving the legacy domain to the archive, the domain/DNS/hosting change must also be performed and checked separately.

## Local checks and deployment

Requirements: Node 22, Python 3.13 and Quarto 1.10.19 (the version pinned in CI).

```powershell
python -m unittest discover -s scripts -p test_security.py
node --test scripts/test-catalogue-security.mjs
node scripts/build-site.mjs
node scripts/validate-site.mjs
```

Use the protected build for publication. `quarto preview` and a direct `quarto render` are authoring tools; they do not apply the final CSP. The validator rejects an unprotected render. Do not bypass a failing check by loosening the policy without investigating the newly introduced content.

These changes must be deployed before they affect the public archive. They do not modify the remote legacy hosting account or prove that its compromise has been eradicated.
