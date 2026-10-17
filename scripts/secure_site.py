"""Reject active legacy content and apply a restrictive publication CSP.

This gate is defense in depth, not a malware detector or a substitute for
reviewing source changes. Raw recovery files must never be published.
"""
import argparse
import base64
import hashlib
import html
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

OWN_SCRIPTS = {'assets/site.js', 'assets/yearbooks.js', 'assets/catalogue-policy.js'}
QUARTO_SCRIPTS = {
    'site_libs/clipboard/clipboard.min.js', 'site_libs/quarto-html/tabby.min.js',
    'site_libs/quarto-html/popper.min.js', 'site_libs/quarto-html/tippy.umd.min.js',
    'site_libs/quarto-html/anchor.min.js',
}
CSP_MARKER = '<meta http-equiv="Content-Security-Policy"'
# Reviewed initialization produced by the pinned Quarto 1.10.19 renderer for
# this project with anchor-sections disabled. A matching element ID alone must
# not authorize injected code.
QUARTO_INITIALIZER_SHA256 = '6156488a629d9ca1b6d3f8ec4f2e8f6bcb83ff6c18e477cad120c423bfd278c1'


def safe_reference(value):
    value = html.unescape(value).strip()
    if any(ord(c) < 32 for c in value) or '\\' in value:
        raise ValueError('Control character or backslash in URL')
    parsed = urlsplit(value)
    if parsed.scheme and parsed.scheme not in ('https', 'mailto', 'tel'):
        raise ValueError('Unsafe URL scheme')
    if parsed.netloc:
        host = (parsed.hostname or '').lower()
        if parsed.scheme != 'https' or parsed.username or parsed.password:
            raise ValueError('External URLs require HTTPS without credentials')
        if host == 'pcssalumni.com' or host.endswith('.pcssalumni.com') or re.search(r'(^|\.)urshort\.', host):
            raise ValueError('Link to compromised legacy or advertising host')
    if re.search(r'(?i)sydvgas|\.(?:php\d*|phtml|phar)(?:[/.?]|$)', unquote(parsed.path)):
        raise ValueError('PHP or known injection target in public URL')


class PageAudit(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inline_scripts = []
        self.script = None
        self.policies = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('base', 'iframe', 'object', 'embed', 'form'):
            raise ValueError(f'Unsupported active element: {tag}')
        for name, value in attrs.items():
            if name.startswith('on') or name in ('srcdoc', 'ping'):
                raise ValueError(f'Unsafe HTML attribute: {name}')
            if name in ('href', 'src', 'action', 'formaction', 'poster', 'data') and value:
                safe_reference(value)
        if tag == 'meta':
            directive = attrs.get('http-equiv', '').lower()
            if directive == 'refresh':
                raise ValueError('Meta refresh redirects are forbidden')
            if directive == 'content-security-policy':
                self.policies.append(attrs.get('content', ''))
        if tag == 'script':
            src = attrs.get('src')
            if src:
                parsed = urlsplit(src)
                if parsed.netloc or parsed.scheme:
                    raise ValueError('External scripts are forbidden')
                local = parsed.path.removeprefix('./').removeprefix('/')
                if local not in OWN_SCRIPTS | QUARTO_SCRIPTS:
                    raise ValueError(f'Unexpected script: {src}')
                if '..' in local.split('/'):
                    raise ValueError('Script path traversal')
                self.script = None
            else:
                # Quarto owns its generated initialization script. Any authored
                # application code belongs in a reviewed external module.
                if attrs.get('id') != 'quarto-html-after-body':
                    raise ValueError('Unexpected inline script')
                self.script = ''

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        if self.script is not None:
            self.script += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            if hashlib.sha256(self.script.encode()).hexdigest() != QUARTO_INITIALIZER_SHA256:
                raise ValueError('Unrecognized Quarto initializer; review renderer/config changes')
            self.inline_scripts.append(self.script)
            self.script = None


def policy_for(scripts):
    hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() + "'" for s in scripts]
    return "; ".join([
        "default-src 'none'", "script-src 'self' " + ' '.join(hashes),
        "style-src 'self' 'unsafe-inline'", "img-src 'self' data:",
        "font-src 'self'", "connect-src 'self'", "object-src 'none'",
        "base-uri 'none'", "form-action 'none'", "frame-src 'none'",
        "upgrade-insecure-requests",
    ])


def audit_tree(site, write_csp=False):
    pages = 0
    for file in sorted(site.rglob('*')):
        if file.is_symlink():
            raise ValueError(f'Symbolic link in publication: {file}')
        if not file.is_file():
            continue
        relative = file.relative_to(site).as_posix()
        if re.search(r'(?i)\.(php\d*|phtml|phar|cgi|py|asp|aspx|jsp)(\.|$)', file.name) or file.name.lower() in ('.htaccess', '.user.ini'):
            raise ValueError(f'Server-executable/config file in publication: {relative}')
        if relative.startswith(('legacy/', 'scripts/')):
            raise ValueError(f'Private recovery/source directory in publication: {relative}')
        if file.suffix not in ('.html', '.js', '.mjs', '.css', '.svg'):
            continue
        text = file.read_text(encoding='utf-8')
        if re.search(r'(?i)sydvgas|urshort\.|<\?(?:php|=)', text):
            raise ValueError(f'Known injection indicator in {relative}')
        if file.suffix == '.svg':
            if re.search(r'<\s*(?:script|foreignObject)\b', text, re.I):
                raise ValueError(f'Active SVG content in {relative}')
            PageAudit().feed(text)
        if file.suffix != '.html':
            continue
        parser = PageAudit()
        parser.feed(text)
        policy = policy_for(parser.inline_scripts)
        if write_csp:
            text = re.sub(r'<meta\s+http-equiv="Content-Security-Policy"[^>]*>\s*', '', text, flags=re.I)
            if not re.search(r'<head\b[^>]*>', text, re.I):
                raise ValueError(f'No head element in {relative}')
            tag = CSP_MARKER + ' content="' + html.escape(policy, quote=True) + '">'
            text = re.sub(r'(<head\b[^>]*>)', lambda m: m[1] + '\n' + tag, text, count=1, flags=re.I)
            file.write_text(text, encoding='utf-8')
        elif parser.policies != [policy]:
            raise ValueError(f'Missing or unexpected security policy in {relative}; run the protected build')
        pages += 1
    if not pages:
        raise ValueError('No HTML pages to audit')
    return pages


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site', nargs='?', type=Path, default=Path(__file__).resolve().parent.parent / '_site')
    parser.add_argument('--write-csp', action='store_true')
    args = parser.parse_args()
    try:
        print(f'Security checked {audit_tree(args.site, args.write_csp)} HTML pages.')
    except (ValueError, OSError) as error:
        parser.exit(1, f'Security validation failed: {error}\n')
